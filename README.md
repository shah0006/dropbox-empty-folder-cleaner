# 📁 Intelligent Replication Suite (formerly Dropbox Cleaner)

A powerful suite for file hygiene and bidirectional synchronization. Features a modern web-based GUI, multi-cloud support (Dropbox, Google Drive, S3, SFTP), and a robust Sync Engine with Ransomware protection.

![Version](https://img.shields.io/badge/version-2.0.0--rc1-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

## 📁 Project Structure

| File | Description |
| :--- | :--- |
| `main.py` | **Core Application**: FastAPI backend + Web GUI |
| `core/` | **Sync Engine**: Database, Transfer logic, Safety checks |
| `providers/` | **VFS Adapters**: Local, Dropbox, Google, S3, SFTP |
| `dropbox_cleaner_web.py` | Legacy v1 Web GUI (Maintenance Mode) |

---

## 🚀 Getting Started

### Option A: Docker (Recommended)
Deploy instantly on any server or NAS (Synology, QNAP):

```bash
docker-compose up -d --build
```
Access at **http://localhost:8765**

### Option B: Local Python
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python3 main.py
   ```

---

## ✨ New in v2.0
- **Bi-Directional Sync**: True stateful sync between Local and Cloud.
- **Multi-Cloud**: Support for S3 Compatible Storage and SFTP.
- **Safety Monitor**: Heuristic analysis detects and blocks mass deletions (Ransomware protection).
- **Dockerized**: specific container for 24/7 background operation.


---

## ✨ Features

- **Smart Detection**: Finds "truly" empty folders (no files, no non-empty subfolders).
- **System File Logic**: Correctly handles `.DS_Store`, `Thumbs.db`, etc.
- **Dry-Run Safety**: Always scans before deleting.
- **Robust Logging**: Every operation is logged with full tracebacks for debugging.
- **Local Scan Mode**: Supports cleaning both Dropbox and local filesystems.

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

## ⚠️ Disclaimer

### USE AT YOUR OWN RISK

**This software is provided "AS IS" without warranty of any kind, express or implied.**

By using this application, you acknowledge and accept the following:

| Term | Description |
|------|-------------|
| **No Warranty** | The developer makes no guarantees about accuracy, reliability, or suitability |
| **No Liability** | The developer shall not be held liable for any damages arising from use |
| **Data Loss Risk** | This application deletes folders - data loss may occur |
| **User Responsibility** | You are solely responsible for backing up your data |
| **Recovery Limits** | Deleted folders can only be recovered for 30 days |

### Safety Measures Implemented

To minimize risk, this application includes:

- ✅ Dry-run mode by default (scan without deleting)
- ✅ Explicit confirmation required before any deletion
- ✅ Deleted folders go to Dropbox trash (30-day recovery)
- ✅ Deepest folders deleted first to prevent errors
- ✅ Comprehensive logging of all operations
- ✅ Export results to JSON/CSV before deletion
- ✅ Visual warnings at every deletion step

### Recommendations

1. **Always scan first** - Review the empty folder list before deleting
2. **Export results** - Download JSON/CSV before deleting for your records
3. **Test on small folders** - Try a small folder first to understand behavior
4. **Ensure sync is complete** - Wait for Dropbox to show "Up to date"
5. **Maintain backups** - Keep separate backups of critical files

---

## 📄 License

MIT License - Feel free to use, modify, and distribute.

**This software is not affiliated with or endorsed by Dropbox, Inc.**

---

## 👤 Author

Created for Tushar Shah

---

**⚠️ IMPORTANT: Always review the empty folder list before deleting! Export to JSON/CSV first. Use at your own risk.**
