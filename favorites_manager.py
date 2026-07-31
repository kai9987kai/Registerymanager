import base64
import json
import os
import tempfile


_BYTES_MARKER = "__registry_manager_bytes_v1_7a0c8f39_5ef4_4e50_9e62_8df2bfeb1702__"


def _encode_json_value(value):
    """Convert values unsupported by JSON into an unambiguous tagged form."""
    if isinstance(value, bytes):
        return {_BYTES_MARKER: base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {key: _encode_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_json_value(item) for item in value]
    return value


def _decode_json_value(value):
    """Restore recursively tagged values while leaving legacy JSON unchanged."""
    if isinstance(value, list):
        return [_decode_json_value(item) for item in value]
    if isinstance(value, dict):
        if set(value) == {_BYTES_MARKER} and isinstance(value[_BYTES_MARKER], str):
            return base64.b64decode(value[_BYTES_MARKER], validate=True)
        return {key: _decode_json_value(item) for key, item in value.items()}
    return value


def _atomic_write_json(path, data):
    """Serialize fully, then atomically replace *path* from the same directory."""
    encoded = _encode_json_value(data)
    serialized = json.dumps(encoded, indent=4, ensure_ascii=False) + "\n"

    target_path = os.path.abspath(os.fspath(path))
    parent_dir = os.path.dirname(target_path)
    os.makedirs(parent_dir, exist_ok=True)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=parent_dir,
            prefix=f".{os.path.basename(target_path)}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            temp_file.write(serialized)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, target_path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

class FavoritesManager:
    def __init__(self, favorites_file="favorites.json"):
        self.favorites_file = favorites_file
        self.favorites = self.load_favorites()

    def load_favorites(self):
        if not os.path.exists(self.favorites_file):
            return []
        try:
            with open(self.favorites_file, 'r', encoding='utf-8') as f:
                data = _decode_json_value(json.load(f))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return []

    def _save_to_file(self):
        _atomic_write_json(self.favorites_file, self.favorites)

    def add_favorite(self, hive_name, path, label=None):
        """Add a registry key path to favorites."""
        entry = {
            "hive": hive_name,
            "path": path,
            "label": label or path.split("\\")[-1] if path else hive_name
        }
        # Avoid duplicates
        for fav in self.favorites:
            if fav["hive"] == hive_name and fav["path"] == path:
                return False
        self.favorites.append(entry)
        try:
            self._save_to_file()
        except Exception:
            self.favorites.pop()
            raise
        return True

    def remove_favorite(self, index):
        """Remove a favorite by index."""
        if 0 <= index < len(self.favorites):
            entry = self.favorites.pop(index)
            try:
                self._save_to_file()
            except Exception:
                self.favorites.insert(index, entry)
                raise
            return True
        return False

    def get_favorites(self):
        return self.favorites
