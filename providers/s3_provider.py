import logging
import s3fs
from typing import Iterator, IO, Optional, Any
from .interface import IFileProvider, FileResource, FileType

logger = logging.getLogger("s3_provider")

class S3Provider(IFileProvider):
    def __init__(self, bucket: str, 
                 access_key: Optional[str] = None, 
                 secret_key: Optional[str] = None, 
                 endpoint_url: Optional[str] = None,
                 region_name: Optional[str] = None):
        """
        Initialize S3 Provider.
        If keys are None, s3fs will try to use environment variables or ~/.aws/credentials
        """
        self.bucket = bucket.strip("/")
        
        client_kwargs = {}
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url
        if region_name:
            client_kwargs['region_name'] = region_name

        self.fs = s3fs.S3FileSystem(
            key=access_key,
            secret=secret_key,
            client_kwargs=client_kwargs
        )

    def _get_s3_path(self, path: str) -> str:
        # S3FS expects "bucket/path/to/file"
        clean_path = path.strip("/")
        return f"{self.bucket}/{clean_path}"

    def list_dir(self, path: str, recursive: bool = False) -> Iterator[FileResource]:
        s3_path = self._get_s3_path(path)
        
        try:
            # s3fs ls returns list of dicts. detail=True gives size, type, etc.
            # If recursive, use find() or walk()
            
            if recursive:
                # find returns {path: {details}}
                files = self.fs.find(s3_path, detail=True)
                for p, info in files.items():
                    yield self._to_resource(info)
            else:
                entries = self.fs.ls(s3_path, detail=True)
                for info in entries:
                    yield self._to_resource(info)
                    
        except FileNotFoundError:
            # Bucket or folder might not exist, or just be empty prefix
            pass
        except Exception as e:
            logger.error(f"S3 list_dir failed: {e}")
            raise e

    def _to_resource(self, info: dict) -> FileResource:
        # s3fs info: {'name': 'bucket/file', 'size': 100, 'type': 'file', 'LastModified': dt}
        path = info['name']
        # Strip bucket from path to normalize to root-relative
        if path.startswith(self.bucket + "/"):
            path = path[len(self.bucket):]
        elif path.startswith(self.bucket): # absolute root
             path = "/"

        ftype = FileType.DIRECTORY if info['type'] == 'directory' else FileType.FILE
        size = info.get('size', 0)
        
        mtime = 0.0
        if 'LastModified' in info:
            # might be datetime object or string? s3fs usually gives datetime
            lm = info['LastModified']
            if hasattr(lm, 'timestamp'):
                mtime = lm.timestamp()
        
        # ETag is often the MD5 for non-multipart files
        chksum = info.get('ETag', '').strip('"')

        return FileResource(
            path=path,
            name=path.split('/')[-1],
            type=ftype,
            size=size,
            mtime=mtime,
            chksum=chksum
        )

    def stat(self, path: str) -> FileResource:
        s3_path = self._get_s3_path(path)
        info = self.fs.info(s3_path)
        return self._to_resource(info)

    def exists(self, path: str) -> bool:
        return self.fs.exists(self._get_s3_path(path))

    def open(self, path: str, mode: str = "rb") -> IO:
        s3_path = self._get_s3_path(path)
        return self.fs.open(s3_path, mode)

    def mkdir(self, path: str, parents: bool = True) -> None:
        # S3 doesn't really have folders, but creating a 0-byte key ending in / is common
        # s3fs.makedirs does this.
        self.fs.makedirs(self._get_s3_path(path), exist_ok=True)

    def delete(self, path: str, recursive: bool = False) -> None:
        s3_path = self._get_s3_path(path)
        self.fs.rm(s3_path, recursive=recursive)

    def move(self, src_path: str, dst_path: str) -> None:
        self.fs.mv(self._get_s3_path(src_path), self._get_s3_path(dst_path))

    def copy(self, src_path: str, dst_path: str) -> None:
        self.fs.copy(self._get_s3_path(src_path), self._get_s3_path(dst_path))

    def set_mtime(self, path: str, timestamp: float) -> None:
        # S3 doesn't verify support arbitary mtime. 
        # Metadata update takes a copy.
        pass
