import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from ui.main_window import RegistryApp
    print("Successfully imported RegistryApp")
except Exception as e:
    print(f"Failed to import RegistryApp: {e}")
    sys.exit(1)
