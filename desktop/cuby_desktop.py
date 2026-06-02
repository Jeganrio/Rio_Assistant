"""Windows desktop launcher for the local CUBY assistant."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = int(os.getenv("CUBY_DESKTOP_PORT", "8000"))


def _health_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/health"


def _app_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/"


def _is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def _is_cuby_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(_health_url(port), timeout=1.5) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _pick_port() -> int:
    if not _is_port_open(DEFAULT_PORT) or _is_cuby_running(DEFAULT_PORT):
        return DEFAULT_PORT
    for port in range(DEFAULT_PORT + 1, DEFAULT_PORT + 20):
        if not _is_port_open(port):
            return port
    return DEFAULT_PORT


def _wait_for_server(port: int, timeout_seconds: int = 45) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _is_cuby_running(port):
            return True
        time.sleep(0.5)
    return False


def _server_environment(port: int) -> dict[str, str]:
    env = os.environ.copy()
    env["CUBY_CLOUD"] = "0"
    env["SERVER_HOST"] = "127.0.0.1"
    env["SERVER_PORT"] = str(port)
    env.setdefault("PYTHONUTF8", "1")
    return env


def _start_server(port: int) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(PROJECT_ROOT),
        env=_server_environment(port),
    )


def main() -> int:
    os.chdir(PROJECT_ROOT)
    port = _pick_port()

    if _is_cuby_running(port):
        print(f"CUBY is already running at {_app_url(port)}")
        webbrowser.open_new_tab(_app_url(port))
        return 0

    print("Starting CUBY desktop assistant...")
    print(f"Project: {PROJECT_ROOT}")
    print(f"Local URL: {_app_url(port)}")
    print("Close this window or press Ctrl+C to stop the local server.")

    process = _start_server(port)
    try:
        if not _wait_for_server(port):
            print("CUBY did not become ready in time. Check the server output above.")
            return process.poll() or 1

        webbrowser.open_new_tab(_app_url(port))
        while process.poll() is None:
            time.sleep(0.5)
        return process.returncode or 0
    except KeyboardInterrupt:
        print("\nStopping CUBY...")
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
