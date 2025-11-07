# FLAM PHV - Job Queue System


<img width="2035" height="1349" alt="Screenshot 2025-11-07 121835" src="https://github.com/user-attachments/assets/1eff465c-c409-45a7-95a4-988df416ae2a" />




A robust job queue system built with Python and Flask, featuring priority queues, job timeout handling, and real-time metrics dashboard.





https://github.com/user-attachments/assets/219477ae-e419-4693-a89e-fb8b5fc47089




## Features

- Job priority queuing
- Job timeout handling
- Real-time metrics dashboard
- Dead letter queue (DLQ) management
- Multiple worker support
- Job retry mechanism with exponential backoff
- SQLite-based persistence

## Setup Instructions

1. Create project directory and files:
```powershell
mkdir -Force 'D:\Projects\FLAM PHV'
cd 'D:\Projects\FLAM PHV'
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

Required dependencies:
- Flask==2.3.3
- click==8.1.7

## Usage Examples

### 1. Enqueue Jobs

```powershell
# Basic job
python queuectl.py enqueue-cmd "echo Hello World"

# Job with priority and timeout
python queuectl.py enqueue-cmd '{\"command\":\"sleep 5\",\"timeout_seconds\":10,\"priority\":10}'

# Job with custom ID
python queuectl.py enqueue-cmd '{\"id\":\"urgent-task\",\"command\":\"echo urgent\",\"priority\":5}'
```

<img width="1266" height="488" alt="Screenshot 2025-11-07 122114" src="https://github.com/user-attachments/assets/8b2c4e79-b344-455f-992c-b85a36419649" />


### 2. Manage Workers

```powershell
# Start workers
python queuectl.py worker start --count 2

# Stop workers
python queuectl.py worker stop
```


<img width="1392" height="733" alt="Screenshot 2025-11-07 122132" src="https://github.com/user-attachments/assets/c9554264-ea16-470e-a301-205ec09f263d" />



### 3. View Status

```powershell
python queuectl.py status
```
This is How the Queuue CLI Looks like 

<img width="727" height="602" alt="Screenshot 2025-11-07 122102" src="https://github.com/user-attachments/assets/45ff5798-03bc-46f4-8aef-8886fdf40fbb" />


### 4. Start Dashboard

```powershell
python dashboard.py
# Access at http://localhost:5000
```

## Architecture Overview

### Components

1. **Queue Controller (`queuectl.py`)**
   - CLI interface for job management
   - Worker process management
   - Configuration handling

2. **Workers (`worker.py`)**
   - Job execution engine
   - Timeout handling
   - Retry mechanism with exponential backoff

3. **Database (`db.py`)**
   - SQLite-based persistence
   - Job state management
   - Metrics collection

4. **Dashboard (`dashboard.py`)**
   - Real-time job monitoring
   - Performance metrics visualization
   - Job status tracking

### Job Lifecycle

1. **Enqueue**: Job created with `pending` state
2. **Process**: Worker claims job, sets state to `processing`
3. **Complete/Fail**: Job moves to `completed` or `failed` state
4. **Retry**: Failed jobs retry with exponential backoff
5. **DLQ**: Jobs exceeding retry limit move to `dead` state

## Testing Instructions

1. **Basic Functionality Test**
```powershell
# Enqueue a simple job
python queuectl.py enqueue-cmd "echo test"

# Start worker and verify execution
python queuectl.py worker start --count 1
```

2. **Priority Queue Test**
```powershell
# Enqueue jobs with different priorities
python queuectl.py enqueue-cmd '{\"command\":\"echo low\",\"priority\":1}'
python queuectl.py enqueue-cmd '{\"command\":\"echo high\",\"priority\":10}'

# Verify high priority job executes first
python queuectl.py worker start --count 1
```

3. **Timeout Test**
```powershell
# Enqueue long-running job with timeout
python queuectl.py enqueue-cmd '{\"command\":\"sleep 10\",\"timeout_seconds\":5}'

# Verify job times out and moves to failed state
python queuectl.py worker start --count 1
```

## Assumptions & Trade-offs

1. **SQLite Database**
   - Pro: Simple setup, no external dependencies
   - Con: Limited concurrent access

2. **Process-based Workers**
   - Pro: True parallelism, isolation
   - Con: Higher resource overhead

3. **In-Memory Job Claiming**
   - Pro: Fast job assignment
   - Con: Potential race conditions in high-load scenarios

4. **Local File System**
   - Pro: Simple implementation
   - Con: Not suitable for distributed deployment

## Configuration

Default settings can be modified using:
```powershell
python queuectl.py config set max-retries 5
python queuectl.py config set backoff-base 2
```



## License

MIT License

## Contributors

Harsha
[perumallaharshavardhan6@gmail.com]
