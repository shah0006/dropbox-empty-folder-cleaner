import unittest
import os
import threading
import time
from core.db import SyncDB

class TestSyncDB(unittest.TestCase):
    def setUp(self):
        # Reset Singleton for fresh test
        if SyncDB._instance:
            try:
                SyncDB._instance.close()
            except:
                pass
            SyncDB._instance = None
            
        self.db_path = "test_sync_db.sqlite"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        self.db = SyncDB(self.db_path)

    def tearDown(self):
        if self.db:
            self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        SyncDB._instance = None

    def test_initialization(self):
        """Verify SyncDB initialization in WAL mode."""
        # Execute a dummy write to ensure DB file checks happen
        self.db.upsert_file_state("/init_check", "test", 0, 0.0, "", 0)
        
        # Check for WAL file existence
        wal_path = self.db_path + "-wal"
        # In WAL mode, the -wal file exists when connection is open
        time.sleep(0.1) # Brief wait for FS
        self.assertTrue(os.path.exists(wal_path), "WAL file should exist in WAL mode")

    def test_upsert_and_get_file_state(self):
        """Test upsert_file_state and get_file_state for data integrity."""
        path = "/test/file.txt"
        provider_id = "prov_1"
        size = 1024
        mtime = 1600000000.0
        checksum = "abc123hash"
        run_id = 1
        
        # Insert
        self.db.upsert_file_state(path, provider_id, size, mtime, checksum, run_id)
        
        # Get
        state = self.db.get_file_state(path)
        self.assertIsNotNone(state)
        self.assertEqual(state['path'], path)
        self.assertEqual(state['size'], size)
        self.assertEqual(state['mtime'], mtime)
        self.assertEqual(state['checksum'], checksum)
        self.assertEqual(state['run_id'], run_id)
        
        # Update (Upsert)
        new_size = 2048
        self.db.upsert_file_state(path, provider_id, new_size, mtime, checksum, run_id)
        state = self.db.get_file_state(path)
        self.assertEqual(state['size'], new_size)

    def test_concurrency(self):
        """Verify concurrency to ensure no sqlite3.OperationalError: database is locked."""
        # Spin up threads to hammer the DB
        error_list = []
        
        def writer_task(thread_id):
            try:
                for i in range(50):
                    path = f"/concurrent/{thread_id}/{i}.txt"
                    self.db.upsert_file_state(path, "prov", i, 123.4, "hash", 1)
            except Exception as e:
                error_list.append(e)

        threads = []
        for i in range(4):
            t = threading.Thread(target=writer_task, args=(i,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        self.assertEqual(len(error_list), 0, f"Concurrency errors occurred: {error_list}")
        
        # Verify some data
        state = self.db.get_file_state("/concurrent/0/49.txt")
        self.assertIsNotNone(state)
        self.assertEqual(state['size'], 49)

if __name__ == '__main__':
    unittest.main()
