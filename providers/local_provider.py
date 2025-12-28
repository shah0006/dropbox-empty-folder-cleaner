import os
import shutil
import fsspec
from typing import Iterator, IO
from .interface import IFileProvider, FileResource, FileType

class LocalProvider(IFileProvider):
    def __init__(self, root_path: str = "/"):
        self.root_path = root_path
        self.fs = fsspec.filesystem("file")

    def _get_abs_path(self, path: str) -> str:
        # Treat all VFS paths as relative to root_path
        # Remove leading slash to ensure os.path.join appends to root_path
        relative_path = path.lstrip("/")
        return os.path.join(self.root_path, relative_path)

    def list_dir(self, path: str, recursive: bool = False) -> Iterator[FileResource]:
        abs_path = self._get_abs_path(path)
        try:
            if recursive:
                for root, dirs, files in os.walk(abs_path):
                    for d in dirs:
                        full_abs = os.path.join(root, d)
                        rel_path = os.path.relpath(full_abs, self.root_path).replace(os.sep, "/")
                        yield self.stat("/" + rel_path)
                    for f in files:
                        full_abs = os.path.join(root, f)
                        rel_path = os.path.relpath(full_abs, self.root_path).replace(os.sep, "/")
                        yield self.stat("/" + rel_path)
            else:
                for p in self.fs.ls(abs_path, detail=True):
                    # fsspec ls returns absolute paths too?
                    # fs.ls on local returns the path passed in?
                    # Let's verify behavior or safe guard.
                    # fs.ls usually returns list of dicts with 'name' as path.
                    name = p['name']
                    # if name starts with root_path, strip it
                    if name.startswith(self.root_path):
                        rel = os.path.relpath(name, self.root_path).replace(os.sep, "/")
                        yield self.stat("/" + rel)
                    else:
                        # Fallback
                        yield self._to_resource(p)
        except FileNotFoundError:
            return

    def _to_resource(self, info: dict) -> FileResource:
        # Map fsspec info to FileResource
        full_path = info['name']
        if full_path.startswith(self.root_path):
            path = os.path.relpath(full_path, self.root_path).replace(os.sep, "/")
            if not path.startswith("/"):
                path = "/" + path
        else:
            path = full_path

        ftype = FileType.DIRECTORY if info['type'] == 'directory' else FileType.FILE
        # fsspec 'file' system might not return mtime in ls? fallback to os.stat if needed
        # fsspec local fs usually gives size, name, type.
        
        try:
            stat = os.stat(path)
            mtime = stat.st_mtime
            size = stat.st_size
        except:
            mtime = 0.0
            size = info.get('size', 0)

        return FileResource(
            path=path,
            name=os.path.basename(path),
            type=ftype,
            size=size,
            mtime=mtime
        )

    def stat(self, path: str) -> FileResource:
        abs_path = self._get_abs_path(path)
        info = self.fs.info(abs_path)
        return self._to_resource(info)

    def open(self, path: str, mode: str = "rb") -> IO:
        abs_path = self._get_abs_path(path)
        return self.fs.open(abs_path, mode)

    def exists(self, path: str) -> bool:
        return self.fs.exists(self._get_abs_path(path))

    def mkdir(self, path: str, parents: bool = True) -> None:
        self.fs.makedirs(self._get_abs_path(path), exist_ok=True)

    def delete(self, path: str, recursive: bool = False) -> None:
        abs_path = self._get_abs_path(path)
        if self.fs.isdir(abs_path):
            self.fs.rm(abs_path, recursive=recursive)
        else:
            self.fs.rm(abs_path)

    def move(self, src_path: str, dst_path: str) -> None:
        self.fs.mv(self._get_abs_path(src_path), self._get_abs_path(dst_path))

    def copy(self, src_path: str, dst_path: str) -> None:
        self.fs.copy(self._get_abs_path(src_path), self._get_abs_path(dst_path))
        
    def set_mtime(self, path: str, timestamp: float) -> None:
        abs_path = self._get_abs_path(path)
        os.utime(abs_path, (timestamp, timestamp))
