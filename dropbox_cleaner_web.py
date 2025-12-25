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
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 6px;
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
        }
        
        .success-icon {
            font-size: 4em;
            margin-bottom: 16px;
            animation: successBounce 1s ease;
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
        
        /* Help Button */
        .help-btn {
            position: fixed;
            top: 16px;
            right: 16px;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 100;
        }
        
        .help-btn:hover {
            background: var(--accent-cyan);
            color: white;
            border-color: var(--accent-cyan);
            transform: scale(1.1);
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
        
        /* Footer - Compact */
        footer {
            text-align: center;
            padding: 16px 10px;
            color: var(--text-secondary);
            font-size: 0.75em;
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
    
    <!-- Help Button -->
    <button class="help-btn" onclick="showHelp()" title="Help & Documentation">?</button>
    
    <div class="container">
        <header>
            <div class="logo">📁</div>
            <h1>Dropbox Empty Folder Cleaner</h1>
            <p class="subtitle">Find and remove empty folders from your Dropbox</p>
        </header>
        
        <div class="card">
            <div class="card-title">
                <span class="card-title-left">🔗 Connection Status</span>
                <span id="connectionStatus" class="status-badge status-disconnected">
                    <span class="status-dot"></span>
                    Connecting...
                </span>
            </div>
            <p id="accountInfo" style="color: var(--text-secondary);"></p>
        </div>
        
        <div class="card">
            <div class="card-title">
                <span class="card-title-left">📂 Select Folder to Scan</span>
            </div>
            <select id="folderSelect">
                <option value="">Loading folders...</option>
            </select>
            <div class="btn-group">
                <button id="scanBtn" class="btn btn-primary" onclick="startScan()">
                    🔍 Scan for Empty Folders
                </button>
                <button id="deleteBtn" class="btn btn-danger" onclick="confirmDelete()" disabled>
                    🗑️ Delete Empty Folders
                </button>
            </div>
            
            <!-- Settings Toggle -->
            <div class="settings-row" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color);">
                <label class="toggle-label">
                    <input type="checkbox" id="ignoreSystemFiles" checked onchange="updateConfig()">
                    <span class="toggle-text">Ignore system files (.DS_Store, Thumbs.db, etc.)</span>
                </label>
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
                    <div class="stat-card folders active" id="folderStatCard">
                        <div class="stat-icon">📁</div>
                        <div class="stat-value" id="folderCount">0</div>
                        <div class="stat-label">Folders Scanned</div>
                    </div>
                    <div class="stat-card files active" id="fileStatCard">
                        <div class="stat-icon">📄</div>
                        <div class="stat-value" id="fileCount">0</div>
                        <div class="stat-label">Files Found</div>
                    </div>
                    <div class="stat-card time active" id="timeStatCard">
                        <div class="stat-icon">⏱️</div>
                        <div class="stat-value" id="elapsedTime">0:00</div>
                        <div class="stat-label">Elapsed Time</div>
                    </div>
                    <div class="stat-card rate active" id="rateStatCard">
                        <div class="stat-icon">⚡</div>
                        <div class="stat-value" id="itemRate">0</div>
                        <div class="stat-label">Items/Second</div>
                    </div>
                    <div class="stat-card empty" id="emptyStatCard" style="display: none;">
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
                    <span id="resultsCount" class="results-count">0 empty folders</span>
                    <button class="btn-small" onclick="exportResults('json')" title="Export as JSON">📄 JSON</button>
                    <button class="btn-small" onclick="exportResults('csv')" title="Export as CSV">📊 CSV</button>
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
            Built for Tushar Shah • Powered by Dropbox API
        </footer>
    </div>
    
    <div class="modal-overlay" id="deleteModal">
        <div class="modal">
            <div class="modal-icon">⚠️</div>
            <h2>Confirm Deletion</h2>
            <p>
                You are about to delete <strong id="deleteCount">0</strong> empty folder(s).<br><br>
                This will move them to your Dropbox trash, where they can be recovered for 30 days.
            </p>
            <div class="btn-group">
                <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                <button class="btn btn-danger" onclick="executeDelete()">
                    🗑️ Delete Folders
                </button>
            </div>
        </div>
    </div>
    
    <!-- Help Modal -->
    <div class="modal-overlay" id="helpModal">
        <div class="modal help-modal">
            <div class="modal-icon">📖</div>
            <h2>Help & Documentation</h2>
            
            <h3>🎯 Purpose</h3>
            <p>This tool helps you find and remove empty folders from your Dropbox account. Over time, empty folders accumulate from deleted files, failed syncs, and reorganization.</p>
            
            <h3>📋 How to Use</h3>
            <div class="help-section">
                <ol>
                    <li><strong>Select a folder</strong> from the dropdown (or "/" for entire Dropbox)</li>
                    <li><strong>Click "Scan"</strong> to find empty folders</li>
                    <li><strong>Review the results</strong> - all empty folders will be listed</li>
                    <li><strong>Click "Delete"</strong> if you want to remove them</li>
                    <li><strong>Confirm</strong> in the popup dialog</li>
                </ol>
            </div>
            
            <h3>✨ Features</h3>
            <ul>
                <li><strong>Smart Detection</strong> - Finds truly empty folders (no files, no non-empty subfolders)</li>
                <li><strong>System File Ignore</strong> - Treats folders with only .DS_Store, Thumbs.db as empty (configurable)</li>
                <li><strong>Safe Deletion</strong> - Deletes deepest folders first, then parents</li>
                <li><strong>Real-time Progress</strong> - Live folder/file counts and elapsed time</li>
                <li><strong>Export Results</strong> - Export to JSON or CSV for records/analysis</li>
                <li><strong>Statistics</strong> - View depth distribution and scan metrics</li>
                <li><strong>Trash Recovery</strong> - Deleted folders go to Dropbox trash (30 days)</li>
                <li><strong>Configuration</strong> - Settings saved in config.json for customization</li>
            </ul>
            
            <h3>⚠️ Limitations</h3>
            <div class="help-warning">
                <strong>Important:</strong>
                <ul>
                    <li>Cannot recover folders once deleted from Dropbox trash</li>
                    <li>Does not check file contents, only if files exist</li>
                    <li>May not work with Team/shared folders</li>
                    <li>Large accounts may take several minutes to scan</li>
                </ul>
            </div>
            
            <h3>💡 Tips</h3>
            <div class="help-tip">
                <ul>
                    <li>Start with a small folder to test</li>
                    <li>Ensure Dropbox is fully synced before scanning</li>
                    <li>Review the list carefully before deleting</li>
                    <li>If rate limited, wait a few minutes and retry</li>
                </ul>
            </div>
            
            <h3>🔐 Privacy</h3>
            <p>Your credentials are stored locally in a .env file. This tool communicates directly with Dropbox - no data is sent to third parties.</p>
            
            <div class="btn-group" style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="closeHelp()">Got it!</button>
            </div>
        </div>
    </div>
    
    <script>
        let pollInterval = null;
        let emptyFolders = [];
        
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateUI(data);
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
        
        function updateUI(data) {
            // Connection status
            const statusEl = document.getElementById('connectionStatus');
            const accountEl = document.getElementById('accountInfo');
            
            if (data.connected) {
                statusEl.className = 'status-badge status-connected';
                statusEl.innerHTML = '<span class="status-dot"></span> Connected';
                accountEl.textContent = `Logged in as ${data.account_name} (${data.account_email})`;
            } else {
                statusEl.className = 'status-badge status-disconnected';
                statusEl.innerHTML = '<span class="status-dot"></span> Disconnected';
            }
            
            // Folders dropdown
            const folderSelect = document.getElementById('folderSelect');
            if (data.folders.length > 0 && folderSelect.options.length <= 1) {
                folderSelect.innerHTML = '<option value="">/ (Entire Dropbox)</option>';
                data.folders.forEach(folder => {
                    const option = document.createElement('option');
                    option.value = folder;
                    option.textContent = folder;
                    folderSelect.appendChild(option);
                });
            }
            
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
                    
                    // Show empty count stat
                    emptyStatCard.style.display = 'block';
                    animateValue('emptyCount', formatNumber(data.empty_folders.length));
                }
                
                // Check if deletion just completed
                if (data.delete_progress.status === 'complete' && !data.deleting) {
                    document.getElementById('progressFill').className = 'progress-bar-fill complete';
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
            const folder = document.getElementById('folderSelect').value;
            document.getElementById('resultsCard').style.display = 'none';
            document.getElementById('emptyStatCard').style.display = 'none';
            
            try {
                await fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({folder: folder})
                });
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
        
        // Start polling
        fetchStatus();
        pollInterval = setInterval(fetchStatus, 400);
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
        self.end_headers()
        self.wfile.write(html.encode())
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.send_html(HTML_PAGE)
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
        else:
            logger.warning(f"Unknown API endpoint: {self.path}")
            self.send_response(404)
            self.end_headers()


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
    """Check if a file is a system file that should be ignored."""
    config = app_state["config"]
    if not config.get("ignore_system_files", True):
        return False
    system_files = config.get("system_files", [])
    return filename.lower() in [sf.lower() for sf in system_files] or filename in system_files

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
                    app_state["scan_progress"]["files"] += 1
                    parent_path = os.path.dirname(entry.path_lower)
                    
                    # Check if this is a system file that should be ignored
                    filename = os.path.basename(entry.path_display)
                    if is_system_file(filename):
                        system_files_ignored += 1
                        folders_with_only_system_files.add(parent_path)
                        logger.debug(f"Ignoring system file: {entry.path_display}")
                    else:
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


def delete_folders():
    """Delete empty folders."""
    total = len(app_state["empty_folders"])
    logger.info(f"Starting deletion of {total} empty folder(s)")
    logger.warning("⚠️  DELETION OPERATION INITIATED - folders will be moved to Dropbox trash")
    
    app_state["deleting"] = True
    app_state["delete_progress"] = {"current": 0, "total": total, "status": "deleting", "percent": 0}
    
    dbx = app_state["dbx"]
    deleted_count = 0
    error_count = 0
    start_time = time.time()
    
    for i, folder in enumerate(app_state["empty_folders"]):
        display_path = app_state["case_map"].get(folder, folder)
        try:
            logger.debug(f"Deleting [{i+1}/{total}]: {display_path}")
            dbx.files_delete_v2(folder)
            deleted_count += 1
            logger.info(f"✓ Deleted: {display_path}")
        except ApiError as e:
            error_count += 1
            logger.error(f"✗ Failed to delete {display_path}: {e}")
            print(f"Delete error for {folder}: {e}")
        except Exception as e:
            error_count += 1
            logger.exception(f"✗ Unexpected error deleting {display_path}: {e}")
            print(f"Delete error for {folder}: {e}")
        
        current = i + 1
        app_state["delete_progress"]["current"] = current
        app_state["delete_progress"]["percent"] = int((current / total) * 100) if total > 0 else 100
    
    elapsed = time.time() - start_time
    app_state["empty_folders"] = []
    app_state["delete_progress"]["status"] = "complete"
    app_state["delete_progress"]["percent"] = 100
    app_state["deleting"] = False
    
    logger.info(f"Deletion complete: {deleted_count} deleted, {error_count} errors in {elapsed:.2f}s")
    if error_count > 0:
        logger.warning(f"⚠️  {error_count} folder(s) could not be deleted - check log for details")


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
    
    port = 8765
    
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
