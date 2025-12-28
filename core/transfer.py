import logging
import concurrent.futures
import zstandard as zstd
import io
from typing import Optional, Callable
from providers.interface import IFileProvider, FileResource

logger = logging.getLogger("transfer_manager")

class TransferManager:
    def __init__(self, max_workers: int = 5):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.compressor = zstd.ZstdCompressor(level=3)
        self.decompressor = zstd.ZstdDecompressor()
        self._active_futures = []

    def submit_copy(self, src_provider: IFileProvider, dst_provider: IFileProvider, 
                   src_file: FileResource, use_compression: bool = False) -> concurrent.futures.Future:
        """Submit a file copy task to the thread pool."""
        future = self.executor.submit(
            self._copy_worker, src_provider, dst_provider, src_file, use_compression
        )
        self._active_futures.append(future)
        # Cleanup finished futures? In a real app we'd track status better
        return future

    def _copy_worker(self, src_provider: IFileProvider, dst_provider: IFileProvider, 
                    src_file: FileResource, compress: bool):
        try:
            logger.debug(f"Starting transfer: {src_file.path}")
            
            # Streaming Copy Logic
            # Note: This relies on providers supporting 'rb' and 'wb' modes correctly.
            # LocalProvider supports 'rb'/'wb'. 
            # Dropbox/Google providers need 'wb' implementations (currently stubs or partial).
            
            with src_provider.open(src_file.path, "rb") as source_stream:
                if compress:
                    # Compressed Transfer Pipeline: Source -> Zstd -> Dest
                    # NOTE: This assumes destination stores the .zst file or transparently handles it.
                    # For "Replication", we usually want exact copy.
                    # Compression is useful if we are "Backing up" to a .sz file.
                    # Here we implement straight copy for "Mirroring", optionally internal compression 
                    # if the destination file name indicates it (e.g. .sz appended).
                    
                    dst_path = src_file.path
                    if not dst_path.endswith('.zst'):
                        dst_path += '.zst'

                    with dst_provider.open(dst_path, "wb") as dest_stream:
                        with self.compressor.stream_writer(dest_stream) as compressor_stream:
                            import shutil
                            shutil.copyfileobj(source_stream, compressor_stream)
                else:
                    # Standard Raw Copy
                    with dst_provider.open(src_file.path, "wb") as dest_stream:
                        import shutil
                        shutil.copyfileobj(source_stream, dest_stream)
            
            # Post-copy metadata update?
            # dst_provider.set_mtime(src_file.path, src_file.mtime)
            
            logger.debug(f"Finished transfer: {src_file.path}")
            return True
            
        except Exception as e:
            logger.error(f"Transfer failed for {src_file.path}: {e}")
            raise e

    def shutdown(self):
        self.executor.shutdown(wait=True)

    def wait_all(self):
        concurrent.futures.wait(self._active_futures)
        self._active_futures = []
