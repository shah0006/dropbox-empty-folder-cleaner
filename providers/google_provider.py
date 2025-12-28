import io
import logging
from typing import Iterator, IO, Optional, Dict

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

from .interface import IFileProvider, FileResource, FileType

logger = logging.getLogger("google_provider")

class GoogleDriveProvider(IFileProvider):
    def __init__(self, service):
        self.service = service
        # Simple cache for path -> id resolution to avoid excessive API calls
        # In a real impl, this might need invalidation or be part of the SyncEngine state
        self._path_cache: Dict[str, str] = {"/": "root", "": "root"}

    def _resolve_path(self, path: str) -> str:
        """Resolve a posix-style path to a Google Drive File ID."""
        path = path.strip("/")
        if not path:
            return "root"
        
        if path in self._path_cache:
            return self._path_cache[path]

        parts = path.split("/")
        parent_id = "root"
        current_path = ""
        
        for part in parts:
            current_path = f"{current_path}/{part}" if current_path else part
            if current_path in self._path_cache:
                parent_id = self._path_cache[current_path]
                continue
                
            # Search for 'part' in 'parent_id'
            try:
                query = f"'{parent_id}' in parents and name = '{part}' and trashed = false"
                results = self.service.files().list(
                    q=query, fields="files(id, name, mimeType)", pageSize=1
                ).execute()
                files = results.get('files', [])
                if not files:
                    raise FileNotFoundError(f"Path not found: {path} (Segment: {part})")
                
                parent_id = files[0]['id']
                self._path_cache[current_path] = parent_id
            except HttpError as e:
                raise FileNotFoundError(f"API Error resolving path {path}: {e}")

        return parent_id

    def list_dir(self, path: str, recursive: bool = False) -> Iterator[FileResource]:
        folder_id = self._resolve_path(path)
        
        page_token = None
        while True:
            try:
                query = f"'{folder_id}' in parents and trashed = false"
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, md5Checksum)",
                    pageToken=page_token
                ).execute()

                for item in results.get('files', []):
                    # Cache the child's ID/Path
                    child_path = f"{path.rstrip('/')}/{item['name']}"
                    self._path_cache[child_path] = item['id']
                    
                    yield self._to_resource(item, child_path)

                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            except HttpError as e:
                logger.error(f"Error listing {path}: {e}")
                break

    def _to_resource(self, item: dict, path: str) -> FileResource:
        is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
        size = int(item.get('size', 0))
        
        # RFC 3339 timestamp parsing could be added here
        # For simplicity, returning 0.0 or needing a parser
        mtime = 0.0 
        
        return FileResource(
            path=path,
            name=item['name'],
            type=FileType.DIRECTORY if is_folder else FileType.FILE,
            size=size,
            mtime=mtime,
            chksum=item.get('md5Checksum'),
            extra={'id': item['id']}
        )

    def open(self, path: str, mode: str = "rb") -> IO:
        file_id = self._resolve_path(path)
        if "w" in mode:
            # Upload logic ... requires a specialized Writer similar to DropboxFileWriter
            # Implementing a basic BytesIO buffer for now
            raise NotImplementedError("Write support pending streaming upload impl")
        else:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.seek(0)
            return fh

    def stat(self, path: str) -> FileResource:
        file_id = self._resolve_path(path)
        item = self.service.files().get(
            fileId=file_id, 
            fields="id, name, mimeType, size, modifiedTime, md5Checksum"
        ).execute()
        return self._to_resource(item, path)

    def exists(self, path: str) -> bool:
        try:
            self._resolve_path(path)
            return True
        except FileNotFoundError:
            return False

    def mkdir(self, path: str, parents: bool = True) -> None:
        # Complex logic: need to find deepest existing parent, then create chain
        pass 

    def delete(self, path: str, recursive: bool = False) -> None:
        file_id = self._resolve_path(path)
        self.service.files().update(fileId=file_id, body={'trashed': True}).execute()
        # Remove from cache
        if path in self._path_cache:
            del self._path_cache[path]

    def move(self, src_path: str, dst_path: str) -> None:
        pass

    def copy(self, src_path: str, dst_path: str) -> None:
        pass

    def set_mtime(self, path: str, timestamp: float) -> None:
        pass
