#!/usr/bin/env python3
"""
Compare "Books (view-only conflicts 2025-12-19)" with "Books" folder
and identify files that need to be moved.
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import dropbox
from dropbox.files import FileMetadata, FolderMetadata

def get_dropbox_client():
    """Get authenticated Dropbox client."""
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    
    if not all([refresh_token, app_key, app_secret]):
        raise ValueError("Missing Dropbox credentials in .env file")
    
    return dropbox.Dropbox(
        oauth2_refresh_token=refresh_token,
        app_key=app_key,
        app_secret=app_secret
    )

from logger_setup import setup_logger, format_api_error

# Initialize robust logging
logger, log_filename = setup_logger('DropboxCompare', 'dropbox_compare')

from utils import ProgressBar

def list_all_files(dbx, folder_path):
    """List all files in a folder recursively."""
    files = {}
    folders = set()
    
    progress = ProgressBar(f"Scanning {os.path.basename(folder_path) or '/'}")
    
    try:
        result = dbx.files_list_folder(folder_path, recursive=True)
        
        while True:
            for entry in result.entries:
                if isinstance(entry, FileMetadata):
                    # Get relative path from the base folder
                    rel_path = entry.path_display[len(folder_path):]
                    files[rel_path.lower()] = {
                        'path': entry.path_display,
                        'rel_path': rel_path,
                        'size': entry.size,
                        'name': entry.name
                    }
                elif isinstance(entry, FolderMetadata):
                    rel_path = entry.path_display[len(folder_path):]
                    folders.add(rel_path.lower())
            
            # Streaming progress update
            progress.update(len(folders), len(files))
            
            if not result.has_more:
                break
            result = dbx.files_list_folder_continue(result.cursor)
            
        progress.finish(f"Found {len(folders):,} folders, {len(files):,} files")
        
    except Exception as e:
        detailed_error = format_api_error(e) if "ApiError" in str(type(e)) else str(e)
        logger.error(f"Error listing {folder_path}: {detailed_error}")
        logger.exception("Listing exception details:")
        print(f"\nError listing {folder_path}: {e}")
    
    return files, folders

def main():
    print("Connecting to Dropbox...")
    dbx = get_dropbox_client()
    
    # Get account info to verify connection
    account = dbx.users_get_current_account()
    print(f"Connected as: {account.name.display_name}")
    
    source_folder = "/Books (view-only conflicts 2025-12-19)"
    dest_folder = "/Books"
    
    print(f"\n{'='*60}")
    print(f"SOURCE: {source_folder}")
    print(f"DESTINATION: {dest_folder}")
    print(f"{'='*60}")
    
    print(f"\nScanning source folder...")
    source_files, source_folders = list_all_files(dbx, source_folder)
    print(f"Found {len(source_files)} files and {len(source_folders)} folders in source")
    
    print(f"\nScanning destination folder...")
    dest_files, dest_folders = list_all_files(dbx, dest_folder)
    print(f"Found {len(dest_files)} files and {len(dest_folders)} folders in destination")
    
    # Find files in source that are NOT in destination
    print(f"\n{'='*60}")
    print("FILES IN SOURCE BUT NOT IN DESTINATION:")
    print(f"{'='*60}")
    
    missing_files = []
    for rel_path, info in source_files.items():
        if rel_path not in dest_files:
            missing_files.append(info)
            print(f"\n  📄 {info['rel_path']}")
            print(f"     Size: {info['size']:,} bytes")
            print(f"     Full path: {info['path']}")
    
    if not missing_files:
        print("\n  ✅ All source files exist in destination!")
    else:
        print(f"\n{'='*60}")
        print(f"SUMMARY: {len(missing_files)} files need to be moved")
        print(f"{'='*60}")
        
        # Show what the move would look like
        print("\nProposed moves:")
        for info in missing_files:
            src = info['path']
            dst = dest_folder + info['rel_path']
            print(f"  FROM: {src}")
            print(f"  TO:   {dst}")
            print()
    
    # Also check for files that exist in both but might have different sizes
    print(f"\n{'='*60}")
    print("FILES THAT EXIST IN BOTH (checking for differences):")
    print(f"{'='*60}")
    
    different_files = []
    for rel_path, src_info in source_files.items():
        if rel_path in dest_files:
            dst_info = dest_files[rel_path]
            if src_info['size'] != dst_info['size']:
                different_files.append({
                    'rel_path': src_info['rel_path'],
                    'src_size': src_info['size'],
                    'dst_size': dst_info['size'],
                    'src_path': src_info['path'],
                    'dst_path': dst_info['path']
                })
    
    if different_files:
        print(f"\n⚠️  {len(different_files)} files have different sizes:")
        for f in different_files:
            print(f"\n  📄 {f['rel_path']}")
            print(f"     Source size: {f['src_size']:,} bytes")
            print(f"     Dest size:   {f['dst_size']:,} bytes")
    else:
        print("\n  ✅ All matching files have the same size")
    
    return missing_files

if __name__ == "__main__":
    missing = main()


