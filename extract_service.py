
import os

source_file = 'dropbox_cleaner_web.py'
target_file = 'dropbox_service.py'

# Ranges to extract
ranges = [
    (6885, 7082), # Block 1: Credentials & Connection
    (7083, 7471), # Block 2: Helpers & Scanning
    (7472, 7548), # Block 3: Local Deletion
    (7549, 8462), # Block 4: Subfolders & Compare
    (8463, 8687)  # Block 5: Final Deletion
]

header = """import os
import json
import time
import logging
import threading
import webbrowser
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import dropbox
from dropbox.files import FileMetadata, FolderMetadata
from dropbox.exceptions import ApiError, AuthError
from dotenv import load_dotenv

from logger_setup import setup_logger
from utils import find_empty_folders

# Constants
CONFIG_FILE = "config.json"
DEFAULT_EXCLUDES = [".git", "node_modules", ".env", "__pycache__", ".venv"]
DEFAULT_SYSTEM_FILES = [".DS_Store", "Thumbs.db", "desktop.ini", "*.alias", ".dropbox", ".dropbox.attr"]

# Initialize logger
logger = setup_logger("dropbox_service")

# Global state
app_state = {
    "connected": False,
    "scanning": False,
    "deleting": False,
    "comparing": False,
    "scan_progress": {
        "folders": 0, 
        "files": 0, 
        "status": "idle", 
        "percent": 0, 
        "start_time": 0, 
        "elapsed": 0,
        "rate": 0,
        "total": 0,
        "current_folder": "",
        "deepest_level": 0,
        "system_files_ignored": 0
    },
    "delete_progress": {
        "current": 4, 
        "total": 0, 
        "status": "idle", 
        "percent": 0,
        "deleted": 0,
        "skipped": 0,
        "errors": 0,
        "log": []
    },
    "empty_folders": [],
    "found_files": [],
    "dbx": None,
    "account_info": None,
    "config": {
        "port": 8765,
        "ignore_system_files": True,
        "system_files": DEFAULT_SYSTEM_FILES,
        "exclude_patterns": DEFAULT_EXCLUDES,
        "local_path": "",
        "export_format": "json"
    },
    "scanning_cancelled": False,
    "case_map": {},
    "compare_results": None,
    "compare_progress": {
        "status": "idle",
        "left_files": 0,
        "right_files": 0,
        "compared": 0,
        "total": 0,
        "current_file": "",
        "start_time": 0,
        "elapsed": 0
    },
    "compare_cancelled": False,
    "compare_executing": False,
    "compare_execute_progress": {
        "status": "idle",
        "current": 0,
        "total": 0,
        "deleted": 0,
        "copied": 0,
        "skipped": 0,
        "errors": [],
        "current_file": "",
        "log": []
    }
}
"""

with open(source_file, 'r') as f:
    lines = f.readlines()

with open(target_file, 'w') as f:
    f.write(header)
    for start, end in ranges:
        # line numbers are 1-based, list is 0-based
        f.write(''.join(lines[start-1:end]))

print(f"Extraction complete. {target_file} created.")
