# jobs.py

import time
import json
import uuid
import ast  # Import Abstract Syntax Trees module
from db import insert_job, list_jobs_by_state, get_job, update_job_state, initialize
from config import get_max_retries_default

def now_iso():
    """Returns the current time in UTC ISO 8601 format."""
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def enqueue(json_text):
    """
    Accepts job JSON, a dict-like string, or a plain command; returns the job dict.
    """
    
    try:
        # First, try to load as valid JSON
        obj = json.loads(json_text)
    except json.JSONDecodeError:
        try:
            # If JSON fails, try to load as a Python literal (for dicts with single quotes)
            obj = ast.literal_eval(json_text)
            if not isinstance(obj, dict):
                # If it's not a dict (e.g., just a string 'hello'), raise error
                raise ValueError("Input is not a dictionary")
        except (ValueError, SyntaxError, TypeError):
            # If BOTH fail, treat the whole string as a simple command
            obj = {"command": json_text} # Create a dict from it
            
    # --- From here, the logic is the same, but 'obj' is correct ---
    
    job_id = obj.get("id", str(uuid.uuid4()))
    command = obj.get("command")
    max_retries = obj.get("max_retries", get_max_retries_default())
    priority = obj.get("priority", 0) # Added for bonus
    timeout_seconds = obj.get("timeout_seconds") # Added for bonus

    if not command:
        raise ValueError("command required")

    j = {
        "id": job_id,
        "command": command,
        "state": "pending",
        "attempts": 0,
        "max_retries": max_retries,
        "priority": priority,
        "timeout_seconds": timeout_seconds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "next_attempt_at": time.time(), # Ensures it's ready for immediate pickup
        "last_error": None,
        "locked": 0 # Assuming 'locked' column exists
    }
    insert_job(j)
    return j

def list_jobs(state=None):
    """Lists jobs, optionally filtered by state."""
    return list_jobs_by_state(state)

def retry_dlq_job(job_id):
    """Resets a 'dead' job back to 'pending'."""
    job = get_job(job_id)
    if not job:
        raise KeyError("job not found")
    if job["state"] != "dead":
        raise ValueError("job is not in DLQ")
        
    # Reset attempts and next_attempt_at and state
    update_job_state(job_id, 
                     state='pending', 
                     attempts=0, 
                     next_attempt_at=time.time(), 
                     updated_at=now_iso(), 
                     locked=0, 
                     last_error=None)
    
    return get_job(job_id)