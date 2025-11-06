# utils.py
import os
import signal
import platform

PID_FILE = "workers.pid"

def write_pids(pids):
    with open(PID_FILE, "w") as f:
        for pid in pids:
            f.write(f"{pid}\n")

def read_pids():
    try:
        with open(PID_FILE) as f:
            return [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        return []

def stop_pids():
    pids = read_pids()
    for pid in pids:
        try:
            if platform.system() == 'Windows':
                import ctypes
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                if handle:
                    ctypes.windll.kernel32.TerminateProcess(handle, -1)
                    ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"Warning: Could not terminate process {pid}: {e}")
    clear_pids()

def clear_pids():
    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass
