# Dropbox Empty Folder Cleaner

A Python tool to find and delete empty folders in your Dropbox account.

## Features

- **Dry-run mode**: Safely list empty folders without deleting anything
- **Smart detection**: Identifies truly empty folders (no files, no non-empty subfolders)
- **Bottom-up deletion**: Deletes deepest folders first, then parents as they become empty
- **Confirmation prompt**: Requires explicit confirmation before any deletion
- **Report generation**: Saves a detailed report of findings/actions
- **Scoped scanning**: Only scans your personal folder, not team folders

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Create a `.env` file with your Dropbox credentials:

```
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret
DROPBOX_ACCESS_TOKEN=your_access_token
```

## Usage

### Dry Run (Recommended First)

List all empty folders without deleting anything:

```bash
python dropbox_empty_folder_cleaner.py --dry-run
```

### Delete Empty Folders

Find and delete empty folders (with confirmation):

```bash
python dropbox_empty_folder_cleaner.py --delete
```

### Scan a Specific Path

```bash
python dropbox_empty_folder_cleaner.py --dry-run --path "/Tushar Shah/Projects"
```

### Skip Report Generation

```bash
python dropbox_empty_folder_cleaner.py --dry-run --no-report
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | List empty folders without deleting (safe mode) |
| `--delete` | Find and delete empty folders (with confirmation) |
| `--path PATH` | Root path to scan (default: `/Tushar Shah`) |
| `--no-report` | Don't save a report file |

## How It Works

1. **Connects** to your Dropbox account using the access token
2. **Recursively scans** all folders under the specified path
3. **Identifies** folders that contain no files and no non-empty subfolders
4. **Sorts** empty folders by depth (deepest first)
5. **In delete mode**: Shows all empty folders and requires you to type `DELETE` to confirm
6. **Deletes** folders in order (deepest first, so parents become empty naturally)
7. **Generates** a report of all actions taken

## Safety Features

- **Dry-run by default**: You must explicitly choose `--delete` to remove anything
- **Confirmation required**: Must type `DELETE` in all caps to proceed
- **Trash-based deletion**: Deleted folders go to Dropbox trash (recoverable for 30 days)
- **Detailed reports**: Every run generates a timestamped report
- **No team folder access**: Only scans your personal folder by default

## Testing Recommendations

Before running on your full Dropbox:

1. Create a test folder: `/Tushar Shah/TEST_EMPTY_FOLDERS`
2. Create some empty subfolders inside it
3. Run: `python dropbox_empty_folder_cleaner.py --dry-run --path "/Tushar Shah/TEST_EMPTY_FOLDERS"`
4. Verify it finds the right folders
5. Run: `python dropbox_empty_folder_cleaner.py --delete --path "/Tushar Shah/TEST_EMPTY_FOLDERS"`
6. Verify only empty folders were deleted

## Troubleshooting

### "Authentication failed"
Your access token may have expired. Generate a new one from the [Dropbox App Console](https://www.dropbox.com/developers/apps).

### "Folder not found"
Check that the path exists and is spelled correctly. Paths are case-insensitive but must match the structure.

### Rate limiting
For very large Dropbox accounts, you may hit rate limits. The script handles pagination automatically, but if you see errors, wait a few minutes and try again.

## License

MIT License - Feel free to modify and use as needed.

