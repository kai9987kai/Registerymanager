import tempfile
import unittest
from pathlib import Path

from app_paths import get_app_paths, migrate_legacy_data


class TestAppPaths(unittest.TestCase):
    def test_override_keeps_mutable_files_together(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = get_app_paths(temp_dir)

            self.assertEqual(paths["root"], Path(temp_dir).resolve())
            self.assertEqual(paths["presets"].parent, paths["root"])
            self.assertEqual(paths["favorites"].parent, paths["root"])
            self.assertTrue(paths["backups"].is_dir())

    def test_legacy_data_is_copied_without_removing_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            legacy = base / "legacy"
            legacy_backups = legacy / "backups"
            legacy_backups.mkdir(parents=True)
            (legacy / "presets.json").write_text('{"Custom": {}}', encoding="utf-8")
            (legacy / "favorites.json").write_text("[]", encoding="utf-8")
            (legacy_backups / "old.reg").write_text("Windows Registry Editor", encoding="utf-8")

            paths = get_app_paths(base / "new")
            report = migrate_legacy_data(paths, [legacy])

            self.assertEqual(Path(paths["presets"]).read_text(encoding="utf-8"), '{"Custom": {}}')
            self.assertEqual(Path(paths["favorites"]).read_text(encoding="utf-8"), "[]")
            self.assertTrue((Path(paths["backups"]) / "old.reg").is_file())
            self.assertTrue((legacy / "presets.json").is_file())
            self.assertEqual(len(report["copied"]), 3)
            self.assertEqual(report["errors"], [])

    def test_migration_never_overwrites_existing_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            legacy = base / "legacy"
            legacy.mkdir()
            (legacy / "presets.json").write_text("legacy", encoding="utf-8")
            paths = get_app_paths(base / "new")
            Path(paths["presets"]).write_text("current", encoding="utf-8")

            migrate_legacy_data(paths, [legacy])

            self.assertEqual(Path(paths["presets"]).read_text(encoding="utf-8"), "current")

    def test_colliding_backup_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            legacy_backups = base / "legacy" / "backups"
            legacy_backups.mkdir(parents=True)
            (legacy_backups / "same.reg").write_text("legacy", encoding="utf-8")
            paths = get_app_paths(base / "new")
            (Path(paths["backups"]) / "same.reg").write_text("current", encoding="utf-8")

            first = migrate_legacy_data(paths, [base / "legacy"])
            second = migrate_legacy_data(paths, [base / "legacy"])

            migrated = sorted(Path(paths["backups"]).glob("same_legacy_*.reg"))
            self.assertEqual([path.name for path in migrated], ["same_legacy_1.reg"])
            self.assertEqual(len(first["copied"]), 1)
            self.assertEqual(second["copied"], [])


if __name__ == "__main__":
    unittest.main()
