"""
FastAPI application initialization script.

Run this before starting the server for the first time.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cuby.bootstrap import prefer_local_venv, restart_with_local_venv_if_needed  # noqa: E402


restart_with_local_venv_if_needed(__file__, PROJECT_ROOT)
prefer_local_venv(PROJECT_ROOT)

from cuby.config import settings  # noqa: E402
from cuby.database import Base, engine  # noqa: E402
from cuby import models  # noqa: E402,F401


def initialize_database() -> None:
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully")


def create_directories() -> None:
    """Create required assistant data directories."""
    directories = [
        settings.DATA_DIR,
        settings.SONGS_DIR,
        settings.SCREENSHOTS_DIR,
        settings.REMEMBER_DIR,
    ]

    print("\nCreating required directories...")
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created: {directory}")


def verify_json_files() -> bool:
    """Verify essential JSON files exist."""
    print("\nVerifying JSON configuration files...")
    cuby_json = settings.DATA_DIR / "cuby.json"

    if not cuby_json.exists():
        print(f"[WARN] {cuby_json} not found")
        print("  The chatbot will not work properly without this file.")
        return False

    print(f"[OK] Found: {cuby_json}")
    return True


def main() -> int:
    """Run all initialization steps."""
    print("=" * 60)
    print("Cuby Assistant - FastAPI Initialization")
    print("=" * 60)

    try:
        initialize_database()
        create_directories()
        verify_json_files()

        print("\n" + "=" * 60)
        print("[OK] Initialization Complete!")
        print("=" * 60)
        print("\nYou can now start the server with:")
        print("  python main.py")
        print("\nOr with uvicorn directly:")
        print("  uvicorn main:app --reload")
        print("\nAPI documentation will be available at:")
        print("  http://localhost:8000/docs")
        return 0
    except Exception as exc:
        print(f"\n[ERROR] Error during initialization: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
