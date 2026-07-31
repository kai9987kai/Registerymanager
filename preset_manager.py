import base64
import json
import os
import tempfile
import winreg


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

class PresetManager:
    def __init__(self, presets_file="presets.json"):
        self.presets_file = presets_file
        self.presets = self.load_presets()
        self.ensure_defaults()

    def load_presets(self):
        if not os.path.exists(self.presets_file):
            return {}
        try:
            with open(self.presets_file, 'r', encoding='utf-8') as f:
                data = _decode_json_value(json.load(f))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return {}

    def ensure_defaults(self):
        defaults = {
            "Enable Dark Mode": {
                "path": r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                "values": [
                    ("AppsUseLightTheme", 0, winreg.REG_DWORD),
                    ("SystemUsesLightTheme", 0, winreg.REG_DWORD)
                ]
            },
            "Enable Light Mode": {
                "path": r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                "values": [
                    ("AppsUseLightTheme", 1, winreg.REG_DWORD),
                    ("SystemUsesLightTheme", 1, winreg.REG_DWORD)
                ]
            },
            "Show File Extensions": {
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "values": [
                    ("HideFileExt", 0, winreg.REG_DWORD)
                ]
            },
            "Hide File Extensions": {
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "values": [
                    ("HideFileExt", 1, winreg.REG_DWORD)
                ]
            },
            "Show Hidden Files": {
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "values": [
                    ("Hidden", 1, winreg.REG_DWORD)
                ]
            },
            "Hide Hidden Files": {
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "values": [
                    ("Hidden", 2, winreg.REG_DWORD) # 2 is hidden, 1 is show
                ]
            },
            "Enable Title Bar Color": {
                "path": r"Software\Microsoft\Windows\DWM",
                "values": [
                    ("ColorPrevalence", 1, winreg.REG_DWORD)
                ]
            },
            "Disable Title Bar Color": {
                "path": r"Software\Microsoft\Windows\DWM",
                "values": [
                    ("ColorPrevalence", 0, winreg.REG_DWORD)
                ]
            }
        }
        
        changed = False
        for name, data in defaults.items():
            if name not in self.presets:
                self.presets[name] = data
                changed = True
        
        if changed:
            self._save_to_file()

    def save_preset(self, name, data):
        previous = self.presets.copy()
        self.presets[name] = data
        try:
            self._save_to_file()
        except Exception:
            self.presets.clear()
            self.presets.update(previous)
            raise

    def delete_preset(self, name):
        if name in self.presets:
            previous = self.presets.copy()
            del self.presets[name]
            try:
                self._save_to_file()
            except Exception:
                self.presets.clear()
                self.presets.update(previous)
                raise

    def get_preset(self, name):
        return self.presets.get(name)

    def _save_to_file(self):
        _atomic_write_json(self.presets_file, self.presets)
