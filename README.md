# 📁 Dropbox Empty Folder Cleaner

A powerful, user-friendly tool to find and safely delete empty folders in your Dropbox account. Features a modern web-based GUI with real-time progress tracking, configurable settings, and comprehensive safety measures.

![Version](https://img.shields.io/badge/version-1.2.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-purple)

**Repository:** [github.com/shah0006/dropbox-empty-folder-cleaner](https://github.com/shah0006/dropbox-empty-folder-cleaner)

---

## 🎯 Purpose

Over time, Dropbox accounts accumulate empty folders from:
- Deleted files leaving behind folder structures
- Failed syncs or interrupted uploads
- Reorganization that moved files but left folders
- Application artifacts and temporary folders
- System files like `.DS_Store` that don't constitute real content

This tool helps you **identify and safely remove** these empty folders to keep your Dropbox organized, reduce clutter, and potentially improve sync performance.

---

## ✨ Features

### Core Functionality
| Feature | Description |
|---------|-------------|
| **Smart Detection** | Finds truly empty folders (no files, no non-empty subfolders) |
| **System File Ignore** | Treats folders with only `.DS_Store`, `Thumbs.db`, `desktop.ini` as empty |
| **Exclusion Patterns** | Automatically skip folders like `.git`, `node_modules`, `__pycache__` |
| **Safe Deletion Order** | Deletes deepest folders first, then works backward to parents |
| **Trash Recovery** | Deleted folders go to Dropbox trash (recoverable for 30 days) |

### Web GUI Features
| Feature | Description |
|---------|-------------|
| **Real-time Progress** | Live folder/file counts as scanning progresses |
| **Visual Progress Bar** | Red/orange while running, solid green when complete |
| **Statistics Panel** | Total scanned, system files ignored, depth distribution |
| **Export Results** | Export empty folder list to JSON or CSV |
| **In-App Setup** | Configure Dropbox credentials directly in Settings |
| **Help Documentation** | Built-in comprehensive help modal |

### Safety & Security
| Feature | Description |
|---------|-------------|
| **Dry-Run by Default** | Scan shows results without deleting anything |
| **Confirmation Required** | Must explicitly confirm before any deletion |
| **Comprehensive Logging** | All operations logged to `logs/` directory |
| **Local Credentials** | Your API keys stored only in local `.env` file |
| **No Third Parties** | Direct communication with Dropbox API only |

---

## 📋 Requirements

- **Python 3.9** or higher
- **Dropbox account** (personal, not team/business)
- **Dropbox API app** (free to create)

---

## 🚀 Quick Start

### 1. Download and Install

```bash
# Clone the repository
git clone https://github.com/shah0006/dropbox-empty-folder-cleaner.git
cd dropbox-empty-folder-cleaner

# Install dependencies
pip install -r requirements.txt
```

### 2. Create a Dropbox App

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click **"Create app"**
3. Select:
   - **"Scoped access"**
   - **"Full Dropbox"** (access type)
4. Name your app (e.g., "My Folder Cleaner")
5. Go to **Permissions** tab and enable:
   - ✅ `files.metadata.read`
   - ✅ `files.content.write`
6. Click **"Submit"** to save permissions
7. Note your **App Key** and **App Secret** from the Settings tab

### 3. Run the Application

```bash
python3 dropbox_cleaner_web.py
```

This opens a browser at `http://127.0.0.1:8765`

### 4. Connect Your Dropbox (First-Time Setup)

1. Click **⚙️ Settings** button
2. Enter your **App Key** and **App Secret**
3. Click **"Get New Token"**
4. Authorize in the Dropbox window that opens
5. Copy the code and paste it back
6. Click **"Complete Authorization"**
7. Click **"Save Settings"**

### 5. Start Cleaning!

1. Select a folder from the dropdown (or "/" for entire Dropbox)
2. Click **"Scan for Empty Folders"**
3. Review the results
4. Click **"Delete Empty Folders"** if desired
5. Confirm in the popup

---

## 📖 Detailed Usage Guide

### Web GUI

#### Main Interface

```
┌─────────────────────────────────────────────┐
│  📁 Dropbox Empty Folder Cleaner            │
│                                             │
│  🔗 Connection Status    ● Connected        │
│     Logged in as Your Name                  │
│                                             │
│  📂 Select Folder to Scan                   │
│  [/ (Entire Dropbox)              ▼]        │
│  ☑ Ignore system files            ⚙️        │
│                                             │
│  [🔍 Scan for Empty Folders]                │
│  [🗑️ Delete Empty Folders]                  │
│                                             │
│  📊 Progress                                │
│  ████████████████████░░░░  80%              │
│  📁 1,234 folders | 📄 5,678 files          │
│                                             │
│  📋 Results              [JSON] [CSV]       │
│  ┌─────────────────────────────────┐        │
│  │ 1. /path/to/empty/folder        │        │
│  │ 2. /another/empty/folder        │        │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘
```

#### Progress Indicators

| Indicator | Meaning |
|-----------|---------|
| Red/Orange animated bar | Scan or deletion in progress |
| Solid green bar | Operation complete |
| Folders scanned | Number of folders checked |
| Files found | Number of files encountered |
| Elapsed time | How long the operation has taken |
| Items/second | Processing rate |

#### Settings Panel

Click **⚙️ Settings** to configure:

| Section | Options |
|---------|---------|
| **Dropbox Connection** | App Key, App Secret, Refresh Token, Test Connection |
| **System File Handling** | Enable/disable, customize file list |
| **Exclusion Patterns** | Folders to skip during scanning |
| **Application** | Server port, default export format |

### Command-Line Interface

For advanced users or automation:

```bash
# Show help
python3 dropbox_cleaner.py --help

# List root folders
python3 dropbox_cleaner.py --list

# Scan specific folder (dry-run, no deletion)
python3 dropbox_cleaner.py --scan "/Documents"

# Scan entire Dropbox
python3 dropbox_cleaner.py --scan ""

# Delete empty folders (with confirmation prompt)
python3 dropbox_cleaner.py --delete "/Old Projects"
```

---

## ⚙️ Configuration

### config.json

Settings are saved to `config.json`:

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

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `ignore_system_files` | boolean | `true` | Treat folders with only system files as empty |
| `system_files` | array | (see above) | File names to consider "system files" |
| `exclude_patterns` | array | (see above) | Folder names to skip during scanning |
| `export_format` | string | `"json"` | Default export format |
| `auto_open_browser` | boolean | `true` | Open browser automatically on startup |
| `port` | integer | `8765` | Web server port |

### .env File

Credentials are stored in `.env`:

```env
DROPBOX_APP_KEY="your_app_key"
DROPBOX_APP_SECRET="your_app_secret"
DROPBOX_REFRESH_TOKEN="your_refresh_token"
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all unit tests (23 tests)
python3 tests.py --unit

# Run integration tests (requires Dropbox connection)
python3 tests.py --integration

# View safety measures report
python3 tests.py --safety-report
```

### Manual Testing

```bash
# Create test folders in Dropbox
python3 tests.py --create-test-folders

# Scan test folders
python3 dropbox_cleaner.py --scan "/TEST_EMPTY_FOLDER_CLEANER"

# Delete test folders
python3 dropbox_cleaner.py --delete "/TEST_EMPTY_FOLDER_CLEANER"

# Clean up test folders
python3 tests.py --cleanup-test-folders
```

### Test Coverage

| Category | Tests | Description |
|----------|-------|-------------|
| Empty folder detection | 8 | Core detection logic |
| Deletion order | 2 | Depth-first ordering |
| Safety measures | 3 | Confirmation flow |
| Input validation | 1 | Path handling |
| System file ignore | 3 | .DS_Store handling |
| Exclusion patterns | 2 | Folder filtering |
| Export feature | 2 | JSON/CSV output |
| Configuration | 2 | Config loading |
| Integration | 3 | Dropbox API |

---

## ⚠️ Important Limitations

### What This Tool DOES ✅

- Finds folders with no files and no non-empty subfolders
- Ignores system files like `.DS_Store` (configurable)
- Excludes specified folder patterns
- Deletes folders in safe order (deepest first)
- Moves deleted folders to Dropbox trash
- Works with personal Dropbox accounts
- Exports results to JSON/CSV

### What This Tool DOES NOT ❌

- **Cannot undo deletion** after trash is emptied (30 days)
- **Does not check file contents** - only if files exist
- **May not work with Team/Business folders**
- **Cannot access shared folders** you don't own
- **Does not delete files** - only empty folders

### Rate Limits

- Dropbox API has rate limits for large operations
- Very large scans may take several minutes
- If rate limited, wait 5-10 minutes and retry

### Sync Considerations

- Ensure Dropbox shows "Up to date" before scanning
- Folders may appear empty if files haven't synced yet
- Recent changes may not appear immediately

---

## 🔐 Security & Privacy

| Aspect | Details |
|--------|---------|
| **Credential Storage** | Local `.env` file only - never uploaded |
| **Data Transmission** | Direct to Dropbox API - no intermediaries |
| **Third Parties** | None - no analytics, tracking, or external servers |
| **Open Source** | Full code available for review |
| **Token Type** | OAuth2 refresh tokens - no password storage |

---

## 📁 File Structure

```
dropbox-empty-folder-cleaner/
├── dropbox_cleaner_web.py    # Web GUI (recommended)
├── dropbox_cleaner.py        # Command-line interface
├── dropbox_auth.py           # OAuth authorization helper
├── tests.py                  # Comprehensive test suite
├── config.json               # Application settings
├── requirements.txt          # Python dependencies
├── .env                      # Your credentials (git-ignored)
├── .gitignore                # Git ignore rules
├── logs/                     # Log files directory
│   └── dropbox_cleaner_*.log
└── README.md                 # This documentation
```

---

## 📊 Logging

Logs are saved to `logs/dropbox_cleaner_YYYYMMDD_HHMMSS.log`:

| Level | Output | Description |
|-------|--------|-------------|
| DEBUG | File only | Detailed diagnostics |
| INFO | Console + File | Key operations |
| WARNING | Console + File | Potential issues |
| ERROR | Console + File | Failures with stack traces |

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| "Not connected" | Click Settings → enter credentials → Get New Token |
| "Authentication failed" | Token expired - get a new one via Settings |
| "Folder not found" | Check path exists and is spelled correctly |
| "Rate limit exceeded" | Wait 5-10 minutes before retrying |
| "Port already in use" | Change port in Settings or kill existing process |
| Scan takes too long | Try scanning a smaller folder first |
| No empty folders found | Your Dropbox is already clean! |
| tkinter crashes (macOS) | Use web GUI instead (this is the default) |

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new features
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📜 Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.2.0 | 2024 | Multi-user support, in-app credential configuration |
| v1.1.1 | 2024 | Comprehensive settings panel |
| v1.1.0 | 2024 | System file ignore, export, statistics |
| v1.0.0 | 2024 | Initial release with web GUI and CLI |

---

## 📄 License

MIT License - Feel free to use, modify, and distribute.

---

## 👤 Author

Created for Tushar Shah

---

**⚠️ Always review the empty folder list before deleting! When in doubt, export to JSON/CSV first.**
