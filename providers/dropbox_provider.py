import io
import dropbox
from dropbox.files import FileMetadata, FolderMetadata, WriteMode
from dropbox.exceptions import ApiError
from typing import Iterator, IO, Optional

from .interface import IFileProvider, FileResource, FileType

class DropboxFileWriter(io.BytesIO):
    """
    Wrapper for writing to Dropbox.
    Uploads content on close().
    """
    def __init__(self, dbx: dropbox.Dropbox, path: str, mode: WriteMode = WriteMode.overwrite):
        super().__init__()
        self.dbx = dbx
        self.path = path
        self.mode = mode
        self._closed = False

    def close(self):
        if self._closed:
            return
        self.seek(0)
        self.dbx.files_upload(self.read(), self.path, mode=self.mode)
        self._closed = True
        super().close()

class DropboxProvider(IFileProvider):
    def __init__(self, dbx: dropbox.Dropbox):
        self.dbx = dbx

    def _normalize_path(self, path: str) -> str:
        if path == "/" or path == ".":
            return ""
        if not path.startswith("/"):
            return "/" + path
        return path

    def _to_resource(self, metadata) -> FileResource:
        ftype = FileType.DIRECTORY if isinstance(metadata, FolderMetadata) else FileType.FILE
        size = getattr(metadata, 'size', 0)
        # client_modified is datetime. converting to timestamp
        mtime = 0.0
        if hasattr(metadata, 'client_modified'):
            mtime = metadata.client_modified.timestamp()
            
        chksum = getattr(metadata, 'content_hash', None)

        return FileResource(
            path=metadata.path_display or metadata.path_lower,
            name=metadata.name,
            type=ftype,
            size=size,
            mtime=mtime,
            chksum=chksum
        )

    def list_dir(self, path: str, recursive: bool = False) -> Iterator[FileResource]:
        dbx_path = self._normalize_path(path)
        try:
            res = self.dbx.files_list_folder(dbx_path, recursive=recursive)
            while True:
                for entry in res.entries:
                    yield self._to_resource(entry)
                
                if not res.has_more:
                    break
                res = self.dbx.files_list_folder_continue(res.cursor)
        except ApiError as e:
            # Handle directory not found or handled essentially as empty if it doesn't exist?
            # Or raise error. LocalProvider raises nothing on iterating missing dir (catch FileNotFoundError).
            pass

    def stat(self, path: str) -> FileResource:
        dbx_path = self._normalize_path(path)
        try:
            md = self.dbx.files_get_metadata(dbx_path)
            return self._to_resource(md)
        except ApiError:
            raise FileNotFoundError(f"Path not found: {path}")

    def exists(self, path: str) -> bool:
        try:
            self.stat(path)
            return True
        except FileNotFoundError:
            return False

    def open(self, path: str, mode: str = "rb") -> IO:
        dbx_path = self._normalize_path(path)
        if "w" in mode:
            # Write mode
            # TODO: Support 'a' (append) via session upload if needed, but 'w' is standard
            return DropboxFileWriter(self.dbx, dbx_path)
        else:
            # Read mode
            try:
                md, res = self.dbx.files_download(dbx_path)
                # res.content is bytes. returning BytesIO for compatibility
                return io.BytesIO(res.content)
                # Optimization: res.raw is a stream, but requires connection handling. 
                # For small files, content is fine. For streaming, we might need a raw wrapper.
            except ApiError:
                raise FileNotFoundError(f"File not found: {path}")

    def mkdir(self, path: str, parents: bool = True) -> None:
        dbx_path = self._normalize_path(path)
        try:
            self.dbx.files_create_folder_v2(dbx_path)
        except ApiError as e:
            # Ignore if folder exists
            if hasattr(e, 'error') and e.error.is_path() and e.error.get_path().is_conflict():
                return
            raise e

    def delete(self, path: str, recursive: bool = False) -> None:
        dbx_path = self._normalize_path(path)
        self.dbx.files_delete_v2(dbx_path)

    def move(self, src_path: str, dst_path: str) -> None:
        self.dbx.files_move_v2(self._normalize_path(src_path), self._normalize_path(dst_path))

    def copy(self, src_path: str, dst_path: str) -> None:
        self.dbx.files_copy_v2(self._normalize_path(src_path), self._normalize_path(dst_path))

    def set_mtime(self, path: str, timestamp: float) -> None:
        # Dropbox doesn't support setting mtime easily on existing files without upload.
        # usually done during upload with client_modified.
        # Ignoring for now or require re-upload.
        pass
