"""Simple logging utility."""

class Logger:
    """Handles application logging with configurable levels."""
    def __init__(self, level: str = "INFO"):
        self.level = level

    def log(self, message: str) -> None:
        print(f"[{self.level}] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")
