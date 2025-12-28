import time
import sys
import os
from collections import defaultdict

class ProgressBar:
    """Simple text-based progress indicator for CLI tools."""
    
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


def find_empty_folders(all_folders, folders_with_content):
    """
    Identify truly empty folders (no files, no non-empty subfolders).
    Shared logic used by Web, CLI, and Compare tools.
    """
    # Build parent-child relationships
    children = defaultdict(set)
    for folder in all_folders:
        parent = os.path.dirname(folder)
        if parent in all_folders:
            children[parent].add(folder)
    
    # Mark folders with content
    has_content = set(folders_with_content)
    
    # Propagate content markers upward
    # If a child has content, all its parents have content
    for folder in folders_with_content:
        current = folder
        while current:
            has_content.add(current)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    
    # Mark folders with non-empty children
    # Uses iterative approach to ensure all "empty-looking" parents 
    # of non-empty children are marked non-empty
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
    
    # Empty folders are those without content
    empty_folders = all_folders - has_content
    
    # Sort by depth (deepest first for safe deletion)
    return sorted(empty_folders, key=lambda x: x.count('/'), reverse=True)
