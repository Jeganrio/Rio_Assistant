"""
Print base64 Google OAuth environment values for Render.

Run locally only:
    python scripts/export_google_env.py

Copy the printed values into Render Environment secret variables. Do not commit
or share the output.
"""

from __future__ import annotations

import base64
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def encode_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def print_secret(key: str, path: Path) -> None:
    if path.exists():
        print(f"{key}={encode_file(path)}")
    else:
        print(f"# {key} skipped: {path.name} not found")


def main() -> int:
    print("# Paste these into Render as secret environment variables.")
    print("# Keep them private.")
    print_secret("GOOGLE_CREDENTIALS_B64", ROOT / "credentials.json")
    print_secret("GOOGLE_TOKEN_B64", ROOT / "token.json")
    print_secret("GOOGLE_GMAIL_TOKEN_B64", ROOT / "token.json")
    print_secret("GOOGLE_CALENDAR_TOKEN_B64", ROOT / "calendar_token.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
