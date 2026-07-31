import unittest
import winreg
import os
import uuid
from registry_handler import RegistryHandler
from change_manager import ChangePlan

class TestRegistryHandler(unittest.TestCase):
    def setUp(self):
        self.handler = RegistryHandler()
        self.test_key_path = f"Software\\RegistryManagerTests\\{uuid.uuid4().hex}"
        self.assertTrue(self.handler.create_key(winreg.HKEY_CURRENT_USER, self.test_key_path))

    def tearDown(self):
        # Clean up
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self.test_key_path)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, "Software\\RegistryManagerTests")
        except FileNotFoundError:
            return

    def test_write_read_value(self):
        name = "TestValue"
        value = "Hello World"
        self.assertTrue(self.handler.write_value(winreg.HKEY_CURRENT_USER, self.test_key_path, name, value, winreg.REG_SZ))
        
        values = self.handler.read_key(winreg.HKEY_CURRENT_USER, self.test_key_path)
        found = False
        for n, v, t in values:
            if n == name and v == value:
                found = True
                break
        self.assertTrue(found)
        self.assertEqual(
            self.handler.read_value(winreg.HKEY_CURRENT_USER, self.test_key_path, name),
            (value, winreg.REG_SZ),
        )

    def test_search(self):
        name = "SearchMe"
        value = "FindThis"
        self.assertTrue(self.handler.write_value(winreg.HKEY_CURRENT_USER, self.test_key_path, name, value, winreg.REG_SZ))
        
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

    def test_backup_names_are_unique(self):
        path = f"HKEY_CURRENT_USER\\{self.test_key_path}"
        first = self.handler.backup_key(path)
        second = self.handler.backup_key(path)
        try:
            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            self.assertNotEqual(first, second)
        finally:
            for backup_file in (first, second):
                if backup_file and os.path.exists(backup_file):
                    os.remove(backup_file)

    def test_guarded_change_plan_apply_and_undo(self):
        plan = ChangePlan(self.handler, "Windows integration")
        plan.set_value(
            winreg.HKEY_CURRENT_USER,
            self.test_key_path,
            "GuardedValue",
            42,
            winreg.REG_DWORD,
        )

        self.assertTrue(plan.apply().success)
        self.assertEqual(
            self.handler.read_value(
                winreg.HKEY_CURRENT_USER, self.test_key_path, "GuardedValue"
            ),
            (42, winreg.REG_DWORD),
        )
        self.assertTrue(plan.create_inverse_plan().apply().success)
        self.assertIsNone(
            self.handler.read_value(
                winreg.HKEY_CURRENT_USER, self.test_key_path, "GuardedValue"
            )
        )

if __name__ == '__main__':
    unittest.main()
