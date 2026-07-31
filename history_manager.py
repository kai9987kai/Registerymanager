from datetime import datetime
from collections import deque

class HistoryManager:
    """
    In-memory history of verified registry change plans.

    Stack entries are only moved after the caller confirms that undo or redo
    completed successfully.  This keeps a transient registry error from
    silently losing the user's recovery action.
    """
    def __init__(self, max_size=100):
        self.undo_stack = deque(maxlen=max_size)
        self.redo_stack = deque(maxlen=max_size)

    def record(self, action, hive, path, name, old_value=None, old_type=None, new_value=None, new_type=None):
        """Record a legacy single-value action for backwards compatibility."""
        entry = {
            "action": action,       # "write", "delete", "create_key"
            "hive": hive,
            "path": path,
            "name": name,
            "old_value": old_value,
            "old_type": old_type,
            "new_value": new_value,
            "new_type": new_type,
            "timestamp": datetime.now().isoformat()
        }
        self.undo_stack.append(entry)
        self.redo_stack.clear()  # Clear redo on new action

    def record_plan(self, plan):
        """Record a successfully applied ``ChangePlan`` as one history item."""
        if not getattr(plan, "applied_successfully", False):
            raise ValueError("Only a successfully applied change plan can enter history.")
        if not getattr(plan, "sealed", False):
            raise ValueError("History plans must be immutable.")
        self.undo_stack.append(plan)
        self.redo_stack.clear()

    def can_undo(self):
        return len(self.undo_stack) > 0

    def can_redo(self):
        return len(self.redo_stack) > 0

    def peek_undo(self):
        """Return the next undo item without changing either stack."""
        return self.undo_stack[-1] if self.undo_stack else None

    def peek_redo(self):
        """Return the next redo item without changing either stack."""
        return self.redo_stack[-1] if self.redo_stack else None

    def commit_undo(self, entry):
        """Move ``entry`` to redo after a verified undo."""
        if not self.undo_stack or self.undo_stack[-1] is not entry:
            return False
        self.redo_stack.append(self.undo_stack.pop())
        return True

    def commit_redo(self, entry):
        """Move ``entry`` back to undo after a verified redo."""
        if not self.redo_stack or self.redo_stack[-1] is not entry:
            return False
        self.undo_stack.append(self.redo_stack.pop())
        return True

    def pop_undo(self):
        """Legacy eager stack movement; prefer ``peek_undo``/``commit_undo``."""
        if self.undo_stack:
            entry = self.undo_stack.pop()
            self.redo_stack.append(entry)
            return entry
        return None

    def pop_redo(self):
        """Legacy eager stack movement; prefer ``peek_redo``/``commit_redo``."""
        if self.redo_stack:
            entry = self.redo_stack.pop()
            self.undo_stack.append(entry)
            return entry
        return None

    def get_history(self):
        """Return full history list (most recent first)."""
        return list(reversed(self.undo_stack))
