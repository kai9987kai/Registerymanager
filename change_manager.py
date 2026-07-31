"""Previewable, conflict-aware registry change plans with compensation."""

from __future__ import annotations

import copy
import winreg
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DuplicateOperationError(ValueError):
    """Raised when a plan targets the same registry value more than once."""


class SnapshotReadError(RuntimeError):
    """Raised when a plan cannot reliably capture registry state."""


class PlanSealedError(RuntimeError):
    """Raised when code tries to mutate a plan after review/execution."""


class ChangeClassification(str, Enum):
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"
    NO_CHANGE = "no_change"


class ApplyStatus(str, Enum):
    SUCCESS = "success"
    NO_CHANGES = "no_changes"
    CONFLICT = "conflict"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"


@dataclass(frozen=True)
class ValueSnapshot:
    """Exact existence, data, and type state for one registry value."""

    exists: bool
    value: Any = None
    value_type: int | None = None

    @classmethod
    def missing(cls):
        return cls(False, None, None)

    @classmethod
    def existing(cls, value, value_type):
        # Registry values are normally immutable scalars/bytes, except
        # REG_MULTI_SZ. Freeze sequences so caller-owned lists cannot mutate
        # history or alter optimistic-concurrency checks after planning.
        if isinstance(value, (list, tuple)):
            value = tuple(copy.deepcopy(item) for item in value)
        elif isinstance(value, (bytearray, memoryview)):
            value = bytes(value)
        else:
            value = copy.deepcopy(value)
        return cls(True, value, value_type)


@dataclass(frozen=True)
class PlannedChange:
    hive: Any
    hive_name: str
    path: str
    name: str
    before: ValueSnapshot
    after: ValueSnapshot

    @property
    def classification(self):
        if self.before == self.after:
            return ChangeClassification.NO_CHANGE
        if not self.before.exists and self.after.exists:
            return ChangeClassification.ADD
        if self.before.exists and not self.after.exists:
            return ChangeClassification.DELETE
        return ChangeClassification.MODIFY

    @property
    def location(self):
        display_name = self.name or "(Default)"
        key_path = f"{self.hive_name}\\{self.path}" if self.path else self.hive_name
        return f"{key_path} • {display_name}"


@dataclass(frozen=True)
class PlanPreview:
    label: str
    changes: tuple[PlannedChange, ...]

    @property
    def effective_changes(self):
        return tuple(
            change for change in self.changes
            if change.classification is not ChangeClassification.NO_CHANGE
        )

    @property
    def has_changes(self):
        return bool(self.effective_changes)

    @property
    def counts(self):
        return {
            classification: sum(
                change.classification is classification for change in self.changes
            )
            for classification in ChangeClassification
        }


@dataclass(frozen=True)
class ChangeError:
    code: str
    message: str
    change: PlannedChange | None = None


@dataclass(frozen=True)
class ApplyResult:
    status: ApplyStatus
    plan: "ChangePlan"
    applied_count: int = 0
    skipped_count: int = 0
    rolled_back_count: int = 0
    error: ChangeError | None = None
    rollback_errors: tuple[ChangeError, ...] = ()

    @property
    def success(self):
        return self.status in (ApplyStatus.SUCCESS, ApplyStatus.NO_CHANGES)

    @property
    def message(self):
        if self.status is ApplyStatus.SUCCESS:
            return f"Applied {self.applied_count} change(s)."
        if self.status is ApplyStatus.NO_CHANGES:
            return "No registry changes were needed."
        if self.status is ApplyStatus.CONFLICT:
            return self.error.message if self.error else "Registry state changed after preview."
        if self.status is ApplyStatus.ROLLED_BACK:
            detail = self.error.message if self.error else "A registry operation failed."
            return f"{detail} Earlier changes were restored."
        if self.status is ApplyStatus.ROLLBACK_FAILED:
            return "Apply failed and one or more changes could not be restored. Use the recovery backup."
        return self.error.message if self.error else "The registry change plan failed."


class ChangePlan:
    """A guarded batch of registry value mutations.

    This is optimistic application-level compensation, not a native Windows
    Registry transaction. State is checked before every write and every write
    is read back, but another process can still mutate a key concurrently.
    """

    def __init__(self, handler, label="Registry changes"):
        self.handler = handler
        self.label = label
        self.created_at = datetime.now(timezone.utc).isoformat()
        self._changes = []
        self._targets = set()
        self._sealed = False
        self._executed = False
        self._last_result = None

    @property
    def changes(self):
        return tuple(self._changes)

    @property
    def effective_changes(self):
        return self.preview().effective_changes

    @property
    def sealed(self):
        return self._sealed

    @property
    def executed(self):
        return self._executed

    @property
    def applied_successfully(self):
        return bool(self._last_result and self._last_result.success)

    def seal(self):
        """Prevent further operations from being appended to this plan."""
        self._sealed = True
        return self

    def _target_key(self, hive, path, name):
        return (hive, path.casefold(), name.casefold())

    def _read_snapshot(self, hive, path, name):
        try:
            current = self.handler.read_value(hive, path, name)
        except Exception as exc:
            raise SnapshotReadError(
                f"Could not read {path or '<root>'}\\{name or '(Default)'}: {exc}"
            ) from exc
        if current is None:
            return ValueSnapshot.missing()
        value, value_type = current
        return ValueSnapshot.existing(value, value_type)

    def _append(self, hive, hive_name, path, name, before, after):
        if self._sealed:
            raise PlanSealedError("This change plan has already been reviewed or executed.")
        target = self._target_key(hive, path, name)
        if target in self._targets:
            raise DuplicateOperationError(
                f"The plan targets {path or '<root>'}\\{name or '(Default)'} more than once."
            )
        self._targets.add(target)
        change = PlannedChange(hive, hive_name, path, name, before, after)
        self._changes.append(change)
        return change

    def set_value(self, hive, path, name, value, value_type, hive_name="HKEY_CURRENT_USER"):
        before = self._read_snapshot(hive, path, name)
        after = ValueSnapshot.existing(value, value_type)
        return self._append(hive, hive_name, path, name, before, after)

    def delete_value(self, hive, path, name, hive_name="HKEY_CURRENT_USER"):
        before = self._read_snapshot(hive, path, name)
        return self._append(
            hive, hive_name, path, name, before, ValueSnapshot.missing()
        )

    def preview(self):
        return PlanPreview(self.label, tuple(self._changes))

    def _read_for_apply(self, change):
        try:
            return self._read_snapshot(change.hive, change.path, change.name), None
        except SnapshotReadError as exc:
            return None, ChangeError("read_failed", str(exc), change)

    def _write_snapshot(self, change, snapshot):
        if snapshot.exists:
            value = snapshot.value
            if snapshot.value_type == winreg.REG_MULTI_SZ and isinstance(value, tuple):
                value = list(value)
            else:
                value = copy.deepcopy(value)
            success = self.handler.write_value(
                change.hive,
                change.path,
                change.name,
                value,
                snapshot.value_type,
            )
            operation = "write"
        else:
            success = self.handler.delete_value(change.hive, change.path, change.name)
            operation = "delete"

        if success:
            return None
        detail = getattr(self.handler, "last_error", None) or "backend returned failure"
        return ChangeError(
            f"{operation}_failed",
            f"Could not {operation} {change.location}: {detail}",
            change,
        )

    def _verify_snapshot(self, change, expected, code="verification_failed"):
        current, error = self._read_for_apply(change)
        if error:
            return error
        if current != expected:
            return ChangeError(
                code,
                f"Verification failed for {change.location}; registry data did not match the requested state.",
                change,
            )
        return None

    def _rollback(self, candidates):
        rollback_errors = []
        rolled_back_count = 0
        for change in reversed(candidates):
            current, read_error = self._read_for_apply(change)
            if read_error:
                rollback_errors.append(read_error)
                continue

            if current == change.before:
                continue
            if current != change.after:
                rollback_errors.append(
                    ChangeError(
                        "rollback_conflict",
                        f"Did not overwrite a concurrent change at {change.location} during recovery.",
                        change,
                    )
                )
                continue

            write_error = self._write_snapshot(change, change.before)
            if write_error:
                rollback_errors.append(write_error)
                continue
            verify_error = self._verify_snapshot(
                change, change.before, code="rollback_verification_failed"
            )
            if verify_error:
                rollback_errors.append(verify_error)
                continue
            rolled_back_count += 1
        return tuple(rollback_errors), rolled_back_count

    def _failed_result(self, error, candidates, applied_count):
        rollback_errors, rolled_back_count = self._rollback(candidates)
        if rollback_errors:
            status = ApplyStatus.ROLLBACK_FAILED
        elif rolled_back_count:
            status = ApplyStatus.ROLLED_BACK
        elif error.code == "conflict":
            status = ApplyStatus.CONFLICT
        else:
            status = ApplyStatus.FAILED
        return ApplyResult(
            status=status,
            plan=self,
            applied_count=applied_count,
            skipped_count=len(self.changes) - len(self.effective_changes),
            rolled_back_count=rolled_back_count,
            error=error,
            rollback_errors=rollback_errors,
        )

    def apply(self):
        if self._executed:
            error = ChangeError(
                "plan_already_executed",
                "This change plan has already been executed. Refresh and review a new plan.",
            )
            return ApplyResult(ApplyStatus.FAILED, self, error=error)

        self.seal()
        self._executed = True
        effective = self.effective_changes
        skipped = len(self.changes) - len(effective)
        if not effective:
            result = ApplyResult(ApplyStatus.NO_CHANGES, self, skipped_count=skipped)
            self._last_result = result
            return result

        candidates = []
        applied_count = 0
        for change in effective:
            current, read_error = self._read_for_apply(change)
            if read_error:
                result = self._failed_result(read_error, candidates, applied_count)
                self._last_result = result
                return result
            if current != change.before:
                conflict = ChangeError(
                    "conflict",
                    f"Registry state changed after preview at {change.location}. Refresh and review again.",
                    change,
                )
                result = self._failed_result(conflict, candidates, applied_count)
                self._last_result = result
                return result

            # Include the attempted operation in recovery. A backend can fail
            # after changing state, so a false return alone is not conclusive.
            candidates.append(change)
            write_error = self._write_snapshot(change, change.after)
            if write_error:
                result = self._failed_result(write_error, candidates, applied_count)
                self._last_result = result
                return result
            verify_error = self._verify_snapshot(change, change.after)
            if verify_error:
                result = self._failed_result(verify_error, candidates, applied_count)
                self._last_result = result
                return result
            applied_count += 1

        result = ApplyResult(
            ApplyStatus.SUCCESS,
            self,
            applied_count=applied_count,
            skipped_count=skipped,
        )
        self._last_result = result
        return result

    @classmethod
    def _from_changes(cls, handler, label, changes):
        plan = cls(handler, label)
        for change in changes:
            plan._append(
                change.hive,
                change.hive_name,
                change.path,
                change.name,
                change.before,
                change.after,
            )
        return plan

    def create_inverse_plan(self, label=None):
        if not self.applied_successfully:
            raise RuntimeError("Only a successfully applied plan can be undone.")
        changes = [
            PlannedChange(
                change.hive,
                change.hive_name,
                change.path,
                change.name,
                change.after,
                change.before,
            )
            for change in reversed(self.effective_changes)
        ]
        return self._from_changes(
            self.handler, label or f"Undo: {self.label}", changes
        )

    def create_forward_plan(self, label=None):
        if not self.applied_successfully:
            raise RuntimeError("Only a successfully applied plan can be redone.")
        changes = [
            PlannedChange(
                change.hive,
                change.hive_name,
                change.path,
                change.name,
                change.before,
                change.after,
            )
            for change in self.effective_changes
        ]
        return self._from_changes(
            self.handler, label or f"Redo: {self.label}", changes
        )
