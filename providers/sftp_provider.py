import logging
import stat
import paramiko
from typing import Iterator, IO, Optional
from urllib.parse import urlparse
from .interface import IFileProvider, FileResource, FileType

logger = logging.getLogger("sftp_provider")

class SFTPProvider(IFileProvider):
    def __init__(self, host: str, username: str, 
                 password: Optional[str] = None, 
                 key_filename: Optional[str] = None,
                 port: int = 22):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._sftp = None
        self._connect()

    def _connect(self):
        try:
            self.ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                key_filename=self.key_filename
            )
            self._sftp = self.ssh.open_sftp()
            logger.info(f"Connected to SFTP: {self.host}")
        except Exception as e:
            logger.error(f"SFTP connection failed: {e}")
            raise e

    def _ensure_connected(self):
        if not self._sftp or not self._sftp.get_channel() or self._sftp.get_channel().closed:
            self._connect()

    def list_dir(self, path: str, recursive: bool = False) -> Iterator[FileResource]:
        self._ensure_connected()
        try:
            # SFTP listdir is shallow. Recursive needs manual walk.
            # Normalizing path: ./ or /
            if not path: path = "."
            
            for attr in self._sftp.listdir_attr(path):
                full_path = f"{path.rstrip('/')}/{attr.filename}"
                
                ftype = FileType.DIRECTORY if stat.S_ISDIR(attr.st_mode) else FileType.FILE
                resource = FileResource(
                    path=full_path,
                    name=attr.filename,
                    type=ftype,
                    size=attr.st_size,
                    mtime=attr.st_mtime
                )
                yield resource

                if recursive and ftype == FileType.DIRECTORY:
                    try:
                       yield from self.list_dir(full_path, recursive=True)
                    except Exception:
                        pass # Permissions?
        except IOError:
            pass

    def stat(self, path: str) -> FileResource:
        self._ensure_connected()
        try:
            attr = self._sftp.stat(path)
            ftype = FileType.DIRECTORY if stat.S_ISDIR(attr.st_mode) else FileType.FILE
            return FileResource(
                path=path,
                name=path.split('/')[-1],
                type=ftype,
                size=attr.st_size,
                mtime=attr.st_mtime
            )
        except IOError:
            raise FileNotFoundError(f"Path not found: {path}")

    def exists(self, path: str) -> bool:
        try:
            self.stat(path)
            return True
        except FileNotFoundError:
            return False

    def open(self, path: str, mode: str = "rb") -> IO:
        self._ensure_connected()
        return self._sftp.open(path, mode)

    def mkdir(self, path: str, parents: bool = True) -> None:
        self._ensure_connected()
        # SFTP mkdir doesn't support parents=True natively, basic impl
        try:
            self._sftp.mkdir(path)
        except IOError:
            # Check if exists?
            pass

    def delete(self, path: str, recursive: bool = False) -> None:
        self._ensure_connected()
        # SFTP remove is unlink for files, rmdir for dirs
        try:
            info = self.stat(path)
            if info.type == FileType.DIRECTORY:
                if recursive:
                    for child in self.list_dir(path, recursive=False):
                        self.delete(child.path, recursive=True)
                self._sftp.rmdir(path)
            else:
                self._sftp.remove(path)
        except Exception as e:
            logger.error(f"Delete failed {path}: {e}")

    def move(self, src_path: str, dst_path: str) -> None:
        self._ensure_connected()
        self._sftp.rename(src_path, dst_path)

    def copy(self, src_path: str, dst_path: str) -> None:
        # SFTP has no remote-side copy usually. Need to stream read->write.
        # This is expensive.
        raise NotImplementedError("SFTP server-side copy not supported. Use read/write stream.")

    def set_mtime(self, path: str, timestamp: float) -> None:
        self._ensure_connected()
        self._sftp.utime(path, (timestamp, timestamp))

    def close(self):
        if self._sftp:
            self._sftp.close()
        if self.ssh:
            self.ssh.close()
