# Calculator Demo

A simple calculator application demonstrating CodeAtlas graph extraction.

## Architecture

- `calculator/` – Core arithmetic operations (add, subtract, multiply, divide)
- `utils/` – Shared utilities (Logger, Config)
- `main.py` – Application entry point

## Design Decisions

- Logger is a simple print-based implementation to avoid external dependencies.
- Config loads JSON from disk; in production this would use environment variables.
- Division by zero raises ValueError for safety.
