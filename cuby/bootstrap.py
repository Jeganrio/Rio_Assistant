"""Startup helpers for running CUBY with the local virtual environment."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _project_root(project_root: str | Path | None = None) -> Path:
    if project_root is not None:
        return Path(project_root).resolve()
    return Path(__file__).resolve().parent.parent


def _venv_python(root: Path) -> Path:
    return root / "venv" / "Scripts" / "python.exe"


def _venv_site_packages(root: Path) -> Path:
    return root / "venv" / "Lib" / "site-packages"


def _venv_version(root: Path) -> tuple[int, int] | None:
    cfg_path = root / "venv" / "pyvenv.cfg"
    if not cfg_path.exists():
        return None
    match = re.search(
        r"^version\s*=\s*(\d+)\.(\d+)",
        cfg_path.read_text(encoding="utf-8", errors="ignore"),
        re.MULTILINE,
    )
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _same_executable(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return str(left).lower() == str(right).lower()


def prefer_local_venv(project_root: str | Path | None = None) -> bool:
    """Add local venv packages to sys.path when the Python versions match."""
    root = _project_root(project_root)
    site_packages = _venv_site_packages(root)
    if not site_packages.exists():
        return False

    version = _venv_version(root)
    if version and version != (sys.version_info.major, sys.version_info.minor):
        return False

    path_text = str(site_packages)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
    return True


def restart_with_local_venv_if_needed(
    script_path: str | Path,
    project_root: str | Path | None = None,
) -> bool:
    """Restart direct script runs with venv Python when it is available."""
    root = _project_root(project_root)
    venv_python = _venv_python(root)
    if not venv_python.exists():
        return False

    current = Path(sys.executable)
    if _same_executable(current, venv_python):
        return False

    os.execv(
        str(venv_python),
        [str(venv_python), str(Path(script_path).resolve()), *sys.argv[1:]],
    )
    return True
