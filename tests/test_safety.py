import unittest
from providers.interface import FileResource, FileType
from core.types import SyncAction, SyncActionType
from core.safety import SafetyMonitor, SafetyException

class TestSafetyMonitor(unittest.TestCase):
    def setUp(self):
        # Configure strict monitor: Max 2 files or 20%
        self.monitor = SafetyMonitor(max_deletions_percent=20.0, max_deletions_count=2)

    def _create_action(self, type: SyncActionType, path: str):
        f = FileResource(path=path, name="x", type=FileType.FILE, size=10, mtime=10.0)
        return SyncAction(type, f, "test")

    def test_safe_plan(self):
        """Verify plan with no deletions passes."""
        actions = [
            self._create_action(SyncActionType.COPY_LEFT_TO_RIGHT, "/a"),
            self._create_action(SyncActionType.COPY_LEFT_TO_RIGHT, "/b")
        ]
        self.assertTrue(self.monitor.analyze_plan(actions))

    def test_safe_deletion(self):
        """Verify plan with allowed number of deletions passes."""
        actions = [
            self._create_action(SyncActionType.DELETE_LEFT, "/a"), # 1 deletion
            self._create_action(SyncActionType.COPY_LEFT_TO_RIGHT, "/b"),
            self._create_action(SyncActionType.COPY_LEFT_TO_RIGHT, "/c"),
        ]
        # 1 del / 3 total = 33%. Wait, max is 20%. 
        # But count limit is 2. 
        # Logic: If count > max_count AND percent > max_percent.
        # Here count (1) is <= max (2). So it should pass regardless of %.
        self.assertTrue(self.monitor.analyze_plan(actions))

    def test_unsafe_plan_threshold_exceeded(self):
        """Verify plan exceeding allowed deletions is blocked."""
        actions = [
            self._create_action(SyncActionType.DELETE_LEFT, "/a"),
            self._create_action(SyncActionType.DELETE_LEFT, "/b"),
            self._create_action(SyncActionType.DELETE_RIGHT, "/c"),
        ]
        # 3 deletions. total 3.
        # Count 3 > 2. Percent 100% > 20%.
        # Should RAISE.
        with self.assertRaises(SafetyException):
            self.monitor.analyze_plan(actions)

    def test_canary_protection(self):
        """Verify touching canary file triggers immediate halt."""
        monitor = SafetyMonitor(canary_files=[".canary"])
        actions = [
            self._create_action(SyncActionType.DELETE_LEFT, "/folder/.canary"),
        ]
        # Should raise regardless of thresholds
        with self.assertRaises(SafetyException):
            monitor.analyze_plan(actions)

if __name__ == '__main__':
    unittest.main()
