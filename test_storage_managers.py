import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import winreg

from favorites_manager import FavoritesManager
from preset_manager import PresetManager


class TestPresetManagerStorage(unittest.TestCase):
    def test_binary_preset_round_trip_and_utf8(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            presets_file = Path(temp_dir) / "nested" / "presets.json"
            manager = PresetManager(presets_file)
            manager.save_preset(
                "Binary caf\u00e9",
                {
                    "path": r"Software\RegistryManager",
                    "values": [
                        ("Payload", b"\x00\xff\x10", winreg.REG_BINARY),
                        ("Nested", [b"one", {"more": b"two"}], winreg.REG_BINARY),
                    ],
                },
            )

            raw_text = presets_file.read_text(encoding="utf-8")
            self.assertIn("Binary caf\u00e9", raw_text)
            self.assertNotIn("\\u00e9", raw_text)

            reloaded = PresetManager(presets_file).get_preset("Binary caf\u00e9")
            self.assertEqual(reloaded["values"][0][1], b"\x00\xff\x10")
            self.assertEqual(reloaded["values"][1][1], [b"one", {"more": b"two"}])

    def test_wrong_top_level_shape_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            presets_file = Path(temp_dir) / "presets.json"
            presets_file.write_text("[]", encoding="utf-8")

            manager = PresetManager(presets_file)

            self.assertIsInstance(manager.presets, dict)
            self.assertIn("Enable Dark Mode", manager.presets)

    def test_serialization_failure_preserves_file_and_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            presets_file = Path(temp_dir) / "presets.json"
            manager = PresetManager(presets_file)
            original_content = presets_file.read_bytes()
            original_presets = manager.presets.copy()

            with self.assertRaises(TypeError):
                manager.save_preset("Unsupported", {"value": object()})

            self.assertEqual(presets_file.read_bytes(), original_content)
            self.assertEqual(manager.presets, original_presets)
            self.assertEqual(list(presets_file.parent.glob("*.tmp")), [])

    def test_replace_failure_preserves_file_and_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            presets_file = Path(temp_dir) / "presets.json"
            manager = PresetManager(presets_file)
            original_content = presets_file.read_bytes()
            original_presets = manager.presets.copy()

            with mock.patch("preset_manager.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    manager.save_preset("Not committed", {"path": "Software", "values": []})

            self.assertEqual(presets_file.read_bytes(), original_content)
            self.assertEqual(manager.presets, original_presets)
            self.assertEqual(list(presets_file.parent.glob("*.tmp")), [])

    def test_existing_untagged_schema_remains_compatible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            presets_file = Path(temp_dir) / "presets.json"
            legacy = {
                "Legacy": {
                    "path": r"Software\Legacy",
                    "values": [["Enabled", 1, winreg.REG_DWORD]],
                }
            }
            presets_file.write_text(json.dumps(legacy), encoding="utf-8")

            manager = PresetManager(presets_file)

            self.assertEqual(manager.get_preset("Legacy"), legacy["Legacy"])


class TestFavoritesManagerStorage(unittest.TestCase):
    def test_wrong_top_level_shape_falls_back_to_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            favorites_file = Path(temp_dir) / "favorites.json"
            favorites_file.write_text("{}", encoding="utf-8")

            manager = FavoritesManager(favorites_file)

            self.assertEqual(manager.get_favorites(), [])

    def test_replace_failure_preserves_file_and_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            favorites_file = Path(temp_dir) / "favorites.json"
            manager = FavoritesManager(favorites_file)
            manager.add_favorite("HKEY_CURRENT_USER", r"Software\Existing")
            original_content = favorites_file.read_bytes()
            original_favorites = list(manager.favorites)

            with mock.patch("favorites_manager.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    manager.add_favorite("HKEY_CURRENT_USER", r"Software\New")

            self.assertEqual(favorites_file.read_bytes(), original_content)
            self.assertEqual(manager.favorites, original_favorites)
            self.assertEqual(list(favorites_file.parent.glob("*.tmp")), [])

    def test_serialization_failure_preserves_file_and_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            favorites_file = Path(temp_dir) / "favorites.json"
            manager = FavoritesManager(favorites_file)
            manager.add_favorite("HKEY_CURRENT_USER", r"Software\Existing")
            original_content = favorites_file.read_bytes()
            original_favorites = list(manager.favorites)

            with self.assertRaises(TypeError):
                manager.add_favorite(
                    "HKEY_CURRENT_USER",
                    r"Software\Unsupported",
                    label=object(),
                )

            self.assertEqual(favorites_file.read_bytes(), original_content)
            self.assertEqual(manager.favorites, original_favorites)
            self.assertEqual(list(favorites_file.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
