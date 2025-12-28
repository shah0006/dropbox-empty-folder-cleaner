import unittest
import tempfile
import os
import shutil
from providers.local_provider import LocalProvider
from providers.interface import FileType

class TestVFSContract(unittest.TestCase):
    def setUp(self):
        self.test_dir_obj = tempfile.TemporaryDirectory()
        self.test_dir = self.test_dir_obj.name
        self.provider = LocalProvider(root_path=self.test_dir)

    def tearDown(self):
        self.test_dir_obj.cleanup()

    def test_list_dir(self):
        """Verify list_dir behaves as expected."""
        # Create some files
        os.makedirs(os.path.join(self.test_dir, "foo/bar"), exist_ok=True)
        with open(os.path.join(self.test_dir, "test.txt"), "w") as f:
            f.write("hello")
            
        items = list(self.provider.list_dir("/", recursive=True))
        
        # Expect test.txt and foo (directory) or foo/bar depending on impl. 
        # LocalProvider usually returns files and folders.
        # Let's check names.
        paths = [item.path for item in items]
        self.assertIn("/test.txt", paths)
        # Note: Implementation detail of local_provider, does it return directories?
        # Usually list_dir returns FileResources.
        
        # Let's verify properties of test.txt
        f_res = next(i for i in items if i.path == "/test.txt")
        self.assertEqual(f_res.size, 5)
        self.assertEqual(f_res.type, FileType.FILE)

    def test_open_read_write(self):
        """Verify open (read/write) works."""
        # Write
        fname = "/write_test.txt"
        with self.provider.open(fname, "wb") as f:
            f.write(b"content")
            
        # Verify on disk
        local_path = os.path.join(self.test_dir, "write_test.txt")
        self.assertTrue(os.path.exists(local_path))
        with open(local_path, "rb") as f:
            self.assertEqual(f.read(), b"content")
            
        # Read via provider
        with self.provider.open(fname, "rb") as f:
            data = f.read()
            self.assertEqual(data, b"content")

    def test_delete(self):
        """Verify delete works."""
        fname = "/del_test.txt"
        local_path = os.path.join(self.test_dir, "del_test.txt")
        with open(local_path, "w") as f:
            f.write("bye")
            
        self.provider.delete(fname)
        self.assertFalse(os.path.exists(local_path))

if __name__ == '__main__':
    unittest.main()
