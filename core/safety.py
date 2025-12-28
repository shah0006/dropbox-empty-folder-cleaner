import logging
import time
from typing import List
from .types import SyncAction, SyncActionType

logger = logging.getLogger("safety_monitor")

class SafetyMonitor:
    def __init__(self, 
                 max_deletions_percent: float = 10.0, 
                 max_deletions_count: int = 50,
                 canary_files: List[str] = None):
        self.max_deletions_percent = max_deletions_percent
        self.max_deletions_count = max_deletions_count
        self.canary_files = canary_files or [".sys_canary", "canary.dat"]

    def analyze_plan(self, actions: List[SyncAction]) -> bool:
        """
        Analyze a proposed sync plan for safety violations.
        Returns True if safe, raises SafetyException if unsafe.
        """
        delete_actions = [a for a in actions if a.action_type in (
            SyncActionType.DELETE_LEFT, SyncActionType.DELETE_RIGHT
        )]
        
        total_actions = len(actions)
        delete_count = len(delete_actions)

        # 1. Canary Check (Placeholder logic - requires Checking File Content Changes)
        # If a canary file is modified/deleted on source, IMMEDIATE HALT.
        for action in actions:
            if action.file and any(c in action.file.path for c in self.canary_files):
                if action.action_type != SyncActionType.SKIP:
                    raise SafetyException(f"CRITICAL: Canary file modified! {action.file.path}")

        # 2. Threshold Check
        if delete_count > self.max_deletions_count:
             # Calculate percent relative to total files (scan size needed, but actions roughly proxy activity)
            percent = (delete_count / total_actions * 100) if total_actions > 0 else 100
            
            if percent > self.max_deletions_percent:
                msg = (f"Safety Limit Exceeded: Planning to delete {delete_count} files "
                       f"({percent:.1f}% of activity). Limit is {self.max_deletions_count} / {self.max_deletions_percent}%.")
                logger.critical(msg)
                raise SafetyException(msg)

        logger.info(f"Safety Check Passed: {delete_count} deletions planned.")
        return True

class SafetyException(Exception):
    pass
