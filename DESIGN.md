# FLAM PHV - System Design

This document provides a detailed overview of the architecture and design of the FLAM PHV job queue system.

## 1. High-Level Architecture

The system is composed of several key components that interact to provide a robust job queuing solution:

```
+-----------------+      +------------------+      +-----------------+
|                 |      |                  |      |                 |
|  queuectl.py    |----->|      db.py       |<-----|   worker.py     |
| (CLI)           |      | (SQLite Backend) |      | (Job Processor) |
|                 |      |                  |      |                 |
+-----------------+      +------------------+      +-----------------+
      ^                        ^
      |                        |
      |                        |
+-----------------+      +------------------+
|                 |      |                  |
|  dashboard.py   |----->|      db.py       |
| (Web UI)        |      | (Metrics)        |
|                 |      |                  |
+-----------------+      +------------------+
```

-   **`queuectl.py` (CLI)**: The primary user interface for enqueuing jobs, managing workers, and viewing queue status. It interacts directly with the database.
-   **`worker.py` (Job Processor)**: A separate process that continuously polls the database for pending jobs, executes them, and updates their status. Multiple workers can run concurrently.
-   **`db.py` (Database Layer)**: An abstraction layer over the SQLite database. It handles all database operations, including job creation, state management, and metrics collection.
-   **`dashboard.py` (Web UI)**: A Flask-based web application that provides a real-time dashboard for monitoring job statuses and system performance metrics. It reads data from the database.
-   **`jobs.py`**: Contains the logic for creating, enqueueing, and manipulating jobs.
-   **`config.py`**: Manages system-wide configuration settings stored in the database.
-   **`utils.py`**: Provides utility functions, primarily for managing worker process IDs (PIDs).

## 2. Component Breakdown

### 2.1. `queuectl.py` - The Controller

-   **Framework**: `click`
-   **Responsibilities**:
    -   Provides a command-line interface for all system operations.
    -   **Job Management**: Enqueues new jobs (`enqueue-cmd`), lists jobs (`list-cmd`), and manages the Dead Letter Queue (`dlq`).
    -   **Worker Management**: Starts (`worker start`) and stops (`worker stop`) worker processes.
    -   **Configuration**: Gets and sets configuration parameters (`config get/set`).
    -   **Status**: Displays a summary of the queue status (`status`).

### 2.2. `worker.py` - The Executor

-   **Concurrency**: Runs as a separate process using the `multiprocessing` module.
-   **Responsibilities**:
    -   **Job Claiming**: Periodically polls the database for available jobs, claiming one for processing.
    -   **Job Execution**: Executes the job's command in a subprocess.
    -   **Timeout Handling**: Monitors the job's execution time and terminates it if it exceeds the specified timeout.
    -   **State Updates**: Updates the job's state to `completed` or `failed` based on the execution result.
    -   **Retry Mechanism**: Implements an exponential backoff strategy for failed jobs. If a job fails, its next attempt time is scheduled further into the future with each subsequent failure.
    -   **Dead Letter Queue (DLQ)**: Moves jobs to the `dead` state after they have exceeded their maximum number of retry attempts.

### 2.3. `db.py` - The Database Layer

-   **Database**: SQLite
-   **Responsibilities**:
    -   **Schema Management**: Initializes the database schema, including the `jobs` and `settings` tables.
    -   **CRUD Operations**: Provides functions for creating, reading, updating, and deleting jobs.
    -   **Atomic Operations**: Uses database transactions (`BEGIN IMMEDIATE`) to ensure that job claiming is an atomic operation, preventing race conditions where multiple workers could claim the same job.
    -   **Metrics**: Aggregates data from the `jobs` table to provide real-time performance metrics.

### 2.4. `dashboard.py` - The Web UI

-   **Framework**: Flask
-   **Responsibilities**:
    -   **Real-time Monitoring**: Displays the current state of all jobs in the queue.
    -   **Metrics Visualization**: Presents key performance indicators, such as job counts by state and average execution time.
    -   **Auto-refresh**: Automatically refreshes the data every 5 seconds to provide a near real-time view.

## 3. Job Lifecycle

A job progresses through the following states during its lifecycle:

1.  **`pending`**: The initial state of a job after it has been enqueued.
2.  **`processing`**: A worker has claimed the job and is currently executing it.
3.  **`completed`**: The job was executed successfully.
4.  **`failed`**: The job execution failed or timed out. The job will be retried if it has not exceeded its maximum retry count.
5.  **`dead`**: The job has failed more times than the configured maximum and will not be retried automatically. It can be manually re-enqueued from the DLQ.

## 4. Database Schema

The SQLite database consists of two main tables:

### `jobs` table

| Column            | Type    | Description                               |
| ----------------- | ------- | ----------------------------------------- |
| `id`              | TEXT    | Primary Key, unique identifier for the job|
| `command`         | TEXT    | The command to be executed                |
| `state`           | TEXT    | The current state of the job              |
| `attempts`        | INTEGER | The number of times the job has been attempted |
| `max_retries`     | INTEGER | The maximum number of retry attempts      |
| `created_at`      | TEXT    | The timestamp when the job was created    |
| `updated_at`      | TEXT    | The timestamp of the last update          |
| `next_attempt_at` | REAL    | The timestamp for the next retry attempt  |
| `locked`          | INTEGER | A flag to prevent race conditions         |
| `last_error`      | TEXT    | The error message from the last failure   |
| `execution_time`  | REAL    | The duration of the last execution        |
| `priority`        | INTEGER | The priority of the job                   |
| `timeout_seconds` | INTEGER | The timeout for the job in seconds        |

### `settings` table

| Column | Type | Description                        |
| ------ | ---- | ---------------------------------- |
| `key`  | TEXT | Primary Key, the setting name      |
| `value`| TEXT | The value of the setting           |

## 5. Concurrency Model

-   **Process-based Workers**: Workers are implemented as separate OS processes, providing true parallelism and isolation.
-   **Atomic Job Claiming**: The `claim_job_for_processing` function in `db.py` uses a `BEGIN IMMEDIATE` transaction to acquire an exclusive lock on the database. This ensures that only one worker can select and update a job at a time, preventing race conditions.
-   **Locking**: A `locked` flag in the `jobs` table is used as a secondary measure to indicate that a job is being processed.

## 6. Configuration

System-wide settings are stored in the `settings` table in the database and managed via `config.py` and the `queuectl config` command. Key configurable parameters include:

-   `max_retries`: The default maximum number of retries for a job.
-   `backoff_base`: The base for the exponential backoff calculation.

## 7. Assumptions and Trade-offs

-   **SQLite Backend**:
    -   **Pros**: Simple, zero-configuration, and file-based, making it easy to set up and manage for local development.
    -   **Cons**: Limited concurrency, not suitable for high-throughput, distributed environments.
-   **Process-based Workers**:
    -   **Pros**: True parallelism and memory isolation between jobs.
    -   **Cons**: Higher resource overhead compared to thread-based workers.
-   **Local Filesystem**:
    -   **Pros**: Simple to implement.
    -   **Cons**: The system is not designed for distributed deployment across multiple machines.
