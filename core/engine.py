import logging
import time
from typing import List, Dict, Tuple

from providers.interface import IFileProvider, FileResource, FileType
from .db import SyncDB
from .safety import SafetyMonitor
from .types import SyncAction, SyncActionType

logger = logging.getLogger("sync_engine")

class SyncEngine:
    def __init__(self, left_provider: IFileProvider, right_provider: IFileProvider, db: SyncDB):
        self.left = left_provider
        self.right = right_provider
        self.db = db
        self.run_id = 0
        self.safety = SafetyMonitor() # Default config

    def sync(self, dry_run: bool = False) -> List[SyncAction]:
        self.run_id = self.db.start_run()
        logger.info(f"Starting Sync Run {self.run_id}")
        
        actions = []
        try:
            # 1. Scan Left
            logger.info("Scanning Left Provider...")
            left_files = {f.path: f for f in self.left.list_dir("/", recursive=True)} # Assumes root /
            
            # 2. Scan Right
            logger.info("Scanning Right Provider...")
            right_files = {f.path: f for f in self.right.list_dir("/", recursive=True)}

            # 3. Compare & Decide
            all_paths = set(left_files.keys()) | set(right_files.keys())
            
            # Phase 3a: Generate Plan
            planned_actions = []
            for path in all_paths:
                file_left = left_files.get(path)
                file_right = right_files.get(path)
                db_state = self.db.get_file_state(path)
                
                action = self._decide(path, file_left, file_right, db_state)
                if action.action_type != SyncActionType.SKIP:
                    planned_actions.append(action)

            # Phase 3b: Safety Check
            logger.info(f"Generated {len(planned_actions)} actions. Validating safety...")
            self.safety.analyze_plan(planned_actions)

            # Phase 4: Execute
            processed_count = 0
            for action in planned_actions:
                actions.append(action)
                if not dry_run:
                    self._execute(action)
                processed_count += 1

            self.db.end_run(self.run_id, "success", processed_count)
            return actions

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.db.end_run(self.run_id, "failed", 0)
            raise e

            self.db.end_run(self.run_id, "success", processed_count)
            return actions

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.db.end_run(self.run_id, "failed", 0)
            raise e

    def _decide(self, path: str, left: FileResource, right: FileResource, db_state: Dict) -> SyncAction:
        """
        SmartTracking Logic Implementation.
        """
        # Case 1: Exists on Both
        if left and right:
            # Compare Checksums/Mtime/Size
            # Simple size comparison for MVP. Should use hash if available.
            if left.size == right.size:
                # Assuming identical (fast check). 
                # Should check DB: did they change since last time?
                # If sizes match and are same as DB, SKIP.
                # If sizes match but DIFFERENT from DB, CONFLICT (both changed to same size?) unlikely but possible.
                self._update_db_state(left) # Confirm match
                return SyncAction(SyncActionType.SKIP, left, "Identical")
            
            # Left Newer?
            if left.mtime > right.mtime + 2.0: # 2s fuzzy window
                return SyncAction(SyncActionType.COPY_LEFT_TO_RIGHT, left, "Left is newer")
            elif right.mtime > left.mtime + 2.0:
                return SyncAction(SyncActionType.COPY_RIGHT_TO_LEFT, right, "Right is newer")
            else:
                return SyncAction(SyncActionType.CONFLICT, left, "Different size, same time")
        
        # Case 2: Left Only
        if left and not right:
            # New file on Left OR Deleted on Right?
            if db_state:
                # Was in DB. Means it existed on Right previously.
                # If Left matches DB, then Right was deleted. Propagate Delete to Left.
                return SyncAction(SyncActionType.DELETE_LEFT, left, "Deleted on Right")
            else:
                # Not in DB. New file on Left.
                return SyncAction(SyncActionType.COPY_LEFT_TO_RIGHT, left, "New on Left")

        # Case 3: Right Only
        if right and not left:
            if db_state:
                # Was in DB. Means it existed on Left.
                # If Right matches DB, then Left was deleted. Propagate Delete to Right.
                return SyncAction(SyncActionType.DELETE_RIGHT, right, "Deleted on Left")
            else:
                # Not in DB. New on Right.
                return SyncAction(SyncActionType.COPY_RIGHT_TO_LEFT, right, "New on Right")
                
        return SyncAction(SyncActionType.SKIP, None, "Impossible state")

    def _execute(self, action: SyncAction):
        try:
            if action.action_type == SyncActionType.COPY_LEFT_TO_RIGHT:
                logger.info(f"Copying L->R: {action.file.path}")
                # Copy Stream
                with self.left.open(action.file.path, "rb") as src, \
                     self.right.open(action.file.path, "wb") as dst: # Need 'open' with write support
                        # Actually IFileProvider needs a copy convenience or stream pipe
                        # For now assume 'wb' works in Providers (Local does, Dropbox need impl)
                        # We use a naive read/write loop here or shutil.copyfileobj
                        import shutil
                        shutil.copyfileobj(src, dst)
                self._update_db_state(action.file)

            elif action.action_type == SyncActionType.COPY_RIGHT_TO_LEFT:
                logger.info(f"Copying R->L: {action.file.path}")
                with self.right.open(action.file.path, "rb") as src, \
                     self.left.open(action.file.path, "wb") as dst:
                        import shutil
                        shutil.copyfileobj(src, dst)
                self._update_db_state(action.file)

            elif action.action_type == SyncActionType.DELETE_LEFT:
                self.left.delete(action.file.path)
                # Remove from DB
                # self.db.remove_file_state(path) # Need this method

            elif action.action_type == SyncActionType.DELETE_RIGHT:
                self.right.delete(action.file.path)

        except Exception as e:
            logger.error(f"Execution failed for {action.file.path}: {e}")

    def _update_db_state(self, file: FileResource):
        self.db.upsert_file_state(
            file.path, 
            "provider", # Should track which side? Sync implies convergence.
            file.size, 
            file.mtime, 
            file.chksum or "", 
            self.run_id
        )
