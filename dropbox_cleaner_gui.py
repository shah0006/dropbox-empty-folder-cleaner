#!/usr/bin/env python3
"""
Dropbox Empty Folder Cleaner - GUI Version
==========================================
A macOS GUI application to find and delete empty folders in Dropbox.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
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


class DropboxCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dropbox Empty Folder Cleaner")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # Configure dark theme colors
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.accent_color = "#0078d4"
        self.secondary_bg = "#2d2d2d"
        self.success_color = "#4caf50"
        self.warning_color = "#ff9800"
        self.error_color = "#f44336"
        
        self.root.configure(bg=self.bg_color)
        
        # State
        self.dbx = None
        self.empty_folders = []
        self.case_map = {}
        self.scanning = False
        self.folders_found = 0
        self.files_found = 0
        
        self.setup_ui()
        self.connect_dropbox()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=('SF Pro Display', 12))
        style.configure("Title.TLabel", font=('SF Pro Display', 18, 'bold'))
        style.configure("Status.TLabel", font=('SF Pro Display', 11))
        style.configure("TButton", font=('SF Pro Display', 12), padding=10)
        style.configure("Accent.TButton", background=self.accent_color, foreground=self.fg_color)
        style.configure("TCombobox", font=('SF Pro Display', 12))
        style.configure("Horizontal.TProgressbar", thickness=20)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="📁 Dropbox Empty Folder Cleaner", style="Title.TLabel")
        title_label.pack(pady=(0, 20))
        
        # Connection status
        self.connection_label = ttk.Label(main_frame, text="⏳ Connecting to Dropbox...", style="Status.TLabel")
        self.connection_label.pack(pady=(0, 15))
        
        # Folder selection frame
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(folder_frame, text="Scan folder:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.folder_var = tk.StringVar(value="/Snagit")
        self.folder_combo = ttk.Combobox(folder_frame, textvariable=self.folder_var, width=40, state='readonly')
        self.folder_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Progress section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=15)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to scan", style="Status.TLabel")
        self.progress_label.pack(pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.stats_label = ttk.Label(progress_frame, text="", style="Status.TLabel")
        self.stats_label.pack(pady=(5, 0))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15)
        
        self.scan_btn = ttk.Button(button_frame, text="🔍 Scan for Empty Folders", command=self.start_scan)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_btn = ttk.Button(button_frame, text="🗑️ Delete Empty Folders", command=self.delete_folders, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Results section
        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(results_frame, text="Results:").pack(anchor=tk.W)
        
        # Results text area with scrollbar
        self.results_text = scrolledtext.ScrolledText(
            results_frame, 
            height=15, 
            font=('SF Mono', 11),
            bg=self.secondary_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            selectbackground=self.accent_color
        )
        self.results_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Footer
        footer_label = ttk.Label(main_frame, text="⚠️ Dry-run mode: Review results before deleting", 
                                  style="Status.TLabel", foreground=self.warning_color)
        footer_label.pack(pady=(10, 0))
    
    def connect_dropbox(self):
        """Connect to Dropbox and load folder list."""
        def connect():
            try:
                load_dotenv()
                app_key = os.getenv("DROPBOX_APP_KEY")
                app_secret = os.getenv("DROPBOX_APP_SECRET")
                refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
                
                if not all([app_key, app_secret, refresh_token]):
                    self.update_connection("❌ Missing credentials in .env file", error=True)
                    return
                
                self.dbx = dropbox.Dropbox(
                    oauth2_refresh_token=refresh_token,
                    app_key=app_key,
                    app_secret=app_secret
                )
                
                account = self.dbx.users_get_current_account()
                self.update_connection(f"✅ Connected as: {account.name.display_name}")
                
                # Load folder list
                result = self.dbx.files_list_folder('')
                folders = [e.path_display for e in result.entries 
                          if isinstance(e, FolderMetadata) and '(' not in e.path_display]
                folders.sort()
                
                self.root.after(0, lambda: self.folder_combo.configure(values=folders))
                if folders:
                    self.root.after(0, lambda: self.folder_var.set(folders[0]))
                    
            except AuthError as e:
                self.update_connection(f"❌ Auth failed: {e}", error=True)
            except Exception as e:
                self.update_connection(f"❌ Error: {e}", error=True)
        
        threading.Thread(target=connect, daemon=True).start()
    
    def update_connection(self, text, error=False):
        """Update connection status label."""
        color = self.error_color if error else self.success_color
        self.root.after(0, lambda: self.connection_label.configure(text=text, foreground=color))
    
    def update_progress(self, text):
        """Update progress label."""
        self.root.after(0, lambda: self.progress_label.configure(text=text))
    
    def update_stats(self, folders, files):
        """Update stats label."""
        self.root.after(0, lambda: self.stats_label.configure(
            text=f"Found: {folders:,} folders, {files:,} files"
        ))
    
    def log(self, text):
        """Add text to results area."""
        self.root.after(0, lambda: self._log_safe(text))
    
    def _log_safe(self, text):
        self.results_text.insert(tk.END, text + "\n")
        self.results_text.see(tk.END)
    
    def start_scan(self):
        """Start scanning for empty folders."""
        if not self.dbx:
            messagebox.showerror("Error", "Not connected to Dropbox")
            return
        
        if self.scanning:
            return
        
        self.scanning = True
        self.scan_btn.configure(state=tk.DISABLED)
        self.delete_btn.configure(state=tk.DISABLED)
        self.results_text.delete(1.0, tk.END)
        self.empty_folders = []
        self.folders_found = 0
        self.files_found = 0
        
        self.progress_bar.start(10)
        
        folder_path = self.folder_var.get()
        threading.Thread(target=self.scan_folder, args=(folder_path,), daemon=True).start()
    
    def scan_folder(self, folder_path):
        """Scan a folder for empty folders."""
        try:
            self.update_progress(f"Scanning: {folder_path}")
            self.log(f"🔍 Starting scan of: {folder_path}")
            self.log("-" * 50)
            
            all_folders = set()
            folders_with_content = set()
            self.case_map = {}
            
            # List all entries recursively
            result = self.dbx.files_list_folder(folder_path, recursive=True)
            batch = 0
            
            while True:
                batch += 1
                for entry in result.entries:
                    if isinstance(entry, FolderMetadata):
                        all_folders.add(entry.path_lower)
                        self.case_map[entry.path_lower] = entry.path_display
                        self.folders_found += 1
                    else:
                        self.files_found += 1
                        parent_path = os.path.dirname(entry.path_lower)
                        folders_with_content.add(parent_path)
                
                self.update_stats(self.folders_found, self.files_found)
                self.update_progress(f"Scanning batch {batch}... ({self.folders_found:,} folders)")
                
                if not result.has_more:
                    break
                
                result = self.dbx.files_list_folder_continue(result.cursor)
            
            self.log(f"✓ Found {self.folders_found:,} folders, {self.files_found:,} files")
            self.update_progress("Analyzing folder structure...")
            
            # Find empty folders
            self.empty_folders = self.find_empty_folders(all_folders, folders_with_content)
            
            # Display results
            self.root.after(0, self.display_results)
            
        except ApiError as e:
            self.log(f"❌ API Error: {e}")
            self.update_progress("Scan failed")
        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.update_progress("Scan failed")
        finally:
            self.scanning = False
            self.root.after(0, lambda: self.progress_bar.stop())
            self.root.after(0, lambda: self.scan_btn.configure(state=tk.NORMAL))
    
    def find_empty_folders(self, all_folders, folders_with_content):
        """Identify truly empty folders."""
        children = defaultdict(set)
        for folder in all_folders:
            parent = os.path.dirname(folder)
            if parent in all_folders:
                children[parent].add(folder)
        
        has_content = set(folders_with_content)
        
        for folder in folders_with_content:
            current = folder
            while current:
                has_content.add(current)
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent
        
        changed = True
        while changed:
            changed = False
            for folder in all_folders:
                if folder in has_content:
                    continue
                for child in children[folder]:
                    if child in has_content:
                        has_content.add(folder)
                        changed = True
                        break
        
        empty_folders = all_folders - has_content
        return sorted(empty_folders, key=lambda x: x.count('/'), reverse=True)
    
    def display_results(self):
        """Display scan results."""
        self.log("")
        self.log("=" * 50)
        
        if not self.empty_folders:
            self.log("✅ No empty folders found!")
            self.update_progress("Scan complete - no empty folders")
        else:
            self.log(f"📋 Found {len(self.empty_folders)} empty folder(s):")
            self.log("")
            
            for i, folder in enumerate(self.empty_folders, 1):
                display_path = self.case_map.get(folder, folder)
                self.log(f"  {i:3}. {display_path}")
            
            self.log("")
            self.log("=" * 50)
            self.update_progress(f"Found {len(self.empty_folders)} empty folders")
            self.delete_btn.configure(state=tk.NORMAL)
    
    def delete_folders(self):
        """Delete the empty folders after confirmation."""
        if not self.empty_folders:
            return
        
        # Confirmation dialog
        count = len(self.empty_folders)
        result = messagebox.askokcancel(
            "Confirm Deletion",
            f"⚠️ WARNING: This cannot be undone!\n\n"
            f"You are about to delete {count} empty folder(s).\n\n"
            f"Deleted folders will go to Dropbox trash\n"
            f"(recoverable for 30 days).\n\n"
            f"Do you want to proceed?",
            icon='warning'
        )
        
        if not result:
            self.log("\n❌ Deletion cancelled by user.")
            return
        
        # Second confirmation
        result2 = messagebox.askokcancel(
            "Final Confirmation",
            f"Are you REALLY sure you want to delete\n"
            f"{count} empty folder(s)?\n\n"
            f"Type 'yes' in your mind and click OK.",
            icon='warning'
        )
        
        if not result2:
            self.log("\n❌ Deletion cancelled by user.")
            return
        
        self.delete_btn.configure(state=tk.DISABLED)
        self.scan_btn.configure(state=tk.DISABLED)
        self.progress_bar.start(10)
        
        threading.Thread(target=self.do_delete, daemon=True).start()
    
    def do_delete(self):
        """Perform the deletion."""
        self.log("\n🗑️ Deleting empty folders...")
        self.log("-" * 50)
        
        deleted = 0
        errors = 0
        total = len(self.empty_folders)
        
        for i, folder in enumerate(self.empty_folders, 1):
            display_path = self.case_map.get(folder, folder)
            self.update_progress(f"Deleting {i}/{total}...")
            
            try:
                self.dbx.files_delete_v2(folder)
                self.log(f"  ✓ Deleted: {display_path}")
                deleted += 1
            except ApiError as e:
                self.log(f"  ✗ Failed: {display_path}")
                self.log(f"      Error: {e}")
                errors += 1
        
        self.log("")
        self.log("=" * 50)
        self.log(f"📊 SUMMARY: Deleted {deleted}, Failed {errors}")
        
        self.update_progress(f"Done! Deleted {deleted} folders")
        self.root.after(0, lambda: self.progress_bar.stop())
        self.root.after(0, lambda: self.scan_btn.configure(state=tk.NORMAL))
        self.empty_folders = []
        
        # Save report
        self.save_report(deleted, errors)
    
    def save_report(self, deleted, errors):
        """Save a report file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"deletion_report_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write(f"Dropbox Empty Folder Deletion Report\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Deleted: {deleted}, Errors: {errors}\n")
            self.log(f"\n📄 Report saved to: {filename}")
        except:
            pass


def main():
    root = tk.Tk()
    
    # macOS specific settings
    try:
        root.tk.call('tk', 'scaling', 2.0)  # Retina display
    except:
        pass
    
    app = DropboxCleanerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

