#!/usr/bin/env python3
"""
Dropbox Empty Folder Cleaner - Web GUI Version
===============================================
A modern web-based GUI that opens in your browser.
No tkinter dependency - works on all macOS versions.

Usage:
    python3 dropbox_cleaner_web.py
"""

import os
import sys
import json
import threading
import webbrowser
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

try:
    import dropbox
    from dropbox.exceptions import ApiError, AuthError
    from dropbox.files import FolderMetadata
except ImportError:
    print("Error: dropbox package not installed.")
    print("Run: pip3 install dropbox python-dotenv")
    sys.exit(1)

# Configure logging
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up file handler
log_filename = f"logs/dropbox_cleaner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

# Set up console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

# Configure root logger
logger = logging.getLogger('DropboxCleaner')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("=" * 60)
logger.info("Dropbox Empty Folder Cleaner - Starting")
logger.info(f"Log file: {log_filename}")
logger.info("=" * 60)

# Default configuration
DEFAULT_CONFIG = {
    "ignore_system_files": True,
    "system_files": [
        ".DS_Store", "Thumbs.db", "desktop.ini", ".dropbox", 
        ".dropbox.attr", "Icon\r", ".localized"
    ],
    "exclude_patterns": [".git", "node_modules", "__pycache__", ".venv", ".env"],
    "export_format": "json",
    "auto_open_browser": True,
    "port": 8765
}

def load_config():
    """Load configuration from config.json."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from {config_path}")
                # Merge with defaults
                merged = {**DEFAULT_CONFIG, **config}
                return merged
    except Exception as e:
        logger.warning(f"Could not load config.json: {e}, using defaults")
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to config.json."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved configuration to {config_path}")
    except Exception as e:
        logger.error(f"Could not save config.json: {e}")

# Global state
app_state = {
    "dbx": None,
    "connected": False,
    "account_name": "",
    "account_email": "",
    "folders": [],
    "scanning": False,
    "scan_progress": {"folders": 0, "files": 0, "status": "idle", "start_time": 0, "elapsed": 0, "rate": 0},
    "empty_folders": [],
    "case_map": {},
    "deleting": False,
    "delete_progress": {"current": 0, "total": 0, "status": "idle", "percent": 0},
    "config": load_config(),
    "stats": {"depth_distribution": {}, "total_scanned": 0, "system_files_ignored": 0},
    "last_scan_folder": ""
}

HTML_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dropbox Empty Folder Cleaner</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: rgba(18, 18, 26, 0.8);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --accent-cyan: #00d4ff;
            --accent-purple: #a855f7;
            --accent-pink: #ec4899;
            --accent-green: #22c55e;
            --accent-orange: #f97316;
            --accent-red: #ef4444;
            --glow-cyan: rgba(0, 212, 255, 0.4);
            --glow-purple: rgba(168, 85, 247, 0.4);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            min-height: 100vh;
            color: var(--text-primary);
            overflow-x: hidden;
        }
        
        /* Animated background */
        .bg-gradient {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background: 
                radial-gradient(ellipse at 20% 20%, rgba(0, 212, 255, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(168, 85, 247, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(236, 72, 153, 0.05) 0%, transparent 70%);
            animation: bgPulse 8s ease-in-out infinite alternate;
        }
        
        @keyframes bgPulse {
            0% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 16px;
            position: relative;
        }
        
        /* Header - Compact */
        header {
            text-align: center;
            padding: 20px 0 16px;
        }
        
        .logo {
            font-size: 2em;
            margin-bottom: 8px;
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }
        
        h1 {
            font-size: 1.6em;
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 4px;
            animation: gradientShift 5s ease infinite;
            background-size: 200% 200%;
        }
        
        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 0.9em;
            font-weight: 400;
        }
        
        /* Cards - Compact */
        .card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid var(--border-color);
            backdrop-filter: blur(20px);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            border-color: rgba(255, 255, 255, 0.12);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        }
        
        .card-title {
            font-size: 0.95em;
            font-weight: 600;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        
        .card-title-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* Status badges - Compact */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            border-radius: 100px;
            font-size: 0.75em;
            font-weight: 600;
            letter-spacing: 0.02em;
        }
        
        .status-connected {
            background: rgba(34, 197, 94, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(34, 197, 94, 0.25);
            box-shadow: 0 0 20px rgba(34, 197, 94, 0.1);
        }
        
        .status-disconnected {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.25);
        }
        
        .status-scanning {
            background: rgba(0, 212, 255, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 212, 255, 0.25);
            animation: pulseGlow 2s ease-in-out infinite;
        }
        
        @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 0 15px rgba(0, 212, 255, 0.2); }
            50% { box-shadow: 0 0 30px rgba(0, 212, 255, 0.4); }
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            animation: blink 1.5s ease-in-out infinite;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        /* Form elements - Compact */
        select {
            width: 100%;
            padding: 10px 14px;
            font-size: 0.9em;
            font-family: inherit;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.4);
            color: var(--text-primary);
            cursor: pointer;
            margin-bottom: 12px;
            transition: all 0.3s ease;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%23a0a0b0' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
        }
        
        select:hover {
            border-color: rgba(255, 255, 255, 0.2);
        }
        
        select:focus {
            outline: none;
            border-color: var(--accent-cyan);
            box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.1);
        }
        
        /* Folder Tree Browser */
        .folder-browser {
            margin-bottom: 12px;
        }
        
        .selected-folder {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            background: rgba(0, 188, 212, 0.1);
            border: 1px solid var(--accent-cyan);
            border-radius: 8px;
            margin-bottom: 8px;
        }
        
        .selected-folder-label {
            color: var(--text-secondary);
            font-size: 0.85em;
        }
        
        .selected-folder-path {
            color: var(--accent-cyan);
            font-weight: 500;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.9em;
        }
        
        .folder-tree-container {
            min-height: 120px;
            max-height: 500px;
            height: 200px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.3);
            resize: vertical;
        }
        
        .folder-tree-container::-webkit-resizer {
            background: linear-gradient(135deg, transparent 50%, var(--accent-cyan) 50%);
            border-radius: 0 0 8px 0;
        }
        
        .folder-tree {
            padding: 8px;
        }
        
        .tree-item {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.15s ease;
            user-select: none;
            font-size: 0.85em;
        }
        
        .tree-item:hover {
            background: rgba(255, 255, 255, 0.08);
        }
        
        .tree-item.selected {
            background: rgba(0, 188, 212, 0.2);
            color: var(--accent-cyan);
        }
        
        .tree-item.selected .tree-label {
            font-weight: 500;
        }
        
        .tree-icon {
            font-size: 1em;
            width: 20px;
            text-align: center;
            flex-shrink: 0;
        }
        
        .tree-expand {
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7em;
            color: var(--text-secondary);
            transition: transform 0.2s ease;
            flex-shrink: 0;
        }
        
        .tree-expand.expanded {
            transform: rotate(90deg);
        }
        
        .tree-expand.loading {
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .tree-label {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .tree-children {
            margin-left: 20px;
            border-left: 1px dashed var(--border-color);
            padding-left: 8px;
        }
        
        .tree-children.collapsed {
            display: none;
        }
        
        .tree-loading {
            padding: 8px 10px;
            color: var(--text-secondary);
            font-size: 0.85em;
            font-style: italic;
        }
        
        .tree-empty {
            padding: 8px 10px;
            color: var(--text-secondary);
            font-size: 0.8em;
            font-style: italic;
        }
        
        /* Buttons - Compact */
        .btn {
            padding: 10px 20px;
            font-size: 0.85em;
            font-weight: 600;
            font-family: inherit;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            gap: 6px;
            position: relative;
            overflow: hidden;
        }
        
        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s ease;
        }
        
        .btn:hover::before {
            left: 100%;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-cyan), #0099cc);
            color: white;
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.3);
        }
        
        .btn-primary:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(0, 212, 255, 0.4);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, var(--accent-red), #dc2626);
            color: white;
            box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
        }
        
        .btn-danger:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(239, 68, 68, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.4;
            cursor: not-allowed;
            transform: none !important;
            box-shadow: none !important;
        }
        
        .btn-group {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }
        
        /* Progress Section - Compact */
        .progress-section {
            margin: 12px 0;
        }
        
        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .progress-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95em;
            font-weight: 600;
        }
        
        .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid rgba(0, 212, 255, 0.2);
            border-top-color: var(--accent-cyan);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Progress Bar - Compact */
        .progress-bar-container {
            position: relative;
            height: 8px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 100px;
            overflow: hidden;
            margin-bottom: 12px;
        }
        
        .progress-bar-bg {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: repeating-linear-gradient(
                -45deg,
                transparent,
                transparent 8px,
                rgba(255, 255, 255, 0.03) 8px,
                rgba(255, 255, 255, 0.03) 16px
            );
        }
        
        .progress-bar-fill {
            height: 100%;
            border-radius: 100px;
            background: linear-gradient(90deg, #ef4444, #f97316, #ef4444);
            background-size: 200% 100%;
            animation: progressGradient 1.5s linear infinite;
            transition: width 0.3s ease, background 0.5s ease;
            position: relative;
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
        }
        
        @keyframes progressGradient {
            0% { background-position: 0% 50%; }
            100% { background-position: 200% 50%; }
        }
        
        .progress-bar-fill.indeterminate {
            width: 40% !important;
            animation: indeterminateSlide 1.5s ease-in-out infinite, progressGradient 1.5s linear infinite;
        }
        
        @keyframes indeterminateSlide {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(300%); }
        }
        
        /* Completed state - solid green, no animation */
        .progress-bar-fill.complete {
            background: #22c55e !important;
            animation: none !important;
            box-shadow: 0 0 20px rgba(34, 197, 94, 0.5) !important;
            width: 100% !important;
        }
        
        .progress-bar-glow {
            position: absolute;
            top: -2px;
            right: -2px;
            width: 20px;
            height: 16px;
            background: white;
            border-radius: 50%;
            filter: blur(8px);
            opacity: 0.6;
        }
        
        .progress-bar-fill.complete .progress-bar-glow {
            display: none;
        }
        
        /* Stats Grid - Compact */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 8px;
        }
        
        .stat-card {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 8px 10px;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            border-color: rgba(255, 255, 255, 0.15);
        }
        
        .stat-card.folders {
            border-left: 3px solid var(--accent-cyan);
        }
        
        .stat-card.files {
            border-left: 3px solid var(--accent-purple);
        }
        
        .stat-card.empty {
            border-left: 3px solid var(--accent-pink);
        }
        
        .stat-icon {
            font-size: 0.9em;
            margin-bottom: 2px;
        }
        
        .stat-value {
            font-size: 1.3em;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            background: linear-gradient(135deg, var(--text-primary), var(--text-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.1;
        }
        
        .stat-card.folders .stat-value {
            background: linear-gradient(135deg, var(--accent-cyan), #0099cc);
            -webkit-background-clip: text;
            background-clip: text;
        }
        
        .stat-card.files .stat-value {
            background: linear-gradient(135deg, var(--accent-purple), #9333ea);
            -webkit-background-clip: text;
            background-clip: text;
        }
        
        .stat-card.empty .stat-value {
            background: linear-gradient(135deg, var(--accent-pink), #db2777);
            -webkit-background-clip: text;
            background-clip: text;
        }
        
        .stat-card.time .stat-value {
            background: linear-gradient(135deg, var(--accent-orange), #ea580c);
            -webkit-background-clip: text;
            background-clip: text;
        }
        
        .stat-card.rate .stat-value {
            background: linear-gradient(135deg, var(--accent-green), #16a34a);
            -webkit-background-clip: text;
            background-clip: text;
        }
        
        .stat-card.time {
            border-left: 3px solid var(--accent-orange);
        }
        
        .stat-card.rate {
            border-left: 3px solid var(--accent-green);
        }
        
        /* Percentage display for deletion - Compact */
        .percent-display {
            text-align: center;
            padding: 12px 0;
            margin-top: 8px;
        }
        
        .percent-value {
            font-size: 2.2em;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
        }
        
        .percent-label {
            color: var(--text-secondary);
            font-size: 0.8em;
            margin-top: 4px;
        }
        
        /* Number animation */
        .stat-value {
            transition: transform 0.15s ease;
        }
        
        .stat-value.updating {
            transform: scale(1.1);
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.65em;
            font-weight: 500;
            margin-top: 1px;
        }
        
        /* Pulse animation for active stats */
        .stat-card.active {
            animation: statPulse 2s ease-in-out infinite;
        }
        
        @keyframes statPulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(0, 212, 255, 0); }
            50% { box-shadow: 0 0 20px 5px rgba(0, 212, 255, 0.1); }
        }
        
        /* Results - Compact */
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .results-count {
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(236, 72, 153, 0.2));
            color: var(--accent-purple);
            padding: 4px 10px;
            border-radius: 100px;
            font-size: 0.75em;
            font-weight: 600;
            border: 1px solid rgba(168, 85, 247, 0.3);
        }
        
        .results-list {
            max-height: 500px;
            overflow-y: auto;
            overflow-x: hidden;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 6px;
        }
        
        /* Hide scrollbar when showing success state */
        .results-list:has(.success-state) {
            overflow-y: hidden;
        }
        
        .results-list::-webkit-scrollbar {
            width: 8px;
        }
        
        .results-list::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 4px;
        }
        
        .results-list::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 4px;
        }
        
        .results-list::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.25);
        }
        
        .folder-item {
            padding: 6px 10px;
            margin: 2px 0;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75em;
            color: var(--text-secondary);
            border-left: 2px solid var(--accent-purple);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .folder-item:hover {
            background: rgba(255, 255, 255, 0.06);
            color: var(--text-primary);
        }
        
        .folder-item-num {
            color: var(--accent-purple);
            font-weight: 600;
            min-width: 24px;
            font-size: 0.9em;
        }
        
        /* Success state */
        .success-state {
            text-align: center;
            padding: 48px 24px;
            overflow: hidden; /* Prevent scrollbar flicker from animation */
        }
        
        .success-icon {
            font-size: 4em;
            margin-bottom: 16px;
            /* Single bounce, then stop - no infinite animation */
        }
        
        @keyframes successBounce {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }
        
        .success-title {
            font-size: 1.4em;
            font-weight: 600;
            color: var(--accent-green);
            margin-bottom: 8px;
        }
        
        .success-text {
            color: var(--text-secondary);
        }
        
        /* Warning box - Compact */
        .warning-box {
            background: rgba(249, 115, 22, 0.1);
            border: 1px solid rgba(249, 115, 22, 0.25);
            border-radius: 8px;
            padding: 10px 12px;
            margin-top: 10px;
            color: var(--accent-orange);
            display: flex;
            align-items: flex-start;
            gap: 8px;
            font-size: 0.8em;
        }
        
        .warning-icon {
            font-size: 1em;
        }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(8px);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .modal-overlay.active {
            display: flex;
        }
        
        .modal {
            background: var(--bg-secondary);
            border-radius: 24px;
            padding: 36px;
            max-width: 480px;
            width: 90%;
            border: 1px solid var(--border-color);
            animation: modalSlide 0.3s ease;
        }
        
        @keyframes modalSlide {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .modal-icon {
            font-size: 3em;
            text-align: center;
            margin-bottom: 16px;
        }
        
        .modal h2 {
            color: var(--accent-red);
            margin-bottom: 16px;
            text-align: center;
            font-size: 1.5em;
        }
        
        .modal p {
            color: var(--text-secondary);
            margin-bottom: 28px;
            line-height: 1.7;
            text-align: center;
        }
        
        .modal .btn-group {
            justify-content: center;
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.12);
            transform: translateY(-2px);
        }
        
        .delete-warning-box {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 14px;
            margin: 16px 0;
            text-align: left;
            color: var(--accent-red);
        }
        
        .delete-warning-box ul {
            margin: 8px 0 0 0;
            padding-left: 20px;
            font-size: 0.9em;
        }
        
        .delete-warning-box li {
            margin-bottom: 4px;
        }
        
        /* Top Navigation */
        .top-nav {
            position: fixed;
            top: 12px;
            right: 12px;
            display: flex;
            gap: 8px;
            z-index: 100;
        }
        
        .nav-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 12px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.8em;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            font-family: inherit;
        }
        
        .nav-btn:hover {
            background: var(--accent-cyan);
            color: white;
            border-color: var(--accent-cyan);
            transform: translateY(-2px);
        }
        
        .nav-icon {
            font-size: 1em;
        }
        
        .nav-label {
            font-weight: 500;
        }
        
        /* Custom Tooltips */
        [data-tooltip] {
            position: relative;
        }
        
        [data-tooltip]::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%) translateY(-8px);
            padding: 8px 12px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            font-size: 0.75em;
            font-weight: 400;
            white-space: nowrap;
            border-radius: 6px;
            opacity: 0;
            visibility: hidden;
            transition: all 0.2s ease;
            z-index: 1000;
            pointer-events: none;
            max-width: 250px;
            white-space: normal;
            text-align: center;
            line-height: 1.4;
        }
        
        [data-tooltip]::before {
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%) translateY(4px);
            border: 6px solid transparent;
            border-top-color: rgba(0, 0, 0, 0.9);
            opacity: 0;
            visibility: hidden;
            transition: all 0.2s ease;
            z-index: 1000;
        }
        
        [data-tooltip]:hover::after,
        [data-tooltip]:hover::before {
            opacity: 1;
            visibility: visible;
        }
        
        /* Tooltip positioning variants */
        [data-tooltip-pos="bottom"]::after {
            bottom: auto;
            top: 100%;
            transform: translateX(-50%) translateY(8px);
        }
        
        [data-tooltip-pos="bottom"]::before {
            bottom: auto;
            top: 100%;
            transform: translateX(-50%) translateY(-4px);
            border-top-color: transparent;
            border-bottom-color: rgba(0, 0, 0, 0.9);
        }
        
        [data-tooltip-pos="left"]::after {
            bottom: auto;
            top: 50%;
            left: auto;
            right: 100%;
            transform: translateY(-50%) translateX(-8px);
        }
        
        [data-tooltip-pos="right"]::after {
            bottom: auto;
            top: 50%;
            left: 100%;
            transform: translateY(-50%) translateX(8px);
        }
        
        /* Help Modal */
        .help-modal {
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .help-modal h2 {
            color: var(--accent-cyan);
            margin-bottom: 20px;
        }
        
        .help-modal h3 {
            color: var(--accent-purple);
            font-size: 0.95em;
            margin: 16px 0 8px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .help-modal p, .help-modal li {
            color: var(--text-secondary);
            font-size: 0.85em;
            line-height: 1.6;
            text-align: left;
            margin-bottom: 8px;
        }
        
        .help-modal ul {
            margin: 8px 0;
            padding-left: 20px;
        }
        
        .help-modal li {
            margin-bottom: 4px;
        }
        
        .help-section {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 12px;
            margin: 12px 0;
        }
        
        .help-warning {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 10px 12px;
            margin: 12px 0;
            color: var(--accent-red);
            font-size: 0.85em;
        }
        
        .help-tip {
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 8px;
            padding: 10px 12px;
            margin: 12px 0;
            color: var(--accent-green);
            font-size: 0.85em;
        }
        
        /* Settings Toggle */
        .settings-row {
            display: flex;
            align-items: center;
        }
        
        .toggle-label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 0.85em;
            color: var(--text-secondary);
        }
        
        .toggle-label input[type="checkbox"] {
            width: 16px;
            height: 16px;
            accent-color: var(--accent-cyan);
            cursor: pointer;
        }
        
        .toggle-text {
            transition: color 0.2s ease;
        }
        
        .toggle-label:hover .toggle-text {
            color: var(--text-primary);
        }
        
        /* Small buttons for export */
        .btn-small {
            padding: 4px 8px;
            font-size: 0.7em;
            font-weight: 500;
            font-family: inherit;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .btn-small:hover {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            border-color: var(--accent-cyan);
        }
        
        /* Settings Modal */
        .settings-modal {
            max-width: 520px;
            max-height: 85vh;
            overflow-y: auto;
        }
        
        .settings-modal h2 {
            color: var(--accent-cyan);
            margin-bottom: 16px;
        }
        
        .settings-modal h3 {
            color: var(--accent-purple);
            font-size: 0.9em;
            margin: 0 0 8px 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .settings-section {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 12px;
            margin: 12px 0;
            border: 1px solid var(--border-color);
        }
        
        .settings-desc {
            color: var(--text-secondary);
            font-size: 0.8em;
            margin-bottom: 8px;
            text-align: left;
        }
        
        .settings-list-container {
            margin-top: 10px;
        }
        
        .settings-label {
            display: block;
            color: var(--text-secondary);
            font-size: 0.8em;
            margin-bottom: 4px;
        }
        
        .settings-textarea {
            width: 100%;
            padding: 8px 10px;
            font-size: 0.85em;
            font-family: 'JetBrains Mono', monospace;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: rgba(0, 0, 0, 0.3);
            color: var(--text-primary);
            resize: vertical;
            min-height: 60px;
        }
        
        .settings-textarea:focus {
            outline: none;
            border-color: var(--accent-cyan);
        }
        
        .checkbox-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px 16px;
            background: rgba(0, 0, 0, 0.2);
            padding: 10px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            max-height: 180px;
            overflow-y: auto;
        }
        
        .checkbox-grid::-webkit-scrollbar {
            width: 6px;
        }
        
        .checkbox-grid::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.15);
            border-radius: 3px;
        }
        
        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.8em;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-secondary);
            padding: 4px 6px;
            border-radius: 4px;
            transition: background 0.2s;
        }
        
        .checkbox-item:hover {
            background: rgba(255,255,255,0.05);
        }
        
        .checkbox-item input[type="checkbox"] {
            width: 14px;
            height: 14px;
            accent-color: var(--accent-cyan);
            cursor: pointer;
        }
        
        .checkbox-item label {
            cursor: pointer;
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .checkbox-item.is-wildcard label {
            color: var(--accent-purple);
        }
        
        .add-custom-row {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }
        
        .add-custom-input {
            flex: 1;
            padding: 6px 10px;
            font-size: 0.8em;
            font-family: 'JetBrains Mono', monospace;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: rgba(0, 0, 0, 0.3);
            color: var(--text-primary);
        }
        
        .add-custom-input:focus {
            outline: none;
            border-color: var(--accent-cyan);
        }
        
        .add-custom-btn {
            padding: 6px 12px;
            font-size: 0.8em;
            background: var(--accent-cyan);
            color: #000;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }
        
        .add-custom-btn:hover {
            filter: brightness(1.1);
        }
        
        .settings-hint {
            display: block;
            color: var(--text-secondary);
            font-size: 0.7em;
            margin-top: 4px;
            opacity: 0.7;
        }
        
        .settings-row-inline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-color);
        }
        
        .settings-row-inline:last-child {
            border-bottom: none;
        }
        
        .settings-row-inline label {
            color: var(--text-secondary);
            font-size: 0.85em;
        }
        
        .settings-input {
            width: 100px;
            padding: 6px 10px;
            font-size: 0.85em;
            font-family: 'JetBrains Mono', monospace;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: rgba(0, 0, 0, 0.3);
            color: var(--text-primary);
            text-align: center;
        }
        
        .settings-input:focus {
            outline: none;
            border-color: var(--accent-cyan);
        }
        
        .settings-select {
            padding: 6px 10px;
            font-size: 0.85em;
            font-family: inherit;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: rgba(0, 0, 0, 0.3);
            color: var(--text-primary);
            cursor: pointer;
        }
        
        .settings-select:focus {
            outline: none;
            border-color: var(--accent-cyan);
        }
        
        .settings-input-full {
            width: 100%;
            padding: 8px 10px;
            font-size: 0.85em;
            font-family: 'JetBrains Mono', monospace;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: rgba(0, 0, 0, 0.3);
            color: var(--text-primary);
        }
        
        .settings-input-full:focus {
            outline: none;
            border-color: var(--accent-cyan);
        }
        
        .btn-tiny {
            padding: 4px 8px;
            font-size: 0.75em;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            cursor: pointer;
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
        }
        
        .btn-tiny:hover {
            color: var(--accent-cyan);
        }
        
        .settings-list-container {
            position: relative;
        }
        
        .connection-status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            margin-bottom: 12px;
            font-size: 0.85em;
        }
        
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        
        .status-indicator.connected {
            background: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
        }
        
        .status-indicator.disconnected {
            background: var(--accent-red);
            box-shadow: 0 0 8px var(--accent-red);
        }
        
        .settings-section details summary {
            font-size: 0.85em;
        }
        
        .settings-section details ol {
            color: var(--text-secondary);
            font-size: 0.9em;
        }
        
        .settings-section details code {
            background: rgba(0, 212, 255, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9em;
            color: var(--accent-cyan);
        }
        
        /* Statistics Panel */
        .stats-panel {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 8px 12px;
            margin-bottom: 10px;
            border: 1px solid var(--border-color);
        }
        
        .stats-row {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            font-size: 0.8em;
            color: var(--text-secondary);
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .stat-item strong {
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Toast Notifications */
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 0.9em;
            font-weight: 500;
            z-index: 2000;
            opacity: 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        
        .toast.show {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
        
        .toast-success {
            background: var(--accent-green);
            color: white;
        }
        
        .toast-error {
            background: var(--accent-red);
            color: white;
        }
        
        .toast-info {
            background: var(--accent-cyan);
            color: white;
        }
        
        /* Setup Wizard */
        .wizard-modal {
            max-width: 580px;
            max-height: 90vh;
            overflow-y: auto;
        }
        
        .wizard-header {
            text-align: center;
            margin-bottom: 24px;
        }
        
        .wizard-icon {
            font-size: 3em;
            margin-bottom: 12px;
        }
        
        .wizard-modal h2 {
            color: var(--accent-cyan);
            margin-bottom: 8px;
        }
        
        .wizard-subtitle {
            color: var(--text-secondary);
            font-size: 0.9em;
        }
        
        .wizard-progress {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-bottom: 28px;
            padding: 16px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
        }
        
        .wizard-step {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            opacity: 0.4;
            transition: all 0.3s ease;
        }
        
        .wizard-step.active {
            opacity: 1;
        }
        
        .wizard-step.completed {
            opacity: 1;
        }
        
        .wizard-step.completed .step-number {
            background: var(--accent-green);
            border-color: var(--accent-green);
        }
        
        .step-number {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: 2px solid var(--accent-cyan);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 0.85em;
            transition: all 0.3s ease;
        }
        
        .wizard-step.active .step-number {
            background: var(--accent-cyan);
            color: white;
        }
        
        .step-label {
            font-size: 0.7em;
            color: var(--text-secondary);
            white-space: nowrap;
        }
        
        .wizard-step-line {
            width: 30px;
            height: 2px;
            background: var(--border-color);
            margin-bottom: 20px;
        }
        
        .wizard-content {
            animation: fadeIn 0.3s ease;
        }
        
        .wizard-content h3 {
            color: var(--accent-purple);
            font-size: 1.1em;
            margin-bottom: 16px;
        }
        
        .wizard-instructions {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .wizard-instructions p {
            color: var(--text-secondary);
            margin-bottom: 12px;
            text-align: left;
        }
        
        .wizard-instructions ol {
            color: var(--text-secondary);
            padding-left: 24px;
            margin: 12px 0;
        }
        
        .wizard-instructions li {
            margin-bottom: 8px;
            line-height: 1.6;
        }
        
        .wizard-action {
            text-align: center;
            margin: 20px 0;
        }
        
        .wizard-action a.btn {
            text-decoration: none;
            display: inline-flex;
        }
        
        .wizard-note {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 8px;
            padding: 12px;
            margin-top: 16px;
            font-size: 0.85em;
            color: var(--accent-cyan);
        }
        
        .wizard-warning {
            background: rgba(249, 115, 22, 0.1);
            border: 1px solid rgba(249, 115, 22, 0.3);
            border-radius: 8px;
            padding: 12px;
            margin-top: 16px;
            font-size: 0.85em;
            color: var(--accent-orange);
        }
        
        .wizard-nav {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
        }
        
        .permission-boxes {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin: 16px 0;
        }
        
        .permission-box {
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 8px;
            padding: 12px 16px;
        }
        
        .permission-check {
            font-size: 1.2em;
        }
        
        .permission-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .permission-info code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9em;
            color: var(--accent-green);
        }
        
        .permission-info span {
            font-size: 0.75em;
            color: var(--text-secondary);
        }
        
        .wizard-inputs {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin: 16px 0;
        }
        
        .wizard-input-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        
        .wizard-input-group label {
            color: var(--text-primary);
            font-size: 0.9em;
            font-weight: 500;
        }
        
        .input-hint {
            font-size: 0.75em;
            color: var(--text-secondary);
        }
        
        .wizard-success {
            text-align: center;
            padding: 20px;
        }
        
        .wizard-success .success-icon {
            font-size: 4em;
            margin-bottom: 16px;
            animation: successBounce 0.5s ease;
        }
        
        .wizard-success h3 {
            color: var(--accent-green) !important;
            font-size: 1.5em !important;
            margin-bottom: 12px !important;
        }
        
        .success-account {
            font-family: 'JetBrains Mono', monospace;
            background: rgba(34, 197, 94, 0.1);
            padding: 8px 16px;
            border-radius: 8px;
            display: inline-block;
            margin-bottom: 16px;
            color: var(--accent-green);
        }
        
        /* Disclaimer Modal */
        .disclaimer-modal {
            max-width: 600px;
            max-height: 85vh;
            overflow-y: auto;
        }
        
        .disclaimer-modal h2 {
            color: var(--accent-orange);
            margin-bottom: 16px;
        }
        
        .disclaimer-content {
            text-align: left;
        }
        
        .disclaimer-section {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 14px;
            margin: 12px 0;
            border-left: 3px solid var(--border-color);
        }
        
        .disclaimer-section.warning {
            background: rgba(239, 68, 68, 0.1);
            border-left-color: var(--accent-red);
        }
        
        .disclaimer-section.warning h3 {
            color: var(--accent-red);
        }
        
        .disclaimer-section.legal {
            background: rgba(168, 85, 247, 0.1);
            border-left-color: var(--accent-purple);
        }
        
        .disclaimer-section h3 {
            color: var(--accent-cyan);
            font-size: 0.95em;
            margin-bottom: 10px;
        }
        
        .disclaimer-section p {
            color: var(--text-secondary);
            font-size: 0.85em;
            line-height: 1.6;
            margin-bottom: 8px;
            text-align: left;
        }
        
        .disclaimer-section ul {
            color: var(--text-secondary);
            font-size: 0.85em;
            padding-left: 20px;
            margin: 8px 0;
        }
        
        .disclaimer-section li {
            margin-bottom: 6px;
            line-height: 1.5;
        }
        
        /* Footer - Compact with Disclaimer */
        footer {
            text-align: center;
            padding: 16px 10px;
            color: var(--text-secondary);
            font-size: 0.75em;
        }
        
        .footer-disclaimer {
            background: rgba(249, 115, 22, 0.1);
            border: 1px solid rgba(249, 115, 22, 0.3);
            border-radius: 6px;
            padding: 8px 12px;
            margin-bottom: 10px;
            color: var(--accent-orange);
            font-size: 0.85em;
        }
        
        .footer-disclaimer a {
            color: var(--accent-cyan);
            text-decoration: underline;
            margin-left: 4px;
        }
        
        .footer-links {
            display: flex;
            justify-content: center;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .footer-links a {
            color: var(--text-secondary);
            text-decoration: none;
            padding: 4px 8px;
            border-radius: 4px;
            transition: all 0.2s ease;
            font-size: 0.9em;
        }
        
        .footer-links a:hover {
            color: var(--accent-cyan);
            background: rgba(0, 212, 255, 0.1);
        }
        
        .footer-sep {
            color: var(--border-color);
        }
        
        .footer-credits {
            color: var(--text-secondary);
        }
        
        footer a {
            color: var(--accent-cyan);
            text-decoration: none;
        }
        
        /* Responsive */
        @media (max-width: 640px) {
            h1 { font-size: 2em; }
            .btn { width: 100%; justify-content: center; }
            .btn-group { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="bg-gradient"></div>
    
    <!-- Top Navigation -->
    <div class="top-nav">
        <button type="button" class="nav-btn" id="settingsNavBtn" title="Configure Dropbox connection, system files, and more">
            <span class="nav-icon">⚙️</span>
            <span class="nav-label">Settings</span>
        </button>
        <a href="https://github.com/shah0006/dropbox-empty-folder-cleaner" target="_blank" class="nav-btn" title="View source code and full documentation on GitHub">
            <span class="nav-icon">📚</span>
            <span class="nav-label">Docs</span>
        </a>
        <button type="button" class="nav-btn" id="helpNavBtn" title="Open help documentation and usage guide">
            <span class="nav-icon">❓</span>
            <span class="nav-label">Help</span>
        </button>
        <button type="button" class="nav-btn" id="disclaimerNavBtn" title="View important disclaimer and terms of use">
            <span class="nav-icon">⚠️</span>
            <span class="nav-label">Disclaimer</span>
        </button>
    </div>
    
    <div class="container">
        <header>
            <div class="logo">📁</div>
            <h1>Dropbox Empty Folder Cleaner</h1>
            <p class="subtitle">Find and remove empty folders from your Dropbox</p>
        </header>
        
        <div class="card">
            <div class="card-title">
                <span class="card-title-left">🔗 Connection Status</span>
                <span id="connectionStatus" class="status-badge status-disconnected" 
                      data-tooltip="Shows whether your Dropbox account is connected. Green = connected, Red = not connected.">
                    <span class="status-dot"></span>
                    Connecting...
                </span>
            </div>
            <p id="accountInfo" style="color: var(--text-secondary);"></p>
            <div id="setupPrompt" style="display: none; margin-top: 12px;">
                <p style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 10px;">
                    Connect your Dropbox account to get started:
                </p>
                <button class="btn btn-primary" onclick="showSetupWizard()"
                        data-tooltip="Start the guided setup wizard to connect your Dropbox account. Takes about 2 minutes."
                        data-tooltip-pos="bottom">
                    🚀 Set Up Dropbox Connection
                </button>
            </div>
        </div>
        
        <div class="card">
            <div class="card-title">
                <span class="card-title-left">📂 Select Folder to Scan</span>
            </div>
            <div class="folder-browser">
                <div class="selected-folder" id="selectedFolderDisplay" 
                     data-tooltip="Currently selected folder. Click in the tree below to change."
                     data-tooltip-pos="bottom">
                    <span class="selected-folder-label">Selected:</span>
                    <span class="selected-folder-path" id="selectedPath">/ (Entire Dropbox)</span>
                </div>
                <div class="folder-tree-container" id="folderTreeContainer">
                    <div class="folder-tree" id="folderTree">
                        <div class="tree-item root-item selected" data-path="">
                            <span class="tree-icon">🏠</span>
                            <span class="tree-label">/ (Entire Dropbox)</span>
                        </div>
                        <div id="rootFolders" class="tree-children">
                            <div class="tree-loading">Loading folders...</div>
                        </div>
                    </div>
                </div>
            </div>
            <input type="hidden" id="folderSelect" value="">
            <div class="btn-group">
                <button id="scanBtn" class="btn btn-primary" onclick="startScan()" 
                        data-tooltip="Search the selected folder for empty folders. This is safe - nothing will be deleted until you click Delete."
                        data-tooltip-pos="bottom">
                    🔍 Scan for Empty Folders
                </button>
                <button id="deleteBtn" class="btn btn-danger" onclick="confirmDelete()" disabled
                        data-tooltip="Permanently delete all found empty folders. You will be asked to confirm before deletion."
                        data-tooltip-pos="bottom">
                    🗑️ Delete Empty Folders
                </button>
            </div>
            
            <!-- Settings Toggle -->
            <div class="settings-row" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color);">
                <label class="toggle-label" data-tooltip="When enabled, folders containing only system files like .DS_Store or Thumbs.db will be treated as empty" data-tooltip-pos="bottom">
                    <input type="checkbox" id="ignoreSystemFiles" checked onchange="updateConfig()">
                    <span class="toggle-text">Ignore system files (.DS_Store, Thumbs.db, etc.)</span>
                </label>
                <button class="btn-small" id="inlineSettingsBtn" style="margin-left: auto;" 
                        data-tooltip="Configure Dropbox connection, system files, exclusion patterns, and more"
                        data-tooltip-pos="bottom">⚙️ Settings</button>
            </div>
        </div>
        
        <div class="card" id="progressCard" style="display: none;">
            <div class="progress-section">
                <div class="progress-header">
                    <div class="progress-title">
                        <div class="spinner" id="progressSpinner"></div>
                        <span id="progressTitle">Scanning your Dropbox...</span>
                    </div>
                    <span id="progressStatus" class="status-badge status-scanning">
                        <span class="status-dot"></span>
                        In Progress
                    </span>
                </div>
                
                <div class="progress-bar-container">
                    <div class="progress-bar-bg"></div>
                    <div id="progressFill" class="progress-bar-fill indeterminate">
                        <div class="progress-bar-glow"></div>
                    </div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card folders active" id="folderStatCard" data-tooltip="Total number of folders checked during the scan">
                        <div class="stat-icon">📁</div>
                        <div class="stat-value" id="folderCount">0</div>
                        <div class="stat-label">Folders Scanned</div>
                    </div>
                    <div class="stat-card files active" id="fileStatCard" data-tooltip="Legitimate files found (excludes ignored system files like .DS_Store)">
                        <div class="stat-icon">📄</div>
                        <div class="stat-value" id="fileCount">0</div>
                        <div class="stat-label">Files Found</div>
                    </div>
                    <div class="stat-card time active" id="timeStatCard" data-tooltip="How long the scan has been running">
                        <div class="stat-icon">⏱️</div>
                        <div class="stat-value" id="elapsedTime">0:00</div>
                        <div class="stat-label">Elapsed Time</div>
                    </div>
                    <div class="stat-card rate active" id="rateStatCard" data-tooltip="Processing speed - items checked per second">
                        <div class="stat-icon">⚡</div>
                        <div class="stat-value" id="itemRate">0</div>
                        <div class="stat-label">Items/Second</div>
                    </div>
                    <div class="stat-card empty" id="emptyStatCard" style="display: none;" data-tooltip="Total empty folders found that can be deleted">
                        <div class="stat-icon">🗂️</div>
                        <div class="stat-value" id="emptyCount">0</div>
                        <div class="stat-label">Empty Folders</div>
                    </div>
                </div>
                
                <!-- Percentage display for deletion -->
                <div class="percent-display" id="percentDisplay" style="display: none;">
                    <div class="percent-value" id="percentValue">0%</div>
                    <div class="percent-label">Deletion Progress</div>
                </div>
            </div>
        </div>
        
        <div class="card" id="resultsCard" style="display: none;">
            <div class="results-header">
                <span class="card-title-left">📋 Results</span>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <span id="resultsCount" class="results-count" data-tooltip="Total number of empty folders found in your scan">0 empty folders</span>
                    <button class="btn-small" onclick="exportResults('json')" 
                            data-tooltip="Download the list of empty folders as a JSON file. Recommended before deleting for your records.">📄 JSON</button>
                    <button class="btn-small" onclick="exportResults('csv')" 
                            data-tooltip="Download the list of empty folders as a CSV spreadsheet. Opens in Excel, Numbers, or Google Sheets.">📊 CSV</button>
                </div>
            </div>
            
            <!-- Statistics Panel -->
            <div id="statsPanel" class="stats-panel" style="display: none;">
                <div class="stats-row">
                    <span class="stat-item"><span class="stat-icon">📁</span> Scanned: <strong id="statScanned">0</strong></span>
                    <span class="stat-item"><span class="stat-icon">🚫</span> System files ignored: <strong id="statIgnored">0</strong></span>
                    <span class="stat-item"><span class="stat-icon">📊</span> Deepest: <strong id="statDeepest">0</strong> levels</span>
                </div>
            </div>
            
            <div id="resultsList" class="results-list"></div>
            <div class="warning-box" id="warningBox" style="display: none;">
                <span class="warning-icon">⚠️</span>
                <div>
                    <strong>Warning:</strong> Deletion cannot be undone directly. Deleted folders will go to Dropbox trash where they can be recovered for 30 days.
                </div>
            </div>
        </div>
        
        <footer>
            <div class="footer-links">
                <a href="#" onclick="showHelp(); return false;" data-tooltip="View usage guide and documentation">📖 Help Guide</a>
                <span class="footer-sep">•</span>
                <a href="https://github.com/shah0006/dropbox-empty-folder-cleaner#readme" target="_blank" data-tooltip="Read full documentation on GitHub">📚 Full Documentation</a>
                <span class="footer-sep">•</span>
                <a href="https://github.com/shah0006/dropbox-empty-folder-cleaner/issues" target="_blank" data-tooltip="Report a bug or request a feature">🐛 Report Issue</a>
                <span class="footer-sep">•</span>
                <a href="#" onclick="showSettings(); return false;" data-tooltip="Configure app settings">⚙️ Settings</a>
            </div>
            <div class="footer-disclaimer">
                ⚠️ <strong>Disclaimer:</strong> Use at your own risk. The developer assumes no responsibility for data loss or damage.
                <a href="#" onclick="showDisclaimer(); return false;">Read full disclaimer</a>
            </div>
            <div class="footer-credits">
                v1.2.3 • Built for Tushar Shah • <a href="https://github.com/shah0006/dropbox-empty-folder-cleaner" target="_blank">GitHub</a>
            </div>
        </footer>
    </div>
    
    <div class="modal-overlay" id="deleteModal">
        <div class="modal">
            <div class="modal-icon">⚠️</div>
            <h2 style="color: var(--accent-red);">Confirm Deletion</h2>
            <p>
                You are about to delete <strong id="deleteCount">0</strong> empty folder(s).
            </p>
            <div class="delete-warning-box">
                <strong>⚠️ Important:</strong>
                <ul>
                    <li>Folders will be moved to Dropbox trash</li>
                    <li>Recovery is possible for <strong>30 days only</strong></li>
                    <li>After 30 days, deletion is <strong>permanent</strong></li>
                    <li>This action cannot be undone after trash is emptied</li>
                </ul>
            </div>
            <p style="font-size: 0.85em; color: var(--text-secondary); margin-top: 16px;">
                💡 <strong>Tip:</strong> Export results to JSON/CSV before deleting for your records.
            </p>
            <div class="btn-group" style="margin-top: 20px;">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-danger" onclick="executeDelete()">
                    🗑️ Yes, Delete Folders
                </button>
            </div>
        </div>
    </div>
    
    <!-- Settings Modal -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal settings-modal">
            <div class="modal-icon">⚙️</div>
            <h2>Settings</h2>
            
            <div class="settings-section">
                <h3>🔐 Dropbox Connection</h3>
                <p class="settings-desc">Configure your Dropbox API credentials. <a href="https://www.dropbox.com/developers/apps" target="_blank" style="color: var(--accent-cyan);">Create a Dropbox App</a></p>
                
                <div class="connection-status" id="settingsConnectionStatus">
                    <span class="status-indicator connected"></span>
                    <span id="settingsAccountInfo">Connected</span>
                </div>
                
                <div class="settings-list-container">
                    <label class="settings-label">App Key:</label>
                    <input type="text" id="settingsAppKey" class="settings-input-full" placeholder="Your Dropbox App Key">
                </div>
                
                <div class="settings-list-container">
                    <label class="settings-label">App Secret:</label>
                    <input type="password" id="settingsAppSecret" class="settings-input-full" placeholder="Your Dropbox App Secret">
                    <button class="btn-tiny" onclick="togglePassword('settingsAppSecret')" title="Show/Hide">👁️</button>
                </div>
                
                <div class="settings-list-container">
                    <label class="settings-label">Refresh Token:</label>
                    <input type="password" id="settingsRefreshToken" class="settings-input-full" placeholder="Your Dropbox Refresh Token">
                    <button class="btn-tiny" onclick="togglePassword('settingsRefreshToken')" title="Show/Hide">👁️</button>
                </div>
                
                <div class="btn-group" style="margin-top: 10px;">
                    <button class="btn-small" onclick="startAuth()">🔑 Get New Token</button>
                    <button class="btn-small" onclick="testConnection()">🔄 Test Connection</button>
                </div>
                
                <div class="settings-hint" style="margin-top: 8px;">
                    <details>
                        <summary style="cursor: pointer; color: var(--accent-cyan);">📖 How to set up Dropbox API</summary>
                        <ol style="margin-top: 8px; padding-left: 20px; line-height: 1.8;">
                            <li>Go to <a href="https://www.dropbox.com/developers/apps" target="_blank" style="color: var(--accent-cyan);">Dropbox App Console</a></li>
                            <li>Click "Create app"</li>
                            <li>Select "Scoped access" → "Full Dropbox"</li>
                            <li>Name your app (e.g., "My Folder Cleaner")</li>
                            <li>Go to Permissions tab, enable:<br>
                                • <code>files.metadata.read</code><br>
                                • <code>files.content.write</code></li>
                            <li>Click "Submit" to save permissions</li>
                            <li>Copy App Key and App Secret here</li>
                            <li>Click "Get New Token" to authorize</li>
                        </ol>
                    </details>
                </div>
            </div>
            
            <div class="settings-section">
                <h3>🗂️ System File Handling</h3>
                <p class="settings-desc">Folders containing only these files will be considered empty.</p>
                
                <label class="toggle-label" style="margin: 12px 0;">
                    <input type="checkbox" id="settingsIgnoreSystem" checked>
                    <span class="toggle-text">Enable system file ignore</span>
                </label>
                
                <div class="settings-list-container">
                    <label class="settings-label">System files to ignore:</label>
                    <div id="systemFilesCheckboxes" class="checkbox-grid">
                        <!-- Checkboxes generated by JavaScript -->
                    </div>
                    <div class="add-custom-row">
                        <input type="text" id="customSystemFile" class="add-custom-input" placeholder="Add custom pattern (e.g., *.tmp)">
                        <button type="button" class="add-custom-btn" onclick="addCustomSystemFile()">+ Add</button>
                    </div>
                    <span class="settings-hint">Check patterns to ignore. Wildcards supported (*.alias, *.lnk)</span>
                </div>
            </div>
            
            <div class="settings-section">
                <h3>🚫 Exclusion Patterns</h3>
                <p class="settings-desc">Folders matching these names will be skipped during scanning.</p>
                
                <div class="settings-list-container">
                    <label class="settings-label">Folder names to exclude:</label>
                    <textarea id="excludePatternsList" class="settings-textarea" rows="3" placeholder="One pattern per line"></textarea>
                    <span class="settings-hint">One folder name per line (e.g., .git, node_modules)</span>
                </div>
            </div>
            
            <div class="settings-section">
                <h3>🌐 Application</h3>
                <div class="settings-row-inline">
                    <label>Server Port:</label>
                    <input type="number" id="settingsPort" class="settings-input" value="8765" min="1024" max="65535">
                </div>
                <div class="settings-row-inline">
                    <label>Default Export Format:</label>
                    <select id="settingsExportFormat" class="settings-select">
                        <option value="json">JSON</option>
                        <option value="csv">CSV</option>
                    </select>
                </div>
            </div>
            
            <div class="btn-group" style="margin-top: 20px;">
                <button class="btn btn-secondary" onclick="resetSettings()">↺ Reset to Defaults</button>
                <button class="btn btn-secondary" onclick="closeSettings()">Cancel</button>
                <button class="btn btn-primary" onclick="saveSettings()">💾 Save Settings</button>
            </div>
        </div>
    </div>
    
    <!-- Auth Modal -->
    <div class="modal-overlay" id="authModal">
        <div class="modal">
            <div class="modal-icon">🔑</div>
            <h2>Authorize Dropbox</h2>
            <div id="authStep1">
                <p>Click the button below to open Dropbox authorization. After authorizing, copy the code and paste it below.</p>
                <div class="btn-group" style="margin: 20px 0;">
                    <button class="btn btn-primary" onclick="openAuthUrl()">🔗 Open Dropbox Authorization</button>
                </div>
                <div class="settings-list-container">
                    <label class="settings-label">Paste authorization code here:</label>
                    <input type="text" id="authCode" class="settings-input-full" placeholder="Paste the code from Dropbox">
                </div>
                <div class="btn-group" style="margin-top: 16px;">
                    <button class="btn btn-secondary" onclick="closeAuth()">Cancel</button>
                    <button class="btn btn-primary" onclick="exchangeCode()">✓ Complete Authorization</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Setup Wizard Modal -->
    <div class="modal-overlay" id="setupWizard">
        <div class="modal wizard-modal">
            <div class="wizard-header">
                <div class="wizard-icon">🚀</div>
                <h2>Welcome! Let's Get Started</h2>
                <p class="wizard-subtitle">Follow these steps to connect your Dropbox account</p>
            </div>
            
            <div class="wizard-progress">
                <div class="wizard-step" id="wizStep1Indicator">
                    <div class="step-number">1</div>
                    <div class="step-label">Create App</div>
                </div>
                <div class="wizard-step-line"></div>
                <div class="wizard-step" id="wizStep2Indicator">
                    <div class="step-number">2</div>
                    <div class="step-label">Permissions</div>
                </div>
                <div class="wizard-step-line"></div>
                <div class="wizard-step" id="wizStep3Indicator">
                    <div class="step-number">3</div>
                    <div class="step-label">Credentials</div>
                </div>
                <div class="wizard-step-line"></div>
                <div class="wizard-step" id="wizStep4Indicator">
                    <div class="step-number">4</div>
                    <div class="step-label">Authorize</div>
                </div>
            </div>
            
            <!-- Step 1: Create Dropbox App -->
            <div class="wizard-content" id="wizStep1">
                <h3>Step 1: Create a Dropbox App</h3>
                <div class="wizard-instructions">
                    <p>First, you need to create a free Dropbox developer app:</p>
                    <ol>
                        <li>Click the button below to open the Dropbox App Console</li>
                        <li>Sign in to your Dropbox account if prompted</li>
                        <li>Click <strong>"Create app"</strong></li>
                        <li>Select <strong>"Scoped access"</strong></li>
                        <li>Select <strong>"Full Dropbox"</strong> for access type</li>
                        <li>Enter a name for your app (e.g., "My Folder Cleaner")</li>
                        <li>Click <strong>"Create app"</strong></li>
                    </ol>
                    <div class="wizard-action">
                        <a href="https://www.dropbox.com/developers/apps/create" target="_blank" class="btn btn-primary">
                            🔗 Open Dropbox App Console
                        </a>
                    </div>
                    <div class="wizard-note">
                        <strong>💡 Tip:</strong> Keep the Dropbox page open - you'll need information from it in the next steps.
                    </div>
                </div>
                <div class="wizard-nav">
                    <button class="btn btn-secondary" onclick="closeWizard()">Cancel</button>
                    <button class="btn btn-primary" onclick="wizardNext(2)">I've Created My App →</button>
                </div>
            </div>
            
            <!-- Step 2: Set Permissions -->
            <div class="wizard-content" id="wizStep2" style="display: none;">
                <h3>Step 2: Set App Permissions</h3>
                <div class="wizard-instructions">
                    <p>Now configure the permissions your app needs:</p>
                    <ol>
                        <li>In your new app's page, click the <strong>"Permissions"</strong> tab</li>
                        <li>Find and <strong>check these two permissions</strong>:</li>
                    </ol>
                    <div class="permission-boxes">
                        <div class="permission-box">
                            <div class="permission-check">☑️</div>
                            <div class="permission-info">
                                <code>files.metadata.read</code>
                                <span>Read file and folder information</span>
                            </div>
                        </div>
                        <div class="permission-box">
                            <div class="permission-check">☑️</div>
                            <div class="permission-info">
                                <code>files.content.write</code>
                                <span>Delete files and folders</span>
                            </div>
                        </div>
                    </div>
                    <ol start="3">
                        <li>Scroll down and click <strong>"Submit"</strong> to save the permissions</li>
                    </ol>
                    <div class="wizard-warning">
                        ⚠️ <strong>Important:</strong> You must enable BOTH permissions and click Submit, or the app won't work!
                    </div>
                </div>
                <div class="wizard-nav">
                    <button class="btn btn-secondary" onclick="wizardBack(1)">← Back</button>
                    <button class="btn btn-primary" onclick="wizardNext(3)">Permissions Set →</button>
                </div>
            </div>
            
            <!-- Step 3: Enter Credentials -->
            <div class="wizard-content" id="wizStep3" style="display: none;">
                <h3>Step 3: Enter Your App Credentials</h3>
                <div class="wizard-instructions">
                    <p>Now copy your app's credentials from Dropbox:</p>
                    <ol>
                        <li>Go back to the <strong>"Settings"</strong> tab of your Dropbox app</li>
                        <li>Find and copy your <strong>App key</strong> and <strong>App secret</strong></li>
                        <li>Paste them in the fields below:</li>
                    </ol>
                    <div class="wizard-inputs">
                        <div class="wizard-input-group">
                            <label>App Key:</label>
                            <input type="text" id="wizardAppKey" class="settings-input-full" placeholder="e.g., abc123xyz789">
                            <span class="input-hint">Found in your app's Settings tab</span>
                        </div>
                        <div class="wizard-input-group">
                            <label>App Secret:</label>
                            <div style="position: relative;">
                                <input type="password" id="wizardAppSecret" class="settings-input-full" placeholder="e.g., xyz789abc123secret">
                                <button class="btn-tiny" onclick="togglePassword('wizardAppSecret')" style="top: 12px;">👁️</button>
                            </div>
                            <span class="input-hint">Click "Show" next to App secret in Dropbox to reveal it</span>
                        </div>
                    </div>
                    <div class="wizard-note">
                        <strong>🔐 Security:</strong> Your credentials are stored only on your computer in a local .env file.
                    </div>
                </div>
                <div class="wizard-nav">
                    <button class="btn btn-secondary" onclick="wizardBack(2)">← Back</button>
                    <button class="btn btn-primary" onclick="wizardValidateAndNext()">Continue →</button>
                </div>
            </div>
            
            <!-- Step 4: Authorize -->
            <div class="wizard-content" id="wizStep4" style="display: none;">
                <h3>Step 4: Authorize the Connection</h3>
                <div class="wizard-instructions">
                    <p>Final step - authorize this app to access your Dropbox:</p>
                    <ol>
                        <li>Click the button below to open Dropbox authorization</li>
                        <li>Click <strong>"Allow"</strong> to grant access</li>
                        <li>Dropbox will show you an <strong>authorization code</strong></li>
                        <li>Copy that code and paste it below</li>
                    </ol>
                    <div class="wizard-action">
                        <button class="btn btn-primary" onclick="wizardOpenAuth()">🔗 Authorize with Dropbox</button>
                    </div>
                    <div class="wizard-input-group" style="margin-top: 20px;">
                        <label>Authorization Code:</label>
                        <input type="text" id="wizardAuthCode" class="settings-input-full" placeholder="Paste the code from Dropbox here">
                        <span class="input-hint">Copy the entire code shown by Dropbox after clicking "Allow"</span>
                    </div>
                </div>
                <div class="wizard-nav">
                    <button class="btn btn-secondary" onclick="wizardBack(3)">← Back</button>
                    <button class="btn btn-primary" onclick="wizardComplete()">✓ Complete Setup</button>
                </div>
            </div>
            
            <!-- Success -->
            <div class="wizard-content" id="wizStepSuccess" style="display: none;">
                <div class="wizard-success">
                    <div class="success-icon">🎉</div>
                    <h3>Setup Complete!</h3>
                    <p class="success-account" id="wizardSuccessAccount">Connected as: Loading...</p>
                    <p>You're all set! You can now scan your Dropbox for empty folders.</p>
                    <div class="wizard-action">
                        <button class="btn btn-primary" onclick="closeWizard()">Start Using the App</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Disclaimer Modal -->
    <div class="modal-overlay" id="disclaimerModal">
        <div class="modal disclaimer-modal">
            <div class="modal-icon">⚠️</div>
            <h2>Important Disclaimer</h2>
            
            <div class="disclaimer-content">
                <div class="disclaimer-section warning">
                    <h3>🚨 USE AT YOUR OWN RISK</h3>
                    <p>This software is provided <strong>"AS IS"</strong> without warranty of any kind, express or implied. By using this application, you acknowledge and accept the following:</p>
                </div>
                
                <div class="disclaimer-section">
                    <h3>📋 Terms of Use</h3>
                    <ul>
                        <li><strong>No Warranty:</strong> The developer makes no guarantees about the accuracy, reliability, or suitability of this software for any purpose.</li>
                        <li><strong>No Liability:</strong> The developer shall not be held liable for any direct, indirect, incidental, special, or consequential damages arising from the use of this software.</li>
                        <li><strong>Data Loss Risk:</strong> This application deletes folders from your Dropbox account. While safety measures are in place, data loss may still occur.</li>
                        <li><strong>User Responsibility:</strong> You are solely responsible for backing up your data and verifying the results before deletion.</li>
                        <li><strong>Recovery Limitations:</strong> Deleted folders can only be recovered from Dropbox trash for 30 days. After that, deletion is permanent.</li>
                    </ul>
                </div>
                
                <div class="disclaimer-section">
                    <h3>✅ Safety Measures Implemented</h3>
                    <p>To minimize risk, this application includes:</p>
                    <ul>
                        <li>Dry-run mode by default (scan without deleting)</li>
                        <li>Explicit confirmation required before any deletion</li>
                        <li>Deleted folders go to Dropbox trash (30-day recovery)</li>
                        <li>Deepest folders deleted first to prevent errors</li>
                        <li>Comprehensive logging of all operations</li>
                        <li>Export results before deletion for your records</li>
                    </ul>
                </div>
                
                <div class="disclaimer-section">
                    <h3>💡 Recommendations</h3>
                    <ul>
                        <li><strong>Always scan first</strong> - Review the empty folder list before deleting</li>
                        <li><strong>Export results</strong> - Download JSON/CSV before deleting</li>
                        <li><strong>Test on small folders</strong> - Try a small folder first to understand behavior</li>
                        <li><strong>Ensure sync is complete</strong> - Wait for Dropbox to show "Up to date"</li>
                        <li><strong>Back up important data</strong> - Maintain separate backups of critical files</li>
                    </ul>
                </div>
                
                <div class="disclaimer-section legal">
                    <h3>📜 Legal</h3>
                    <p>This software is licensed under the MIT License. By using this software, you agree to hold harmless the developer, contributors, and any affiliated parties from any claims, damages, or other liability.</p>
                    <p><strong>This is not affiliated with or endorsed by Dropbox, Inc.</strong></p>
                </div>
            </div>
            
            <div class="btn-group" style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="acceptDisclaimer()">I Understand and Accept</button>
            </div>
        </div>
    </div>
    
    <!-- Help Modal -->
    <div class="modal-overlay" id="helpModal">
        <div class="modal help-modal">
            <div class="modal-icon">📖</div>
            <h2>Help & Documentation</h2>
            
            <h3>🎯 Purpose</h3>
            <p>This tool helps you find and remove empty folders from your Dropbox account. Over time, empty folders accumulate from deleted files, failed syncs, reorganization, and application artifacts. Cleaning these up keeps your Dropbox organized and can improve sync performance.</p>
            
            <h3>🚀 First-Time Setup</h3>
            <div class="help-section">
                <p>If you haven't connected to Dropbox yet:</p>
                <ol>
                    <li>Go to <a href="https://www.dropbox.com/developers/apps" target="_blank" style="color: var(--accent-cyan);">Dropbox App Console</a> and create a new app</li>
                    <li>Select <strong>"Scoped access"</strong> → <strong>"Full Dropbox"</strong></li>
                    <li>In the app's <strong>Permissions</strong> tab, enable:
                        <br>• <code style="background: rgba(0,212,255,0.1); padding: 2px 6px; border-radius: 4px;">files.metadata.read</code>
                        <br>• <code style="background: rgba(0,212,255,0.1); padding: 2px 6px; border-radius: 4px;">files.content.write</code></li>
                    <li>Click <strong>⚙️ Settings</strong> in this app</li>
                    <li>Enter your <strong>App Key</strong> and <strong>App Secret</strong></li>
                    <li>Click <strong>"Get New Token"</strong> and follow the authorization flow</li>
                    <li>Click <strong>"Save Settings"</strong></li>
                </ol>
            </div>
            
            <h3>📋 How to Use</h3>
            <div class="help-section">
                <ol>
                    <li><strong>Select a folder</strong> from the dropdown
                        <br><span style="color: var(--text-secondary); font-size: 0.9em;">• Choose "/" to scan your entire Dropbox</span>
                        <br><span style="color: var(--text-secondary); font-size: 0.9em;">• Or select a specific folder to scan only that area</span></li>
                    <li><strong>Configure options</strong> (optional)
                        <br><span style="color: var(--text-secondary); font-size: 0.9em;">• Toggle "Ignore system files" to treat .DS_Store folders as empty</span></li>
                    <li><strong>Click "Scan for Empty Folders"</strong>
                        <br><span style="color: var(--text-secondary); font-size: 0.9em;">• Watch real-time progress: folders scanned, files found, elapsed time</span></li>
                    <li><strong>Review the results</strong>
                        <br><span style="color: var(--text-secondary); font-size: 0.9em;">• All empty folders are listed, sorted by depth (deepest first)</span>
                        <br><span style="color: var(--text-secondary); font-size: 0.9em;">• Export to JSON/CSV if you want a record</span></li>
                    <li><strong>Click "Delete Empty Folders"</strong> if you want to remove them</li>
                    <li><strong>Confirm deletion</strong> in the popup dialog</li>
                </ol>
            </div>
            
            <h3>✨ Features</h3>
            <ul>
                <li><strong>Smart Detection</strong> - Finds truly empty folders (no files, no non-empty subfolders)</li>
                <li><strong>System File Ignore</strong> - Treats folders with only .DS_Store, Thumbs.db, desktop.ini as empty</li>
                <li><strong>Exclusion Patterns</strong> - Skip folders like .git, node_modules automatically</li>
                <li><strong>Safe Deletion Order</strong> - Deletes deepest folders first, then works backward to parents</li>
                <li><strong>Real-time Progress</strong> - Live folder/file counts, elapsed time, items/second rate</li>
                <li><strong>Visual Progress Bar</strong> - Red/orange while running, solid green when complete</li>
                <li><strong>Export Results</strong> - Export empty folder list to JSON or CSV for records</li>
                <li><strong>Statistics Panel</strong> - View total scanned, system files ignored, deepest level</li>
                <li><strong>Trash Recovery</strong> - Deleted folders go to Dropbox trash (recoverable for 30 days)</li>
                <li><strong>Multi-User Support</strong> - Configure your own Dropbox credentials in Settings</li>
                <li><strong>Persistent Settings</strong> - All settings saved to config.json</li>
                <li><strong>Comprehensive Logging</strong> - Detailed logs saved to logs/ directory</li>
            </ul>
            
            <h3>⚙️ Settings</h3>
            <div class="help-section">
                <p>Click the <strong>⚙️ Settings</strong> button to configure:</p>
                <ul>
                    <li><strong>Dropbox Connection</strong> - App Key, App Secret, Refresh Token</li>
                    <li><strong>System Files</strong> - Which files to ignore (.DS_Store, Thumbs.db, etc.)</li>
                    <li><strong>Exclusion Patterns</strong> - Folders to skip (.git, node_modules, etc.)</li>
                    <li><strong>Export Format</strong> - Default format for exports (JSON or CSV)</li>
                </ul>
            </div>
            
            <h3>⚠️ Limitations</h3>
            <div class="help-warning">
                <strong>Important - Please Read:</strong>
                <ul>
                    <li><strong>Deletion is not immediately permanent</strong> - Folders go to Dropbox trash first</li>
                    <li><strong>30-day recovery window</strong> - After that, deletion cannot be undone</li>
                    <li><strong>Does not check file contents</strong> - Only checks if files exist in folders</li>
                    <li><strong>Team folders may not work</strong> - Designed for personal Dropbox accounts</li>
                    <li><strong>Large accounts take time</strong> - Scanning 100,000+ items may take several minutes</li>
                    <li><strong>Rate limits apply</strong> - Very large operations may be rate-limited by Dropbox</li>
                </ul>
            </div>
            
            <h3>💡 Tips & Best Practices</h3>
            <div class="help-tip">
                <ul>
                    <li><strong>Test first</strong> - Start with a small folder to understand how it works</li>
                    <li><strong>Sync first</strong> - Ensure Dropbox is fully synced ("Up to date") before scanning</li>
                    <li><strong>Review carefully</strong> - Check the list before deleting, especially the first time</li>
                    <li><strong>Export for records</strong> - Use JSON/CSV export before deleting for a backup list</li>
                    <li><strong>Rate limit handling</strong> - If you see errors, wait 5-10 minutes and retry</li>
                    <li><strong>Check logs</strong> - Look in the logs/ folder for detailed diagnostic information</li>
                </ul>
            </div>
            
            <h3>🔐 Security & Privacy</h3>
            <div class="help-section">
                <ul>
                    <li><strong>Local credentials</strong> - Your App Key, Secret, and Token are stored only in your local .env file</li>
                    <li><strong>No third parties</strong> - This tool communicates directly with Dropbox API only</li>
                    <li><strong>No data collection</strong> - No analytics, no tracking, no external servers</li>
                    <li><strong>Open source</strong> - Full code available for review on GitHub</li>
                    <li><strong>Refresh tokens</strong> - Long-term access without storing your password</li>
                </ul>
            </div>
            
            <h3>🛠️ Troubleshooting</h3>
            <div class="help-section">
                <ul>
                    <li><strong>"Not connected"</strong> - Click Settings → enter credentials → Get New Token</li>
                    <li><strong>"Authentication failed"</strong> - Your token may have expired, get a new one</li>
                    <li><strong>"Folder not found"</strong> - Check the path exists in your Dropbox</li>
                    <li><strong>"Rate limit exceeded"</strong> - Wait 5-10 minutes before retrying</li>
                    <li><strong>Scan taking too long</strong> - Try scanning a smaller folder first</li>
                    <li><strong>No empty folders found</strong> - Your selection may already be clean!</li>
                </ul>
            </div>
            
            <h3>📄 Version Information</h3>
            <p style="font-family: 'JetBrains Mono', monospace; font-size: 0.8em;">
                Version: 1.2.0<br>
                GitHub: <a href="https://github.com/shah0006/dropbox-empty-folder-cleaner" target="_blank" style="color: var(--accent-cyan);">shah0006/dropbox-empty-folder-cleaner</a>
            </p>
            
            <div class="btn-group" style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="closeHelp()">Got it!</button>
            </div>
        </div>
    </div>
    
    <script>
        console.log('=== SCRIPT STARTING ===');
        
        let pollInterval = null;
        let emptyFolders = [];
        let selectedFolderPath = '';
        let loadedFolders = new Set(); // Track which folders have been loaded
        
        // Folder Tree Functions
        function selectFolder(element, path) {
            console.log('selectFolder called with path:', path);
            
            // Remove selected class from all items
            document.querySelectorAll('.tree-item.selected').forEach(el => {
                el.classList.remove('selected');
            });
            
            // Add selected class to clicked item
            element.classList.add('selected');
            
            // Update hidden input and display
            selectedFolderPath = path;
            document.getElementById('folderSelect').value = path;
            document.getElementById('selectedPath').textContent = path || '/ (Entire Dropbox)';
            
            console.log('selectedFolderPath is now:', selectedFolderPath);
        }
        
        // Event delegation for tree clicks (runs immediately since script is at end of body)
        (function() {
            const treeContainer = document.getElementById('folderTreeContainer');
            if (treeContainer) {
                treeContainer.addEventListener('click', function(event) {
                    const target = event.target;
                    
                    // Check if expand arrow was clicked
                    if (target.classList.contains('tree-expand')) {
                        event.stopPropagation();
                        const treeItem = target.closest('.tree-item');
                        if (treeItem) {
                            const path = treeItem.dataset.path;
                            console.log('Expand clicked, path:', path);
                            toggleFolderExpand(treeItem, path);
                        }
                        return;
                    }
                    
                    // Check if a tree item was clicked (but not the expand icon)
                    const treeItem = target.closest('.tree-item');
                    if (treeItem) {
                        const path = treeItem.dataset.path;
                        console.log('Tree item clicked, path:', path);
                        selectFolder(treeItem, path);
                    }
                });
            }
        })();
        
        async function toggleFolderExpand(element, path) {
            const wrapper = element.closest('.tree-item-wrapper') || element.parentElement;
            const childrenContainer = wrapper.querySelector('.tree-children');
            const expandIcon = element.querySelector('.tree-expand');
            
            if (!childrenContainer) return;
            
            // If already expanded, collapse
            if (!childrenContainer.classList.contains('collapsed')) {
                childrenContainer.classList.add('collapsed');
                if (expandIcon) expandIcon.classList.remove('expanded');
                return;
            }
            
            // If not loaded yet, load subfolders
            if (!loadedFolders.has(path)) {
                if (expandIcon) {
                    expandIcon.classList.add('loading');
                    expandIcon.textContent = '⟳';
                }
                
                try {
                    const response = await fetch('/api/subfolders?path=' + encodeURIComponent(path));
                    const data = await response.json();
                    
                    if (data.subfolders && data.subfolders.length > 0) {
                        childrenContainer.innerHTML = data.subfolders.map(folder => {
                            const escapedPath = folder.path.replace(/"/g, '&quot;');
                            return `
                            <div class="tree-item-wrapper">
                                <div class="tree-item" data-path="${escapedPath}">
                                    <span class="tree-expand">▶</span>
                                    <span class="tree-icon">📁</span>
                                    <span class="tree-label">${folder.name}</span>
                                </div>
                                <div class="tree-children collapsed"></div>
                            </div>
                        `}).join('');
                    } else {
                        childrenContainer.innerHTML = '<div class="tree-empty">No subfolders</div>';
                    }
                    
                    loadedFolders.add(path);
                } catch (e) {
                    console.error('Failed to load subfolders:', e);
                    childrenContainer.innerHTML = '<div class="tree-empty">Error loading folders</div>';
                }
                
                if (expandIcon) {
                    expandIcon.classList.remove('loading');
                    expandIcon.textContent = '▶';
                }
            }
            
            // Expand
            childrenContainer.classList.remove('collapsed');
            expandIcon.classList.add('expanded');
        }
        
        async function loadRootFolders() {
            console.log('loadRootFolders() called');
            const container = document.getElementById('rootFolders');
            if (!container) {
                console.error('rootFolders container not found!');
                return;
            }
            
            try {
                console.log('Fetching /api/subfolders?path=');
                const response = await fetch('/api/subfolders?path=');
                console.log('Response status:', response.status);
                const data = await response.json();
                console.log('Received', data.subfolders ? data.subfolders.length : 0, 'folders');
                
                if (data.subfolders && data.subfolders.length > 0) {
                    container.innerHTML = data.subfolders.map(folder => {
                        const escapedPath = folder.path.replace(/"/g, '&quot;');
                        return `
                        <div class="tree-item-wrapper">
                            <div class="tree-item" data-path="${escapedPath}">
                                <span class="tree-expand">▶</span>
                                <span class="tree-icon">📁</span>
                                <span class="tree-label">${folder.name}</span>
                            </div>
                            <div class="tree-children collapsed"></div>
                        </div>
                    `}).join('');
                    console.log('Folder tree HTML updated');
                } else {
                    container.innerHTML = '<div class="tree-empty">No folders found</div>';
                    console.log('No subfolders returned');
                }
            } catch (e) {
                console.error('Failed to load root folders:', e);
                container.innerHTML = '<div class="tree-empty">Error loading folders: ' + e.message + '</div>';
            }
        }
        
        // Get list of currently expanded folder paths
        function getExpandedPaths() {
            const expanded = [];
            document.querySelectorAll('.tree-children:not(.collapsed)').forEach(container => {
                const wrapper = container.closest('.tree-item-wrapper');
                if (wrapper) {
                    const treeItem = wrapper.querySelector('.tree-item');
                    if (treeItem && treeItem.dataset.path) {
                        expanded.push(treeItem.dataset.path);
                    }
                }
            });
            // Also include root if rootFolders is visible
            const rootFolders = document.getElementById('rootFolders');
            if (rootFolders && !rootFolders.classList.contains('collapsed')) {
                expanded.push('');  // Root path is empty string
            }
            return expanded;
        }
        
        // Re-expand folders to given paths
        async function expandToPaths(paths) {
            for (const path of paths) {
                if (path === '') {
                    // Root is always expanded, skip
                    continue;
                }
                
                // Find the tree item with this path
                const treeItem = document.querySelector(`.tree-item[data-path="${CSS.escape(path)}"]`);
                if (treeItem) {
                    const wrapper = treeItem.closest('.tree-item-wrapper');
                    const childrenContainer = wrapper ? wrapper.querySelector('.tree-children') : null;
                    
                    if (childrenContainer && childrenContainer.classList.contains('collapsed')) {
                        // Expand this folder
                        await toggleFolderExpand(treeItem, path);
                    }
                }
            }
        }
        
        // Refresh folder tree after deletions (preserving expanded state)
        async function refreshFolderTree() {
            console.log('Refreshing folder tree...');
            
            // Save currently expanded paths and selected path
            const expandedPaths = getExpandedPaths();
            const previousSelection = selectedFolderPath;
            console.log('Preserving expanded paths:', expandedPaths);
            console.log('Preserving selection:', previousSelection);
            
            // Clear the cache of loaded folders
            loadedFolders.clear();
            
            // Reload root folders
            await loadRootFolders();
            
            // Re-expand previously expanded folders (in order from root to deep)
            // Sort by depth (number of slashes) to expand parents before children
            expandedPaths.sort((a, b) => (a.match(/\//g) || []).length - (b.match(/\//g) || []).length);
            await expandToPaths(expandedPaths);
            
            // Try to re-select the previously selected folder
            if (previousSelection) {
                const prevItem = document.querySelector(`.tree-item[data-path="${CSS.escape(previousSelection)}"]`);
                if (prevItem) {
                    selectFolder(prevItem, previousSelection);
                    console.log('Re-selected folder:', previousSelection);
                } else {
                    // Folder was deleted, reset to root
                    console.log('Previous selection no longer exists, resetting to root');
                    selectedFolderPath = '';
                    document.getElementById('folderSelect').value = '';
                    document.getElementById('selectedPath').textContent = '/ (Entire Dropbox)';
                    
                    document.querySelectorAll('.tree-item.selected').forEach(el => el.classList.remove('selected'));
                    const rootItem = document.querySelector('.tree-item.root-item');
                    if (rootItem) rootItem.classList.add('selected');
                }
            }
        }
        
        // Track if we've already refreshed after last deletion/scan
        let lastDeleteRefreshed = false;
        let lastScanRefreshed = false;
        
        async function fetchStatus() {
            console.log('fetchStatus() running...');
            try {
                const response = await fetch('/api/status');
                console.log('Got response:', response.status);
                if (!response.ok) {
                    console.error('Status response not OK:', response.status);
                    return;
                }
                const data = await response.json();
                console.log('Status data - connected:', data.connected);
                await updateUI(data);
                console.log('updateUI() completed');
            } catch (e) {
                console.error('Failed to fetch status:', e);
            }
        }
        
        function formatNumber(num) {
            return num.toLocaleString();
        }
        
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }
        
        function animateValue(elementId, newValue) {
            const el = document.getElementById(elementId);
            if (el.textContent !== newValue) {
                el.classList.add('updating');
                el.textContent = newValue;
                setTimeout(() => el.classList.remove('updating'), 150);
            }
        }
        
        async function updateUI(data) {
            // Connection status
            const statusEl = document.getElementById('connectionStatus');
            const accountEl = document.getElementById('accountInfo');
            const setupPrompt = document.getElementById('setupPrompt');
            
            if (data.connected) {
                statusEl.className = 'status-badge status-connected';
                statusEl.innerHTML = '<span class="status-dot"></span> Connected';
                accountEl.textContent = `Logged in as ${data.account_name} (${data.account_email})`;
                setupPrompt.style.display = 'none';
            } else {
                statusEl.className = 'status-badge status-disconnected';
                statusEl.innerHTML = '<span class="status-dot"></span> Not Connected';
                accountEl.textContent = '';
                setupPrompt.style.display = 'block';
            }
            
            // Folder tree is loaded separately via loadRootFolders()
            // No need to populate dropdown anymore since we use tree view
            
            // Progress
            const progressCard = document.getElementById('progressCard');
            const scanBtn = document.getElementById('scanBtn');
            const deleteBtn = document.getElementById('deleteBtn');
            const progressSpinner = document.getElementById('progressSpinner');
            const emptyStatCard = document.getElementById('emptyStatCard');
            
            const percentDisplay = document.getElementById('percentDisplay');
            const timeStatCard = document.getElementById('timeStatCard');
            const rateStatCard = document.getElementById('rateStatCard');
            
            if (data.scanning) {
                progressCard.style.display = 'block';
                document.getElementById('progressTitle').textContent = 'Scanning your Dropbox...';
                document.getElementById('progressStatus').className = 'status-badge status-scanning';
                document.getElementById('progressStatus').innerHTML = '<span class="status-dot"></span> In Progress';
                document.getElementById('progressFill').className = 'progress-bar-fill indeterminate';
                
                // Animate the numbers
                animateValue('folderCount', formatNumber(data.scan_progress.folders));
                animateValue('fileCount', formatNumber(data.scan_progress.files));
                animateValue('elapsedTime', formatTime(data.scan_progress.elapsed || 0));
                animateValue('itemRate', formatNumber(data.scan_progress.rate || 0));
                
                progressSpinner.style.display = 'block';
                document.getElementById('folderStatCard').classList.add('active');
                document.getElementById('fileStatCard').classList.add('active');
                timeStatCard.style.display = 'block';
                rateStatCard.style.display = 'block';
                timeStatCard.classList.add('active');
                rateStatCard.classList.add('active');
                emptyStatCard.style.display = 'none';
                percentDisplay.style.display = 'none';
                scanBtn.disabled = true;
                deleteBtn.disabled = true;
            } else if (data.deleting) {
                progressCard.style.display = 'block';
                document.getElementById('progressTitle').textContent = 'Deleting empty folders...';
                
                const pct = data.delete_progress.percent || 0;
                document.getElementById('progressStatus').innerHTML = `${pct}%`;
                document.getElementById('progressStatus').className = 'status-badge status-scanning';
                document.getElementById('progressFill').className = 'progress-bar-fill';
                document.getElementById('progressFill').style.width = pct + '%';
                
                // Show big percentage
                percentDisplay.style.display = 'block';
                animateValue('percentValue', `${pct}%`);
                document.getElementById('percentDisplay').querySelector('.percent-label').textContent = 
                    `Deleting ${data.delete_progress.current} of ${data.delete_progress.total} folders`;
                
                // Hide scan stats during deletion
                document.getElementById('folderStatCard').style.display = 'none';
                document.getElementById('fileStatCard').style.display = 'none';
                timeStatCard.style.display = 'none';
                rateStatCard.style.display = 'none';
                emptyStatCard.style.display = 'none';
                
                progressSpinner.style.display = 'block';
                scanBtn.disabled = true;
                deleteBtn.disabled = true;
            } else {
                scanBtn.disabled = false;
                progressSpinner.style.display = 'none';
                document.getElementById('folderStatCard').classList.remove('active');
                document.getElementById('fileStatCard').classList.remove('active');
                timeStatCard.classList.remove('active');
                rateStatCard.classList.remove('active');
                percentDisplay.style.display = 'none';
                
                // Show all stat cards again
                document.getElementById('folderStatCard').style.display = 'block';
                document.getElementById('fileStatCard').style.display = 'block';
                
                if (data.scan_progress.status === 'complete') {
                    progressCard.style.display = 'block';
                    document.getElementById('progressTitle').textContent = 'Scan Complete!';
                    document.getElementById('progressStatus').className = 'status-badge status-connected';
                    document.getElementById('progressStatus').innerHTML = '<span class="status-dot"></span> Done';
                    
                    // Solid green completed progress bar
                    document.getElementById('progressFill').className = 'progress-bar-fill complete';
                    document.getElementById('progressFill').style.width = '100%';
                    
                    // Show final stats
                    timeStatCard.style.display = 'block';
                    rateStatCard.style.display = 'block';
                    animateValue('elapsedTime', formatTime(data.scan_progress.elapsed || 0));
                    animateValue('itemRate', formatNumber(data.scan_progress.rate || 0));
                    
                    // Refresh folder tree after scan (only once)
                    if (!lastScanRefreshed) {
                        lastScanRefreshed = true;
                        console.log('Scan complete - triggering folder tree refresh');
                        await refreshFolderTree();
                        console.log('Folder tree refresh complete');
                    }
                    
                    // Show empty count stat
                    emptyStatCard.style.display = 'block';
                    animateValue('emptyCount', formatNumber(data.empty_folders.length));
                }
                
                // Check if deletion just completed
                if (data.delete_progress.status === 'complete' && !data.deleting) {
                    document.getElementById('progressFill').className = 'progress-bar-fill complete';
                    
                    // Refresh folder tree after deletion (only once)
                    if (!lastDeleteRefreshed) {
                        lastDeleteRefreshed = true;
                        console.log('Deletion complete - triggering folder tree refresh');
                        await refreshFolderTree();
                        console.log('Folder tree refresh complete');
                    }
                } else if (data.deleting) {
                    // Reset flag when new deletion starts
                    lastDeleteRefreshed = false;
                }
            }
            
            // Update config UI
            updateConfigUI(data.config);
            
            // Results
            if (data.empty_folders.length > 0 || data.scan_progress.status === 'complete') {
                const resultsCard = document.getElementById('resultsCard');
                resultsCard.style.display = 'block';
                
                emptyFolders = data.empty_folders;
                document.getElementById('resultsCount').textContent = `${emptyFolders.length} empty folder(s)`;
                
                // Update statistics
                updateStats(data.stats);
                
                const resultsList = document.getElementById('resultsList');
                if (emptyFolders.length === 0) {
                    resultsList.innerHTML = `
                        <div class="success-state">
                            <div class="success-icon">✨</div>
                            <div class="success-title">All Clean!</div>
                            <p class="success-text">No empty folders found in this location.</p>
                        </div>`;
                    document.getElementById('warningBox').style.display = 'none';
                    deleteBtn.disabled = true;
                } else {
                    resultsList.innerHTML = emptyFolders.map((folder, i) => 
                        `<div class="folder-item">
                            <span class="folder-item-num">${i + 1}.</span>
                            <span>${folder}</span>
                        </div>`
                    ).join('');
                    document.getElementById('warningBox').style.display = 'flex';
                    deleteBtn.disabled = false;
                }
            }
        }
        
        async function startScan() {
            const folder = selectedFolderPath; // Use tree selection
            console.log('startScan called, folder:', folder);
            
            // Reset refresh flags for next cycle
            lastDeleteRefreshed = false;
            lastScanRefreshed = false;
            
            document.getElementById('resultsCard').style.display = 'none';
            document.getElementById('emptyStatCard').style.display = 'none';
            
            try {
                const response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({folder: folder})
                });
                const result = await response.json();
                console.log('Scan API response:', result);
            } catch (e) {
                console.error('Failed to start scan:', e);
            }
        }
        
        function confirmDelete() {
            document.getElementById('deleteCount').textContent = emptyFolders.length;
            document.getElementById('deleteModal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('deleteModal').classList.remove('active');
        }
        
        function showHelp() {
            document.getElementById('helpModal').classList.add('active');
        }
        
        function closeHelp() {
            document.getElementById('helpModal').classList.remove('active');
        }
        
        async function executeDelete() {
            closeModal();
            try {
                await fetch('/api/delete', {method: 'POST'});
            } catch (e) {
                console.error('Failed to delete:', e);
            }
        }
        
        async function updateConfig() {
            const ignoreSystemFiles = document.getElementById('ignoreSystemFiles').checked;
            try {
                await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ignore_system_files: ignoreSystemFiles})
                });
            } catch (e) {
                console.error('Failed to update config:', e);
            }
        }
        
        function exportResults(format) {
            window.open(`/api/export?format=${format}`, '_blank');
        }
        
        function updateStats(stats) {
            const panel = document.getElementById('statsPanel');
            if (stats && stats.total_scanned > 0) {
                panel.style.display = 'block';
                document.getElementById('statScanned').textContent = formatNumber(stats.total_scanned);
                document.getElementById('statIgnored').textContent = formatNumber(stats.system_files_ignored || 0);
                
                const depths = Object.keys(stats.depth_distribution || {});
                const maxDepth = depths.length > 0 ? Math.max(...depths.map(Number)) : 0;
                document.getElementById('statDeepest').textContent = maxDepth;
            }
        }
        
        function updateConfigUI(config) {
            if (config) {
                document.getElementById('ignoreSystemFiles').checked = config.ignore_system_files !== false;
            }
        }
        
        let currentConfig = {};
        
        function showSettings() {
            // Populate settings from current config
            fetch('/api/config')
                .then(r => r.json())
                .then(config => {
                    currentConfig = config;
                    document.getElementById('settingsIgnoreSystem').checked = config.ignore_system_files !== false;
                    loadSystemFilesFromConfig(config.system_files || defaultSystemFiles);
                    document.getElementById('excludePatternsList').value = (config.exclude_patterns || []).join('\\n');
                    document.getElementById('settingsPort').value = config.port || 8765;
                    document.getElementById('settingsExportFormat').value = config.export_format || 'json';
                    document.getElementById('settingsModal').classList.add('active');
                })
                .catch(e => {
                    console.error('Failed to load config:', e);
                    alert('Failed to load settings');
                });
        }
        
        function closeSettings() {
            document.getElementById('settingsModal').classList.remove('active');
        }
        
        async function saveSettings() {
            const newConfig = {
                ignore_system_files: document.getElementById('settingsIgnoreSystem').checked,
                system_files: getEnabledSystemFiles(),
                exclude_patterns: document.getElementById('excludePatternsList').value
                    .split('\\n')
                    .map(s => s.trim())
                    .filter(s => s.length > 0),
                port: parseInt(document.getElementById('settingsPort').value) || 8765,
                export_format: document.getElementById('settingsExportFormat').value
            };
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(newConfig)
                });
                
                if (response.ok) {
                    closeSettings();
                    // Update main toggle
                    document.getElementById('ignoreSystemFiles').checked = newConfig.ignore_system_files;
                    showToast('Settings saved successfully!', 'success');
                } else {
                    showToast('Failed to save settings', 'error');
                }
            } catch (e) {
                console.error('Failed to save settings:', e);
                showToast('Failed to save settings', 'error');
            }
        }
        
        // Default system files list
        const defaultSystemFiles = [
            '.DS_Store', 'Thumbs.db', 'desktop.ini', '.dropbox', 
            '.dropbox.attr', 'Icon', 'Icon\\r', '.localized',
            '*.alias', '*.lnk', '*.symlink'
        ];
        
        // Current system files (enabled ones)
        let currentSystemFiles = new Set();
        // All known patterns (for checkbox display)
        let allSystemFilePatterns = new Set(defaultSystemFiles);
        
        function renderSystemFileCheckboxes() {
            const container = document.getElementById('systemFilesCheckboxes');
            const patterns = Array.from(allSystemFilePatterns).sort((a, b) => {
                // Sort: exact names first, then wildcards
                const aWild = a.includes('*');
                const bWild = b.includes('*');
                if (aWild !== bWild) return aWild ? 1 : -1;
                return a.localeCompare(b);
            });
            
            container.innerHTML = patterns.map(pattern => {
                const id = 'sysfile_' + pattern.replace(/[^a-zA-Z0-9]/g, '_');
                const isWildcard = pattern.includes('*') || pattern.includes('?');
                const checked = currentSystemFiles.has(pattern) ? 'checked' : '';
                return `
                    <div class="checkbox-item ${isWildcard ? 'is-wildcard' : ''}">
                        <input type="checkbox" id="${id}" value="${pattern}" ${checked} onchange="toggleSystemFile('${pattern}', this.checked)">
                        <label for="${id}" title="${pattern}">${pattern}</label>
                    </div>
                `;
            }).join('');
        }
        
        function toggleSystemFile(pattern, enabled) {
            if (enabled) {
                currentSystemFiles.add(pattern);
            } else {
                currentSystemFiles.delete(pattern);
            }
        }
        
        function addCustomSystemFile() {
            const input = document.getElementById('customSystemFile');
            const pattern = input.value.trim();
            if (pattern && !allSystemFilePatterns.has(pattern)) {
                allSystemFilePatterns.add(pattern);
                currentSystemFiles.add(pattern);
                renderSystemFileCheckboxes();
                input.value = '';
            } else if (allSystemFilePatterns.has(pattern)) {
                // Pattern exists, just enable it
                currentSystemFiles.add(pattern);
                renderSystemFileCheckboxes();
                input.value = '';
            }
        }
        
        function loadSystemFilesFromConfig(systemFiles) {
            // Add any new patterns from config to our known patterns
            systemFiles.forEach(f => allSystemFilePatterns.add(f));
            // Set current enabled files
            currentSystemFiles = new Set(systemFiles);
            renderSystemFileCheckboxes();
        }
        
        function getEnabledSystemFiles() {
            return Array.from(currentSystemFiles);
        }
        
        function resetSettings() {
            if (confirm('Reset all settings to defaults?')) {
                document.getElementById('settingsIgnoreSystem').checked = true;
                allSystemFilePatterns = new Set(defaultSystemFiles);
                currentSystemFiles = new Set(defaultSystemFiles);
                renderSystemFileCheckboxes();
                document.getElementById('excludePatternsList').value = '.git\\nnode_modules\\n__pycache__\\n.venv\\n.env';
                document.getElementById('settingsPort').value = '8765';
                document.getElementById('settingsExportFormat').value = 'json';
            }
        }
        
        function showToast(message, type) {
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);
            
            // Animate in
            setTimeout(() => toast.classList.add('show'), 10);
            
            // Remove after delay
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
        
        function togglePassword(inputId) {
            const input = document.getElementById(inputId);
            input.type = input.type === 'password' ? 'text' : 'password';
        }
        
        async function loadCredentials() {
            try {
                // Load credentials
                const credResponse = await fetch('/api/credentials');
                const credData = await credResponse.json();
                document.getElementById('settingsAppKey').value = credData.app_key || '';
                document.getElementById('settingsAppSecret').value = credData.app_secret || '';
                document.getElementById('settingsRefreshToken').value = credData.refresh_token || '';
                
                // Update connection status in settings
                const statusEl = document.getElementById('settingsConnectionStatus');
                const indicator = statusEl.querySelector('.status-indicator');
                const info = document.getElementById('settingsAccountInfo');
                
                if (credData.connected) {
                    indicator.className = 'status-indicator connected';
                    info.textContent = `Connected as ${credData.account_name}`;
                } else {
                    indicator.className = 'status-indicator disconnected';
                    info.textContent = 'Not connected';
                }
                
                // Also load config
                const configResponse = await fetch('/api/config');
                const config = await configResponse.json();
                document.getElementById('settingsIgnoreSystem').checked = config.ignore_system_files !== false;
                loadSystemFilesFromConfig(config.system_files || defaultSystemFiles);
                document.getElementById('excludePatternsList').value = (config.exclude_patterns || []).join('\\n');
                document.getElementById('settingsPort').value = config.port || 8765;
                document.getElementById('settingsExportFormat').value = config.export_format || 'json';
                
            } catch (e) {
                console.error('Failed to load credentials/config:', e);
            }
        }
        
        function startAuth() {
            const appKey = document.getElementById('settingsAppKey').value.trim();
            const appSecret = document.getElementById('settingsAppSecret').value.trim();
            
            if (!appKey || !appSecret) {
                showToast('Please enter App Key and App Secret first', 'error');
                return;
            }
            
            document.getElementById('authModal').classList.add('active');
        }
        
        function closeAuth() {
            document.getElementById('authModal').classList.remove('active');
            document.getElementById('authCode').value = '';
        }
        
        function openAuthUrl() {
            const appKey = document.getElementById('settingsAppKey').value.trim();
            const authUrl = `https://www.dropbox.com/oauth2/authorize?client_id=${appKey}&response_type=code&token_access_type=offline`;
            window.open(authUrl, '_blank');
        }
        
        async function exchangeCode() {
            const appKey = document.getElementById('settingsAppKey').value.trim();
            const appSecret = document.getElementById('settingsAppSecret').value.trim();
            const code = document.getElementById('authCode').value.trim();
            
            if (!code) {
                showToast('Please enter the authorization code', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/auth/exchange', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_key: appKey, app_secret: appSecret, code: code})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('settingsRefreshToken').value = data.refresh_token;
                    closeAuth();
                    showToast('Authorization successful! Click Save Settings to apply.', 'success');
                } else {
                    showToast(`Authorization failed: ${data.error}`, 'error');
                }
            } catch (e) {
                console.error('Exchange failed:', e);
                showToast('Authorization failed. Check console for details.', 'error');
            }
        }
        
        async function testConnection() {
            const appKey = document.getElementById('settingsAppKey').value.trim();
            const appSecret = document.getElementById('settingsAppSecret').value.trim();
            const refreshToken = document.getElementById('settingsRefreshToken').value.trim();
            
            if (!appKey || !appSecret || !refreshToken) {
                showToast('Please enter all credentials first', 'error');
                return;
            }
            
            showToast('Testing connection...', 'info');
            
            try {
                const response = await fetch('/api/auth/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_key: appKey, app_secret: appSecret, refresh_token: refreshToken})
                });
                
                const data = await response.json();
                
                const indicator = document.querySelector('#settingsConnectionStatus .status-indicator');
                const info = document.getElementById('settingsAccountInfo');
                
                if (data.success) {
                    indicator.className = 'status-indicator connected';
                    info.textContent = `Connected as ${data.account_name}`;
                    showToast(`Connected as ${data.account_name}!`, 'success');
                } else {
                    indicator.className = 'status-indicator disconnected';
                    info.textContent = 'Connection failed';
                    showToast(`Connection failed: ${data.error}`, 'error');
                }
            } catch (e) {
                console.error('Test failed:', e);
                showToast('Connection test failed', 'error');
            }
        }
        
        // Override showSettings to also load credentials
        const originalShowSettings = showSettings;
        showSettings = async function() {
            try {
                await loadCredentials();
                // Show settings modal directly instead of calling original
                document.getElementById('settingsModal').classList.add('active');
            } catch (e) {
                console.error('Error opening settings:', e);
                // Still show the modal even if credentials fail to load
                document.getElementById('settingsModal').classList.add('active');
            }
        };
        
        // Override saveSettings to also save credentials
        const originalSaveSettings = saveSettings;
        saveSettings = async function() {
            // Save credentials
            const credentials = {
                app_key: document.getElementById('settingsAppKey').value.trim(),
                app_secret: document.getElementById('settingsAppSecret').value.trim(),
                refresh_token: document.getElementById('settingsRefreshToken').value.trim()
            };
            
            try {
                await fetch('/api/credentials', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(credentials)
                });
            } catch (e) {
                console.error('Failed to save credentials:', e);
            }
            
            // Call original save
            await originalSaveSettings();
        };
        
        // Setup Wizard Functions
        let currentWizardStep = 1;
        
        function showSetupWizard() {
            currentWizardStep = 1;
            updateWizardStep(1);
            document.getElementById('setupWizard').classList.add('active');
        }
        
        function closeWizard() {
            document.getElementById('setupWizard').classList.remove('active');
            // Refresh the page to update connection status
            location.reload();
        }
        
        function updateWizardStep(step) {
            // Hide all content
            for (let i = 1; i <= 4; i++) {
                const content = document.getElementById(`wizStep${i}`);
                const indicator = document.getElementById(`wizStep${i}Indicator`);
                if (content) content.style.display = 'none';
                if (indicator) {
                    indicator.classList.remove('active', 'completed');
                    if (i < step) indicator.classList.add('completed');
                    if (i === step) indicator.classList.add('active');
                }
            }
            document.getElementById('wizStepSuccess').style.display = 'none';
            
            // Show current step
            const currentContent = document.getElementById(`wizStep${step}`);
            if (currentContent) currentContent.style.display = 'block';
            
            currentWizardStep = step;
        }
        
        function wizardNext(step) {
            updateWizardStep(step);
        }
        
        function wizardBack(step) {
            updateWizardStep(step);
        }
        
        function wizardValidateAndNext() {
            const appKey = document.getElementById('wizardAppKey').value.trim();
            const appSecret = document.getElementById('wizardAppSecret').value.trim();
            
            if (!appKey) {
                showToast('Please enter your App Key', 'error');
                document.getElementById('wizardAppKey').focus();
                return;
            }
            
            if (!appSecret) {
                showToast('Please enter your App Secret', 'error');
                document.getElementById('wizardAppSecret').focus();
                return;
            }
            
            if (appKey.length < 10) {
                showToast('App Key seems too short. Please check and try again.', 'error');
                return;
            }
            
            if (appSecret.length < 10) {
                showToast('App Secret seems too short. Please check and try again.', 'error');
                return;
            }
            
            wizardNext(4);
        }
        
        function wizardOpenAuth() {
            const appKey = document.getElementById('wizardAppKey').value.trim();
            if (!appKey) {
                showToast('Please go back and enter your App Key first', 'error');
                return;
            }
            const authUrl = `https://www.dropbox.com/oauth2/authorize?client_id=${appKey}&response_type=code&token_access_type=offline`;
            window.open(authUrl, '_blank');
        }
        
        async function wizardComplete() {
            const appKey = document.getElementById('wizardAppKey').value.trim();
            const appSecret = document.getElementById('wizardAppSecret').value.trim();
            const code = document.getElementById('wizardAuthCode').value.trim();
            
            if (!code) {
                showToast('Please enter the authorization code from Dropbox', 'error');
                document.getElementById('wizardAuthCode').focus();
                return;
            }
            
            showToast('Completing setup...', 'info');
            
            try {
                // Exchange code for token
                const exchangeResponse = await fetch('/api/auth/exchange', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({app_key: appKey, app_secret: appSecret, code: code})
                });
                
                const exchangeData = await exchangeResponse.json();
                
                if (!exchangeData.success) {
                    showToast(`Authorization failed: ${exchangeData.error}`, 'error');
                    return;
                }
                
                // Save credentials
                await fetch('/api/credentials', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        app_key: appKey,
                        app_secret: appSecret,
                        refresh_token: exchangeData.refresh_token
                    })
                });
                
                // Test connection to get account name
                const testResponse = await fetch('/api/auth/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        app_key: appKey,
                        app_secret: appSecret,
                        refresh_token: exchangeData.refresh_token
                    })
                });
                
                const testData = await testResponse.json();
                
                if (testData.success) {
                    // Show success
                    document.getElementById('wizardSuccessAccount').textContent = `Connected as: ${testData.account_name}`;
                    
                    // Mark all steps completed
                    for (let i = 1; i <= 4; i++) {
                        document.getElementById(`wizStep${i}Indicator`).classList.add('completed');
                        document.getElementById(`wizStep${i}Indicator`).classList.remove('active');
                    }
                    
                    // Hide all steps and show success
                    for (let i = 1; i <= 4; i++) {
                        document.getElementById(`wizStep${i}`).style.display = 'none';
                    }
                    document.getElementById('wizStepSuccess').style.display = 'block';
                    
                    showToast('Setup complete!', 'success');
                } else {
                    showToast(`Connection test failed: ${testData.error}`, 'error');
                }
            } catch (e) {
                console.error('Wizard error:', e);
                showToast('Setup failed. Please check your credentials and try again.', 'error');
            }
        }
        
        // Check if setup is needed on page load
        async function checkSetupNeeded() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (!data.connected) {
                    // Show setup wizard after a short delay
                    setTimeout(() => {
                        showSetupWizard();
                    }, 1000);
                }
            } catch (e) {
                console.error('Failed to check status:', e);
            }
        }
        
        // Disclaimer functions
        function showDisclaimer() {
            document.getElementById('disclaimerModal').classList.add('active');
        }
        
        function acceptDisclaimer() {
            localStorage.setItem('disclaimerAccepted', 'true');
            localStorage.setItem('disclaimerDate', new Date().toISOString());
            document.getElementById('disclaimerModal').classList.remove('active');
        }
        
        function checkDisclaimerAccepted() {
            const accepted = localStorage.getItem('disclaimerAccepted');
            if (!accepted) {
                // Show disclaimer on first visit
                setTimeout(() => {
                    showDisclaimer();
                }, 500);
            }
        }
        
        // Direct function to open settings modal - defined before event listeners
        window.openSettingsModal = async function() {
            console.log('Opening settings modal...');
            try {
                // Load credentials
                const credResponse = await fetch('/api/credentials');
                const credData = await credResponse.json();
                console.log('Credentials loaded:', credData.connected);
                
                document.getElementById('settingsAppKey').value = credData.app_key || '';
                document.getElementById('settingsAppSecret').value = credData.app_secret || '';
                document.getElementById('settingsRefreshToken').value = credData.refresh_token || '';
                
                // Update connection status in settings
                const statusEl = document.getElementById('settingsConnectionStatus');
                if (statusEl) {
                    const indicator = statusEl.querySelector('.status-indicator');
                    const info = document.getElementById('settingsAccountInfo');
                    
                    if (credData.connected) {
                        indicator.className = 'status-indicator connected';
                        info.textContent = 'Connected as ' + credData.account_name;
                    } else {
                        indicator.className = 'status-indicator disconnected';
                        info.textContent = 'Not connected';
                    }
                }
                
                // Load config
                const configResponse = await fetch('/api/config');
                const config = await configResponse.json();
                console.log('Config loaded');
                
                document.getElementById('settingsIgnoreSystem').checked = config.ignore_system_files !== false;
                loadSystemFilesFromConfig(config.system_files || defaultSystemFiles);
                document.getElementById('excludePatternsList').value = (config.exclude_patterns || []).join('\\n');
                document.getElementById('settingsPort').value = config.port || 8765;
                document.getElementById('settingsExportFormat').value = config.export_format || 'json';
                
            } catch (e) {
                console.error('Error loading settings data:', e);
            }
            
            // Show the modal
            console.log('Showing settings modal');
            document.getElementById('settingsModal').classList.add('active');
        };
        
        // Add event listeners for navigation buttons
        document.getElementById('settingsNavBtn').addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Settings nav button clicked');
            window.openSettingsModal();
        });
        
        document.getElementById('helpNavBtn').addEventListener('click', function(e) {
            e.preventDefault();
            showHelp();
        });
        
        document.getElementById('disclaimerNavBtn').addEventListener('click', function(e) {
            e.preventDefault();
            showDisclaimer();
        });
        
        // Also add listener for inline settings button
        document.getElementById('inlineSettingsBtn').addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Inline settings button clicked');
            window.openSettingsModal();
        });
        
        // Start polling
        console.log('=== STARTING INITIALIZATION ===');
        try {
            fetchStatus();
            console.log('fetchStatus() called successfully');
        } catch(e) {
            console.error('Error calling fetchStatus:', e);
        }
        pollInterval = setInterval(fetchStatus, 400);
        console.log('Poll interval set');
        
        // Load folder tree
        console.log('Initializing - calling loadRootFolders...');
        loadRootFolders().then(() => {
            console.log('Root folders loaded successfully');
        }).catch(e => {
            console.error('Failed to load root folders on init:', e);
        });
        
        // Check if setup is needed
        checkSetupNeeded();
        
        // Check if disclaimer needs to be shown
        checkDisclaimerAccepted();
    </script>
</body>
</html>
'''


class DropboxHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the web GUI."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_html(self, html):
        """Send HTML response."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.send_html(HTML_PAGE)
        elif self.path.startswith('/api/subfolders'):
            # Get subfolders for a given path
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            folder_path = params.get('path', [''])[0]
            
            if not app_state["connected"] or not app_state["dbx"]:
                self.send_json({"error": "Not connected", "subfolders": []})
            else:
                try:
                    dbx = app_state["dbx"]
                    # List folder contents (non-recursive, folders only)
                    result = dbx.files_list_folder(folder_path if folder_path else "")
                    subfolders = []
                    
                    while True:
                        for entry in result.entries:
                            if isinstance(entry, dropbox.files.FolderMetadata):
                                subfolders.append({
                                    "name": entry.name,
                                    "path": entry.path_display
                                })
                        if not result.has_more:
                            break
                        result = dbx.files_list_folder_continue(result.cursor)
                    
                    # Sort alphabetically
                    subfolders.sort(key=lambda x: x["name"].lower())
                    self.send_json({"subfolders": subfolders})
                except Exception as e:
                    logger.error(f"Error listing subfolders for {folder_path}: {e}")
                    self.send_json({"error": str(e), "subfolders": []})
        elif self.path == '/api/status':
            self.send_json({
                "connected": app_state["connected"],
                "account_name": app_state["account_name"],
                "account_email": app_state["account_email"],
                "folders": app_state["folders"],
                "scanning": app_state["scanning"],
                "scan_progress": app_state["scan_progress"],
                "empty_folders": [app_state["case_map"].get(f, f) for f in app_state["empty_folders"]],
                "deleting": app_state["deleting"],
                "delete_progress": app_state["delete_progress"],
                "config": app_state["config"],
                "stats": app_state["stats"]
            })
        elif self.path == '/api/config':
            self.send_json(app_state["config"])
        elif self.path == '/api/credentials':
            # Return credentials (masked for security)
            load_dotenv()
            self.send_json({
                "app_key": os.getenv("DROPBOX_APP_KEY", ""),
                "app_secret": os.getenv("DROPBOX_APP_SECRET", ""),
                "refresh_token": os.getenv("DROPBOX_REFRESH_TOKEN", ""),
                "connected": app_state["connected"],
                "account_name": app_state["account_name"]
            })
        elif self.path.startswith('/api/export'):
            self.handle_export()
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_export(self):
        """Handle export requests."""
        query = urlparse(self.path).query
        params = parse_qs(query)
        export_format = params.get('format', ['json'])[0]
        
        empty_folders = [app_state["case_map"].get(f, f) for f in app_state["empty_folders"]]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_format == 'csv':
            # CSV format
            content = "Path,Depth\n"
            for folder in empty_folders:
                depth = folder.count('/')
                content += f'"{folder}",{depth}\n'
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv')
            self.send_header('Content-Disposition', f'attachment; filename="empty_folders_{timestamp}.csv"')
            self.end_headers()
            self.wfile.write(content.encode())
        else:
            # JSON format
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "scan_folder": app_state["last_scan_folder"] or "/",
                "account": app_state["account_name"],
                "total_empty_folders": len(empty_folders),
                "stats": app_state["stats"],
                "config_used": {
                    "ignore_system_files": app_state["config"].get("ignore_system_files"),
                    "system_files": app_state["config"].get("system_files"),
                    "exclude_patterns": app_state["config"].get("exclude_patterns")
                },
                "empty_folders": [{"path": f, "depth": f.count('/')} for f in empty_folders]
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Disposition', f'attachment; filename="empty_folders_{timestamp}.json"')
            self.end_headers()
            self.wfile.write(json.dumps(export_data, indent=2).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            data = json.loads(body) if body else {}
        except Exception as e:
            logger.warning(f"Failed to parse JSON body: {e}")
            data = {}
        
        if self.path == '/api/scan':
            folder = data.get('folder', '')
            logger.info(f"API request: Start scan for folder '{folder if folder else '/'}'")
            threading.Thread(target=scan_folder, args=(folder,), daemon=True).start()
            self.send_json({"status": "started"})
        elif self.path == '/api/delete':
            logger.info("API request: Start deletion")
            threading.Thread(target=delete_folders, daemon=True).start()
            self.send_json({"status": "started"})
        elif self.path == '/api/config':
            # Update configuration
            logger.info(f"API request: Update config with {data}")
            app_state["config"].update(data)
            save_config(app_state["config"])
            self.send_json({"status": "ok", "config": app_state["config"]})
        elif self.path == '/api/credentials':
            # Save credentials to .env file
            logger.info("API request: Update credentials")
            save_credentials(data)
            # Reconnect with new credentials
            if connect_dropbox():
                self.send_json({"status": "ok", "connected": True})
            else:
                self.send_json({"status": "ok", "connected": False})
        elif self.path == '/api/auth/exchange':
            # Exchange authorization code for refresh token
            logger.info("API request: Exchange auth code")
            result = exchange_auth_code(data)
            self.send_json(result)
        elif self.path == '/api/auth/test':
            # Test connection with provided credentials
            logger.info("API request: Test connection")
            result = test_credentials(data)
            self.send_json(result)
        else:
            logger.warning(f"Unknown API endpoint: {self.path}")
            self.send_response(404)
            self.end_headers()


def save_credentials(creds):
    """Save credentials to .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # Read existing .env content
    existing = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    existing[key] = value
    
    # Update with new credentials
    if creds.get('app_key'):
        existing['DROPBOX_APP_KEY'] = f'"{creds["app_key"]}"'
    if creds.get('app_secret'):
        existing['DROPBOX_APP_SECRET'] = f'"{creds["app_secret"]}"'
    if creds.get('refresh_token'):
        existing['DROPBOX_REFRESH_TOKEN'] = f'"{creds["refresh_token"]}"'
    
    # Write back
    with open(env_path, 'w') as f:
        for key, value in existing.items():
            f.write(f'{key}={value}\n')
    
    logger.info("Credentials saved to .env file")
    
    # Reload environment
    load_dotenv(override=True)


def exchange_auth_code(data):
    """Exchange authorization code for refresh token."""
    import urllib.request
    import urllib.parse
    
    app_key = data.get('app_key', '')
    app_secret = data.get('app_secret', '')
    code = data.get('code', '')
    
    if not all([app_key, app_secret, code]):
        return {"success": False, "error": "Missing credentials or code"}
    
    try:
        # Exchange code for token
        token_url = "https://api.dropboxapi.com/oauth2/token"
        post_data = urllib.parse.urlencode({
            'code': code,
            'grant_type': 'authorization_code'
        }).encode()
        
        # Create request with basic auth
        import base64
        auth_header = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
        
        req = urllib.request.Request(token_url, data=post_data)
        req.add_header('Authorization', f'Basic {auth_header}')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            refresh_token = result.get('refresh_token')
            
            if refresh_token:
                logger.info("Successfully exchanged auth code for refresh token")
                return {"success": True, "refresh_token": refresh_token}
            else:
                return {"success": False, "error": "No refresh token in response"}
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logger.error(f"Token exchange failed: {e.code} - {error_body}")
        return {"success": False, "error": f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return {"success": False, "error": str(e)}


def test_credentials(data):
    """Test Dropbox credentials."""
    app_key = data.get('app_key', '')
    app_secret = data.get('app_secret', '')
    refresh_token = data.get('refresh_token', '')
    
    if not all([app_key, app_secret, refresh_token]):
        return {"success": False, "error": "Missing credentials"}
    
    try:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        account = dbx.users_get_current_account()
        logger.info(f"Test connection successful: {account.name.display_name}")
        return {
            "success": True,
            "account_name": account.name.display_name,
            "email": account.email
        }
    except Exception as e:
        logger.error(f"Test connection failed: {e}")
        return {"success": False, "error": str(e)}


def connect_dropbox():
    """Connect to Dropbox."""
    logger.info("Attempting to connect to Dropbox...")
    load_dotenv()
    
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    
    logger.debug(f"App key present: {bool(app_key)}")
    logger.debug(f"App secret present: {bool(app_secret)}")
    logger.debug(f"Refresh token present: {bool(refresh_token)}")
    
    if not all([app_key, app_secret, refresh_token]):
        logger.error("Missing credentials in .env file")
        print("❌ Missing credentials in .env file")
        return False
    
    try:
        logger.debug("Creating Dropbox client with OAuth2 refresh token...")
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        
        logger.debug("Fetching account information...")
        account = dbx.users_get_current_account()
        
        app_state["dbx"] = dbx
        app_state["connected"] = True
        app_state["account_name"] = account.name.display_name
        app_state["account_email"] = account.email
        
        logger.info(f"Successfully connected as: {account.name.display_name} ({account.email})")
        
        # Load folders - include ALL folders (including conflict copies)
        logger.debug("Loading root folders...")
        result = dbx.files_list_folder('')
        folders = [e.path_display for e in result.entries 
                  if isinstance(e, FolderMetadata)]
        folders.sort()
        app_state["folders"] = folders
        
        logger.info(f"Found {len(folders)} root-level folders")
        logger.debug(f"Root folders: {folders[:10]}{'...' if len(folders) > 10 else ''}")
        
        print(f"✅ Connected as: {account.name.display_name}")
        return True
        
    except AuthError as e:
        logger.error(f"Authentication failed: {e}")
        print(f"❌ Connection failed: {e}")
        return False
    except ApiError as e:
        logger.error(f"Dropbox API error: {e}")
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error during connection: {e}")
        print(f"❌ Connection failed: {e}")
        return False


def is_system_file(filename):
    """Check if a file is a system file that should be ignored.
    Supports exact matches and wildcard patterns (e.g., *.alias, *.symlink)
    """
    import fnmatch
    config = app_state["config"]
    if not config.get("ignore_system_files", True):
        return False
    system_files = config.get("system_files", [])
    filename_lower = filename.lower()
    
    for pattern in system_files:
        pattern_lower = pattern.lower()
        # Check for exact match
        if filename_lower == pattern_lower:
            return True
        # Check for wildcard pattern match (e.g., *.alias, *.symlink)
        if '*' in pattern or '?' in pattern:
            if fnmatch.fnmatch(filename_lower, pattern_lower):
                return True
    return False

def should_exclude_folder(folder_path):
    """Check if a folder should be excluded based on patterns."""
    config = app_state["config"]
    exclude_patterns = config.get("exclude_patterns", [])
    folder_name = os.path.basename(folder_path)
    return folder_name.lower() in [p.lower() for p in exclude_patterns]

def scan_folder(folder_path):
    """Scan a folder for empty folders."""
    display_path = folder_path if folder_path else "/ (entire Dropbox)"
    logger.info(f"Starting scan of: {display_path}")
    
    config = app_state["config"]
    logger.info(f"Ignore system files: {config.get('ignore_system_files', True)}")
    logger.info(f"System files: {config.get('system_files', [])}")
    logger.info(f"Exclude patterns: {config.get('exclude_patterns', [])}")
    
    start_time = time.time()
    app_state["scanning"] = True
    app_state["scan_progress"] = {
        "folders": 0, 
        "files": 0, 
        "status": "scanning", 
        "start_time": start_time,
        "elapsed": 0,
        "rate": 0
    }
    app_state["empty_folders"] = []
    app_state["case_map"] = {}
    app_state["last_scan_folder"] = folder_path
    app_state["stats"] = {"depth_distribution": {}, "total_scanned": 0, "system_files_ignored": 0, "excluded_folders": 0}
    
    dbx = app_state["dbx"]
    all_folders = set()
    folders_with_content = set()
    folders_with_only_system_files = set()  # Track folders with only system files
    batch_count = 0
    system_files_ignored = 0
    excluded_folders = 0
    
    try:
        logger.debug(f"Calling files_list_folder with recursive=True for path: '{folder_path}'")
        result = dbx.files_list_folder(folder_path, recursive=True)
        
        while True:
            batch_count += 1
            batch_folders = 0
            batch_files = 0
            
            for entry in result.entries:
                if isinstance(entry, FolderMetadata):
                    # Check if folder should be excluded
                    if should_exclude_folder(entry.path_display):
                        excluded_folders += 1
                        logger.debug(f"Excluding folder (pattern match): {entry.path_display}")
                        continue
                    
                    all_folders.add(entry.path_lower)
                    app_state["case_map"][entry.path_lower] = entry.path_display
                    app_state["scan_progress"]["folders"] = len(all_folders)
                    batch_folders += 1
                else:
                    parent_path = os.path.dirname(entry.path_lower)
                    
                    # Check if this is a system file that should be ignored
                    filename = os.path.basename(entry.path_display)
                    if is_system_file(filename):
                        system_files_ignored += 1
                        folders_with_only_system_files.add(parent_path)
                        logger.debug(f"Ignoring system file: {entry.path_display}")
                    else:
                        # Only count legitimate (non-ignored) files
                        app_state["scan_progress"]["files"] += 1
                        folders_with_content.add(parent_path)
                        batch_files += 1
            
            # Update elapsed time and rate
            elapsed = time.time() - start_time
            total_items = app_state["scan_progress"]["folders"] + app_state["scan_progress"]["files"]
            app_state["scan_progress"]["elapsed"] = elapsed
            app_state["scan_progress"]["rate"] = int(total_items / elapsed) if elapsed > 0 else 0
            
            logger.debug(f"Batch {batch_count}: +{batch_folders} folders, +{batch_files} files | Total: {len(all_folders)} folders, {app_state['scan_progress']['files']} files")
            
            if not result.has_more:
                logger.debug("No more results, scan complete")
                break
            
            result = dbx.files_list_folder_continue(result.cursor)
        
        # Final timing update
        elapsed = time.time() - start_time
        total_items = app_state["scan_progress"]["folders"] + app_state["scan_progress"]["files"]
        app_state["scan_progress"]["elapsed"] = elapsed
        app_state["scan_progress"]["rate"] = int(total_items / elapsed) if elapsed > 0 else 0
        
        # Update stats
        app_state["stats"]["total_scanned"] = len(all_folders)
        app_state["stats"]["system_files_ignored"] = system_files_ignored
        app_state["stats"]["excluded_folders"] = excluded_folders
        
        logger.info(f"Scan complete: {len(all_folders)} folders, {app_state['scan_progress']['files']} files in {elapsed:.2f}s ({batch_count} batches)")
        logger.info(f"System files ignored: {system_files_ignored}, Excluded folders: {excluded_folders}")
        
        # Find empty folders (folders with only system files are considered empty)
        logger.debug("Analyzing folder structure to find empty folders...")
        empty = find_empty_folders(all_folders, folders_with_content)
        app_state["empty_folders"] = empty
        app_state["scan_progress"]["status"] = "complete"
        
        # Calculate depth distribution
        depth_dist = {}
        for folder in empty:
            depth = folder.count('/')
            depth_dist[depth] = depth_dist.get(depth, 0) + 1
        app_state["stats"]["depth_distribution"] = depth_dist
        
        logger.info(f"Found {len(empty)} empty folder(s)")
        if empty:
            logger.debug(f"Empty folders: {[app_state['case_map'].get(f, f) for f in empty[:10]]}{'...' if len(empty) > 10 else ''}")
            logger.info(f"Depth distribution: {depth_dist}")
        
    except ApiError as e:
        logger.error(f"Dropbox API error during scan: {e}")
        logger.debug(f"API error details: {e.error if hasattr(e, 'error') else 'N/A'}")
        print(f"Scan error: {e}")
        app_state["scan_progress"]["status"] = "error"
    except Exception as e:
        logger.exception(f"Unexpected error during scan: {e}")
        print(f"Scan error: {e}")
        app_state["scan_progress"]["status"] = "error"
    
    app_state["scanning"] = False
    logger.debug("Scan thread finished")


def find_empty_folders(all_folders, folders_with_content):
    """Find truly empty folders."""
    logger.debug(f"Analyzing {len(all_folders)} folders, {len(folders_with_content)} have direct content")
    
    # Build parent-child relationships
    children = defaultdict(set)
    for folder in all_folders:
        parent = os.path.dirname(folder)
        if parent in all_folders:
            children[parent].add(folder)
    
    has_content = set(folders_with_content)
    
    # Propagate content markers upward
    for folder in folders_with_content:
        current = folder
        while current:
            has_content.add(current)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    
    # Mark folders with non-empty children
    iterations = 0
    changed = True
    while changed:
        changed = False
        iterations += 1
        for folder in all_folders:
            if folder in has_content:
                continue
            for child in children[folder]:
                if child in has_content:
                    has_content.add(folder)
                    changed = True
                    break
    
    empty_folders = all_folders - has_content
    sorted_empty = sorted(empty_folders, key=lambda x: x.count('/'), reverse=True)
    
    logger.debug(f"Analysis complete: {iterations} iterations, {len(sorted_empty)} empty folders found")
    if sorted_empty:
        max_depth = max(f.count('/') for f in sorted_empty)
        min_depth = min(f.count('/') for f in sorted_empty)
        logger.debug(f"Empty folder depths: min={min_depth}, max={max_depth}")
    
    return sorted_empty


def verify_folder_empty(dbx, folder_path):
    """
    FAIL-SAFE: Independently verify a folder is truly empty before deletion.
    Makes a direct API call to check for any files in the folder's subtree.
    Returns: (is_empty: bool, file_count: int, error: str or None)
    """
    try:
        result = dbx.files_list_folder(folder_path, recursive=True)
        file_count = 0
        
        while True:
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    file_count += 1
                    # Found a file - no need to continue
                    if file_count > 0:
                        return False, file_count, None
            
            if not result.has_more:
                break
            result = dbx.files_list_folder_continue(result.cursor)
        
        return file_count == 0, file_count, None
        
    except ApiError as e:
        if hasattr(e.error, 'is_path') and e.error.is_path():
            # Folder doesn't exist - might have been deleted already
            return True, 0, "folder_not_found"
        return False, 0, str(e)
    except Exception as e:
        return False, 0, str(e)


def delete_folders():
    """Delete empty folders with fail-safe verification before each deletion."""
    total = len(app_state["empty_folders"])
    logger.info(f"Starting deletion of {total} empty folder(s)")
    logger.warning("⚠️  DELETION OPERATION INITIATED - folders will be moved to Dropbox trash")
    logger.info("🛡️  FAIL-SAFE ENABLED: Each folder will be re-verified before deletion")
    
    app_state["deleting"] = True
    app_state["delete_progress"] = {"current": 0, "total": total, "status": "deleting", "percent": 0}
    
    dbx = app_state["dbx"]
    deleted_count = 0
    skipped_count = 0  # Folders skipped because they're no longer empty
    error_count = 0
    start_time = time.time()
    
    for i, folder in enumerate(app_state["empty_folders"]):
        display_path = app_state["case_map"].get(folder, folder)
        
        # FAIL-SAFE: Verify folder is still empty before deleting
        logger.debug(f"Verifying [{i+1}/{total}]: {display_path}")
        is_empty, file_count, error = verify_folder_empty(dbx, folder)
        
        if error == "folder_not_found":
            # Folder already deleted (possibly parent was deleted)
            logger.debug(f"⊘ Already gone: {display_path}")
            deleted_count += 1  # Count as success
        elif error:
            # Verification failed - skip this folder for safety
            error_count += 1
            logger.error(f"✗ Verification failed for {display_path}: {error}")
            logger.warning(f"  SKIPPED deletion for safety")
        elif not is_empty:
            # FAIL-SAFE TRIGGERED: Folder has files now!
            skipped_count += 1
            logger.warning(f"🛡️  FAIL-SAFE: {display_path} is NO LONGER EMPTY!")
            logger.warning(f"   Found {file_count} file(s) - SKIPPING deletion")
        else:
            # Verified empty - safe to delete
            try:
                logger.debug(f"Deleting [{i+1}/{total}]: {display_path}")
                dbx.files_delete_v2(folder)
                deleted_count += 1
                logger.info(f"✓ Deleted: {display_path}")
            except ApiError as e:
                if 'not_found' in str(e).lower():
                    # Already deleted
                    deleted_count += 1
                    logger.debug(f"⊘ Already deleted: {display_path}")
                else:
                    error_count += 1
                    logger.error(f"✗ Failed to delete {display_path}: {e}")
            except Exception as e:
                error_count += 1
                logger.exception(f"✗ Unexpected error deleting {display_path}: {e}")
        
        current = i + 1
        app_state["delete_progress"]["current"] = current
        app_state["delete_progress"]["percent"] = int((current / total) * 100) if total > 0 else 100
    
    elapsed = time.time() - start_time
    app_state["empty_folders"] = []
    app_state["delete_progress"]["status"] = "complete"
    app_state["delete_progress"]["percent"] = 100
    app_state["deleting"] = False
    
    # Detailed completion log
    logger.info(f"=" * 60)
    logger.info(f"DELETION COMPLETE")
    logger.info(f"=" * 60)
    logger.info(f"  ✓ Successfully deleted: {deleted_count}")
    logger.info(f"  🛡️  Skipped (fail-safe): {skipped_count}")
    logger.info(f"  ✗ Errors: {error_count}")
    logger.info(f"  ⏱️  Time: {elapsed:.2f}s")
    logger.info(f"=" * 60)
    
    if skipped_count > 0:
        logger.warning(f"⚠️  {skipped_count} folder(s) were SKIPPED because they gained files since the scan")
        logger.warning(f"   Run a new scan to see updated results")
    if error_count > 0:
        logger.warning(f"⚠️  {error_count} folder(s) had errors - check log for details")


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     📁 DROPBOX EMPTY FOLDER CLEANER - Web GUI                ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    if not connect_dropbox():
        logger.error("Failed to connect to Dropbox - exiting")
        print("\nRun 'python3 dropbox_auth.py' to set up authentication.")
        sys.exit(1)
    
    port = app_state["config"].get("port", 8765)
    
    try:
        server = HTTPServer(('127.0.0.1', port), DropboxHandler)
        logger.info(f"Web server started on http://127.0.0.1:{port}")
    except OSError as e:
        logger.error(f"Failed to start server on port {port}: {e}")
        print(f"❌ Port {port} is already in use. Stop any existing server and try again.")
        sys.exit(1)
    
    url = f"http://127.0.0.1:{port}"
    print(f"\n🌐 Starting web server at: {url}")
    print("   Opening browser...")
    print(f"   Log file: logs/dropbox_cleaner_*.log")
    print("\n   Press Ctrl+C to stop the server.\n")
    
    # Open browser after short delay
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    
    try:
        logger.info("Server ready - waiting for requests")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested (Ctrl+C)")
        print("\n\n👋 Server stopped.")
        server.shutdown()
    
    logger.info("Application terminated")


if __name__ == "__main__":
    main()
