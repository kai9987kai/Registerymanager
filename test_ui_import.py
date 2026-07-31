import unittest

from ui.main_window import RegistryApp


class TestUiImport(unittest.TestCase):
    def test_registry_app_imports(self):
        self.assertTrue(issubclass(RegistryApp, object))


if __name__ == "__main__":
    unittest.main()
