#!/usr/bin/env python3
"""
Dropbox Empty Folder Cleaner
============================
A command-line tool to find and delete empty folders in Dropbox.
Features a nice progress display without requiring tkinter.

Usage:
    python3 dropbox_cleaner.py --scan "/Snagit"        # Scan a specific folder
    python3 dropbox_cleaner.py --scan ""               # Scan entire Dropbox
    python3 dropbox_cleaner.py --delete "/Snagit"      # Delete empty folders
"""

import os
import sys
import time
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


class ProgressBar:
    """Simple text-based progress indicator."""
    
    def __init__(self, desc="Processing"):
        self.desc = desc
        self.folders = 0
        self.files = 0
        self.start_time = time.time()
        self.spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spin_idx = 0
    
    def update(self, folders, files):
        """Update the progress display."""
        self.folders = folders
        self.files = files
        self.spin_idx = (self.spin_idx + 1) % len(self.spinner)
        
        elapsed = time.time() - self.start_time
        spinner = self.spinner[self.spin_idx]
        
        # Create progress bar
        bar_width = 30
        progress_str = f"\r{spinner} {self.desc}: "
        progress_str += f"📁 {folders:,} folders | 📄 {files:,} files | "
        progress_str += f"⏱️  {elapsed:.1f}s"
        
        # Pad to clear previous line
        progress_str = progress_str.ljust(80)
        
        sys.stdout.write(progress_str)
        sys.stdout.flush()
    
    def finish(self, message="Done!"):
        """Finish the progress display."""
        elapsed = time.time() - self.start_time
        print(f"\r✅ {message} ({elapsed:.1f}s)".ljust(80))


def print_header():
    """Print application header."""
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        📁 DROPBOX EMPTY FOLDER CLEANER                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


def print_section(title):
    """Print a section header."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def connect_dropbox():
    """Connect to Dropbox and return client."""
    load_dotenv()
    
    app_key = os.getenv("DROPBOX_APP_KEY")
    app_secret = os.getenv("DROPBOX_APP_SECRET")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    
    if not all([app_key, app_secret, refresh_token]):
        print("❌ Error: Missing credentials in .env file")
        print("   Run: python3 dropbox_auth.py")
        sys.exit(1)
    
    try:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        account = dbx.users_get_current_account()
        print(f"✅ Connected as: {account.name.display_name} ({account.email})")
        return dbx
    except AuthError as e:
        print(f"❌ Authentication failed: {e}")
        print("   Run: python3 dropbox_auth.py")
        sys.exit(1)


def list_root_folders(dbx):
    """List folders at root level."""
    print("\n📂 Available folders at root level:")
    print("-" * 40)
    
    result = dbx.files_list_folder('')
    folders = []
    for entry in result.entries:
        if isinstance(entry, FolderMetadata):
            folders.append(entry.path_display)
            print(f"   {entry.path_display}")
    
    print("-" * 40)
    print(f"   Total: {len(folders)} folders")
    return folders


def scan_folder(dbx, folder_path):
    """Scan a folder and return all folders and their content status."""
    display_path = folder_path if folder_path else "/ (entire Dropbox)"
    print(f"\n🔍 Scanning: {display_path}")
    
    all_folders = set()
    folders_with_content = set()
    case_map = {}
    
    progress = ProgressBar("Scanning")
    
    try:
        result = dbx.files_list_folder(folder_path, recursive=True)
        folders_count = 0
        files_count = 0
        
        while True:
            for entry in result.entries:
                if isinstance(entry, FolderMetadata):
                    all_folders.add(entry.path_lower)
                    case_map[entry.path_lower] = entry.path_display
                    folders_count += 1
                else:
                    files_count += 1
                    parent_path = os.path.dirname(entry.path_lower)
                    folders_with_content.add(parent_path)
            
            progress.update(folders_count, files_count)
            
            if not result.has_more:
                break
            
            result = dbx.files_list_folder_continue(result.cursor)
        
        progress.finish(f"Scanned {folders_count:,} folders, {files_count:,} files")
        
    except ApiError as e:
        print(f"\n❌ Error scanning folder: {e}")
        sys.exit(1)
    
    return all_folders, folders_with_content, case_map


def find_empty_folders(all_folders, folders_with_content):
    """Identify truly empty folders (no files, no non-empty subfolders)."""
    print("\n🔎 Analyzing folder structure...")
    
    # Build parent-child relationships
    children = defaultdict(set)
    for folder in all_folders:
        parent = os.path.dirname(folder)
        if parent in all_folders:
            children[parent].add(folder)
    
    # Mark folders with content
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
    changed = True
    iterations = 0
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
    
    # Empty folders are those without content
    empty_folders = all_folders - has_content
    
    # Sort by depth (deepest first for safe deletion)
    empty_list = sorted(empty_folders, key=lambda x: x.count('/'), reverse=True)
    
    print(f"   Analysis complete ({iterations} iterations)")
    
    return empty_list


def display_results(empty_folders, case_map):
    """Display scan results."""
    print_section("RESULTS")
    
    if not empty_folders:
        print("\n✅ No empty folders found! Your Dropbox is clean.")
        return
    
    print(f"\n📋 Found {len(empty_folders)} empty folder(s):\n")
    
    # Group by depth for better display
    max_display = 50
    displayed = 0
    
    for folder in empty_folders:
        if displayed >= max_display:
            remaining = len(empty_folders) - max_display
            print(f"\n   ... and {remaining} more folders")
            break
        
        display_path = case_map.get(folder, folder)
        depth = display_path.count('/')
        indent = "  " * min(depth, 3)
        print(f"   {displayed + 1:3}. {display_path}")
        displayed += 1
    
    print(f"\n   Total: {len(empty_folders)} empty folder(s)")


def confirm_deletion(count):
    """Get user confirmation for deletion."""
    print_section("⚠️  DELETION WARNING")
    
    print(f"""
   You are about to delete {count} empty folder(s).
   
   • Deleted folders will go to Dropbox trash
   • They can be recovered for 30 days
   • This action requires explicit confirmation
""")
    
    print("   Type 'DELETE' to confirm (or anything else to cancel): ", end="")
    response = input().strip()
    
    return response == "DELETE"


def delete_folders(dbx, empty_folders, case_map):
    """Delete the empty folders."""
    print_section("DELETING FOLDERS")
    
    deleted = 0
    errors = 0
    total = len(empty_folders)
    
    for i, folder in enumerate(empty_folders, 1):
        display_path = case_map.get(folder, folder)
        
        # Progress indicator
        pct = (i / total) * 100
        bar_filled = int(pct / 5)
        bar = '█' * bar_filled + '░' * (20 - bar_filled)
        
        sys.stdout.write(f"\r   [{bar}] {pct:5.1f}% - Deleting {i}/{total}")
        sys.stdout.flush()
        
        try:
            dbx.files_delete_v2(folder)
            deleted += 1
        except ApiError as e:
            errors += 1
            print(f"\n   ✗ Failed: {display_path} - {e}")
    
    print(f"\r   [████████████████████] 100.0% - Complete!".ljust(70))
    
    # Summary
    print_section("DELETION SUMMARY")
    print(f"\n   ✅ Successfully deleted: {deleted}")
    if errors > 0:
        print(f"   ❌ Failed: {errors}")
    
    return deleted, errors


def save_report(folder_path, empty_folders, case_map, deleted=None, mode="scan"):
    """Save a report file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dropbox_report_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write("DROPBOX EMPTY FOLDER REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Folder scanned: {folder_path if folder_path else '/ (entire Dropbox)'}\n")
        f.write(f"Mode: {mode}\n")
        f.write("=" * 60 + "\n\n")
        
        if mode == "scan":
            f.write(f"Empty folders found: {len(empty_folders)}\n\n")
            for folder in empty_folders:
                display_path = case_map.get(folder, folder)
                f.write(f"  {display_path}\n")
        else:
            f.write(f"Folders deleted: {deleted}\n\n")
    
    print(f"\n📄 Report saved: {filename}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Find and delete empty folders in Dropbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 dropbox_cleaner.py --list                    # List root folders
  python3 dropbox_cleaner.py --scan "/Snagit"          # Scan specific folder
  python3 dropbox_cleaner.py --scan ""                 # Scan entire Dropbox
  python3 dropbox_cleaner.py --delete "/Snagit"        # Delete empty folders
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List root folders")
    group.add_argument("--scan", metavar="PATH", help="Scan folder for empty folders (use \"\" for root)")
    group.add_argument("--delete", metavar="PATH", help="Scan and delete empty folders")
    
    args = parser.parse_args()
    
    print_header()
    dbx = connect_dropbox()
    
    if args.list:
        list_root_folders(dbx)
        return
    
    folder_path = args.scan if args.scan is not None else args.delete
    
    # Handle empty string for root
    if folder_path == '""' or folder_path == "''":
        folder_path = ""
    
    # Scan
    all_folders, folders_with_content, case_map = scan_folder(dbx, folder_path)
    
    if not all_folders:
        print("\n✅ No folders found in the specified path.")
        return
    
    # Find empty folders
    empty_folders = find_empty_folders(all_folders, folders_with_content)
    
    # Display results
    display_results(empty_folders, case_map)
    
    if not empty_folders:
        return
    
    # Save scan report
    save_report(folder_path, empty_folders, case_map, mode="scan")
    
    # Handle delete mode
    if args.delete is not None:
        if confirm_deletion(len(empty_folders)):
            deleted, errors = delete_folders(dbx, empty_folders, case_map)
            save_report(folder_path, empty_folders, case_map, deleted=deleted, mode="delete")
        else:
            print("\n❌ Deletion cancelled.")
    else:
        print("\n💡 To delete these folders, run:")
        print(f'   python3 dropbox_cleaner.py --delete "{folder_path}"')


if __name__ == "__main__":
    main()

