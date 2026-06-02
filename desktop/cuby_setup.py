"""Clickable Windows setup EXE for installing the local CUBY launcher."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path


APP_NAME = "CUBY Assistant"


def _message(title: str, text: str, icon: int = 0x40) -> None:
    if "--quiet" in sys.argv:
        print(f"{title}: {text}")
        return
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, icon)
    except Exception:
        print(f"{title}: {text}")


def _candidate_roots() -> list[Path]:
    candidates = [Path.cwd()]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([exe_dir, exe_dir.parent, exe_dir.parent.parent])
    else:
        file_dir = Path(__file__).resolve().parent
        candidates.extend([file_dir, file_dir.parent])
    return candidates


def _find_project_root() -> Path:
    for candidate in _candidate_roots():
        current = candidate.resolve()
        for parent in [current, *current.parents]:
            if (
                (parent / "main.py").exists()
                and (parent / "desktop" / "cuby_desktop.py").exists()
                and (parent / "requirements.txt").exists()
            ):
                return parent
    raise FileNotFoundError(
        "Could not find the CUBY project folder. Keep this setup EXE inside "
        "the project folder or inside the dist folder created by the build script."
    )


def _run_powershell(script: Path, project_root: Path, no_deps: bool) -> int:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    if no_deps:
        command.append("-NoDeps")
    return subprocess.call(command, cwd=str(project_root))


def main() -> int:
    try:
        project_root = _find_project_root()
        script = project_root / "scripts" / "install_desktop_app.ps1"
        if not script.exists():
            raise FileNotFoundError(f"Missing installer script: {script}")

        if "--dry-run" in sys.argv:
            print(f"CUBY project found: {project_root}")
            print(f"Installer script found: {script}")
            return 0

        no_deps = "--install-deps" not in sys.argv
        exit_code = _run_powershell(script, project_root, no_deps=no_deps)
        if exit_code != 0:
            _message(
                APP_NAME,
                "CUBY setup did not finish successfully. Run the setup EXE from "
                "PowerShell to see the detailed error.",
                0x10,
            )
            return exit_code

        _message(
            APP_NAME,
            "CUBY Assistant installed successfully.\n\n"
            "Open it from the Desktop or Start Menu shortcut.",
        )
        return 0
    except Exception as exc:
        _message(APP_NAME, str(exc), 0x10)
        return 1


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())
