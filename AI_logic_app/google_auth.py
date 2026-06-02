from __future__ import annotations

import base64
import json
import os
import pickle
from pathlib import Path
from typing import Iterable

from google.oauth2.credentials import Credentials


def load_authorized_credentials(
    token_path: str | Path,
    scopes: list[str],
    env_names: Iterable[str],
) -> Credentials | None:
    """Load Google OAuth user credentials from env or the local token file."""
    for env_name in env_names:
        raw = os.getenv(env_name, "").strip()
        if not raw:
            continue
        try:
            return Credentials.from_authorized_user_info(
                _json_from_env(raw),
                scopes,
            )
        except Exception as exc:
            print(f"Error loading {env_name}: {exc}")

    token_file = Path(token_path)
    if not token_file.exists():
        return None

    try:
        token_data = token_file.read_bytes()
        try:
            return pickle.loads(token_data)
        except Exception:
            return Credentials.from_authorized_user_info(
                json.loads(token_data.decode("utf-8")),
                scopes,
            )
    except Exception as exc:
        print(f"Error loading {token_file.name}: {exc}. Re-authenticating.")
        return None


def load_client_config(credentials_path: str | Path) -> dict | None:
    """Load Google OAuth client configuration from env or credentials.json."""
    for env_name in ("GOOGLE_CREDENTIALS_JSON", "GOOGLE_CLIENT_SECRET_JSON"):
        raw = os.getenv(env_name, "").strip()
        if raw:
            try:
                return _json_from_env(raw)
            except Exception as exc:
                print(f"Error loading {env_name}: {exc}")

    for env_name in ("GOOGLE_CREDENTIALS_B64", "GOOGLE_CLIENT_SECRET_B64"):
        raw = os.getenv(env_name, "").strip()
        if raw:
            try:
                decoded = base64.b64decode(raw).decode("utf-8")
                return json.loads(decoded)
            except Exception as exc:
                print(f"Error loading {env_name}: {exc}")

    credentials_file = Path(credentials_path)
    if not credentials_file.exists():
        return None

    try:
        return json.loads(credentials_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Error loading {credentials_file.name}: {exc}")
        return None


def google_not_connected_message(service_name: str) -> str:
    return (
        f"{service_name} is not connected on the live server yet. "
        "Use this from the local desktop app, or connect Google in Render Environment "
        "with GOOGLE_CREDENTIALS_B64 and the matching OAuth token secret."
    )


def _json_from_env(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
