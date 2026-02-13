import winreg
import shutil
import os
import subprocess
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
        except Exception as e:
            print(f"Error reading key {subkey}: {e}")
            return None

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
            
    def backup_key(self, path, backup_folder="backups"):
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.reg"
        filepath = os.path.join(backup_folder, filename)
        
        # Using subprocess for better security
        cmd = ['reg', 'export', path, filepath, '/y']
        try:
            subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return filepath
        except subprocess.CalledProcessError as e:
            print(f"Backup failed: {e}")
            return None

    def restore_backup(self, filepath):
        if not os.path.exists(filepath):
            return False
            
        cmd = ['reg', 'import', filepath]
        try:
            subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Restore failed: {e}")
            return False

    def search_registry(self, hive, start_path, query, stop_event=None):
        """
        Recursive search for keys or values containing the query.
        Returns a list of results: [{'path': ..., 'type': 'Key'|'Value', 'name': ...}, ...]
        """
        results = []
        try:
            # Check keys
            subkeys = self.enum_keys(hive, start_path)
            for sk in subkeys:
                if stop_event and stop_event.is_set():
                    return results
                
                full_sub_path = f"{start_path}\\{sk}" if start_path else sk
                
                if query.lower() in sk.lower():
                    results.append({'path': full_sub_path, 'type': 'Key', 'name': sk})
                
                # Recurse
                results.extend(self.search_registry(hive, full_sub_path, query, stop_event))
            
            # Check values
            values = self.read_key(hive, start_path)
            if values and not isinstance(values, str):
                for name, data, type_ in values:
                    if stop_event and stop_event.is_set():
                        return results
                    
                    name_str = name if name else "(Default)"
                    if query.lower() in name_str.lower() or query.lower() in str(data).lower():
                        results.append({'path': start_path, 'type': 'Value', 'name': name_str, 'data': str(data)})
                        
        except Exception as e:
            # Access denied or other errors are common in registry traversal
            pass
            
        return results
