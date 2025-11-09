import unittest
import sys
sys.path.append('..')
from queuectl import QueueController

class TestQueue(unittest.TestCase):
    def setUp(self):
        self.queue = QueueController()
        
    def test_job_enqueue(self):
        job_id = self.queue.enqueue_job('echo test')
        self.assertIsNotNone(job_id)
        
    def test_priority_ordering(self):
        job1 = self.queue.enqueue_job('echo low', priority=1)
        job2 = self.queue.enqueue_job('echo high', priority=10)
        next_job = self.queue.get_next_job()
        self.assertEqual(next_job['id'], job2)  # High priority should be first
        
    def test_dlq_handling(self):
        job_id = self.queue.enqueue_job('false')
        for _ in range(5):  # Exceed max retries
            self.queue.mark_job_failed(job_id)
        job = self.queue.get_job(job_id)
        self.assertEqual(job['status'], 'dead')

if __name__ == '__main__':
    unittest.main()
