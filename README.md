# 📁 Dropbox Empty Folder Cleaner

A powerful tool to find and safely delete empty folders in your Dropbox account. Available as both a modern web-based GUI and a command-line interface.

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-purple)

## 🎯 Purpose

Over time, Dropbox accounts accumulate empty folders from:
- Deleted files leaving behind folder structures
- Failed syncs or interrupted uploads
- Reorganization that moved files but left folders
- Application artifacts and temporary folders

This tool helps you **identify and remove** these empty folders to keep your Dropbox organized and clean.

## ✨ Features

### Core Features
- **Recursive scanning** - Finds all empty folders, including nested ones
- **Smart detection** - Only identifies truly empty folders (no files, no non-empty subfolders)
- **System file ignore** - Treats folders with only .DS_Store, Thumbs.db as empty (configurable)
- **Exclusion patterns** - Skip folders like .git, node_modules (configurable)
- **Safe deletion order** - Deletes deepest folders first, then works backward to parents
- **Dry-run mode** - Preview what would be deleted before taking action
- **Confirmation prompts** - Requires explicit confirmation before any deletion
- **Export results** - Export to JSON or CSV for records and analysis
- **Report generation** - Saves detailed reports of all actions

### Web GUI Features
- **Real-time progress** - Live folder/file counts as scanning progresses
- **Elapsed time tracking** - See how long the scan takes
- **Processing rate** - Items per second indicator
- **Visual progress bar** - Red while running, solid green when complete
- **Percentage display** - Exact completion percentage during deletion
- **Statistics panel** - Depth distribution and scan metrics
- **Settings toggle** - Enable/disable system file ignore on-the-fly
- **Modern dark theme** - Easy on the eyes, compact design
- **Help documentation** - Built-in help modal with full guide

### Command-Line Features
- **Animated progress** - Spinner with live statistics
- **Flexible paths** - Scan specific folders or entire Dropbox
- **Batch operations** - Process multiple folders efficiently

### Safety Features
- **10 implemented safety measures** (see Safety Report)
- **Comprehensive logging** - DEBUG/INFO/WARNING/ERROR levels
- **30-day recovery** - Deleted folders go to Dropbox trash
- **Test suite** - 25+ unit and integration tests

## 📋 Requirements

- Python 3.9 or higher
- Dropbox account
- Dropbox API app with appropriate permissions

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Dropbox API Access

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click **"Create app"**
3. Choose **"Scoped access"** → **"Full Dropbox"**
4. Name your app (e.g., "Empty Folder Cleaner")
5. Go to **Permissions** tab and enable:
   - `files.metadata.read`
   - `files.content.write`
6. Click **Submit** to save permissions

### 3. Run the Application

```bash
python3 dropbox_cleaner_web.py
```

### 4. Configure Dropbox Connection (First-Time Setup)

1. Click the **⚙️ Settings** button in the app
2. In the **Dropbox Connection** section:
   - Enter your **App Key** and **App Secret**
   - Click **"Get New Token"** to authorize
   - A new window opens - authorize and copy the code
   - Paste the code and click **"Complete Authorization"**
3. Click **"Save Settings"**

**Alternative: Command-Line Setup**
```bash
python3 dropbox_auth.py
```

### 5. Start Using the App

**Web GUI (Recommended):**
```bash
python3 dropbox_cleaner_web.py
```
Opens a browser at http://127.0.0.1:8765

**Command Line:**
```bash
# List available folders
python3 dropbox_cleaner.py --list

# Scan a specific folder (dry-run)
python3 dropbox_cleaner.py --scan "/Documents"

# Scan and delete empty folders
python3 dropbox_cleaner.py --delete "/Documents"
```

## ⚙️ Configuration

The tool uses `config.json` for customizable settings:

```json
{
  "ignore_system_files": true,
  "system_files": [
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".dropbox",
    ".dropbox.attr",
    "Icon\r",
    ".localized"
  ],
  "exclude_patterns": [
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    ".env"
  ],
  "export_format": "json",
  "auto_open_browser": true,
  "port": 8765
}
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `ignore_system_files` | `true` | Treat folders with only system files as empty |
| `system_files` | (list) | File names to consider as "system files" |
| `exclude_patterns` | (list) | Folder names to skip during scanning |
| `export_format` | `"json"` | Default export format (json or csv) |
| `auto_open_browser` | `true` | Open browser automatically on startup |
| `port` | `8765` | Web server port |

## 📖 Usage Guide

### Web GUI

1. **Select a folder** from the dropdown menu
2. **Toggle settings** - Enable/disable system file ignore if needed
3. **Click "Scan for Empty Folders"** to start scanning
4. **Watch the progress** - folder count, file count, elapsed time, and rate
5. **Review the results** - all empty folders are listed with statistics
6. **Export if needed** - Click JSON or CSV to download results
7. **Click "Delete Empty Folders"** if you want to remove them
8. **Confirm deletion** in the popup dialog

### Command Line

```bash
# Show help
python3 dropbox_cleaner.py --help

# List root folders
python3 dropbox_cleaner.py --list

# Scan specific folder (no deletion)
python3 dropbox_cleaner.py --scan "/Photos/2023"

# Scan entire Dropbox
python3 dropbox_cleaner.py --scan ""

# Delete empty folders (with confirmation)
python3 dropbox_cleaner.py --delete "/Old Projects"
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all unit tests
python3 tests.py --unit

# Run integration tests (requires Dropbox connection)
python3 tests.py --integration

# Create test folders in Dropbox for manual testing
python3 tests.py --create-test-folders

# Clean up test folders
python3 tests.py --cleanup-test-folders

# View safety measures report
python3 tests.py --safety-report
```

### Test Coverage

| Category | Tests | Coverage |
|----------|-------|----------|
| Empty folder detection | 8 | Core logic |
| Deletion order | 2 | Depth-first ordering |
| Safety measures | 3 | Confirmation flow |
| Input validation | 1 | Path handling |
| System file ignore | 3 | .DS_Store handling |
| Exclusion patterns | 2 | Folder filtering |
| Export feature | 2 | JSON/CSV output |
| Configuration | 2 | Config loading/merging |
| Integration | 3 | Dropbox API |

## ⚠️ Important Limitations

### What This Tool DOES:
- ✅ Finds folders with no files and no non-empty subfolders
- ✅ Ignores system files like .DS_Store (configurable)
- ✅ Excludes specified folder patterns
- ✅ Deletes folders in safe order (deepest first)
- ✅ Moves deleted folders to Dropbox trash (recoverable for 30 days)
- ✅ Works with your personal Dropbox folders
- ✅ Exports results to JSON/CSV

### What This Tool DOES NOT:
- ❌ **Cannot recover deleted folders** - Once deleted from trash, they're gone forever
- ❌ **Does not check file contents** - Only checks if files exist, not what's in them
- ❌ **May not work with Team folders** - Designed for personal Dropbox accounts
- ❌ **Cannot undo deletions** - Always use dry-run first!

### Rate Limits
- Dropbox API has rate limits for large accounts
- Very large scans may take several minutes
- If you see errors, wait a few minutes and try again

### Sync Considerations
- Ensure Dropbox is fully synced before scanning
- Folders may appear empty if files haven't synced yet
- Best used when Dropbox shows "Up to date"

## 🔐 Security & Privacy

- **Credentials stored locally** - Your `.env` file stays on your machine
- **No data sent to third parties** - Direct communication with Dropbox API only
- **Refresh tokens** - Long-term access without storing passwords
- **Comprehensive logging** - All actions logged for audit trail
- **Open source** - Full code available for review

## 📁 File Structure

```
├── dropbox_cleaner_web.py    # Web GUI (recommended)
├── dropbox_cleaner.py        # Command-line interface
├── dropbox_auth.py           # OAuth2 authorization helper
├── tests.py                  # Comprehensive test suite
├── config.json               # Configuration settings
├── requirements.txt          # Python dependencies
├── .env                      # Your credentials (git-ignored)
├── .gitignore               # Git ignore rules
├── logs/                    # Log files directory
└── README.md                # This file
```

## 📊 Logging

Logs are saved to `logs/dropbox_cleaner_YYYYMMDD_HHMMSS.log`:

- **DEBUG**: Detailed diagnostics (file only)
- **INFO**: Key operations (console + file)
- **WARNING**: Potential issues
- **ERROR**: Failures with stack traces

## 🛠️ Troubleshooting

### "Authentication failed"
- Your tokens may have expired
- Run `python3 dropbox_auth.py` to re-authorize

### "Folder not found"
- Check the folder path is correct
- Paths are case-insensitive but must match structure

### "Rate limit exceeded"
- Wait 5-10 minutes before retrying
- Try scanning smaller folders individually

### GUI won't open
- Ensure port 8765 is available
- Try: `lsof -i :8765` to check for conflicts

### tkinter crashes (macOS)
- Use the web GUI instead (`dropbox_cleaner_web.py`)
- Known issue with macOS Tahoe and old Tcl/Tk

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

MIT License - Feel free to use, modify, and distribute.

## 👤 Author

Built for Tushar Shah

---

**⚠️ Always use dry-run mode first and verify the results before deleting!**
