from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass
from typing import Iterator, IO, Any, Optional, List, Dict

class FileType(Enum):
    FILE = auto()
    DIRECTORY = auto()
    SYMLINK = auto()

@dataclass
class FileResource:
    path: str
    name: str
    type: FileType
    size: int
    mtime: float
    chksum: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

class IFileProvider(ABC):
    """
    Abstract Base Class for File Providers.
    Wraps standard IO operations to allow provider-agnostic access.
    """

    @abstractmethod
    def list_dir(self, path: str, recursive: bool = False) -> Iterator[FileResource]:
        """List contents of a directory."""
        pass

    @abstractmethod
    def open(self, path: str, mode: str = "rb") -> IO:
        """Open a file in specified mode."""
        pass

    @abstractmethod
    def stat(self, path: str) -> FileResource:
        """Get file metadata."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists."""
        pass

    @abstractmethod
    def mkdir(self, path: str, parents: bool = True) -> None:
        """Create directory."""
        pass

    @abstractmethod
    def delete(self, path: str, recursive: bool = False) -> None:
        """Delete file or directory."""
        pass
    
    @abstractmethod
    def move(self, src_path: str, dst_path: str) -> None:
        """Move/Rename a file."""
        pass

    @abstractmethod
    def copy(self, src_path: str, dst_path: str) -> None:
        """Copy a file (intra-provider)."""
        pass
        
    @abstractmethod
    def set_mtime(self, path: str, timestamp: float) -> None:
        """Set modification time of a file."""
        pass
