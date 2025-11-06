# utils.py
import os
import signal
import time

PID_FILE = "workers.pid"

def write_pids(pids):
    with open(PID_FILE, "w") as f:
        for pid in pids:
            f.write(str(pid) + "\n")

def read_pids():
    if not os.path.exists(PID_FILE):
        return []
    with open(PID_FILE, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    return [int(l) for l in lines]

def clear_pids():
    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass

def stop_pids():
    pids = read_pids()
    if not pids:
        print("No running workers found.")
        return
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to pid {pid}")
        except ProcessLookupError:
            print(f"Process {pid} not found")
    # wait a little and remove pid file
    time.sleep(0.5)
    clear_pids()
