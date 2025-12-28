
import os
import pickle
import logging
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from logger_setup import setup_logger
from dropbox_service import app_state

logger, _ = setup_logger("google_service")

# Scopes: metadata.readonly for scanning, drive.file for deleting/trashing (only files created by app?)
# Actually 'https://www.googleapis.com/auth/drive' is full access, might be needed for cleanup.
SCOPES = ['https://www.googleapis.com/auth/drive']

def connect_google():
    """Authenticate with Google Drive."""
    creds = None
    token_path = 'token_google.pickle'
    secrets_path = 'client_secrets.json'
    
    # Check for token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    # Refresh or Login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(secrets_path):
                logger.error("client_secrets.json not found")
                return False, "client_secrets.json not found. Please download it from Google Cloud Console."
                
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Auth flow failed: {e}")
                return False, str(e)
            
        # Save token
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('drive', 'v3', credentials=creds)
        
        # Test call
        about = service.about().get(fields="user").execute()
        user_info = about.get('user', {})
        
        app_state["google_service"] = service
        app_state["connected"] = True
        app_state["account_name"] = user_info.get('displayName', 'Google User')
        app_state["account_email"] = user_info.get('emailAddress', '')
        
        logger.info(f"Connected to Google Drive as {app_state['account_name']}")
        return True, "Connected"
    except Exception as e:
        logger.error(f"Failed to build service: {e}")
        return False, str(e)

def scan_google_drive(folder_id='root'):
    """Recursive scan of Google Drive."""
    service = app_state.get("google_service")
    if not service:
        logger.error("Not connected to Google Drive")
        return

    logger.info("Starting Google Drive Scan...")
    app_state["scanning"] = True
    app_state["scan_progress"] = {
        "status": "scanning",
        "start_time": time.time(),
        "folders": 0,
        "files": 0,
        "total": 0,
        "percent": 0,
        "current_folder": "",
        "folder_sizes": {}
    }
    app_state["empty_folders"] = []
    app_state["google_paths"] = {}  # Map path -> id for deletion
    
    try:
        if folder_id == 'root':
            # Get root name? Usually just 'My Drive'
            pass
            
        _recursive_scan(service, folder_id, "/My Drive")
        
        app_state["scan_progress"]["status"] = "complete"
        app_state["scan_progress"]["percent"] = 100
        logger.info(f"Scan complete. Found {len(app_state['empty_folders'])} empty folders.")
        
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        app_state["scan_progress"]["status"] = "error"
        app_state["scan_progress"]["error"] = str(e)
    finally:
        app_state["scanning"] = False

def _recursive_scan(service, folder_id, current_path):
    if app_state["scanning_cancelled"]: return False
    
    app_state["scan_progress"]["current_folder"] = current_path
    
    # Get children
    page_token = None
    has_files = False
    subfolders = []
    
    while True:
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, size)",
                pageToken=page_token
            ).execute()
        except Exception as e:
             logger.error(f"Error listing {current_path}: {e}")
             return False # Treat as not empty to be safe?

        items = results.get('files', [])
        for item in items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                subfolders.append(item)
            else:
                has_files = True
                app_state["scan_progress"]["files"] += 1
                
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    # Recursively check subfolders
    for sub in subfolders:
        app_state["scan_progress"]["folders"] += 1
        sub_path = f"{current_path}/{sub['name']}"
        sub_is_empty = _recursive_scan(service, sub['id'], sub_path)
        
        # If a subfolder is NOT empty, then THIS folder is not empty
        if not sub_is_empty:
            has_files = True
            
    # If no files and no non-empty subfolders (Wait, logic check)
    # If a folder has subfolders, and ALL subfolders are empty, then the folder contains only empty folders.
    # Is it "empty"?
    # Definition of empty folder usually means "contains nothing".
    # But often we want to delete "chains of empty folders".
    # If I delete the child, the parent becomes empty.
    # So bottom-up: return true if I am empty.
    
    is_empty = (not has_files)
    
    # If I am empty (no files), I *might* have empty subfolders.
    # If I recurse, I should delete deep first.
    # If has_files is True, I am definitely NOT empty.
    
    if is_empty:
        # Validate against system files? GDrive doesn't really have them unless synced.
        # But we should respect exclude patterns from config.
        config = app_state.get("config", {})
        excludes = config.get("exclude_patterns", [])
        folder_name = current_path.split('/')[-1]
        
        if any(ex in folder_name for ex in excludes): # Simple substring check or glob?
             # If excluded, treat as NOT empty so we don't delete parents?
             # Or just ignore it?
             return False

        app_state["empty_folders"].append(current_path)
        app_state["google_paths"][current_path] = folder_id
        
    return is_empty

def delete_google_folders():
    """Delete empty folders (move to trash)."""
    service = app_state.get("google_service")
    if not service:
        return
        
    paths = app_state.get("empty_folders", [])
    path_map = app_state.get("google_paths", {})
    
    app_state["deleting"] = True
    app_state["delete_progress"] = {
        "status": "deleting",
        "current": 0,
        "total": len(paths),
        "deleted": 0,
        "skipped": 0,
        "errors": 0,
        "percent": 0
    }
    
    try:
        for i, path in enumerate(paths):
            if app_state["scanning_cancelled"]: # Reuse scanning_cancelled flag? Or add deleting_cancelled?
                # Usually we should have separate flag but for MVP ok.
                break
                
            file_id = path_map.get(path)
            if file_id:
                try:
                    logger.info(f"Trashing folder: {path} ({file_id})")
                    service.files().update(fileId=file_id, body={'trashed': True}).execute()
                    app_state["delete_progress"]["deleted"] += 1
                except Exception as e:
                    logger.error(f"Failed to delete {path}: {e}")
                    app_state["delete_progress"]["errors"] += 1
            else:
                app_state["delete_progress"]["skipped"] += 1
                
            app_state["delete_progress"]["current"] = i + 1
            app_state["delete_progress"]["percent"] = int(((i + 1) / len(paths)) * 100)
            
        app_state["delete_progress"]["status"] = "complete"
        
    except Exception as e:
        logger.error(f"Deletion failed: {e}")
        app_state["delete_progress"]["status"] = "error"
    finally:
        app_state["deleting"] = False
        app_state["empty_folders"] = [] # Clear list after deletion

