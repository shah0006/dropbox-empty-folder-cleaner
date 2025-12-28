import sqlite3
import threading
import queue
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("sync_db")

class DatabaseWorker(threading.Thread):
    def __init__(self, db_path: str):
        super().__init__(daemon=True)
        self.db_path = db_path
        self.queue = queue.Queue()
        self.connection = None
        self.running = True
        self.start()

    def run(self):
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.execute("PRAGMA journal_mode=WAL;")
            self.connection.execute("PRAGMA synchronous=NORMAL;")
            self._create_tables()
            
            while self.running:
                try:
                    task = self.queue.get(timeout=1.0)
                    if task is None:
                        break
                    query, args, result_queue = task
                    try:
                        cursor = self.connection.execute(query, args)
                        if query.strip().upper().startswith("SELECT"):
                            result = cursor.fetchall()
                        else:
                            self.connection.commit()
                            result = cursor.lastrowid
                        result_queue.put(('success', result))
                    except Exception as e:
                        result_queue.put(('error', e))
                    finally:
                        self.queue.task_done()
                except queue.Empty:
                    continue
        except Exception as e:
            logger.critical(f"Database worker failed: {e}")
        finally:
            if self.connection:
                self.connection.close()
    
    def _create_tables(self):
        schema = """
        CREATE TABLE IF NOT EXISTS file_state (
            path TEXT PRIMARY KEY,
            provider_id TEXT,
            size INTEGER,
            mtime REAL,
            checksum TEXT,
            inode TEXT,
            last_seen_run_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS run_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time REAL,
            end_time REAL,
            status TEXT,
            files_processed INTEGER
        );
        """
        self.connection.executescript(schema)
        self.connection.commit()

    def execute(self, query: str, args: tuple = ()) -> Any:
        result_queue = queue.Queue()
        self.queue.put((query, args, result_queue))
        status, result = result_queue.get()
        if status == 'error':
            raise result
        return result

    def close(self):
        self.running = False
        self.queue.put(None)
        self.join()

class SyncDB:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = "sync_state.db"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SyncDB, cls).__new__(cls)
                cls._instance._init(db_path)
        return cls._instance

    def _init(self, db_path):
        self.worker = DatabaseWorker(db_path)

    def upsert_file_state(self, path: str, provider_id: str, size: int, mtime: float, checksum: str, run_id: int):
        query = """
        INSERT INTO file_state (path, provider_id, size, mtime, checksum, last_seen_run_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            size=excluded.size,
            mtime=excluded.mtime,
            checksum=excluded.checksum,
            last_seen_run_id=excluded.last_seen_run_id
        """
        self.worker.execute(query, (path, provider_id, size, mtime, checksum, run_id))

    def get_file_state(self, path: str) -> Optional[Dict]:
        rows = self.worker.execute("SELECT * FROM file_state WHERE path = ?", (path,))
        if not rows:
            return None
        # Map tuple to dict based on fixed schema position
        # path, provider_id, size, mtime, checksum, inode, last_seen_run_id
        r = rows[0]
        return {
            "path": r[0], "provider": r[1], "size": r[2], "mtime": r[3], "checksum": r[4], "inode": r[5], "run_id": r[6]
        }

    def start_run(self) -> int:
        return self.worker.execute("INSERT INTO run_history (start_time, status) VALUES (?, ?)", (time.time(), "running"))

    def end_run(self, run_id: int, status: str, files_count: int):
        self.worker.execute("UPDATE run_history SET end_time=?, status=?, files_processed=? WHERE id=?", 
                            (time.time(), status, files_count, run_id))
    
    def close(self):
        self.worker.close()
