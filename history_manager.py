from datetime import datetime
from collections import deque

class HistoryManager:
    """
    In-memory history of registry changes for undo/redo support.
    Each entry records: action type, path, value name, old value, new value.
    """
    def __init__(self, max_size=100):
        self.undo_stack = deque(maxlen=max_size)
        self.redo_stack = deque(maxlen=max_size)

    def record(self, action, hive, path, name, old_value=None, old_type=None, new_value=None, new_type=None):
        """Record an action for undo support."""
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

    def can_undo(self):
        return len(self.undo_stack) > 0

    def can_redo(self):
        return len(self.redo_stack) > 0

    def pop_undo(self):
        """Pop the last action for undoing."""
        if self.undo_stack:
            entry = self.undo_stack.pop()
            self.redo_stack.append(entry)
            return entry
        return None

    def pop_redo(self):
        """Pop the last undone action for redoing."""
        if self.redo_stack:
            entry = self.redo_stack.pop()
            self.undo_stack.append(entry)
            return entry
        return None

    def get_history(self):
        """Return full history list (most recent first)."""
        return list(reversed(self.undo_stack))
