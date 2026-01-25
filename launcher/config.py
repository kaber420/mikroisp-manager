import json
import os
from pathlib import Path

CONFIG_DIR = "."
CONFIG_FILE = "launcher_config.json"

class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(CONFIG_DIR, CONFIG_FILE)
        self._ensure_dir()
        self.config = self._load_config()

    def _ensure_dir(self):
        if not os.path.exists(CONFIG_DIR):
            try:
                os.makedirs(CONFIG_DIR)
            except OSError:
                # Fallback if cannot create directory, though it should exist based on user context
                pass

    def _load_config(self):
        if not os.path.exists(self.config_path):
            return self._default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._default_config()

    def _default_config(self):
        return {
            "headless": False
        }

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self._save_config()

    def _save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

# Global instance
config_manager = ConfigManager()
