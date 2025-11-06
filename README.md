Project: FLAM PHV

Creating files in PowerShell:
1. mkdir -Force 'D:\Projects\FLAM PHV'
2. cd 'D:\Projects\FLAM PHV'
3. foreach ($f in "queuectl.py","db.py","worker.py","jobs.py","config.py","utils.py","requirements.txt","README.md") { New-Item -Path $f -ItemType File -Force }

Run:
- python queuectl.py --help
