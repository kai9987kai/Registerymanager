import json
import os
import winreg

class PresetManager:
    def __init__(self, presets_file="presets.json"):
        self.presets_file = presets_file
        self.presets = self.load_presets()
        self.ensure_defaults()

    def load_presets(self):
        if not os.path.exists(self.presets_file):
            return {}
        try:
            with open(self.presets_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
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
        self.presets[name] = data
        self._save_to_file()

    def delete_preset(self, name):
        if name in self.presets:
            del self.presets[name]
            self._save_to_file()

    def get_preset(self, name):
        return self.presets.get(name)

    def _save_to_file(self):
        with open(self.presets_file, 'w') as f:
            json.dump(self.presets, f, indent=4)
