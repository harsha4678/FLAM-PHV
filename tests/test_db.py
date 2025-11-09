import unittest
import sys
sys.path.append('..')
from db import Database
import os

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = Database(':memory:')  # Use in-memory SQLite for testing
        
    def test_job_crud(self):
        # Create
        job_id = self.db.create_job({
            'command': 'echo test',
            'status': 'pending'
        })
        self.assertIsNotNone(job_id)
        
        # Read
        job = self.db.get_job(job_id)
        self.assertEqual(job['command'], 'echo test')
        
        # Update
        self.db.update_job_status(job_id, 'completed')
        job = self.db.get_job(job_id)
        self.assertEqual(job['status'], 'completed')
        
    def test_metrics(self):
        self.db.create_job({'status': 'completed'})
        self.db.create_job({'status': 'failed'})
        metrics = self.db.get_metrics()
        self.assertEqual(metrics['completed_jobs'], 1)
        self.assertEqual(metrics['failed_jobs'], 1)

if __name__ == '__main__':
    unittest.main()
