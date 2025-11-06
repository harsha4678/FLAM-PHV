# jobs.py
import time
import json
import uuid
from db import insert_job, list_jobs_by_state, get_job, update_job_state, initialize
from config import get_max_retries_default

def now_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def enqueue(json_text):
    """
    Accepts job JSON string or plain command; returns job dict
    """
    try:
        obj = json.loads(json_text)
        job_id = obj.get("id", str(uuid.uuid4()))
        command = obj.get("command")
        max_retries = obj.get("max_retries", get_max_retries_default())
    except json.JSONDecodeError:
        # if it's not JSON, treat it as a command
        job_id = str(uuid.uuid4())
        command = json_text
        max_retries = get_max_retries_default()

    if not command:
        raise ValueError("command required")

    j = {
        "id": job_id,
        "command": command,
        "state": "pending",
        "attempts": 0,
        "max_retries": max_retries,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "next_attempt_at": time.time(),
        "last_error": None
    }
    insert_job(j)
    return j

def list_jobs(state=None):
    return list_jobs_by_state(state)

def retry_dlq_job(job_id):
    job = get_job(job_id)
    if not job:
        raise KeyError("job not found")
    if job["state"] != "dead":
        raise ValueError("job is not in DLQ")
    # reset attempts and next_attempt_at and state
    update_job_state(job_id, state='pending', attempts=0, next_attempt_at=time.time(), updated_at=now_iso(), locked=0, last_error=None)
    return get_job(job_id)
