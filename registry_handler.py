import winreg
import shutil
import os
from datetime import datetime

class RegistryHandler:
    def __init__(self):
        pass

    def read_key(self, hive, subkey):
        try:
            key = winreg.OpenKey(hive, subkey)
            values = []
            i = 0
            while True:
                try:
                    values.append(winreg.EnumValue(key, i))
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
            return values
        except FileNotFoundError:
            return None
        except PermissionError:
            return "Permission Denied"

    def enum_keys(self, hive, subkey):
        try:
            key = winreg.OpenKey(hive, subkey)
            subkeys = []
            i = 0
            while True:
                try:
                    subkeys.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
            return subkeys
        except Exception:
            return []

    def write_value(self, hive, subkey, name, value, val_type):
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, name, 0, val_type, value)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error writing value: {e}")
            return False

    def delete_value(self, hive, subkey, name):
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_WRITE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error deleting value: {e}")
            return False

    def create_key(self, hive, subkey):
        try:
            winreg.CreateKey(hive, subkey)
            return True
        except Exception as e:
            print(f"Error creating key: {e}")
            return False
            
    # Note: True backup/restore of registry keys programmatically is complex and often requires
    # calling reg.exe or using specific APIs. For safety, we might just export to .reg file.
    def backup_key(self, path, backup_folder="backups"):
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.reg"
        filepath = os.path.join(backup_folder, filename)
        
        # Using reg.exe for export as it's reliable
        # path format for reg.exe: HKEY_CURRENT_USER\Software\MyApp
        cmd = f'reg export "{path}" "{filepath}" /y'
        os.system(cmd)
        return filepath

    def restore_backup(self, filepath):
        if not os.path.exists(filepath):
            return False
        
        # reg import
        cmd = f'reg import "{filepath}"'
        ret = os.system(cmd)
        return ret == 0
