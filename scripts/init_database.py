"""Create and initialize the fin-data database.

Usage:
    PYTHONPATH=. python scripts/init_database.py

The database URL and schema are read from the environment or .env through
src.config.settings.Settings. This script is safe to run more than once.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrastructure.database import models  # noqa: F401
from src.infrastructure.database.engine import DATABASE_SCHEMA, create_all_tables


if __name__ == "__main__":
    create_all_tables()
    print(f"Database initialized successfully in schema {DATABASE_SCHEMA}")
