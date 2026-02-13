import unittest
import winreg
import os
from registry_handler import RegistryHandler

class TestRegistryHandler(unittest.TestCase):
    def setUp(self):
        self.handler = RegistryHandler()
        self.test_key_path = "Software\\TestRegistryManager"
        self.handler.create_key(winreg.HKEY_CURRENT_USER, self.test_key_path)

    def tearDown(self):
        # Clean up
        try:
            val_path = self.test_key_path
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, val_path, 0, winreg.KEY_WRITE)
            winreg.DeleteKey(key, "")
            winreg.CloseKey(key)
        except Exception:
            pass

    def test_write_read_value(self):
        name = "TestValue"
        value = "Hello World"
        self.handler.write_value(winreg.HKEY_CURRENT_USER, self.test_key_path, name, value, winreg.REG_SZ)
        
        values = self.handler.read_key(winreg.HKEY_CURRENT_USER, self.test_key_path)
        found = False
        for n, v, t in values:
            if n == name and v == value:
                found = True
                break
        self.assertTrue(found)

    def test_search(self):
        name = "SearchMe"
        value = "FindThis"
        self.handler.write_value(winreg.HKEY_CURRENT_USER, self.test_key_path, name, value, winreg.REG_SZ)
        
        results = self.handler.search_registry(winreg.HKEY_CURRENT_USER, self.test_key_path, "FindThis")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['name'], name)
        self.assertEqual(results[0]['data'], value)

    def test_backup(self):
        # This might fail if reg.exe is not in path or permissions issues, but good to try
        path = f"HKEY_CURRENT_USER\\{self.test_key_path}"
        backup_file = self.handler.backup_key(path)
        self.assertIsNotNone(backup_file)
        self.assertTrue(os.path.exists(backup_file))
        # cleanup
        if backup_file and os.path.exists(backup_file):
            os.remove(backup_file)

if __name__ == '__main__':
    unittest.main()
