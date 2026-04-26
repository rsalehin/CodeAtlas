"""Configuration loader for the application."""

import json
from pathlib import Path

class Config:
    """Loads and manages application configuration."""
    def __init__(self, path: str = "config.json"):
        self.path = Path(path)
        self.data = {}

    def load(self) -> dict:
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
        return self.data

    def get(self, key: str, default=None):
        return self.data.get(key, default)
