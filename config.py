# config.py
from db import get_setting, set_setting

def get_backoff_base():
    val = get_setting('backoff_base', '2')
    return int(val)

def set_backoff_base(x):
    set_setting('backoff_base', str(x))

def get_max_retries_default():
    val = get_setting('max_retries', '3')
    return int(val)

def set_max_retries(x):
    set_setting('max_retries', str(x))
