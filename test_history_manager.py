import unittest

from history_manager import HistoryManager


class AppliedPlan:
    applied_successfully = True
    sealed = True


class TestHistoryManager(unittest.TestCase):
    def test_plan_moves_only_after_explicit_success_commit(self):
        history = HistoryManager()
        plan = AppliedPlan()
        history.record_plan(plan)

        self.assertIs(history.peek_undo(), plan)
        self.assertFalse(history.can_redo())

        # A caller can attempt and fail an undo without mutating history.
        self.assertIs(history.peek_undo(), plan)
        self.assertFalse(history.can_redo())

        self.assertTrue(history.commit_undo(plan))
        self.assertFalse(history.can_undo())
        self.assertIs(history.peek_redo(), plan)

        self.assertTrue(history.commit_redo(plan))
        self.assertIs(history.peek_undo(), plan)
        self.assertFalse(history.can_redo())

    def test_wrong_entry_cannot_move_stack(self):
        history = HistoryManager()
        plan = AppliedPlan()
        history.record_plan(plan)

        self.assertFalse(history.commit_undo(object()))
        self.assertIs(history.peek_undo(), plan)

    def test_unapplied_plan_is_rejected(self):
        history = HistoryManager()
        with self.assertRaises(ValueError):
            history.record_plan(object())


if __name__ == "__main__":
    unittest.main()
