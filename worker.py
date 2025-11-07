# worker.py
import subprocess
import time
import signal
import os
from db import claim_job_for_processing, update_job_state, get_conn, unlock_job, get_conn as _get_conn, get_conn as unused
from db import get_conn as conn_factory
from db import get_conn as gc
from db import get_setting
from db import initialize
from config import get_backoff_base
import threading
import sys
import sqlite3
from db import update_job_state as db_update_job_state, get_job
import math
import json
import ast

SHUTDOWN = False

def _signal_handler(signum, frame):
    global SHUTDOWN
    SHUTDOWN = True
    print(f"[worker] received signal {signum}, shutting down after current job...")

def run_with_timeout(cmd, timeout):
    """Run command with timeout"""
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stderr.decode()
    except subprocess.TimeoutExpired:
        process.kill()
        return -1, "Job timed out"

def claim_job_for_processing(timeout_seconds=5):
    """Modified to consider priority"""
    now = time.time()
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        # Order by priority DESC, then created_at
        cur.execute("""
            SELECT * FROM jobs 
            WHERE locked = 0 
            AND next_attempt_at <= ? 
            AND state IN ('pending', 'failed') 
            ORDER BY priority DESC, created_at 
            LIMIT 1
        """, (now,))
        row = cur.fetchone()
        if not row:
            conn.commit()
            return None
            
        job = dict(row)
        cur.execute(
            "UPDATE jobs SET locked = 1, state = 'processing', updated_at = ? WHERE id = ?",
            (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)), job["id"])
        )
        conn.commit()
        return job
    finally:
        conn.close()

def worker_loop(worker_id, poll_interval=1.0):
    global SHUTDOWN
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    print(f"[worker {worker_id}] starting loop, pid={os.getpid()}")
    
    while not SHUTDOWN:
        job = claim_job_for_processing()
        if not job:
            time.sleep(poll_interval)
            continue
            
        job_id = job["id"]
        command = job["command"]
        print(f"[worker {worker_id}] Processing job {job_id}: {command}")
        
        start_time = time.time()
        try:
            # Special handling for sleep command
            if command.startswith('sleep'):
                try:
                    sleep_time = int(command.split()[1]) if len(command.split()) > 1 else 1
                    time.sleep(sleep_time)
                    rc = 0
                    err = None
                except ValueError:
                    rc = 1
                    err = "Invalid sleep duration"
            else:
                # Normal command execution
                timeout = job.get('timeout_seconds')
                if timeout:
                    rc, err = run_with_timeout(command, timeout)
                else:
                    res = subprocess.run(command, shell=True, text=True, capture_output=True)
                    rc = res.returncode
                    err = res.stderr if res.stderr else None

            duration = time.time() - start_time
            
            if rc == 0:
                db_update_job_state(
                    job_id,
                    state='completed',
                    updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    locked=0,
                    execution_time=duration
                )
                print(f"[worker {worker_id}] Job {job_id} completed in {duration:.2f}s")
            else:
                attempts = job["attempts"] + 1
                if attempts >= job["max_retries"]:
                    db_update_job_state(
                        job_id,
                        state='dead',
                        attempts=attempts,
                        updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        locked=0,
                        last_error=err
                    )
                    print(f"[worker {worker_id}] Job {job_id} moved to DLQ after {attempts} attempts")
                else:
                    next_attempt = time.time() + (2 ** attempts)
                    db_update_job_state(
                        job_id,
                        state='failed',
                        attempts=attempts,
                        next_attempt_at=next_attempt,
                        updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        locked=0,
                        last_error=err
                    )
                    print(f"[worker {worker_id}] Job {job_id} failed (rc={rc}), scheduled retry in {2**attempts}s (attempt {attempts}/{job['max_retries']})")
                    
        except Exception as e:
            print(f"[worker {worker_id}] Error processing job {job_id}: {str(e)}")
            unlock_job(job_id)
            
    print(f"[worker {worker_id}] exiting loop")
