# db.py
import sqlite3
import threading
import time
from contextlib import contextmanager

DB_FILE = "queuectl.db"
_lock = threading.Lock()

def get_conn():
    # use check_same_thread=False to allow access across threads/processes.
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn

def initialize():
    with _get_conn_cursor() as cur:
        # Create jobs table with all columns
        cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            state TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            next_attempt_at REAL NOT NULL,
            locked INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            execution_time REAL,
            priority INTEGER DEFAULT 0,
            timeout_seconds INTEGER
        )""")

        # Create settings table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # Ensure default settings exist
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('backoff_base','2')")
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('max_retries','3')")

        # Check if we need to add new columns
        cur.execute("PRAGMA table_info(jobs)")
        columns = {row['name'] for row in cur.fetchall()}
        
        # Add columns if they don't exist
        if 'execution_time' not in columns:
            cur.execute("ALTER TABLE jobs ADD COLUMN execution_time REAL")
        if 'priority' not in columns:
            cur.execute("ALTER TABLE jobs ADD COLUMN priority INTEGER DEFAULT 0")
        if 'timeout_seconds' not in columns:
            cur.execute("ALTER TABLE jobs ADD COLUMN timeout_seconds INTEGER")

@contextmanager
def _get_conn_cursor():
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

def set_setting(key, value):
    with _get_conn_cursor() as cur:
        cur.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", (key, str(value)))

def get_setting(key, default=None):
    with _get_conn_cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        r = cur.fetchone()
        return r["value"] if r else default

def insert_job(job):
    with _get_conn_cursor() as cur:
        cur.execute("""
            INSERT INTO jobs (
                id, command, state, attempts, max_retries,
                created_at, updated_at, next_attempt_at,
                locked, last_error, priority, timeout_seconds
            ) VALUES (
                :id, :command, :state, :attempts, :max_retries,
                :created_at, :updated_at, :next_attempt_at,
                :locked, :last_error, :priority, :timeout_seconds
            )
        """, job)

def list_jobs_by_state(state=None, limit=None):
    """List jobs filtered by state with optional limit"""
    with _get_conn_cursor() as cur:
        if state:
            cur.execute(
                "SELECT * FROM jobs WHERE state = ? ORDER BY created_at DESC LIMIT ?",
                (state, limit or -1)
            )
        else:
            cur.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit or -1,)
            )
        return [dict(row) for row in cur.fetchall()]

def get_job(job_id):
    with _get_conn_cursor() as cur:
        cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        r = cur.fetchone()
        return dict(r) if r else None

def update_job_state(job_id, **fields):
    # fields: state, attempts, next_attempt_at, updated_at, locked, last_error
    pairs = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values())
    values.append(job_id)
    with _get_conn_cursor() as cur:
        cur.execute(f"UPDATE jobs SET {pairs} WHERE id = ?", values)

def claim_job_for_processing(timeout_seconds=5):
    """
    Atomically find a job with state='pending' or state='failed' with next_attempt_at <= now and locked=0,
    claim it by setting locked=1 and state='processing', and return it.
    We'll use a transaction to avoid race.
    """
    now = time.time()
    conn = get_conn()
    try:
        # BEGIN IMMEDIATE to block other writers - improves claim safety
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM jobs WHERE locked = 0 AND next_attempt_at <= ? AND state IN ('pending', 'failed') ORDER BY created_at LIMIT 1",
            (now,)
        )
        row = cur.fetchone()
        if not row:
            conn.commit()
            return None
        job = dict(row)
        cur.execute("UPDATE jobs SET locked = 1, state = 'processing', updated_at = ? WHERE id = ?", (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)), job["id"]))
        conn.commit()
        return job
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def unlock_job(job_id):
    with _get_conn_cursor() as cur:
        cur.execute("UPDATE jobs SET locked = 0 WHERE id = ?", (job_id,))

def delete_job(job_id):
    with _get_conn_cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

def all_metrics():
    with _get_conn_cursor() as cur:
        # Get job counts by state
        cur.execute("""
            SELECT state, COUNT(*) as count 
            FROM jobs 
            GROUP BY state
        """)
        metrics = {row['state']: row['count'] for row in cur.fetchall()}
        
        # Get average execution times for completed jobs
        cur.execute("""
            SELECT 
                COUNT(*) as total_completed,
                AVG(execution_time) as avg_time,
                MIN(execution_time) as min_time,
                MAX(execution_time) as max_time
            FROM jobs 
            WHERE state = 'completed' AND execution_time IS NOT NULL
        """)
        stats = dict(cur.fetchone())
        
        # Combine all metrics
        return {
            'pending': metrics.get('pending', 0),
            'processing': metrics.get('processing', 0),
            'completed': metrics.get('completed', 0),
            'failed': metrics.get('failed', 0),
            'dead': metrics.get('dead', 0),
            'avg_time': round(stats['avg_time'] or 0, 2),
            'min_time': round(stats['min_time'] or 0, 2),
            'max_time': round(stats['max_time'] or 0, 2)
        }
