
import os
import json
import threading
import webbrowser
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import dropbox

from dropbox_service import (
    app_state, connect_dropbox, scan_folder, scan_local_folder, 
    delete_folders, delete_local_folders, compare_folders, 
    execute_comparison_actions, exchange_auth_code, test_credentials, 
    save_credentials, get_local_subfolders, logger, delete_conflict_files,
    save_config
)
from scheduler_service import scheduler
from google_service import connect_google, scan_google_drive, delete_google_folders
from core.db import SyncDB
from core.engine import SyncEngine
from providers.local_provider import LocalProvider
from providers.dropbox_provider import DropboxProvider
from providers.google_provider import GoogleDriveProvider

app = FastAPI(title="Dropbox Empty Folder Cleaner v1.4.0")

# Initialize Core Services
sync_db = SyncDB("sync_state.db")
# Providers will be initialized on demand or at startup depending on auth state


# Mount static files and templates
os.makedirs("web/static/css", exist_ok=True)
os.makedirs("web/static/js", exist_ok=True)
os.makedirs("web/templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

@app.on_event("startup")
async def startup_event():
    # Attempt to connect to Dropbox on startup
    threading.Thread(target=connect_dropbox, daemon=True).start()
    
    # Start Scheduler
    scheduler.start()
    
    # Open browser after a short delay
    port = app_state["config"].get("port", 8765)
    url = f"http://127.0.0.1:{port}"
    logger.info(f"Application starting at {url}")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    # Only return serializable fields that the frontend needs
    safe_keys = [
        "connected", "scanning", "deleting", "comparing", 
        "scan_progress", "delete_progress", "empty_folders", 
        "account_name", "account_email", "config", "stats",
        "compare_progress", "compare_executing", "compare_execute_progress"
    ]
    sanitized_state = {k: app_state.get(k) for k in safe_keys}
    
    # Add counts for large lists
    sanitized_state["files_found_count"] = len(app_state.get("found_files", []))
    sanitized_state["conflicts_count"] = len(app_state.get("conflicts", []))

    # Calculate next scheduled run
    scheduler_info = app_state.get("config", {}).get("schedule", {})
    if scheduler_info.get("enabled"):
        import time
        last = scheduler_info.get("last_run", 0)
        interval = scheduler_info.get("interval_hours", 24) * 3600
        next_run = last + interval
        remaining = next_run - time.time()
        sanitized_state["next_scheduled_run"] = max(0, remaining)
    else:
        sanitized_state["next_scheduled_run"] = None
    
    return sanitized_state

@app.get("/api/subfolders")
async def get_subfolders(path: str = "", mode: Optional[str] = None):
    # Use current mode if not specified
    if mode is None:
        mode = app_state["config"].get("mode", "dropbox")
        
    if mode == "local":
        return {"subfolders": get_local_subfolders(path), "mode": "local"}
    else:
        dbx = app_state["dbx"]
        if not dbx:
            return {"subfolders": [], "error": "Not connected", "mode": "dropbox"}
        try:
            dbx_path = "" if path == "/" or not path else path
            res = dbx.files_list_folder(dbx_path)
            subfolders = []
            
            while True:
                for entry in res.entries:
                    if isinstance(entry, dropbox.files.FolderMetadata):
                        subfolders.append({
                            "name": entry.name,
                            "path": entry.path_display
                        })
                if not res.has_more:
                    break
                res = dbx.files_list_folder_continue(res.cursor)
            
            return {"subfolders": sorted(subfolders, key=lambda x: x["name"].lower()), "mode": "dropbox"}
        except Exception as e:
            logger.error(f"Error listing subfolders for {path}: {e}")
            return {"subfolders": [], "error": str(e), "mode": "dropbox"}

@app.get("/api/files")
async def get_files():
    return {"files": app_state.get("found_files", [])}

@app.get("/api/config")
async def get_config():
    return app_state["config"]

@app.post("/api/config")
async def update_config(config: dict):
    app_state["config"].update(config)
    try:
        with open("config.json", "w") as f:
            json.dump(app_state["config"], f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
    return {"status": "success"}

@app.get("/api/credentials")
async def get_credentials():
    config = app_state["config"]
    return {
        "app_key": config.get("app_key", ""),
        "has_secret": bool(os.getenv("DROPBOX_APP_SECRET")),
        "has_token": bool(os.getenv("DROPBOX_REFRESH_TOKEN"))
    }

@app.post("/api/credentials")
async def post_credentials(creds: dict):
    save_credentials(creds)
    # Reconnect in background
    threading.Thread(target=connect_dropbox, daemon=True).start()
    return {"status": "success"}

@app.post("/api/google/connect")
async def api_connect_google():
    success, message = connect_google()
    if success:
        return {"status": "success", "message": message}
    else:
        return {"status": "error", "message": message}

@app.post("/api/scan")
async def start_scan(background_tasks: BackgroundTasks, request: Request):
    data = await request.json()
    folder = data.get("folder", "")
    mode = app_state["config"].get("mode", "dropbox")
    
    if app_state["scanning"]:
        return {"status": "already_scanning"}
    
    app_state["scanning_cancelled"] = False
    
    if mode == "local":
        background_tasks.add_task(scan_local_folder, folder)
    elif mode == "google":
        background_tasks.add_task(scan_google_drive, folder)
    else:
        background_tasks.add_task(scan_folder, folder)
    
    return {"status": "started"}

@app.post("/api/cancel")
async def cancel_action():
    app_state["scanning_cancelled"] = True
    app_state["compare_cancelled"] = True
    return {"status": "cancelled"}

@app.post("/api/delete")
async def start_delete(background_tasks: BackgroundTasks):
    mode = app_state["config"].get("mode", "dropbox")
    if app_state["deleting"]:
        return {"status": "already_deleting"}
    
    if mode == "local":
        background_tasks.add_task(delete_local_folders)
    elif mode == "google":
        background_tasks.add_task(delete_google_folders)
    else:
        background_tasks.add_task(delete_folders)
    return {"status": "started"}

@app.get("/api/conflicts")
async def get_conflicts():
    return {"conflicts": app_state.get("conflicts", [])}

@app.post("/api/conflicts/delete")
async def delete_conflicts_endpoint(background_tasks: BackgroundTasks):
    if app_state["deleting"]:
        return {"status": "already_deleting"}
        
    background_tasks.add_task(delete_conflict_files)
    return {"status": "started"}

@app.post("/api/auth/exchange")
async def auth_exchange(data: dict):
    result = exchange_auth_code(data)
    if result.get("success"):
        return {"status": "success", "refresh_token": result["refresh_token"]}
    return {"status": "error", "error": result.get("error")}

@app.post("/api/auth/test")
async def auth_test(data: dict):
    result = test_credentials(data)
    if result.get("success"):
        return {"status": "success", "account": result["account_name"]}
    return {"status": "error", "error": result.get("error")}

@app.post("/api/compare/start")
async def compare_start_endpoint(background_tasks: BackgroundTasks, data: dict):
    left_path = data.get("left_path", "")
    right_path = data.get("right_path", "")
    left_mode = data.get("left_mode", "dropbox")
    right_mode = data.get("right_mode", "dropbox")
    
    if app_state["comparing"]:
        return {"status": "already_comparing"}
        
    background_tasks.add_task(compare_folders, left_path, right_path, left_mode, right_mode)
    return {"status": "started"}

@app.post("/api/compare/cancel")
async def compare_cancel_endpoint():
    app_state["compare_cancelled"] = True
    return {"status": "cancelled"}

@app.post("/api/sync/start")
async def sync_start(background_tasks: BackgroundTasks, data: dict):
    """
    Experimental Endpoint to trigger the New Sync Engine.
    For MVP, we assume Left=Local, Right=Dropbox (or Google).
    """
    if app_state["scanning"] or app_state["deleting"]:
        return {"status": "busy"}

    mode = app_state["config"].get("mode", "dropbox")
    local_path = app_state["config"].get("local_path", ".")
    
    # Initialize Providers based on Config
    left_provider = LocalProvider(local_path)
    
    right_provider = None
    if mode == "dropbox":
        if not app_state.get("dbx"):
             return {"status": "error", "message": "Dropbox not connected"}
        right_provider = DropboxProvider(app_state["dbx"])
    elif mode == "google":
        service = app_state.get("google_service")
        if not service:
             return {"status": "error", "message": "Google Drive not connected"}
        right_provider = GoogleDriveProvider(service)
    else:
        # Local to Local? Not currently supported in UI config
        # Or could be Local->Local if designed.
        return {"status": "error", "message": "Invalid mode for sync"}

    def run_sync_task():
        engine = SyncEngine(left_provider, right_provider, sync_db)
        try:
            logger.info("Starting Experimental Sync...")
            actions = engine.sync()
            logger.info(f"Sync Finished. Actions: {len(actions)}")
            # Logic to update global app_state for UI visibility?
        except Exception as e:
            logger.error(f"Sync Task Failed: {e}")

    background_tasks.add_task(run_sync_task)
    return {"status": "started", "engine": "swapsync-v2"}

@app.post("/api/compare/status")
@app.get("/api/compare/status")
async def compare_status_endpoint():
    return app_state["compare_progress"]

@app.post("/api/compare/results")
async def compare_results_endpoint():
    return app_state["compare_results"]

@app.post("/api/compare/execute")
async def compare_execute_endpoint(background_tasks: BackgroundTasks, data: dict):
    if app_state["compare_executing"]:
        return {"status": "already_executing"}
    
    delete_indices = data.get("delete_indices")
    copy_indices = data.get("copy_indices")
    
    background_tasks.add_task(execute_comparison_actions, delete_indices, copy_indices)
    return {"status": "started"}

@app.post("/api/compare/reset")
async def compare_reset_endpoint():
    app_state["compare_results"] = None
    app_state["compare_progress"] = {"status": "idle"}
    return {"status": "success"}

@app.get("/api/export")
async def export_results_endpoint(format: str = "json"):
    empty_folders = [app_state["case_map"].get(f, f) for f in app_state["empty_folders"]]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format == 'csv':
        content = "Path,Depth\n"
        for folder in empty_folders:
            depth = folder.count('/')
            content += f'"{folder}",{depth}\n'
        
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=\"empty_folders_{timestamp}.csv\""}
        )
    else:
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "scan_folder": app_state.get("last_scan_folder") or "/",
            "account": app_state.get("account_name"),
            "total_empty_folders": len(empty_folders),
            "stats": app_state.get("stats"),
            "config_used": app_state["config"],
            "empty_folders": [{"path": f, "depth": f.count('/')} for f in empty_folders]
        }
        
        return Response(
            content=json.dumps(export_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=\"empty_folders_{timestamp}.json\""}
        )

if __name__ == "__main__":
    port = app_state["config"].get("port", 8765)
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="127.0.0.1", port=port)
