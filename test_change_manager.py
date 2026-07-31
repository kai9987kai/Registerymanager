import copy
import unittest

from change_manager import (
    ApplyStatus,
    ChangeClassification,
    ChangePlan,
    DuplicateOperationError,
    PlanSealedError,
)


HIVE = 0x80000001


class FakeRegistryHandler:
    def __init__(self, initial=None, fail_calls=(), corrupt_calls=()):
        self.values = copy.deepcopy(initial or {})
        self.fail_calls = set(fail_calls)
        self.corrupt_calls = set(corrupt_calls)
        self.operation_count = 0
        self.last_error = None

    def _key(self, hive, path, name):
        return hive, path.casefold(), name.casefold()

    def read_value(self, hive, path, name):
        value = self.values.get(self._key(hive, path, name))
        return copy.deepcopy(value)

    def _begin_operation(self):
        self.operation_count += 1
        if self.operation_count in self.fail_calls:
            self.last_error = f"injected failure {self.operation_count}"
            return False
        self.last_error = None
        return True

    def write_value(self, hive, path, name, value, value_type):
        if not self._begin_operation():
            return False
        stored = (copy.deepcopy(value), value_type)
        if self.operation_count in self.corrupt_calls:
            stored = ("corrupted", value_type)
        self.values[self._key(hive, path, name)] = stored
        return True

    def delete_value(self, hive, path, name):
        if not self._begin_operation():
            return False
        self.values.pop(self._key(hive, path, name), None)
        return True


class TestChangePlan(unittest.TestCase):
    def key(self, path, name):
        return HIVE, path.casefold(), name.casefold()

    def test_preview_classifies_changes_without_writing(self):
        handler = FakeRegistryHandler({
            self.key("Software\\Demo", "Same"): (1, 4),
            self.key("Software\\Demo", "Modify"): (1, 4),
            self.key("Software\\Demo", "Delete"): (b"old", 3),
        })
        plan = ChangePlan(handler, "Preview")
        plan.set_value(HIVE, "Software\\Demo", "Add", "new", 1)
        plan.set_value(HIVE, "Software\\Demo", "Same", 1, 4)
        plan.set_value(HIVE, "Software\\Demo", "Modify", 2, 4)
        plan.delete_value(HIVE, "Software\\Demo", "Delete")

        self.assertEqual(
            [change.classification for change in plan.preview().changes],
            [
                ChangeClassification.ADD,
                ChangeClassification.NO_CHANGE,
                ChangeClassification.MODIFY,
                ChangeClassification.DELETE,
            ],
        )
        self.assertEqual(handler.operation_count, 0)

    def test_type_only_change_is_a_modification(self):
        handler = FakeRegistryHandler({self.key("Software", "Value"): (1, 4)})
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "Value", 1, 11)
        self.assertIs(
            plan.preview().changes[0].classification,
            ChangeClassification.MODIFY,
        )

    def test_duplicate_targets_are_case_insensitive(self):
        handler = FakeRegistryHandler()
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software\\Demo", "Value", 1, 4)
        with self.assertRaises(DuplicateOperationError):
            plan.set_value(HIVE, "software\\demo", "VALUE", 2, 4)

    def test_stale_preview_is_rejected_before_write(self):
        handler = FakeRegistryHandler({self.key("Software", "Value"): (1, 4)})
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "Value", 2, 4)
        handler.values[self.key("Software", "Value")] = (99, 4)

        result = plan.apply()

        self.assertEqual(result.status, ApplyStatus.CONFLICT)
        self.assertFalse(result.success)
        self.assertEqual(handler.operation_count, 0)
        self.assertEqual(handler.values[self.key("Software", "Value")], (99, 4))

    def test_second_failure_restores_first_change_exactly(self):
        initial = {self.key("Software", "Existing"): (b"old", 3)}
        handler = FakeRegistryHandler(initial, fail_calls={2})
        plan = ChangePlan(handler, "Batch")
        plan.set_value(HIVE, "Software", "Created", "new", 1)
        plan.set_value(HIVE, "Software", "Existing", b"new", 3)

        result = plan.apply()

        self.assertEqual(result.status, ApplyStatus.ROLLED_BACK)
        self.assertEqual(handler.values, initial)
        self.assertEqual(result.rollback_errors, ())

    def test_first_unchanged_write_failure_is_not_mislabeled_as_rollback(self):
        initial = {self.key("Software", "Value"): (1, 4)}
        handler = FakeRegistryHandler(initial, fail_calls={1})
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "Value", 2, 4)

        result = plan.apply()

        self.assertEqual(result.status, ApplyStatus.FAILED)
        self.assertEqual(result.rolled_back_count, 0)
        self.assertEqual(handler.values, initial)

    def test_verification_failure_is_compensated(self):
        initial = {self.key("Software", "Value"): ("old", 1)}
        handler = FakeRegistryHandler(initial, corrupt_calls={1})
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "Value", "new", 1)

        result = plan.apply()

        self.assertEqual(result.status, ApplyStatus.ROLLBACK_FAILED)
        self.assertTrue(result.rollback_errors)
        # Recovery refuses to overwrite unexpected state after verification
        # detects corruption; this must be surfaced for backup-based recovery.
        self.assertEqual(handler.values[self.key("Software", "Value")], ("corrupted", 1))

    def test_rollback_failure_is_explicit(self):
        initial = {self.key("Software", "First"): (1, 4)}
        handler = FakeRegistryHandler(initial, fail_calls={2, 3})
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "First", 2, 4)
        plan.set_value(HIVE, "Software", "Second", 3, 4)

        result = plan.apply()

        self.assertEqual(result.status, ApplyStatus.ROLLBACK_FAILED)
        self.assertTrue(result.rollback_errors)
        self.assertEqual(handler.values[self.key("Software", "First")], (2, 4))

    def test_successful_plan_undo_and_redo_preserve_existence_data_and_type(self):
        initial = {self.key("Software", "Existing"): (b"old", 3)}
        handler = FakeRegistryHandler(initial)
        plan = ChangePlan(handler, "Mixed batch")
        plan.set_value(HIVE, "Software", "Existing", b"new", 3)
        plan.set_value(HIVE, "Software", "Created", ["a", "b"], 7)

        self.assertTrue(plan.apply().success)
        applied_state = copy.deepcopy(handler.values)

        inverse = plan.create_inverse_plan()
        self.assertTrue(inverse.apply().success)
        self.assertEqual(handler.values, initial)

        forward = plan.create_forward_plan()
        self.assertTrue(forward.apply().success)
        self.assertEqual(handler.values, applied_state)

    def test_applied_plan_is_sealed_against_later_history_mutation(self):
        handler = FakeRegistryHandler()
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "First", 1, 4)
        self.assertTrue(plan.apply().success)

        with self.assertRaises(PlanSealedError):
            plan.set_value(HIVE, "Software", "Unrelated", 2, 4)
        self.assertEqual(len(plan.changes), 1)

    def test_mutable_multi_string_input_is_frozen_at_plan_time(self):
        handler = FakeRegistryHandler()
        items = ["one", "two"]
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "Multi", items, 7)
        items.append("mutated later")

        self.assertEqual(plan.changes[0].after.value, ("one", "two"))
        self.assertTrue(plan.apply().success)
        self.assertEqual(
            handler.values[self.key("Software", "Multi")],
            (["one", "two"], 7),
        )

    def test_plan_can_only_execute_once(self):
        handler = FakeRegistryHandler()
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "Value", 1, 4)

        self.assertTrue(plan.apply().success)
        retry = plan.apply()
        self.assertEqual(retry.status, ApplyStatus.FAILED)
        self.assertEqual(handler.operation_count, 1)

    def test_no_op_plan_performs_no_backend_operations(self):
        handler = FakeRegistryHandler({self.key("Software", "Value"): (1, 4)})
        plan = ChangePlan(handler)
        plan.set_value(HIVE, "Software", "Value", 1, 4)

        result = plan.apply()

        self.assertEqual(result.status, ApplyStatus.NO_CHANGES)
        self.assertTrue(result.success)
        self.assertEqual(handler.operation_count, 0)


if __name__ == "__main__":
    unittest.main()
