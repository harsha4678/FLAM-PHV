# queuectl.py
import click
import json
import uuid
import time
import os
from db import initialize, get_setting, set_setting, list_jobs_by_state, get_conn
from jobs import enqueue, list_jobs, retry_dlq_job
from worker import worker_loop
from config import set_backoff_base, set_max_retries, get_backoff_base, get_max_retries_default
from utils import write_pids, read_pids, stop_pids, clear_pids
from multiprocessing import Process
import signal

initialize()

@click.group()
def cli():
    """queuectl - a minimal background job queue CLI"""
    pass

@cli.command()
@click.argument('job_json', nargs=1)
def enqueue_cmd(job_json):
    """Enqueue a job. Provide a JSON string or just a command string."""
    try:
        job = enqueue(job_json)
        print("Enqueued:", job["id"])
    except Exception as e:
        print("Error enqueuing job:", e)

@cli.group()
def worker():
    """Manage worker processes"""
    pass

@worker.command("start")
@click.option('--count', default=1, help="Number of worker processes to start")
@click.option('--foreground', is_flag=True, default=False, help="Run workers in foreground (blocking)")
def worker_start(count, foreground):
    """Start worker processes."""
    procs = []
    if foreground:
        # run single loop in current process (useful for debugging)
        try:
            worker_loop("fg-1")
        except KeyboardInterrupt:
            print("Foreground worker stopped.")
        return
        
    try:
        for i in range(count):
            p = Process(target=worker_loop, args=(f"proc-{i+1}",), daemon=True)  # Changed to daemon=True
            p.start()
            procs.append(p)
            print(f"Started worker pid={p.pid}")
        
        # Save PIDs
        write_pids([p.pid for p in procs])
        print("Workers started and PIDs saved to workers.pid")
        
        # Wait for processes to complete or interrupt
        try:
            for p in procs:
                p.join()
        except KeyboardInterrupt:
            print("\nGracefully shutting down workers...")
            for p in procs:
                try:
                    p.terminate()
                    p.join(timeout=2)  # Give each process 2 seconds to shut down
                except:
                    pass
            print("Workers shutdown complete.")
            
    except Exception as e:
        print(f"Error starting workers: {e}")
        for p in procs:
            try:
                p.terminate()
            except:
                pass
        raise

@worker.command("stop")
def worker_stop():
    """Stop running workers (by PID file)."""
    stop_pids()
    print("Stop signal(s) sent.")

@cli.command()
def status():
    """Show summary of job states and active workers."""
    rows = list_jobs_by_state(None)
    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    print("Job counts by state:")
    for s in ["pending", "processing", "completed", "failed", "dead"]:
        print(f"  {s:10s}: {counts.get(s,0)}")
    pids = read_pids()
    print("Active workers (from pid file):", pids)

@cli.command()
@click.option('--state', default=None, help="Filter by state: pending/processing/completed/failed/dead")
def list_cmd(state):
    """List jobs (optionally filtered by state)."""
    jobs = list_jobs(state)
    for j in jobs:
        print(json.dumps(j))

@cli.group()
def dlq():
    """Dead Letter Queue commands"""
    pass

@dlq.command("list")
def dlq_list():
    jobs = list_jobs("dead")
    for j in jobs:
        print(json.dumps(j))

@dlq.command("retry")
@click.argument("job_id")
def dlq_retry(job_id):
    try:
        j = retry_dlq_job(job_id)
        print("Requeued:", j["id"])
    except Exception as e:
        print("Error:", e)

@cli.group()
def config():
    """Manage configuration"""
    pass

@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    if key == "max-retries":
        set_max_retries(int(value))
    elif key == "backoff-base":
        set_backoff_base(int(value))
    else:
        set_setting(key, value)
    print(f"Set {key} = {value}")

@config.command("get")
@click.argument("key")
def config_get(key):
    val = get_setting(key, None)
    print(f"{key} = {val}")

if __name__ == "__main__":
    cli()
