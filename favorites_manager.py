import json
import os

class FavoritesManager:
    def __init__(self, favorites_file="favorites.json"):
        self.favorites_file = favorites_file
        self.favorites = self.load_favorites()

    def load_favorites(self):
        if not os.path.exists(self.favorites_file):
            return []
        try:
            with open(self.favorites_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _save_to_file(self):
        with open(self.favorites_file, 'w') as f:
            json.dump(self.favorites, f, indent=4)

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
        self._save_to_file()
        return True

    def remove_favorite(self, index):
        """Remove a favorite by index."""
        if 0 <= index < len(self.favorites):
            self.favorites.pop(index)
            self._save_to_file()
            return True
        return False

    def get_favorites(self):
        return self.favorites
