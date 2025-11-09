import unittest
from unittest.mock import Mock, patch
import sys
sys.path.append('..')
from worker import Worker

class TestWorker(unittest.TestCase):
    def setUp(self):
        self.worker = Worker()
        
    def test_job_execution(self):
        job = {
            'id': 'test-job',
            'command': 'echo test',
            'timeout_seconds': 5
        }
        result = self.worker.execute_job(job)
        self.assertEqual(result['status'], 'completed')
        
    def test_job_timeout(self):
        job = {
            'id': 'timeout-job',
            'command': 'sleep 10',
            'timeout_seconds': 1
        }
        result = self.worker.execute_job(job)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue('timeout' in result['error'])
        
    def test_retry_mechanism(self):
        job = {
            'id': 'retry-job',
            'command': 'false',
            'retries': 0,
            'max_retries': 3
        }
        result = self.worker.execute_job(job)
        self.assertEqual(result['retries'], 1)

if __name__ == '__main__':
    unittest.main()
