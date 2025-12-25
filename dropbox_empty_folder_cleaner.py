#!/usr/bin/env python3
"""
Dropbox Empty Folder Cleaner
============================
Finds and deletes empty folders in your Dropbox account.

Usage:
    python dropbox_empty_folder_cleaner.py --dry-run    # List empty folders (no deletion)
    python dropbox_empty_folder_cleaner.py --delete     # Find and delete empty folders

Author: Built for Tushar Shah
"""

import os
import sys
import argparse
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

try:
    import dropbox
    from dropbox.exceptions import ApiError, AuthError
    from dropbox.files import FolderMetadata
except ImportError:
    print("Error: dropbox package not installed.")
    print("Run: pip install dropbox python-dotenv")
    sys.exit(1)


# Configuration
ROOT_FOLDER = ""  # Scan entire personal Dropbox (root level)


def load_credentials():
    """Load Dropbox credentials from .env file."""
    load_dotenv()
    
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
    
    return {
        "app_key": app_key,
        "app_secret": app_secret,
        "refresh_token": refresh_token,
        "access_token": access_token
    }


def get_dropbox_client():
    """Initialize and return authenticated Dropbox client."""
    creds = load_credentials()
    
    # Prefer refresh token flow (long-term tokens)
    if creds["refresh_token"] and creds["app_key"] and creds["app_secret"]:
        try:
            dbx = dropbox.Dropbox(
                oauth2_refresh_token=creds["refresh_token"],
                app_key=creds["app_key"],
                app_secret=creds["app_secret"]
            )
            account = dbx.users_get_current_account()
            print(f"✓ Authenticated as: {account.name.display_name} ({account.email})")
            return dbx
        except AuthError as e:
            print(f"Error: Authentication with refresh token failed - {e}")
            print("Run 'python3 dropbox_auth.py' to re-authorize.")
            sys.exit(1)
    
    # Fall back to access token (may expire)
    elif creds["access_token"]:
        try:
            dbx = dropbox.Dropbox(creds["access_token"])
            account = dbx.users_get_current_account()
            print(f"✓ Authenticated as: {account.name.display_name} ({account.email})")
            print("⚠️  Using short-lived access token. Run 'python3 dropbox_auth.py' for long-term tokens.")
            return dbx
        except AuthError as e:
            print(f"Error: Authentication failed - {e}")
            print("Your access token has expired.")
            print("Run 'python3 dropbox_auth.py' to get a refresh token (recommended).")
            sys.exit(1)
    
    else:
        print("Error: No Dropbox credentials found in .env file")
        print("Run 'python3 dropbox_auth.py' to set up authentication.")
        sys.exit(1)


def list_all_entries(dbx, root_path):
    """
    Recursively list all files and folders under the given path.
    Returns two sets: all_folders and folders_with_content.
    """
    print(f"\n📂 Scanning: {root_path if root_path else '/ (entire Dropbox)'}")
    print("   This may take a while for large Dropbox accounts...")
    print("   Progress updates every 1000 items...\n")
    sys.stdout.flush()
    
    all_folders = set()
    folders_with_content = set()
    file_count = 0
    batch_count = 0
    
    try:
        # Start recursive listing
        result = dbx.files_list_folder(root_path, recursive=True)
        
        while True:
            batch_count += 1
            for entry in result.entries:
                if isinstance(entry, FolderMetadata):
                    all_folders.add(entry.path_lower)
                else:
                    # It's a file - mark its parent folder as having content
                    file_count += 1
                    parent_path = os.path.dirname(entry.path_lower)
                    folders_with_content.add(parent_path)
            
            # Progress indicator - print every batch
            total_items = len(all_folders) + file_count
            if total_items % 1000 < 100:  # Print roughly every 1000 items
                print(f"   Progress: {len(all_folders):,} folders, {file_count:,} files (batch {batch_count})...")
                sys.stdout.flush()
            
            if not result.has_more:
                break
            
            result = dbx.files_list_folder_continue(result.cursor)
        
        print(f"\n   ✓ Scan complete: {len(all_folders):,} folders, {file_count:,} files")
        sys.stdout.flush()
        
    except ApiError as e:
        print(f"\nError listing folder '{root_path}': {e}")
        if "not_found" in str(e):
            print(f"The folder '{root_path}' does not exist.")
        sys.exit(1)
    
    return all_folders, folders_with_content


def find_empty_folders(all_folders, folders_with_content):
    """
    Identify truly empty folders (no files and no non-empty subfolders).
    Returns list sorted by depth (deepest first) for safe deletion order.
    """
    # A folder is empty if:
    # 1. It has no files directly in it (not in folders_with_content)
    # 2. All its subfolders (if any) are also empty
    
    # Build parent-child relationships
    children = defaultdict(set)
    for folder in all_folders:
        parent = os.path.dirname(folder)
        if parent in all_folders:
            children[parent].add(folder)
    
    # Mark folders with content and propagate upward
    has_content = set(folders_with_content)
    
    # Propagate: if a folder has content, all its ancestors have content too
    for folder in folders_with_content:
        current = folder
        while current:
            has_content.add(current)
            parent = os.path.dirname(current)
            if parent == current:  # Root reached
                break
            current = parent
    
    # Also mark folders that have non-empty children
    changed = True
    while changed:
        changed = False
        for folder in all_folders:
            if folder in has_content:
                continue
            # Check if any child has content
            for child in children[folder]:
                if child in has_content:
                    has_content.add(folder)
                    changed = True
                    break
    
    # Empty folders are those not in has_content
    empty_folders = all_folders - has_content
    
    # Sort by depth (deepest first) for safe deletion
    # This ensures we delete children before parents
    empty_list = sorted(empty_folders, key=lambda x: x.count('/'), reverse=True)
    
    return empty_list


def display_empty_folders(empty_folders, original_case_map=None):
    """Display the list of empty folders found."""
    if not empty_folders:
        print("\n✅ No empty folders found! Your Dropbox is clean.")
        return
    
    print(f"\n📋 Found {len(empty_folders)} empty folder(s):\n")
    print("-" * 70)
    
    for i, folder in enumerate(empty_folders, 1):
        # Display with original case if available
        display_path = original_case_map.get(folder, folder) if original_case_map else folder
        print(f"  {i:4}. {display_path}")
    
    print("-" * 70)
    print(f"\nTotal: {len(empty_folders)} empty folder(s)")


def get_original_case_paths(dbx, root_path):
    """Get mapping from lowercase paths to original case paths."""
    case_map = {}
    
    try:
        result = dbx.files_list_folder(root_path, recursive=True)
        
        while True:
            for entry in result.entries:
                if isinstance(entry, FolderMetadata):
                    case_map[entry.path_lower] = entry.path_display
            
            if not result.has_more:
                break
            
            result = dbx.files_list_folder_continue(result.cursor)
    except ApiError:
        pass  # Fall back to lowercase paths
    
    return case_map


def confirm_deletion(empty_folders):
    """
    Show confirmation prompt before deletion.
    Returns True if user confirms, False otherwise.
    """
    print("\n" + "=" * 70)
    print("⚠️  WARNING: DELETION CANNOT BE UNDONE!")
    print("=" * 70)
    print(f"""
You are about to permanently delete {len(empty_folders)} empty folder(s).

These folders will be moved to your Dropbox trash, where they will be
permanently deleted after 30 days (or immediately if you empty trash).

This action CANNOT be undone from this script.
""")
    print("=" * 70)
    
    # Require explicit confirmation
    response = input("\nType 'DELETE' (all caps) to confirm deletion, or anything else to cancel: ")
    
    return response == "DELETE"


def delete_empty_folders(dbx, empty_folders, case_map):
    """Delete the empty folders from Dropbox."""
    print(f"\n🗑️  Deleting {len(empty_folders)} empty folder(s)...\n")
    
    deleted = []
    errors = []
    
    for i, folder in enumerate(empty_folders, 1):
        display_path = case_map.get(folder, folder)
        try:
            dbx.files_delete_v2(folder)
            deleted.append(display_path)
            print(f"  ✓ [{i}/{len(empty_folders)}] Deleted: {display_path}")
        except ApiError as e:
            errors.append((display_path, str(e)))
            print(f"  ✗ [{i}/{len(empty_folders)}] Failed: {display_path}")
            print(f"      Error: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DELETION SUMMARY")
    print("=" * 70)
    print(f"  Successfully deleted: {len(deleted)}")
    print(f"  Failed: {len(errors)}")
    
    if errors:
        print("\n  Errors encountered:")
        for path, error in errors:
            print(f"    - {path}: {error}")
    
    return deleted, errors


def save_report(empty_folders, case_map, deleted=None, mode="dry-run"):
    """Save a report of the operation to a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"empty_folders_report_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write(f"Dropbox Empty Folder Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Mode: {mode}\n")
        f.write(f"Root folder scanned: {ROOT_FOLDER}\n")
        f.write("=" * 70 + "\n\n")
        
        if mode == "dry-run":
            f.write(f"Empty folders found: {len(empty_folders)}\n\n")
            for folder in empty_folders:
                display_path = case_map.get(folder, folder)
                f.write(f"  {display_path}\n")
        else:
            f.write(f"Folders deleted: {len(deleted) if deleted else 0}\n\n")
            if deleted:
                for folder in deleted:
                    f.write(f"  ✓ {folder}\n")
    
    print(f"\n📄 Report saved to: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(
        description="Find and delete empty folders in your Dropbox account.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dropbox_empty_folder_cleaner.py --dry-run    # List empty folders only
  python dropbox_empty_folder_cleaner.py --delete     # Delete empty folders
  python dropbox_empty_folder_cleaner.py --dry-run --path "/Tushar Shah/Projects"
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="List empty folders without deleting them (safe mode)"
    )
    group.add_argument(
        "--delete",
        action="store_true",
        help="Find and delete empty folders (with confirmation)"
    )
    
    parser.add_argument(
        "--path",
        type=str,
        default=ROOT_FOLDER,
        help=f"Root path to scan (default: {ROOT_FOLDER})"
    )
    
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Don't save a report file"
    )
    
    args = parser.parse_args()
    
    # Header
    print("\n" + "=" * 70)
    print("  DROPBOX EMPTY FOLDER CLEANER")
    print("=" * 70)
    print(f"  Mode: {'DRY RUN (no deletions)' if args.dry_run else 'DELETE MODE'}")
    print(f"  Path: {args.path}")
    print("=" * 70)
    
    # Connect to Dropbox
    dbx = get_dropbox_client()
    
    # Get all folders and identify which have content
    all_folders, folders_with_content = list_all_entries(dbx, args.path)
    
    if not all_folders:
        print("\n✅ No folders found in the specified path.")
        return
    
    # Get original case paths for display
    print("\n   Retrieving folder display names...")
    case_map = get_original_case_paths(dbx, args.path)
    
    # Find empty folders
    print("   Analyzing folder structure...")
    empty_folders = find_empty_folders(all_folders, folders_with_content)
    
    # Display results
    display_empty_folders(empty_folders, case_map)
    
    if not empty_folders:
        return
    
    # Save report
    if not args.no_report:
        if args.dry_run:
            save_report(empty_folders, case_map, mode="dry-run")
    
    # Handle deletion mode
    if args.delete:
        if confirm_deletion(empty_folders):
            deleted, errors = delete_empty_folders(dbx, empty_folders, case_map)
            if not args.no_report:
                save_report(empty_folders, case_map, deleted=deleted, mode="delete")
        else:
            print("\n❌ Deletion cancelled.")
    else:
        print("\n💡 This was a dry run. No folders were deleted.")
        print("   Run with --delete to remove these empty folders.")


if __name__ == "__main__":
    main()

