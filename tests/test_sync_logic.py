import unittest
from unittest.mock import MagicMock, ANY
from core.engine import SyncEngine
from core.types import SyncActionType, SyncAction
from providers.interface import IFileProvider, FileResource, FileType
from core.db import SyncDB

class TestSyncLogic(unittest.TestCase):
    def setUp(self):
        self.left = MagicMock(spec=IFileProvider)
        self.right = MagicMock(spec=IFileProvider)
        self.db = MagicMock(spec=SyncDB)
        self.engine = SyncEngine(self.left, self.right, self.db)
        
        # Defaults
        self.db.start_run.return_value = 999

    def test_scenario_a_new_file_left(self):
        """Scenario A: New File on Left, invalid in DB -> Action: Copy L->R."""
        # Setup
        # File exists on Left
        f_left = FileResource(path="/new_doc.txt", name="new_doc.txt", size=100, mtime=1000.0, type=FileType.FILE, chksum="abc")
        self.left.list_dir.return_value = [f_left]
        
        # Missing on Right
        self.right.list_dir.return_value = []
        
        # Not in DB (None)
        self.db.get_file_state.return_value = None
        
        # Run Sync
        actions = self.engine.sync(dry_run=True)
        
        # Verify
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action.action_type, SyncActionType.COPY_LEFT_TO_RIGHT)
        self.assertEqual(action.file.path, "/new_doc.txt")
        self.assertEqual(action.reason, "New on Left")

    def test_scenario_b_deletion_on_left(self):
        """Scenario B: Exists in DB (so was synced), missing on Left -> Action: Delete Right."""
        # Setup
        # Missing on Left
        self.left.list_dir.return_value = []
        
        # Exists on Right
        f_right = FileResource(path="/old_doc.txt", name="old_doc.txt", size=100, mtime=1000.0, type=FileType.FILE, chksum="abc")
        self.right.list_dir.return_value = [f_right]
        
        # Exists in DB (meaning it was known)
        self.db.get_file_state.return_value = {
            "path": "/old_doc.txt", 
            "size": 100, 
            "mtime": 1000.0, 
            "checksum": "abc"
        }
        
        # Run Sync
        actions = self.engine.sync(dry_run=True)
        
        # Verify
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action.action_type, SyncActionType.DELETE_RIGHT)
        self.assertEqual(action.file.path, "/old_doc.txt")
        self.assertEqual(action.reason, "Deleted on Left")

    def test_scenario_c_conflict(self):
        """Scenario C: Modified on Left AND Right since last sync -> Action: Conflict."""
        # Setup
        # Left has version 2
        f_left = FileResource(path="/doc.txt", name="doc.txt", size=200, mtime=2000.0, type=FileType.FILE, chksum="def")
        self.left.list_dir.return_value = [f_left]
        
        # Right has version 3 (concurrent edit)
        f_right = FileResource(path="/doc.txt", name="doc.txt", size=205, mtime=2000.0, type=FileType.FILE, chksum="xyz")
        self.right.list_dir.return_value = [f_right]
        
        # DB has version 1
        self.db.get_file_state.return_value = {
            "path": "/doc.txt", "size": 100, "mtime": 1000.0
        }
        
        # Run
        actions = self.engine.sync(dry_run=True)
        
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action.action_type, SyncActionType.CONFLICT)
        self.assertEqual(action.file.path, "/doc.txt")

if __name__ == '__main__':
    unittest.main()
