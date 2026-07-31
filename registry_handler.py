import winreg
import os
import subprocess
import uuid
from datetime import datetime, timezone


class RegistryOperationError(RuntimeError):
    """Raised when registry state cannot be read reliably."""

    def __init__(self, operation, subkey, detail):
        self.operation = operation
        self.subkey = subkey
        self.detail = str(detail)
        super().__init__(f"{operation} failed for {subkey or '<root>'}: {self.detail}")

class RegistryHandler:
    def __init__(self, backup_folder="backups"):
        self.last_error = None
        self.backup_folder = os.fspath(backup_folder)

    def read_key(self, hive, subkey):
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                values = []
                i = 0
                while True:
                    try:
                        values.append(winreg.EnumValue(key, i))
                        i += 1
                    except OSError:
                        break
            return values
        except FileNotFoundError:
            return None
        except PermissionError:
            return "Permission Denied"
        except Exception as e:
            print(f"Error reading key {subkey}: {e}")
            return None

    def read_value(self, hive, subkey, name):
        """Return ``(value, type)`` for a value, or ``None`` when absent.

        Unlike ``read_key``, access and I/O errors are raised so callers never
        mistake an unreadable value for a value that does not exist.
        """
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_QUERY_VALUE) as key:
                return winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise RegistryOperationError("read value", subkey, exc) from exc

    def enum_keys(self, hive, subkey):
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                subkeys = []
                i = 0
                while True:
                    try:
                        subkeys.append(winreg.EnumKey(key, i))
                        i += 1
                    except OSError:
                        break
            return subkeys
        except Exception:
            return []

    def write_value(self, hive, subkey, name, value, val_type):
        self.last_error = None
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, val_type, value)
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"Error writing value: {e}")
            return False

    def delete_value(self, hive, subkey, name):
        self.last_error = None
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"Error deleting value: {e}")
            return False

    def create_key(self, hive, subkey):
        self.last_error = None
        try:
            with winreg.CreateKey(hive, subkey):
                pass
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"Error creating key: {e}")
            return False
            
    def backup_key(self, path, backup_folder=None):
        self.last_error = None
        backup_folder = os.fspath(backup_folder or self.backup_folder)
        os.makedirs(backup_folder, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        key_label = path.rstrip("\\").split("\\")[-1] or "registry"
        safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in key_label)[:48]
        filename = f"{safe_label}_{timestamp}_{uuid.uuid4().hex[:8]}.reg"
        filepath = os.path.abspath(os.path.join(backup_folder, filename))
        
        cmd = ['reg', 'export', path, filepath, '/y']
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=60,
            )
            return filepath
        except (OSError, subprocess.SubprocessError) as e:
            self.last_error = str(e)
            print(f"Backup failed: {e}")
            return None

    def restore_backup(self, filepath):
        self.last_error = None
        filepath = os.path.abspath(filepath)
        if not os.path.isfile(filepath) or not filepath.lower().endswith(".reg"):
            self.last_error = "Backup must be an existing .reg file."
            return False
            
        cmd = ['reg', 'import', filepath]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=60,
            )
            return True
        except (OSError, subprocess.SubprocessError) as e:
            self.last_error = str(e)
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
