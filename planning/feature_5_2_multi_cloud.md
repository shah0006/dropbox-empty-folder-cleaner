# Feature 5.2: Multi-Cloud Connectors (Google Drive)

## Objective
Expand the Intelligent Hygiene Suite to support Google Drive, allowing users to scan for empty folders and perform hygiene on their Google Drive storage.

## Architecture
The system will move towards a "Provider" pattern, where Dropbox, Local, and Google Drive are interchangeable providers.

### 1. New Dependencies
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`

### 2. Authorization Flow
- **Google Cloud Console Project**: Need a project with Google Drive API enabled.
- **OAuth 2.0**: Similar to Dropbox, but using Google's flow.
- **Scopes**: `https://www.googleapis.com/auth/drive.metadata.readonly` (for scanning) and `https://www.googleapis.com/auth/drive` (for deletion, if full access needed). Ideally start with least privilege.

### 3. `google_service.py`
Create a new service module `google_service.py` that mirrors the interface of `dropbox_service.py` (or at least the core functions):
- `connect_google()`
- `scan_google_drive()`
- `delete_google_drive_folders()`

### 4. Integration
- Update `app_state` in `dropbox_service.py` (which effectively acts as the `state_manager` currently) to hold Google credentials/service objects.
- Update `main.py` Config API to support `mode="google"`.
- Update Frontend Settings to allow selecting Google Drive and entering credentials (client_secret.json or equivalent).

## Implementation Steps

1. [ ] **Dependencies**: Update `requirements.txt`.
2. [ ] **Service Module**: Create `google_service.py` with authentication logic.
3. [ ] **Scanning Logic**: Implement recursive folder scanning using Google Drive API (`files.list` with `q` parameter for mimeType `application/vnd.google-apps.folder`).
4. [ ] **UI Update**: Add Google Drive option to Settings Modal.
5. [ ] **Integration**: Wire up the "Start Scan" button to call `scan_google_drive` when mode is Google.

## Risks & Challenges
- **Rate Limiting**: Google Drive API has strict quotas. Need robust backoff/retry.
- **Trash Behavior**: Google Drive Trash logic differs from Dropbox.
- **Shared Drives**: Support for "Shared Drives" (formerly Team Drives) might require extra logic.
