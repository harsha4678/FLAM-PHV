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

SHUTDOWN = False

def _signal_handler(signum, frame):
    global SHUTDOWN
    SHUTDOWN = True
    print(f"[worker] received signal {signum}, shutting down after current job...")

def worker_loop(worker_id, poll_interval=1.0):
    global SHUTDOWN
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    print(f"[worker {worker_id}] starting loop, pid={os.getpid()}")
    while not SHUTDOWN:
        try:
            job = claim_job_for_processing()
            if not job:
                time.sleep(poll_interval)
                continue
            job_id = job["id"]
            command = job["command"]
            print(f"[worker {worker_id}] Processing job {job_id}: {command}")
            # run command
            start = time.time()
            try:
                res = subprocess.run(command, shell=True)
                rc = res.returncode
            except Exception as e:
                rc = 1
                err = str(e)
            duration = time.time() - start

            if rc == 0:
                # success
                db_update_job_state(job_id, state='completed', updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), locked=0)
                print(f"[worker {worker_id}] Job {job_id} completed in {duration:.2f}s")
            else:
                # failure: schedule retry or dead
                current = get_job(job_id)
                attempts = (current["attempts"] or 0) + 1
                max_retries = current["max_retries"]
                backoff_base = get_backoff_base()
                if attempts >= max_retries:
                    # move to DLQ
                    db_update_job_state(job_id, state='dead', attempts=attempts, updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), locked=0, last_error=f"exit:{rc}")
                    print(f"[worker {worker_id}] Job {job_id} moved to DLQ after {attempts} attempts")
                else:
                    delay = backoff_base ** attempts
                    next_ts = time.time() + delay
                    db_update_job_state(job_id, state='failed', attempts=attempts, next_attempt_at=next_ts, updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), locked=0, last_error=f"exit:{rc}")
                    print(f"[worker {worker_id}] Job {job_id} failed (rc={rc}), scheduled retry in {delay}s (attempt {attempts}/{max_retries})")
        except Exception as e:
            print(f"[worker {worker_id}] Error in loop: {e}")
            time.sleep(1.0)
    print(f"[worker {worker_id}] exiting loop")
