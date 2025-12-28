
import time
import threading
import logging
from datetime import datetime
from dropbox_service import app_state, scan_folder, scan_local_folder, save_config

logger = logging.getLogger("scheduler")

class SchedulerService:
    def __init__(self):
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self.running:
            return
        
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True, name="SchedulerThread")
        self.thread.start()
        logger.info("Scheduler service started")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("Scheduler service stopped")

    def _loop(self):
        while self.running and not self._stop_event.is_set():
            try:
                self._check_schedule()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
            
            # Check every minute
            if self._stop_event.wait(60):
                break

    def _check_schedule(self):
        config = app_state.get("config", {})
        schedule = config.get("schedule", {})
        
        if not schedule.get("enabled", False):
            return

        interval_hours = schedule.get("interval_hours", 24)
        last_run = schedule.get("last_run", 0)
        
        # Calculate time diff
        now_ts = time.time()
        elapsed_hours = (now_ts - last_run) / 3600
        
        if elapsed_hours >= interval_hours:
            logger.info("⏰ Scheduled scan due. Triggering now...")
            self._trigger_scan()

    def _trigger_scan(self):
        if app_state["scanning"] or app_state["deleting"] or app_state["comparing"]:
            logger.info("Skipping scheduled scan - system busy")
            return

        mode = app_state["config"].get("mode", "dropbox")
        logger.info(f"Starting scheduled scan in {mode} mode")
        
        # Determine path
        path = ""
        if mode == "local":
            path = app_state["config"].get("local_path", "")
            if not path:
                logger.error("Cannot run scheduled local scan: No local path set")
                return
            
            # Run scan in separate thread (files thread)
            # But wait, scan_local_folder runs in a thread? 
            # scan_local_folder in dropbox_service.py spawns a thread?
            # Let's check dropbox_service.py. It seems it DOES spawn a thread.
            scan_local_folder(path)
            
        else:
            # Dropbox
            if not app_state.get("connected"):
                logger.error("Cannot run scheduled Dropbox scan: Not connected")
                return
                
            scan_folder("") # Scan root
            
        # Update last run time
        config = app_state["config"]
        if "schedule" not in config:
            config["schedule"] = {}
            
        config["schedule"]["last_run"] = time.time()
        save_config() # This assumes save_config handles app_state["config"]

# Global instance
scheduler = SchedulerService()
