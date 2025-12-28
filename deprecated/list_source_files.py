#!/usr/bin/env python3
"""
List all files in the source conflict folder only.
"""

import os
from dotenv import load_dotenv
load_dotenv()

import dropbox
from dropbox.files import FileMetadata, FolderMetadata

def get_dropbox_client():
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    return dropbox.Dropbox(
        oauth2_refresh_token=refresh_token,
        app_key=app_key,
        app_secret=app_secret
    )

dbx = get_dropbox_client()
account = dbx.users_get_current_account()
print(f"Connected as: {account.name.display_name}\n")

source = "/Books (view-only conflicts 2025-12-19)"
print(f"Scanning: {source}\n")

files = []
folders = []

result = dbx.files_list_folder(source, recursive=True)
while True:
    for entry in result.entries:
        if isinstance(entry, FileMetadata):
            files.append({
                'path': entry.path_display,
                'rel': entry.path_display[len(source):],
                'size': entry.size,
                'name': entry.name
            })
        elif isinstance(entry, FolderMetadata):
            folders.append(entry.path_display)
    if not result.has_more:
        break
    result = dbx.files_list_folder_continue(result.cursor)

print(f"Found {len(files)} FILES:")
print("="*60)
for f in files:
    print(f"  📄 {f['rel']}")
    print(f"     Size: {f['size']:,} bytes")
    print()

print(f"\nFound {len(folders)} FOLDERS:")
print("="*60)
for folder in sorted(folders):
    print(f"  📁 {folder}")


