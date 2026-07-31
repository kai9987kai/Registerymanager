import unittest

from change_manager import ChangePlan
from history_manager import HistoryManager
from ui.main_window import RegistryApp


class FakeHandler:
    def __init__(self):
        self.values = {}
        self.last_error = None

    def read_value(self, hive, path, name):
        return self.values.get((hive, path, name))

    def write_value(self, hive, path, name, value, value_type):
        self.values[(hive, path, name)] = (value, value_type)
        return True

    def delete_value(self, hive, path, name):
        self.values.pop((hive, path, name), None)
        return True


class AppHarness:
    def __init__(self):
        self.registry_handler = FakeHandler()
        self.history_manager = HistoryManager()
        self.statuses = []
        self.undo_updates = 0

    def set_status(self, text, color="gray"):
        self.statuses.append((text, color))

    def update_undo_status(self):
        self.undo_updates += 1

    def _result_color(self, status):
        return RegistryApp._result_color(self, status)


class TestApplyUiBoundary(unittest.TestCase):
    def test_refresh_failure_does_not_masquerade_as_apply_failure(self):
        app = AppHarness()
        plan = ChangePlan(app.registry_handler, "UI boundary")
        plan.set_value(1, "Software", "Value", 2, 4)

        def fail_refresh():
            raise RuntimeError("destroyed widget")

        result = RegistryApp.apply_change_plan(
            app,
            plan,
            create_backup=False,
            on_success=fail_refresh,
        )

        self.assertTrue(result.success)
        self.assertIs(app.history_manager.peek_undo(), plan)
        self.assertIn("View refresh failed", app.statuses[-1][0])
        self.assertEqual(app.statuses[-1][1], "orange")


if __name__ == "__main__":
    unittest.main()
