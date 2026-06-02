"""
mcp_tools.py
============
MCP (Model Context Protocol) inspired tool integrations for CUBY AI Assistant.

Provides:
  - AppLauncherTool      : open/close/list apps, websites, files and folders
  - DesktopSystemTool    : Windows desktop system controls and status
  - FileSystemTool       : list, read, create, delete files/folders
  - WeatherTool          : current weather + forecast via Open-Meteo (free, no key)
  - NewsTool             : dynamic Google News RSS + optional GNews top headlines
  - FlightTool           : real-time flight info via AviationStack (free tier)
  - CalendarTool         : Google Calendar meetings and upcoming events
  - ReminderTool         : local persistent reminders and due alerts
  - BriefingTool         : daily briefing from weather, calendar, Gmail, reminders, and optional news
  - UtilityAlertTool     : power-cut and water-cut alerts from official pages + RSS fallback

Every tool exposes:
  .name          : str
  .description   : str
  .run(**kwargs) : dict  →  {"status": "ok"|"error", "data": ..., "message": str}
"""

from __future__ import annotations

import os
import subprocess
import shutil
import json
import datetime
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from cuby.config import settings as app_settings  # Import app_settings to get BASE_DIR
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

try:
    from AI_logic_app.mcp_gmail import GmailTool
except ImportError as exc:
    GmailTool = None
    _GMAIL_IMPORT_ERROR = exc
else:
    _GMAIL_IMPORT_ERROR = None

try:
    from AI_logic_app.mcp_calendar import CalendarTool
except ImportError as exc:
    CalendarTool = None
    _CALENDAR_IMPORT_ERROR = exc
else:
    _CALENDAR_IMPORT_ERROR = None

from AI_logic_app.mcp_notification import NotificationTool
from AI_logic_app.mcp_jobs import JobTool
from AI_logic_app.mcp_media import MediaControlTool
from AI_logic_app.mcp_reminders import ReminderTool

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class MCPTool:
    name: str = "base_tool"
    description: str = "Base MCP tool"

    def run(self, **kwargs) -> dict:
        raise NotImplementedError

    # helpers
    @staticmethod
    def _ok(data: Any, message: str = "Success") -> dict:
        return {"status": "ok", "data": data, "message": message}

    @staticmethod
    def _err(message: str) -> dict:
        return {"status": "error", "data": None, "message": message}


if GmailTool is None:
    class GmailTool(MCPTool):
        name = "gmail"
        description = "Gmail integration is unavailable until Google API packages are installed."

        def __init__(self, base_dir=None):
            self.base_dir = base_dir

        def run(self, **kwargs) -> dict:
            return self._err(
                "Gmail is unavailable because Google API packages are not installed. "
                "Run: python -m pip install -r requirements.txt"
            )


if CalendarTool is None:
    class CalendarTool(MCPTool):
        name = "calendar"
        description = "Google Calendar integration is unavailable until Google API packages are installed."

        def __init__(self, base_dir=None):
            self.base_dir = base_dir

        def run(self, **kwargs) -> dict:
            return self._err(
                "Google Calendar is unavailable because Google API packages are not installed. "
                "Run: python -m pip install -r requirements.txt"
            )


# ---------------------------------------------------------------------------
# 1. App / File / Folder Launcher
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 1. Dynamic App / File / Folder Launcher
# ---------------------------------------------------------------------------

import webbrowser


class AppLauncherTool(MCPTool):

    """
    Open, close, and list installed applications, websites, files and folders.
    """

    name = "app_launcher"

    description = (
        "Open, close, and list local Windows apps, websites, files, and folders."
    )

    _WEBSITES = {
        "youtube": "https://youtube.com",
        "gmail": "https://mail.google.com",
        "calendar": "https://calendar.google.com",
        "google calendar": "https://calendar.google.com",
        "spotify": "https://open.spotify.com",
        "spotify web": "https://open.spotify.com",
        "linkedin": "https://linkedin.com",
        "github": "https://github.com",
        "google": "https://google.com",
        "chatgpt": "https://chat.openai.com",
        "netflix": "https://netflix.com",
        "amazon": "https://amazon.in",
        "hotstar": "https://hotstar.com",
    }

    _KNOWN_APP_PATHS = {
        "spotify": [
            r"%APPDATA%\Spotify\Spotify.exe",
            r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe",
            r"C:\Program Files\Spotify\Spotify.exe",
            r"C:\Program Files (x86)\Spotify\Spotify.exe",
        ],
        "chrome": [
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        ],
        "google chrome": [
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        ],
        "edge": [
            r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
            r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        ],
        "microsoft edge": [
            r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
            r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        ],
        "vscode": [
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
        ],
        "vs code": [
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
        ],
        "visual studio code": [
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
        ],
        "notepad": [r"%WINDIR%\System32\notepad.exe"],
        "paint": [r"%WINDIR%\System32\mspaint.exe"],
        "word": [r"%PROGRAMFILES%\Microsoft Office\root\Office16\WINWORD.EXE"],
        "excel": [r"%PROGRAMFILES%\Microsoft Office\root\Office16\EXCEL.EXE"],
        "powerpoint": [r"%PROGRAMFILES%\Microsoft Office\root\Office16\POWERPNT.EXE"],
        "outlook": [r"%PROGRAMFILES%\Microsoft Office\root\Office16\OUTLOOK.EXE"],
        "teams": [
            r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",
            r"%LOCALAPPDATA%\Microsoft\WindowsApps\ms-teams.exe",
        ],
        "whatsapp": [r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"],
        "telegram": [r"%APPDATA%\Telegram Desktop\Telegram.exe"],
    }

    _PATH_COMMANDS = {
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "cmd": "cmd",
        "command prompt": "cmd",
        "powershell": "powershell",
        "windows terminal": "wt",
        "terminal": "wt",
        "explorer": "explorer",
        "file explorer": "explorer",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
    }

    _PROTOCOLS = {
        "spotify": "spotify:",
        "calculator": "calculator:",
        "calc": "calculator:",
        "settings": "ms-settings:",
        "windows settings": "ms-settings:",
        "mail": "mailto:",
    }

    _PROCESS_ALIASES = {
        "spotify": ["Spotify.exe"],
        "chrome": ["chrome.exe"],
        "google chrome": ["chrome.exe"],
        "edge": ["msedge.exe"],
        "microsoft edge": ["msedge.exe"],
        "firefox": ["firefox.exe"],
        "browser": ["chrome.exe", "msedge.exe", "firefox.exe"],
        "vscode": ["Code.exe"],
        "vs code": ["Code.exe"],
        "visual studio code": ["Code.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["CalculatorApp.exe", "Calculator.exe", "calc.exe"],
        "calc": ["CalculatorApp.exe", "Calculator.exe", "calc.exe"],
        "paint": ["mspaint.exe"],
        "word": ["WINWORD.EXE"],
        "excel": ["EXCEL.EXE"],
        "powerpoint": ["POWERPNT.EXE"],
        "outlook": ["OUTLOOK.EXE"],
        "teams": ["Teams.exe", "ms-teams.exe"],
        "whatsapp": ["WhatsApp.exe"],
        "telegram": ["Telegram.exe"],
        "vlc": ["vlc.exe"],
        "zoom": ["Zoom.exe"],
        "discord": ["Discord.exe"],
        "file explorer": ["explorer.exe"],
        "explorer": ["explorer.exe"],
    }

    @staticmethod
    def _browser_action(url: str, label: str = "Open") -> dict:
        return {
            "type": "open_url",
            "url": url,
            "label": label,
            "target": "_blank",
        }

    @staticmethod
    def _expand_path(path_text: str) -> str:
        return os.path.expandvars(path_text)

    @staticmethod
    def _strip_command_words(target: str) -> str:
        value = (target or "").strip().strip("\"'")
        value = re.sub(
            r"^(please\s+)?(open|launch|start|run|close|quit|exit|stop)\s+",
            "",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\b(app|application|program|software)\b",
            "",
            value,
            flags=re.IGNORECASE,
        )
        for marker in (" and play ", " then play ", " please "):
            index = value.lower().find(marker)
            if index > 0:
                value = value[:index]
        return re.sub(r"\s+", " ", value).strip()

    def _normalize_target(self, target: str) -> tuple[str, str]:
        display = self._strip_command_words(target)
        key = display.lower().replace("-", " ").replace("_", " ").strip()
        aliases = {
            "google": "google",
            "google chrome browser": "google chrome",
            "chrome browser": "chrome",
            "edge browser": "edge",
            "visual studio": "visual studio code",
            "code editor": "visual studio code",
            "vs cod": "vs code",
            "spotifi": "spotify",
        }
        key = aliases.get(key, key)
        return display, key

    @staticmethod
    def _is_url(value: str) -> bool:
        text = (value or "").strip().lower()
        return text.startswith(("http://", "https://")) or text.startswith("www.")

    @staticmethod
    def _format_url(value: str) -> str:
        text = value.strip()
        if text.lower().startswith("www."):
            return f"https://{text}"
        return text

    # -------------------------------------------------------
    # START MENU PATHS
    # -------------------------------------------------------

    def _start_menu_paths(self):

        return [

            Path(
                os.environ.get(
                    "PROGRAMDATA",
                    r"C:\ProgramData"
                )
            ) / r"Microsoft\Windows\Start Menu\Programs",

            Path(
                os.environ.get(
                    "APPDATA",
                    ""
                )
            ) / r"Microsoft\Windows\Start Menu\Programs"
        ]

    # -------------------------------------------------------
    # SCAN INSTALLED APPS
    # -------------------------------------------------------

    def _scan_apps(self):

        apps = {}

        for start_path in self._start_menu_paths():

            if not start_path.exists():
                continue

            for file in start_path.rglob("*"):

                if file.suffix.lower() in [
                    ".lnk",
                    ".exe"
                ]:

                    app_name = (
                        file.stem.lower()
                        .replace("-", " ")
                        .replace("_", " ")
                        .strip()
                    )

                    apps[app_name] = str(file)

        return apps

    def _app_label(self, target: str, apps: dict[str, str]) -> tuple[str | None, str | None]:
        if target in apps:
            return target, apps[target]
        for app_name, app_path in apps.items():
            if target and target in app_name:
                return app_name, app_path
        return None, None

    def _open_known_path(self, target: str) -> dict | None:
        for app_path in self._KNOWN_APP_PATHS.get(target, []):
            expanded = self._expand_path(app_path)
            if os.path.exists(expanded):
                os.startfile(expanded)
                return self._ok({"app": target, "path": expanded}, f"Opened {target}")
        return None

    def _open_path_command(self, target: str) -> dict | None:
        command = self._PATH_COMMANDS.get(target, target)
        exe = shutil.which(command)
        if not exe:
            return None
        subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return self._ok({"exe": exe, "app": target}, f"Opened {target}")

    def _open_protocol(self, target: str) -> dict | None:
        protocol = self._PROTOCOLS.get(target)
        if not protocol:
            return None
        try:
            os.startfile(protocol)
            return self._ok({"app": target, "protocol": protocol}, f"Opened {target}")
        except Exception:
            return None

    def _open_target(self, target: str, url: str = "") -> dict:
        display, key = self._normalize_target(target)
        requested_url = url or (self._format_url(display) if self._is_url(display) else "")

        if requested_url:
            webbrowser.open_new_tab(requested_url)
            return self._ok(
                {"url": requested_url, "browser_action": self._browser_action(requested_url, "Open URL")},
                f"Opened URL: {requested_url}",
            )

        if not display:
            return self._err("No target specified.")

        path = Path(display).expanduser()
        if path.exists():
            os.startfile(str(path))
            return self._ok({"path": str(path)}, f"Opened {path.name}")

        for opener in (self._open_known_path, self._open_path_command):
            result = opener(key)
            if result:
                return result

        apps = self._scan_apps()
        app_name, app_path = self._app_label(key, apps)
        if app_name and app_path:
            os.startfile(app_path)
            return self._ok({"app": app_name, "path": app_path}, f"Opened {app_name}")

        result = self._open_protocol(key)
        if result:
            return result

        if key in self._WEBSITES:
            website_url = self._WEBSITES[key]
            webbrowser.open_new_tab(website_url)
            return self._ok(
                {
                    "website": key,
                    "url": website_url,
                    "browser_action": self._browser_action(website_url, f"Open {key}"),
                },
                f"Opened {key}",
            )

        search_url = f"https://www.google.com/search?q=download+{quote_plus(display)}"
        webbrowser.open_new_tab(search_url)
        return self._ok(
            {"search": search_url, "browser_action": self._browser_action(search_url, "Search download")},
            f"{display} not installed. Opened install page.",
        )

    def _process_names_for_target(self, target: str) -> list[str]:
        display, key = self._normalize_target(target)
        names = self._PROCESS_ALIASES.get(key)
        if names:
            return names

        apps = self._scan_apps()
        app_name, app_path = self._app_label(key, apps)
        if app_path:
            candidate = Path(app_path)
            if candidate.suffix.lower() == ".exe":
                return [candidate.name]

        if display.lower().endswith(".exe"):
            return [display]
        return []

    def _close_target(self, target: str) -> dict:
        display, key = self._normalize_target(target)
        if not display:
            return self._err("No app specified to close.")

        process_names = self._process_names_for_target(display)
        if not process_names:
            return self._err(
                f"I do not know the running process for {display}. Try close it to close the active window."
            )

        try:
            import psutil
        except Exception as exc:
            return self._err(f"Desktop close needs psutil. Run: python -m pip install psutil. Details: {exc}")

        wanted = {name.lower() for name in process_names}
        current_pid = os.getpid()
        matched = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = (proc.info.get("name") or "").lower()
                if proc.info.get("pid") == current_pid or proc_name not in wanted:
                    continue
                matched.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not matched:
            return self._ok(
                {"app": key or display, "process_names": sorted(wanted), "closed": 0},
                f"{display} is not running.",
            )

        closed = []
        blocked = []
        for proc in matched:
            try:
                proc.terminate()
                closed.append(proc.info.get("name") or str(proc.pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                blocked.append(f"{proc.info.get('name') or proc.pid}: {exc}")

        gone, alive = psutil.wait_procs(matched, timeout=3)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                blocked.append(f"{proc.info.get('name') or proc.pid}: {exc}")

        count = len(gone) + max(0, len(alive) - len(blocked))
        message = f"Closed {display} ({max(count, len(closed))} process(es))."
        if blocked:
            message += " Some windows could not be closed because Windows denied access."
        return self._ok(
            {
                "app": key or display,
                "process_names": sorted(wanted),
                "closed": max(count, len(closed)),
                "blocked": blocked,
            },
            message,
        )

    def _list_targets(self, target: str = "") -> dict:
        apps = self._scan_apps()
        app_names = sorted(apps.keys())
        websites = sorted(self._WEBSITES.keys())
        close_supported = sorted(self._PROCESS_ALIASES.keys())

        filter_text = self._normalize_target(target)[1]
        if filter_text:
            app_names = [name for name in app_names if filter_text in name]
            websites = [name for name in websites if filter_text in name]
            close_supported = [name for name in close_supported if filter_text in name]

        data = {
            "installed_apps": app_names[:80],
            "websites": websites,
            "close_supported": close_supported,
            "total_installed_apps": len(apps),
        }
        if filter_text:
            message = (
                f"Found {len(app_names)} app shortcut(s), {len(websites)} website shortcut(s), "
                f"and {len(close_supported)} close action(s) matching {filter_text}."
            )
        else:
            message = (
                f"Found {len(apps)} installed app shortcut(s). "
                "Say open app name, close app name, or list apps matching a name."
            )
        return self._ok(data, message)

    # -------------------------------------------------------
    # MAIN
    # -------------------------------------------------------

    def run(
        self,
        action: str = "open",
        target: str = "",
        url: str = ""
    ) -> dict:

        try:
            action_key = (action or "open").lower().strip()
            if action_key in {"open", "launch", "start", "run"}:
                return self._open_target(target=target, url=url)
            if action_key in {"close", "quit", "exit", "stop"}:
                return self._close_target(target=target)
            if action_key in {"list", "show", "find"}:
                return self._list_targets(target=target)
            return self._err(f"Unsupported app action: {action}")

        except Exception as e:

            return self._err(str(e))


class DesktopSystemTool(MCPTool):
    """Windows-only desktop system controls for the local EXE app."""

    name = "desktop_system"
    description = (
        "Control Windows desktop system actions: close apps, shutdown, restart, "
        "screenshots, volume, Wi-Fi/Bluetooth status, file search, and running apps."
    )

    _CLOSE_ALL_PROCESS_NAMES = {
        name.lower()
        for names in AppLauncherTool._PROCESS_ALIASES.values()
        for name in names
    } | {
        "acrord32.exe",
        "applicationframehost.exe",
        "discord.exe",
        "firefox.exe",
        "notepad++.exe",
        "obs64.exe",
        "postman.exe",
        "slack.exe",
        "vlc.exe",
        "windowsterminal.exe",
        "zoom.exe",
    }

    _PROTECTED_PROCESS_NAMES = {
        "cmd.exe",
        "conhost.exe",
        "csrss.exe",
        "dwm.exe",
        "explorer.exe",
        "lsass.exe",
        "powershell.exe",
        "python.exe",
        "pythonw.exe",
        "services.exe",
        "smss.exe",
        "system",
        "taskhostw.exe",
        "uvicorn.exe",
        "wininit.exe",
        "winlogon.exe",
    }

    _SKIP_SEARCH_DIRS = {
        "$recycle.bin",
        ".git",
        "__pycache__",
        "appdata",
        "node_modules",
        "program files",
        "program files (x86)",
        "programdata",
        "windows",
        "venv",
    }

    @staticmethod
    def _is_cloud() -> bool:
        return os.getenv("CUBY_CLOUD", "").lower() in {"1", "true", "yes"}

    def _require_desktop(self) -> dict | None:
        if self._is_cloud():
            return self._err("Desktop system control is available only in the local Windows app.")
        if os.name != "nt":
            return self._err("Desktop system control currently supports Windows only.")
        return None

    @staticmethod
    def _browser_action(path: str, label: str = "Open file location") -> dict:
        return {
            "type": "open_local_path",
            "path": path,
            "label": label,
        }

    @staticmethod
    def _open_in_explorer(path: Path) -> None:
        try:
            if path.is_file():
                subprocess.Popen(["explorer", f"/select,{path}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif path.exists():
                os.startfile(str(path))
        except Exception:
            pass

    def _close_all_apps(self) -> dict:
        if err := self._require_desktop():
            return err
        try:
            import psutil
        except Exception as exc:
            return self._err(f"Running app control needs psutil. Details: {exc}")

        current_pid = os.getpid()
        matched = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                pid = int(proc.info.get("pid") or 0)
                if (
                    not name
                    or pid == current_pid
                    or name in self._PROTECTED_PROCESS_NAMES
                    or name not in self._CLOSE_ALL_PROCESS_NAMES
                ):
                    continue
                matched.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                continue

        if not matched:
            return self._ok({"closed": 0, "processes": []}, "No known user apps are running.")

        closed = []
        blocked = []
        for proc in matched:
            try:
                proc.terminate()
                closed.append(proc.info.get("name") or str(proc.pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                blocked.append(f"{proc.info.get('name') or proc.pid}: {exc}")
        _, alive = psutil.wait_procs(matched, timeout=3)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                blocked.append(f"{proc.info.get('name') or proc.pid}: {exc}")

        unique_closed = sorted(set(closed), key=str.lower)
        message = f"Closed {len(unique_closed)} known user app process type(s)."
        if blocked:
            message += " Some apps could not be closed because Windows denied access."
        return self._ok(
            {"closed": len(unique_closed), "processes": unique_closed, "blocked": blocked},
            message,
        )

    def _power(self, action: str, delay: int = 30) -> dict:
        if err := self._require_desktop():
            return err
        delay = max(5, min(3600, int(delay or 30)))
        if action == "cancel_shutdown":
            subprocess.Popen(["shutdown", "/a"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return self._ok({"action": action}, "Cancelled any pending shutdown or restart.")
        flag = "/r" if action == "restart" else "/s"
        subprocess.Popen(["shutdown", flag, "/t", str(delay)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        label = "restart" if action == "restart" else "shutdown"
        return self._ok(
            {"action": action, "delay_seconds": delay},
            f"Windows {label} scheduled in {delay} seconds. Say cancel shutdown to stop it.",
        )

    def _screenshot(self) -> dict:
        if err := self._require_desktop():
            return err
        try:
            import pyautogui
        except Exception as exc:
            return self._err(f"Screenshot needs PyAutoGUI. Details: {exc}")
        folder = Path(app_settings.BASE_DIR) / "AI_logic_app" / "data" / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"cuby_screenshot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
        image = pyautogui.screenshot()
        image.save(path)
        self._open_in_explorer(path)
        return self._ok(
            {"path": str(path), "browser_action": self._browser_action(str(path))},
            f"Screenshot saved: {path}",
        )

    @staticmethod
    def _set_volume_core_audio(percent: int | None = None, mute: bool | None = None) -> tuple[int | None, bool | None]:
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        volume = getattr(devices, "EndpointVolume", None)
        if volume is None:
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
        if mute is not None:
            volume.SetMute(1 if mute else 0, None)
        if percent is not None:
            volume.SetMasterVolumeLevelScalar(max(0, min(100, percent)) / 100.0, None)
            volume.SetMute(0, None)
        current = int(round(volume.GetMasterVolumeLevelScalar() * 100))
        muted = bool(volume.GetMute())
        return current, muted

    def _volume(self, percent: int | None = None, mute: bool | None = None, action: str = "status") -> dict:
        if err := self._require_desktop():
            return err
        if action == "full":
            percent = 100
            mute = False
        elif action == "mute":
            mute = True
        elif action == "unmute":
            mute = False

        try:
            current, muted = self._set_volume_core_audio(percent=percent, mute=mute)
        except Exception:
            try:
                import pyautogui
                if mute is not None:
                    pyautogui.press("volumemute")
                if percent is not None:
                    pyautogui.press("volumedown", presses=50, interval=0.01)
                    pyautogui.press("volumeup", presses=max(0, min(50, round(percent / 2))), interval=0.01)
                current, muted = percent, mute
            except Exception as exc:
                return self._err(
                    "Volume percentage control needs pycaw/comtypes or PyAutoGUI media keys. "
                    f"Details: {exc}"
                )

        if action == "volume_status" and current is not None:
            message = f"Volume is {current} percent" + (" and muted." if muted else ".")
        elif muted:
            message = "Volume muted."
        elif current is not None:
            message = f"Volume set to {current} percent."
        else:
            message = "Volume updated."
        return self._ok({"volume_percent": current, "muted": muted}, message)

    def _wifi_status(self) -> dict:
        if err := self._require_desktop():
            return err
        try:
            proc = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=8,
                errors="replace",
            )
        except Exception as exc:
            return self._err(f"Could not check Wi-Fi status: {exc}")
        if proc.returncode != 0:
            return self._err((proc.stderr or proc.stdout or "Wi-Fi status unavailable.").strip())

        info = {}
        for line in proc.stdout.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key in {"state", "ssid", "signal", "profile", "radio type", "authentication"}:
                info[key.replace(" ", "_")] = value

        connected = info.get("state", "").lower() == "connected"
        ssid = info.get("ssid", "")
        if connected and ssid:
            msg = f"Wi-Fi is connected to {ssid}."
            if info.get("signal"):
                msg += f" Signal {info['signal']}."
        else:
            msg = "Wi-Fi is not connected."
        return self._ok({"connected": connected, **info}, msg)

    def _bluetooth_status(self) -> dict:
        if err := self._require_desktop():
            return err
        script = r"""
$service = Get-Service bthserv -ErrorAction SilentlyContinue
$devices = @(Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |
  Select-Object -First 12 FriendlyName,Status,Problem)
[pscustomobject]@{
  serviceStatus = if ($service) { $service.Status.ToString() } else { "Unknown" }
  devices = $devices
} | ConvertTo-Json -Depth 4
"""
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=10,
                errors="replace",
            )
            data = json.loads(proc.stdout or "{}")
        except Exception as exc:
            return self._err(f"Could not check Bluetooth status: {exc}")

        devices = data.get("devices") or []
        if isinstance(devices, dict):
            devices = [devices]
        ok_devices = [
            d.get("FriendlyName")
            for d in devices
            if str(d.get("Status", "")).upper() == "OK" and d.get("FriendlyName")
        ]
        service = data.get("serviceStatus", "Unknown")
        if ok_devices:
            msg = f"Bluetooth service is {service}. Available Bluetooth device(s): {', '.join(ok_devices[:5])}."
        else:
            msg = f"Bluetooth service is {service}. No connected or ready Bluetooth device was found."
        return self._ok({"service_status": service, "devices": devices, "ok_devices": ok_devices}, msg)

    def _network_status(self, include_wifi: bool = True, include_bluetooth: bool = True) -> dict:
        results = {}
        messages = []
        if include_wifi:
            wifi = self._wifi_status()
            results["wifi"] = wifi
            messages.append(wifi.get("message", "Wi-Fi status unavailable."))
        if include_bluetooth:
            bluetooth = self._bluetooth_status()
            results["bluetooth"] = bluetooth
            messages.append(bluetooth.get("message", "Bluetooth status unavailable."))
        return self._ok(results, " ".join(messages))

    def _search_roots(self, scope: str = "user") -> list[Path]:
        home = Path.home()
        names = ["Desktop", "Downloads", "Documents", "Pictures", "Videos", "Music"]
        roots = [home / name for name in names if (home / name).exists()]
        if not roots and home.exists():
            roots = [home]
        if scope == "pc":
            system_drive = Path(os.environ.get("SystemDrive", "C:") + "\\")
            if system_drive.exists():
                roots.append(system_drive)
        unique = []
        for root in roots:
            if root not in unique:
                unique.append(root)
        return unique

    def _search_files(self, query: str, scope: str = "user", max_results: int = 10, timeout_seconds: int = 18) -> dict:
        if err := self._require_desktop():
            return err
        needle = re.sub(r"\s+", " ", (query or "").strip().lower())
        if not needle:
            return self._err("Tell me the file name or part of the file name to search.")
        tokens = [token for token in re.split(r"\s+", needle) if token not in {"file", "folder", "document"}]
        if not tokens:
            tokens = [needle]

        matches = []
        started = time.monotonic()
        for root in self._search_roots(scope):
            if time.monotonic() - started > timeout_seconds:
                break
            try:
                walker = os.walk(root)
                for dirpath, dirnames, filenames in walker:
                    dirnames[:] = [
                        d for d in dirnames
                        if d.lower() not in self._SKIP_SEARCH_DIRS and not d.startswith(".")
                    ]
                    names = [(name, "file") for name in filenames] + [(name, "folder") for name in dirnames]
                    for name, item_type in names:
                        lower_name = name.lower()
                        if needle in lower_name or all(token in lower_name for token in tokens):
                            path = Path(dirpath) / name
                            matches.append({
                                "name": name,
                                "path": str(path),
                                "type": item_type,
                            })
                            if len(matches) >= max_results:
                                raise StopIteration
                    if time.monotonic() - started > timeout_seconds:
                        raise TimeoutError
            except (PermissionError, OSError):
                continue
            except (StopIteration, TimeoutError):
                break

        if not matches:
            return self._ok(
                {"query": query, "matches": [], "searched_roots": [str(p) for p in self._search_roots(scope)]},
                f"No matching file found for {query}.",
            )

        first = Path(matches[0]["path"])
        self._open_in_explorer(first)
        return self._ok(
            {
                "query": query,
                "matches": matches,
                "searched_roots": [str(p) for p in self._search_roots(scope)],
                "browser_action": self._browser_action(str(first)),
            },
            f"Found {len(matches)} match(es) for {query}. Opened the first file location.",
        )

    def _running_apps(self, limit: int = 12) -> dict:
        if err := self._require_desktop():
            return err
        try:
            import psutil
        except Exception as exc:
            return self._err(f"Running app monitor needs psutil. Details: {exc}")

        rows = []
        current_pid = os.getpid()
        for proc in psutil.process_iter(["pid", "name", "memory_info", "username"]):
            try:
                name = proc.info.get("name") or ""
                pid = int(proc.info.get("pid") or 0)
                if not name or pid == current_pid or name.lower() in self._PROTECTED_PROCESS_NAMES:
                    continue
                memory = proc.info.get("memory_info").rss if proc.info.get("memory_info") else 0
                if memory <= 20 * 1024 * 1024 and name.lower() not in self._CLOSE_ALL_PROCESS_NAMES:
                    continue
                rows.append({
                    "pid": pid,
                    "name": name,
                    "memory_mb": round(memory / (1024 * 1024), 1),
                    "username": proc.info.get("username") or "",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                continue
        rows.sort(key=lambda item: item["memory_mb"], reverse=True)
        rows = rows[:max(1, min(30, int(limit or 12)))]
        if not rows:
            return self._ok({"background_apps": []}, "No major background apps found.")
        names = ", ".join(f"{item['name']} {item['memory_mb']} MB" for item in rows[:5])
        return self._ok({"background_apps": rows}, f"Top background apps: {names}.")

    def run(
        self,
        action: str = "status",
        target: str = "",
        percent: int | None = None,
        delay: int = 30,
        query: str = "",
        scope: str = "user",
        include_wifi: bool = True,
        include_bluetooth: bool = True,
        limit: int = 12,
    ) -> dict:
        try:
            action_key = (action or "status").lower().strip()
            if action_key == "close_all":
                return self._close_all_apps()
            if action_key in {"shutdown", "restart", "cancel_shutdown"}:
                return self._power(action_key, delay=delay)
            if action_key == "screenshot":
                return self._screenshot()
            if action_key in {"volume", "full", "mute", "unmute", "volume_status"}:
                return self._volume(percent=percent, action=action_key)
            if action_key == "wifi_status":
                return self._wifi_status()
            if action_key == "bluetooth_status":
                return self._bluetooth_status()
            if action_key == "network_status":
                return self._network_status(include_wifi=include_wifi, include_bluetooth=include_bluetooth)
            if action_key == "search_files":
                return self._search_files(query=query or target, scope=scope)
            if action_key == "running_apps":
                return self._running_apps(limit=limit)
            return self._err(f"Unsupported desktop system action: {action}")
        except Exception as exc:
            return self._err(str(exc))


class FileSystemTool(MCPTool):
    """
    Perform file / folder operations.

    kwargs:
      action      : "list" | "read" | "write" | "delete" | "create_folder" | "exists"
      path        : target path (str)
      content     : text content for "write" action
      max_lines   : int, max lines to return for "read" (default 100)
    """
    name = "filesystem"
    description = "List, read, write, delete files and folders on the local system."

    def run(self, action: str = "list", path: str = ".", content: str = "",
            max_lines: int = 100) -> dict:
        p = Path(path)

        if action == "list":
            if not p.exists():
                return self._err(f"Path not found: {path}")
            items = []
            for item in sorted(p.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                    "size_bytes": item.stat().st_size if item.is_file() else None,
                    "modified": datetime.datetime.fromtimestamp(
                        item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            return self._ok({"path": str(p), "items": items},
                            f"Listed {len(items)} items in {path}")

        elif action == "read":
            if not p.is_file():
                return self._err(f"Not a file: {path}")
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                snippet = lines[:max_lines]
                return self._ok({
                    "path": str(p),
                    "total_lines": len(lines),
                    "content": "\n".join(snippet),
                    "truncated": len(lines) > max_lines
                }, f"Read {p.name}")
            except Exception as exc:
                return self._err(str(exc))

        elif action == "write":
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return self._ok({"path": str(p)}, f"Written to {p.name}")
            except Exception as exc:
                return self._err(str(exc))

        elif action == "delete":
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                return self._ok({"path": str(p)}, f"Deleted {p.name}")
            except Exception as exc:
                return self._err(str(exc))

        elif action == "create_folder":
            try:
                p.mkdir(parents=True, exist_ok=True)
                return self._ok({"path": str(p)}, f"Folder created: {path}")
            except Exception as exc:
                return self._err(str(exc))

        elif action == "exists":
            return self._ok({"path": str(p), "exists": p.exists(),
                             "type": "folder" if p.is_dir() else "file" if p.is_file() else "none"})

        return self._err(f"Unknown action: {action}")


# ---------------------------------------------------------------------------
# 3. Weather Tool  (Open-Meteo — completely free, no API key)
# ---------------------------------------------------------------------------

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icing fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm",
}


class WeatherTool(MCPTool):
    """
    Real-time weather + 7-day forecast for any city using Open-Meteo (free, no key).

    kwargs:
      city        : city name (str), default "Chennai"
      forecast    : True to include 7-day daily forecast
    """
    name = "weather"
    description = "Get current weather and smart rain/heat advice for any city. No API key required."

    @staticmethod
    def _parse_time(value: str) -> datetime.datetime | None:
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception:
            return None

    @staticmethod
    def _format_time(value: str) -> str:
        parsed = WeatherTool._parse_time(value)
        if not parsed:
            return value or "soon"
        return parsed.strftime("%I %p").lstrip("0")

    @staticmethod
    def _day_period(hour: int) -> str:
        if 5 <= hour < 12:
            return "morning"
        if 12 <= hour < 17:
            return "afternoon"
        if 17 <= hour < 21:
            return "evening"
        return "night"

    @staticmethod
    def _rain_intensity(weather_code: int, rain_mm: float, rain_prob: int | None) -> str:
        rain_mm = float(rain_mm or 0)
        rain_prob = int(rain_prob or 0)
        if weather_code in {65, 82, 95, 96, 99} or rain_mm >= 7 or rain_prob >= 80:
            return "heavy"
        if weather_code in {53, 55, 63, 81} or rain_mm >= 2 or rain_prob >= 60:
            return "moderate"
        return "light"

    @staticmethod
    def _stronger_intensity(left: str, right: str) -> str:
        rank = {"none": 0, "light": 1, "moderate": 2, "heavy": 3}
        return right if rank.get(right, 0) > rank.get(left, 0) else left

    @staticmethod
    def _is_rain_hour(weather_code: int, rain_mm: float, rain_prob: int | None) -> bool:
        rain_codes = set(range(51, 68)) | set(range(80, 83)) | {95, 96, 99}
        return float(rain_mm or 0) > 0 or int(rain_prob or 0) >= 40 or weather_code in rain_codes

    @staticmethod
    def _safe_hourly(hourly: dict, key: str, index: int, default=None):
        values = hourly.get(key) or []
        if 0 <= index < len(values):
            return values[index]
        return default

    def _current_hour_index(self, hourly: dict, current_time: str) -> int:
        times = hourly.get("time") or []
        if not times:
            return 0
        if current_time in times:
            return times.index(current_time)
        current_dt = self._parse_time(current_time) or datetime.datetime.now()
        best_index = 0
        best_delta = None
        for index, value in enumerate(times):
            parsed = self._parse_time(value)
            if not parsed:
                continue
            delta = abs((parsed - current_dt).total_seconds())
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_index = index
        return best_index

    def run(self, city: str = "Chennai", forecast: bool = False,
            rain_alert_hours: int = 24, target_date: str = "",
            timeframe: str = "today", forecast_days: int = 16) -> dict:
        # Step 1 – geocode
        try:
            geo = requests.get(_GEOCODE_URL, params={"name": city, "count": 1},
                               timeout=8).json()
            if not geo.get("results"):
                return self._err(f"City not found: {city}")
            loc = geo["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]
            display_name = f"{loc['name']}, {loc.get('country', '')}"
        except Exception as exc:
            return self._err(f"Geocoding failed: {exc}")

        # Step 2 – fetch weather
        params = {
            "latitude": lat, "longitude": lon,
            "current_weather": True,
            "hourly": (
                "temperature_2m,relativehumidity_2m,apparent_temperature,"
                "precipitation,precipitation_probability,weathercode,windspeed_10m"
            ),
            "timezone": "auto",
        }
        needs_daily = bool(forecast or target_date or timeframe not in {"", "today", "now", "current"})
        if needs_daily:
            params["forecast_days"] = max(1, min(int(forecast_days or 16), 16))
            params["daily"] = (
                "weathercode,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max,windspeed_10m_max"
            )

        try:
            raw = requests.get(_WEATHER_URL, params=params, timeout=10).json()
        except Exception as exc:
            return self._err(f"Weather fetch failed: {exc}")

        cw = raw.get("current_weather", {})
        hourly = raw.get("hourly", {})
        current_index = self._current_hour_index(hourly, cw.get("time", ""))
        current_code = cw.get("weathercode", self._safe_hourly(hourly, "weathercode", current_index, -1))
        current_temp = cw.get("temperature", self._safe_hourly(hourly, "temperature_2m", current_index))
        current_wind = cw.get("windspeed", self._safe_hourly(hourly, "windspeed_10m", current_index))
        current_prob = self._safe_hourly(hourly, "precipitation_probability", current_index)
        current_rain = self._safe_hourly(hourly, "precipitation", current_index, 0)
        current_humidity = self._safe_hourly(hourly, "relativehumidity_2m", current_index)
        feels_like = self._safe_hourly(hourly, "apparent_temperature", current_index)

        result: dict = {
            "city": display_name,
            "temperature_c": current_temp,
            "windspeed_kmh": current_wind,
            "condition": _WMO_CODES.get(current_code, "Unknown"),
            "is_day": bool(cw.get("is_day", 1)),
            "time": cw.get("time", ""),
            "updated_at": datetime.datetime.now().astimezone().isoformat(),
            "source": "Open-Meteo",
            "latitude": lat,
            "longitude": lon,
            "rain_probability_pct": current_prob,
            "precipitation_mm": current_rain,
        }

        if current_humidity is not None:
            result["humidity_pct"] = current_humidity
        if feels_like is not None:
            result["feels_like_c"] = feels_like

        try:
            upcoming = []
            limit = max(1, min(int(rain_alert_hours), 24))
            times = hourly.get("time", [])
            current_dt = (
                self._parse_time(cw.get("time", ""))
                or self._parse_time(times[current_index] if times else "")
                or datetime.datetime.now()
            )
            today_date = current_dt.date()
            period_map: dict[str, dict] = {}

            for i in range(current_index, min(current_index + limit, len(times))):
                time_value = times[i]
                parsed_time = self._parse_time(time_value)
                weather_code = self._safe_hourly(hourly, "weathercode", i, -1)
                rain_mm = self._safe_hourly(hourly, "precipitation", i, 0) or 0
                rain_prob = self._safe_hourly(hourly, "precipitation_probability", i)
                if not self._is_rain_hour(weather_code, rain_mm, rain_prob):
                    continue

                intensity = self._rain_intensity(weather_code, rain_mm, rain_prob)
                rain_item = {
                    "time": time_value,
                    "time_label": self._format_time(time_value),
                    "period": self._day_period(parsed_time.hour) if parsed_time else "upcoming",
                    "condition": _WMO_CODES.get(weather_code, "Unknown"),
                    "rain_mm": rain_mm,
                    "rain_probability_pct": rain_prob,
                    "intensity": intensity,
                }
                upcoming.append(rain_item)

                if parsed_time and parsed_time.date() == today_date:
                    period = rain_item["period"]
                    existing = period_map.setdefault(period, {
                        "period": period,
                        "first_time": time_value,
                        "first_time_label": rain_item["time_label"],
                        "condition": rain_item["condition"],
                        "max_probability_pct": rain_prob or 0,
                        "total_rain_mm": 0,
                        "intensity": "none",
                    })
                    existing["max_probability_pct"] = max(existing["max_probability_pct"], rain_prob or 0)
                    existing["total_rain_mm"] = round(existing["total_rain_mm"] + float(rain_mm or 0), 2)
                    existing["intensity"] = self._stronger_intensity(existing["intensity"], intensity)
                    if existing["intensity"] == intensity:
                        existing["condition"] = rain_item["condition"]

            result["upcoming_rain"] = upcoming
            result["rain_expected"] = bool(upcoming)
            result["rain_alert_hours"] = limit
            result["rain_periods_today"] = list(period_map.values())
        except Exception:
            result["upcoming_rain"] = []
            result["rain_expected"] = False
            result["rain_periods_today"] = []
            result["rain_alert_hours"] = max(1, min(int(rain_alert_hours or 24), 24))

        advice = []
        alert_level = "normal"
        rain_summary = "No rain is expected in the next checked hours."
        travel_advice = "Weather looks manageable for travel."
        suggested_reminder = None

        if result.get("rain_expected") and result.get("upcoming_rain"):
            first = result["upcoming_rain"][0]
            intensity = first.get("intensity", "light")
            when = first.get("time_label", "soon")
            period = first.get("period", "today")
            prob = first.get("rain_probability_pct")
            probability_text = f" with {prob}% chance" if prob is not None else ""
            rain_summary = f"{intensity.title()} rain is possible this {period} around {when}{probability_text}."
            if intensity == "heavy":
                alert_level = "warning"
                travel_advice = "Carry an umbrella or raincoat and avoid travel during the heavy rain window if possible."
            elif intensity == "moderate":
                alert_level = "watch"
                travel_advice = "Carry an umbrella before going out and keep extra travel time."
            else:
                alert_level = "info"
                travel_advice = "Light rain is possible, so carry an umbrella if you go out and travel carefully."
            advice.extend([rain_summary, travel_advice])

            rain_time = self._parse_time(first.get("time", ""))
            if rain_time:
                reminder_due = rain_time - datetime.timedelta(minutes=30)
                now_local = self._parse_time(cw.get("time", "")) or datetime.datetime.now()
                if reminder_due <= now_local:
                    reminder_due = now_local + datetime.timedelta(minutes=1)
                suggested_reminder = {
                    "text": f"{intensity.title()} rain possible around {when}. {travel_advice}",
                    "due_at": reminder_due.isoformat(),
                    "weather_time": first.get("time", ""),
                }

        heat_value = result.get("feels_like_c")
        if heat_value is None:
            heat_value = result.get("temperature_c")
        try:
            heat_value = float(heat_value)
            if heat_value >= 40:
                alert_level = "warning" if alert_level == "normal" else alert_level
                heat_text = f"It feels very hot at about {heat_value:g} C. Drink water and avoid long outdoor travel."
                advice.append(heat_text)
                result["heat_alert"] = True
                result["heat_summary"] = heat_text
            elif heat_value >= 36:
                heat_text = f"It feels hot at about {heat_value:g} C. Stay hydrated if you go out."
                advice.append(heat_text)
                result["heat_alert"] = True
                result["heat_summary"] = heat_text
            else:
                result["heat_alert"] = False
        except Exception:
            result["heat_alert"] = False

        if not advice and current_code in {0, 1}:
            advice.append("The weather is mostly clear right now.")

        result["rain_summary"] = rain_summary
        result["travel_advice"] = travel_advice
        result["smart_advice"] = advice
        result["alert_level"] = alert_level
        if suggested_reminder:
            result["suggested_reminder"] = suggested_reminder
        result["summary"] = (
            f"{display_name}: {result.get('temperature_c')} C, "
            f"{result.get('condition', 'Unknown')}. "
            f"{rain_summary if result.get('rain_expected') else travel_advice}"
        )

        if needs_daily and "daily" in raw:
            d = raw["daily"]
            result["forecast_7day"] = [
                {
                    "date": d["time"][i],
                    "condition": _WMO_CODES.get(d["weathercode"][i], "Unknown"),
                    "max_c": d["temperature_2m_max"][i],
                    "min_c": d["temperature_2m_min"][i],
                    "rain_mm": d["precipitation_sum"][i],
                    "rain_probability_pct": (d.get("precipitation_probability_max") or [None])[i],
                    "wind_kmh": d["windspeed_10m_max"][i],
                }
                for i in range(len(d["time"]))
            ]

            target_day = target_date
            if not target_day and timeframe in {"tomorrow", "day_after_tomorrow", "after_week"}:
                offset = {"tomorrow": 1, "day_after_tomorrow": 2, "after_week": 7}[timeframe]
                target_day = (datetime.datetime.now().astimezone().date() + datetime.timedelta(days=offset)).isoformat()

            if target_day:
                for day in result["forecast_7day"]:
                    if day.get("date") != target_day:
                        continue

                    target_periods = []
                    for item in result.get("upcoming_rain", []):
                        parsed = self._parse_time(item.get("time", ""))
                        if parsed and parsed.date().isoformat() == target_day:
                            target_periods.append(item)

                    rain_prob = day.get("rain_probability_pct")
                    rain_mm = float(day.get("rain_mm") or 0)
                    target_rain = bool(target_periods or rain_mm > 0 or int(rain_prob or 0) >= 40)
                    intensity = "none"
                    if target_rain:
                        intensity = self._rain_intensity(
                            61 if rain_mm > 0 else 0,
                            rain_mm,
                            rain_prob,
                        )
                        for item in target_periods:
                            intensity = self._stronger_intensity(intensity, item.get("intensity", "light"))

                    day_label = datetime.date.fromisoformat(target_day).strftime("%A, %d %b")
                    target_summary = (
                        f"Forecast for {display_name} on {day_label}: "
                        f"{day.get('condition')}, max {day.get('max_c')} C, min {day.get('min_c')} C, "
                        f"rain chance {rain_prob if rain_prob is not None else 'unknown'}%, "
                        f"expected rain {rain_mm:g} mm."
                    )
                    target_advice = "Weather looks manageable for travel."
                    if target_rain:
                        if intensity == "heavy":
                            target_advice = "Carry an umbrella or raincoat and avoid travel during heavy rain if possible."
                        elif intensity == "moderate":
                            target_advice = "Carry an umbrella and keep extra travel time."
                        else:
                            target_advice = "Light rain is possible, so carry an umbrella if you go out."
                    elif float(day.get("max_c") or 0) >= 36:
                        target_advice = "It may be hot, so stay hydrated and avoid long outdoor travel."

                    result["target_forecast"] = {
                        **day,
                        "label": day_label,
                        "rain_expected": target_rain,
                        "rain_intensity": intensity,
                        "rain_periods": target_periods,
                        "advice": target_advice,
                    }
                    result["summary"] = f"{target_summary} {target_advice}"
                    result["smart_advice"] = [target_advice]
                    result["rain_expected"] = target_rain
                    result["rain_summary"] = target_summary
                    result["travel_advice"] = target_advice
                    result["target_date"] = target_day
                    result["target_label"] = day_label
                    break

            if timeframe in {"week", "next_week"} and result.get("forecast_7day"):
                days = result["forecast_7day"][:7]
                wet_days = [day for day in days if float(day.get("rain_mm") or 0) > 0 or int(day.get("rain_probability_pct") or 0) >= 40]
                hottest = max(days, key=lambda day: float(day.get("max_c") or 0))
                weekly_advice = (
                    "Keep an umbrella available this week."
                    if wet_days else "No major rain signal in the 7 day forecast."
                )
                if float(hottest.get("max_c") or 0) >= 36:
                    weekly_advice += " Some days look hot, so stay hydrated for outdoor travel."
                result["weekly_summary"] = {
                    "days_checked": len(days),
                    "rainy_days": len(wet_days),
                    "hottest_day": hottest,
                }
                result["summary"] = (
                    f"7 day forecast for {display_name}: {len(wet_days)} rainy day(s) possible. "
                    f"Hottest day may be {hottest.get('date')} with {hottest.get('max_c')} C. "
                    f"{weekly_advice}"
                )
                result["smart_advice"] = [weekly_advice]

        return self._ok(result, f"Weather for {display_name}")


# ---------------------------------------------------------------------------
# 4. News Tool  (Google News RSS + optional GNews API)
# ---------------------------------------------------------------------------

_GNEWS_URL = "https://gnews.io/api/v4/top-headlines"
_GOOGLE_NEWS_RSS = "https://news.google.com/rss"
_GOOGLE_NEWS_SEARCH_RSS = "https://news.google.com/rss/search"
_RSS_FEEDS = {
    "general":     "https://feeds.bbci.co.uk/news/rss.xml",
    "technology":  "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "sports":      "https://feeds.bbci.co.uk/sport/rss.xml",
    "science":     "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "health":      "https://feeds.bbci.co.uk/news/health/rss.xml",
    "business":    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "india":       "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
}
_NEWS_CATEGORY_QUERIES = {
    "general": "",
    "india": "India",
    "indian": "India",
    "tamilnadu": "Tamil Nadu",
    "tamil nadu": "Tamil Nadu",
    "trichy": "Trichy Tamil Nadu",
    "tiruchirappalli": "Tiruchirappalli Tamil Nadu",
    "global": "world international",
    "world": "world international",
    "politics": "politics India",
    "political": "politics India",
    "finance": "finance business markets India",
    "financial": "finance business markets India",
    "business": "business India",
    "weather": "weather India",
    "technology": "technology India",
    "tech": "technology India",
    "sports": "sports India",
    "science": "science",
    "health": "health India",
}
_GNEWS_SUPPORTED_TOPICS = {
    "general", "world", "nation", "business", "technology",
    "entertainment", "sports", "science", "health",
}


class NewsTool(MCPTool):
    """
    Fetch top news headlines.
    Uses Google News RSS for dynamic topics/locations, with optional GNews API
    for supported top-level categories.

    kwargs:
      category : "general" | "technology" | "sports" | "science" | "health"
                 | "business" | "india" | "tamilnadu" | "trichy"
      query    : optional keyword search string
      count    : number of articles to return (default 5)
      fresh_hours : maximum article age in hours (default 48)
      api_key  : GNews API key (overrides env var)
    """
    name = "news"
    description = "Fetch real-time top news headlines by category or keyword."

    def run(self, category: str = "general", query: str = "",
            count: int = 5, api_key: str = "", fresh_hours: int = 48) -> dict:
        try:
            count = max(1, min(int(count or 5), 100))
        except Exception:
            count = 5
        try:
            fresh_hours = max(1, min(int(fresh_hours or 48), 168))
        except Exception:
            fresh_hours = 48

        category = (category or "general").lower().strip()
        query = (query or "").strip()

        key = (
            api_key
            or os.environ.get("GNEWS_API_KEY", "")
            or app_settings.GNEWS_API_KEY
        )

        if key and not query and category in _GNEWS_SUPPORTED_TOPICS and count <= 10:
            return self._gnews(key, category, query, count, fresh_hours)
        return self._google_news_rss(
            category=category,
            query=query,
            count=count,
            fresh_hours=fresh_hours,
        )

    # --- GNews ---
    def _gnews(self, key: str, category: str, query: str, count: int, fresh_hours: int) -> dict:
        params = {
            "token": key, "lang": "en", "max": count,
            "topic": category if not query else None,
            "q": query or None,
        }
        params = {k: v for k, v in params.items() if v is not None}
        try:
            resp = requests.get(_GNEWS_URL, params=params, timeout=10).json()
            articles = []
            for a in resp.get("articles", []):
                published = a.get("publishedAt", "")
                if not self._is_fresh_news(published, fresh_hours):
                    continue
                articles.append({
                    "title":       a["title"],
                    "description": a.get("description", ""),
                    "source":      a["source"]["name"],
                    "url":         a["url"],
                    "published":   published,
                    "fresh_hours": fresh_hours,
                })
            return self._ok({"category": category, "query": query, "fresh_hours": fresh_hours, "articles": articles},
                            f"Fetched {len(articles)} articles")
        except Exception as exc:
            return self._err(f"GNews error: {exc}")

    def _google_news_rss(self, category: str, query: str, count: int, fresh_hours: int) -> dict:
        from xml.etree import ElementTree as ET

        search_query = query or _NEWS_CATEGORY_QUERIES.get(category, category)
        params = {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        url = _GOOGLE_NEWS_RSS
        if search_query:
            url = _GOOGLE_NEWS_SEARCH_RSS
            params["q"] = self._with_recency_query(search_query, fresh_hours)

        try:
            resp = requests.get(
                url,
                params=params,
                timeout=12,
                headers={"User-Agent": "CubyAI/1.0"},
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            articles = []
            for item in items:
                source = item.findtext("source") or "Google News"
                published = (item.findtext("pubDate") or "").strip()
                if not self._is_fresh_news(published, fresh_hours):
                    continue
                articles.append({
                    "title":       (item.findtext("title") or "").strip(),
                    "description": (item.findtext("description") or "").strip(),
                    "source":      source.strip(),
                    "url":         (item.findtext("link") or "").strip(),
                    "published":   published,
                    "fresh_hours": fresh_hours,
                })
                if len(articles) >= count:
                    break
            return self._ok(
                {
                    "category": category,
                    "query": search_query,
                    "count_requested": count,
                    "fresh_hours": fresh_hours,
                    "articles": articles,
                },
                f"Fetched {len(articles)} current news article(s)"
            )
        except Exception as exc:
            fallback = self._rss_fallback(category, count, fresh_hours)
            if fallback.get("status") == "ok" and (fallback.get("data") or {}).get("articles"):
                return fallback
            return self._err(f"Google News RSS error: {exc}")

    # --- BBC RSS fallback (no key needed) ---
    def _rss_fallback(self, category: str, count: int, fresh_hours: int) -> dict:
        from xml.etree import ElementTree as ET
        if category not in _RSS_FEEDS:
            return self._ok(
                {"category": category, "query": "", "fresh_hours": fresh_hours, "articles": []},
                "No fallback feed for this local or custom topic."
            )
        feed_url = _RSS_FEEDS.get(category, _RSS_FEEDS["general"])
        try:
            resp = requests.get(feed_url, timeout=10,
                                headers={"User-Agent": "CubyAI/1.0"})
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            articles = []
            for item in items:
                published = (item.findtext("pubDate") or "").strip()
                if not self._is_fresh_news(published, fresh_hours):
                    continue
                articles.append({
                    "title":       (item.findtext("title") or "").strip(),
                    "description": (item.findtext("description") or "").strip(),
                    "source":      "BBC News",
                    "url":         (item.findtext("link") or "").strip(),
                    "published":   published,
                    "fresh_hours": fresh_hours,
                })
                if len(articles) >= count:
                    break
            return self._ok({"category": category, "query": "", "fresh_hours": fresh_hours, "articles": articles},
                            f"Fetched {len(articles)} current articles (RSS)")
        except Exception as exc:
            return self._err(f"RSS fetch error: {exc}")

    @staticmethod
    def _with_recency_query(search_query: str, fresh_hours: int) -> str:
        query = (search_query or "").strip()
        if re.search(r"\bwhen:\d+[hd]\b", query, flags=re.IGNORECASE):
            return query
        if fresh_hours <= 24:
            return f"{query} when:1d".strip()
        days = max(1, min(7, (fresh_hours + 23) // 24))
        return f"{query} when:{days}d".strip()

    @staticmethod
    def _parse_news_datetime(value: str) -> datetime.datetime | None:
        value = (value or "").strip()
        if not value:
            return None
        try:
            if re.match(r"^\d{4}-\d{2}-\d{2}T", value):
                if value.endswith("Z"):
                    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
                else:
                    parsed = datetime.datetime.fromisoformat(value)
            elif value.endswith("Z"):
                parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            return parsed.astimezone(datetime.timezone.utc)
        except Exception:
            return None

    @classmethod
    def _is_fresh_news(cls, published: str, fresh_hours: int) -> bool:
        parsed = cls._parse_news_datetime(published)
        if parsed is None:
            return False
        now = datetime.datetime.now(datetime.timezone.utc)
        age = now - parsed
        return datetime.timedelta(0) <= age <= datetime.timedelta(hours=fresh_hours)


# ---------------------------------------------------------------------------
# 5. Flight Information Tool  (AviationStack free tier)
# ---------------------------------------------------------------------------

_AVIATIONSTACK_URL = "http://api.aviationstack.com/v1/flights"


class FlightTool(MCPTool):
    """
    Real-time flight information via AviationStack (free tier allows 100 req/month).
    Set AVIATIONSTACK_KEY environment variable or pass api_key kwarg.

    kwargs:
      flight_iata : flight code e.g. "AI101"
      dep_iata    : departure airport IATA e.g. "MAA"
      arr_iata    : arrival airport IATA e.g. "DEL"
      airline_name: e.g. "IndiGo"
      count       : max results (default 5)
      api_key     : override env var AVIATIONSTACK_KEY
    """
    name = "flight_info"
    description = (
        "Real-time flight status, schedules, delays for any flight number or route."
    )

    def run(self, flight_iata: str = "", dep_iata: str = "", arr_iata: str = "",
            airline_name: str = "", count: int = 5, api_key: str = "") -> dict:

        key = (
            api_key
            or os.environ.get("AVIATIONSTACK_KEY", "")
            or app_settings.AVIATIONSTACK_KEY
        )
        if not key:
            return self._err(
                "No AviationStack API key found. "
                "Set AVIATIONSTACK_KEY env var or pass api_key=... "
                "Get a free key at https://aviationstack.com/signup/free"
            )

        params: dict = {"access_key": key, "limit": count}
        if flight_iata:
            params["flight_iata"] = flight_iata.upper()
        if dep_iata:
            params["dep_iata"] = dep_iata.upper()
        if arr_iata:
            params["arr_iata"] = arr_iata.upper()
        if airline_name:
            params["airline_name"] = airline_name

        try:
            resp = requests.get(_AVIATIONSTACK_URL, params=params, timeout=12)
            raw = resp.json()
        except Exception as exc:
            return self._err(f"Flight API request failed: {exc}")

        if "error" in raw:
            return self._err(raw["error"].get("info", "AviationStack error"))

        flights = []
        for f in raw.get("data", []):
            dep = f.get("departure", {})
            arr = f.get("arrival", {})
            flights.append({
                "flight":        f.get("flight", {}).get("iata", "N/A"),
                "airline":       f.get("airline", {}).get("name", "N/A"),
                "status":        f.get("flight_status", "unknown"),
                "departure": {
                    "airport":   dep.get("airport", "N/A"),
                    "iata":      dep.get("iata", ""),
                    "scheduled": dep.get("scheduled", ""),
                    "estimated": dep.get("estimated", ""),
                    "actual":    dep.get("actual", ""),
                    "delay_min": dep.get("delay"),
                    "terminal":  dep.get("terminal", ""),
                    "gate":      dep.get("gate", ""),
                },
                "arrival": {
                    "airport":   arr.get("airport", "N/A"),
                    "iata":      arr.get("iata", ""),
                    "scheduled": arr.get("scheduled", ""),
                    "estimated": arr.get("estimated", ""),
                    "actual":    arr.get("actual", ""),
                    "delay_min": arr.get("delay"),
                    "terminal":  arr.get("terminal", ""),
                    "gate":      arr.get("gate", ""),
                },
                "aircraft":      f.get("aircraft", {}).get("iata", ""),
                "live": {
                    "altitude_m":  (f.get("live") or {}).get("altitude"),
                    "speed_kmh":   (f.get("live") or {}).get("speed_horizontal"),
                    "is_ground":   (f.get("live") or {}).get("is_ground"),
                } if f.get("live") else None,
            })

        return self._ok(
            {"query": params, "count": len(flights), "flights": flights},
            f"Found {len(flights)} flight(s)"
        )


# ---------------------------------------------------------------------------
# MCP Registry — single access point
# ---------------------------------------------------------------------------

class TrainTool(MCPTool):
    """
    Open official Indian Railways / IRCTC train pages.
    """

    name = "train"
    description = "Open official train availability, PNR, running status, and booking pages."

    def run(self, action: str = "availability", from_station: str = "",
            to_station: str = "", date: str = "", train_no: str = "",
            pnr: str = "") -> dict:
        action = (action or "availability").lower().strip()
        urls = {
            "availability": "https://www.indianrail.gov.in/enquiry/SEAT/SeatAvailability.html?locale=en",
            "book": "https://www.irctc.co.in/nget/train-search",
            "pnr": "https://www.indianrail.gov.in/enquiry/PNR/PnrEnquiry.html?locale=en",
            "status": "https://enquiry.indianrail.gov.in/mntes/",
        }
        if action not in urls:
            action = "availability"

        url = urls[action]
        webbrowser.open(url)

        details = {
            "action": action,
            "url": url,
            "from_station": from_station,
            "to_station": to_station,
            "date": date,
            "train_no": train_no,
            "pnr": pnr,
        }

        route = ""
        if from_station or to_station:
            route = f" from {from_station or '?'} to {to_station or '?'}"
        if date:
            route += f" on {date}"

        if action == "book":
            message = f"Opened official IRCTC booking page{route}. Please login and confirm payment manually."
        elif action == "pnr":
            message = f"Opened official PNR enquiry page{f' for {pnr}' if pnr else ''}."
        elif action == "status":
            message = f"Opened official train running status page{f' for {train_no}' if train_no else ''}."
        else:
            message = f"Opened official train seat availability page{route}."

        return self._ok(details, message)


class UtilityAlertTool(MCPTool):
    """
    Check planned power cuts and water-supply interruptions for a local area.

    The official TNPDCL planned outage page is captcha protected, so this tool
    checks it and reports the limitation, then combines Trichy Corporation /
    TN Urban Tree / district pages with a Google News RSS fallback.
    """

    name = "utility_alerts"
    description = (
        "Check power-cut and water-supply cut alerts for Ponnagar, "
        "Karumandapam, Trichy from official pages and public RSS fallback."
    )

    _POWER_OFFICIAL_URL = "https://www.tnebltd.gov.in/outages/viewshutdown.xhtml"
    _DEFAULT_LOCATION = "Ponnagar, Karumandapam, Trichy"
    _HEADERS = {"User-Agent": "CubyAI/1.0 (local assistant)"}
    _REQUEST_TIMEOUT = 6

    _OFFICIAL_SOURCES = [
        {
            "name": "TNPDCL Planned Power Outage Details",
            "url": _POWER_OFFICIAL_URL,
            "kind": "power",
            "official": True,
        },
        {
            "name": "Trichy Corporation Home",
            "url": "https://www.trichycorporation.gov.in/",
            "kind": "all",
            "official": True,
        },
        {
            "name": "Trichy Corporation Engineering",
            "url": "https://www.trichycorporation.gov.in/enggdept",
            "kind": "water",
            "official": True,
        },
        {
            "name": "TN Urban Tree Trichy Water Supply",
            "url": "https://www.tnurbantree.tn.gov.in/trichy/en/water-supply/",
            "kind": "water",
            "official": True,
        },
        {
            "name": "Tiruchirappalli District Announcements",
            "url": "https://tiruchirappalli.nic.in/notice_category/announcements/",
            "kind": "all",
            "official": True,
        },
    ]

    _POWER_TERMS = (
        "power", "electric", "electricity", "tnpdcl", "tangedco", "tneb",
        "eb", "substation", "powercut", "power cut",
    )
    _WATER_TERMS = (
        "water", "drinking water", "water supply", "twad", "pump",
        "pumping", "reservoir", "overhead tank", "oht",
    )
    _OUTAGE_TERMS = (
        "cut", "shutdown", "shut down", "outage", "suspended", "suspension",
        "interruption", "interrupted", "disrupted", "disruption",
        "maintenance", "will not receive", "will not get", "won't get",
        "not receive", "no supply", "stopped", "hit tomorrow", "affected",
    )
    _STRONG_OUTAGE_TERMS = (
        "cut", "shutdown", "shut down", "outage", "suspended", "suspension",
        "interruption", "interrupted", "disrupted", "disruption",
        "will not receive", "will not get", "won't get", "not receive",
        "no supply", "stopped", "hit tomorrow",
    )
    _DATE_TERMS = (
        "today", "tomorrow", "tonight", "monday", "tuesday", "wednesday",
        "thursday", "friday", "saturday", "sunday", "am", "pm", "2026",
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
        "oct", "nov", "dec",
    )

    def run(
        self,
        action: str = "check",
        kind: str = "all",
        location: str = "",
        area: str = "",
        city: str = "Trichy",
        days: int = 7,
        query: str = "",
        max_results: int = 6,
        official_wait_seconds: int = 150,
    ) -> dict:
        action = (action or "check").lower().strip()
        kind = self._normalize_kind(kind)
        location = (area or location or getattr(app_settings, "UTILITY_ALERT_LOCATION", "") or self._DEFAULT_LOCATION).strip()
        city = (city or "Trichy").strip()
        try:
            days = max(1, min(int(days or 7), 30))
            max_results = max(1, min(int(max_results or 6), 20))
            official_wait_seconds = max(30, min(int(official_wait_seconds or 150), 300))
        except Exception:
            days = 7
            max_results = 6
            official_wait_seconds = 150

        aliases = self._area_aliases(location, city)
        if action in {"confirm_power", "official_power", "tnpdcl", "official"}:
            return self._run_tnpdcl_confirmation(
                location=location,
                city=city,
                aliases=aliases,
                wait_seconds=official_wait_seconds,
                max_results=max_results,
            )

        checked_at = datetime.datetime.now().astimezone().isoformat()
        source_status: list[dict] = []
        alerts: list[dict] = []

        sources = self._sources_for_kind(kind)
        with ThreadPoolExecutor(max_workers=max(1, min(6, len(sources)))) as executor:
            future_map = {
                executor.submit(self._fetch_source_text, source): source
                for source in sources
            }
            for future in as_completed(future_map):
                source = future_map[future]
                try:
                    text, status = future.result()
                except Exception as exc:
                    text = ""
                    status = {
                        "name": source["name"],
                        "url": source["url"],
                        "official": source.get("official", False),
                        "status": "failed",
                        "note": str(exc),
                    }
                source_status.append(status)
                if text:
                    alerts.extend(
                        self._alerts_from_text(
                            text=text,
                            source=source,
                            kind=kind,
                            aliases=aliases,
                            location=location,
                        )
                    )

        alerts.extend(
            self._alerts_from_google_news(
                kind=kind,
                location=location,
                city=city,
                aliases=aliases,
                days=days,
            )
        )
        source_status.append({
            "name": "Google News RSS fallback",
            "url": _GOOGLE_NEWS_SEARCH_RSS,
            "official": False,
            "status": "checked",
            "note": "Used only when matching official-page text is not enough.",
        })

        alerts = self._dedupe_alerts(alerts)
        alerts = sorted(
            alerts,
            key=lambda item: (
                1 if item.get("official") else 0,
                item.get("score", 0),
                item.get("confidence_rank", 0),
            ),
            reverse=True,
        )[:max_results]

        manual_links = [
            {
                "label": "TNPDCL planned power outage form",
                "url": self._POWER_OFFICIAL_URL,
                "note": "Captcha protected. Select TRICHY METRO manually for the official list.",
            },
            {
                "label": "Trichy Corporation",
                "url": "https://www.trichycorporation.gov.in/",
                "note": "Official corporation notices and civic contact details.",
            },
            {
                "label": "Trichy grievance portal",
                "url": "https://trichypublic.grievancecell.org/",
                "note": "Raise or track water and civic complaints.",
            },
        ]

        data = {
            "kind": kind,
            "location": location,
            "city": city,
            "query": query,
            "checked_at": checked_at,
            "alerts": alerts,
            "source_status": source_status,
            "manual_links": manual_links,
            "helplines": {
                "power_failure": "94987 94987",
                "trichy_corporation": "0431-2415393 / 1800-102-1994",
            },
        }

        if alerts:
            official_count = sum(1 for item in alerts if item.get("official"))
            first = alerts[0]
            source_note = (
                f"{official_count} official match(es)"
                if official_count else "public news/RSS fallback match(es)"
            )
            message = (
                f"Found {len(alerts)} possible utility alert(s) for {location} "
                f"from {source_note}. First alert: {first.get('title') or first.get('snippet', '')}"
            )
        else:
            message = (
                f"No matching official power or water cut notice found right now for {location}. "
                "I checked TNPDCL, Trichy Corporation, TN Urban Tree, district announcements, "
                "and Google News RSS. TNPDCL's official outage details form is captcha protected, "
                "so open it manually for final confirmation."
            )

        data["summary"] = message
        return self._ok(data, message)

    def _run_tnpdcl_confirmation(
        self,
        location: str,
        city: str,
        aliases: list[str],
        wait_seconds: int,
        max_results: int,
    ) -> dict:
        """
        Human-in-the-loop TNPDCL confirmation.

        CUBY may select the official circle and read the submitted page, but the
        captcha must be typed by the user in the visible browser.
        """
        checked_at = datetime.datetime.now().astimezone().isoformat()
        source = {
            "name": "TNPDCL Planned Power Outage Details - user confirmed",
            "url": self._POWER_OFFICIAL_URL,
            "kind": "power",
            "official": True,
        }
        base_data = {
            "kind": "power",
            "location": location,
            "city": city,
            "checked_at": checked_at,
            "alerts": [],
            "source_status": [{
                "name": source["name"],
                "url": source["url"],
                "official": True,
                "status": "needs_user_captcha",
                "note": "Captcha must be entered by the user. CUBY will not auto-solve it.",
            }],
            "manual_links": [{
                "label": "TNPDCL planned power outage form",
                "url": self._POWER_OFFICIAL_URL,
                "note": "Select TRICHY METRO, enter captcha, submit, then CUBY reads the page.",
            }],
            "requires_human_captcha": True,
            "automation": "playwright",
        }

        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception:
            webbrowser.open(self._POWER_OFFICIAL_URL)
            message = (
                "Opened the official TNPDCL power outage page. Playwright is not installed in this "
                "environment yet, so please select TRICHY METRO and enter the captcha manually. "
                "CUBY cannot auto-solve captcha."
            )
            base_data["summary"] = message
            base_data["source_status"][0]["status"] = "opened_without_playwright"
            base_data["source_status"][0]["note"] = "Install Playwright to let CUBY select the circle and read the submitted result."
            return self._ok(base_data, message)

        browser = None
        official_text = ""
        selected_circle = False
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(channel="chrome", headless=False)
                except Exception:
                    browser = p.chromium.launch(headless=False)

                page = browser.new_page()
                page.goto(self._POWER_OFFICIAL_URL, wait_until="domcontentloaded", timeout=30000)
                try:
                    select = page.locator("select").first
                    select.wait_for(timeout=6000)
                    try:
                        select.select_option(label="TRICHY METRO")
                    except Exception:
                        select.select_option(value="TRICHY METRO")
                    selected_circle = True
                except Exception:
                    selected_circle = False

                try:
                    page.bring_to_front()
                except Exception:
                    pass

                print(
                    "CUBY official TNPDCL check: please enter the captcha in the opened browser "
                    "and press Submit. CUBY will wait for the result page."
                )

                deadline = time.time() + wait_seconds
                while time.time() < deadline:
                    try:
                        text = page.locator("body").inner_text(timeout=2500)
                    except PlaywrightTimeoutError:
                        time.sleep(1.5)
                        continue

                    lowered = text.lower()
                    result_markers = (
                        "feeder", "substation", "area affected", "from time",
                        "to time", "reason", "no records", "maintenance work",
                    )
                    if "enter text shown in the image" not in lowered and any(marker in lowered for marker in result_markers):
                        official_text = text
                        break
                    if "no records found" in lowered:
                        official_text = text
                        break
                    time.sleep(2)

                if not official_text:
                    try:
                        official_text = page.locator("body").inner_text(timeout=3000)
                    except Exception:
                        official_text = ""

        except Exception as exc:
            webbrowser.open(self._POWER_OFFICIAL_URL)
            message = (
                f"I opened the official TNPDCL page, but Playwright could not complete the guided check: {exc}. "
                "Please enter the captcha manually. CUBY cannot auto-solve captcha."
            )
            base_data["summary"] = message
            base_data["source_status"][0]["status"] = "playwright_failed"
            base_data["source_status"][0]["note"] = str(exc)
            return self._ok(base_data, message)
        finally:
            try:
                if browser:
                    browser.close()
            except Exception:
                pass

        base_data["selected_circle"] = selected_circle
        if not official_text or "enter text shown in the image" in official_text.lower():
            message = (
                "I opened TNPDCL and selected TRICHY METRO if the page allowed it. "
                "I did not receive a submitted result before the timeout. Please type the captcha "
                "and press Submit in the official page, then ask CUBY to confirm again."
            )
            base_data["summary"] = message
            base_data["source_status"][0]["status"] = "captcha_not_completed"
            return self._ok(base_data, message)

        alerts = self._alerts_from_text(
            text=official_text,
            source=source,
            kind="power",
            aliases=aliases,
            location=location,
        )
        alerts = sorted(
            self._dedupe_alerts(alerts),
            key=lambda item: (item.get("score", 0), item.get("confidence_rank", 0)),
            reverse=True,
        )[:max_results]
        base_data["alerts"] = alerts
        base_data["official_text_excerpt"] = self._shorten(official_text, 1200)
        base_data["source_status"][0]["status"] = "confirmed_by_user_captcha"
        base_data["source_status"][0]["note"] = "User entered captcha; CUBY read the submitted TNPDCL result page."

        if alerts:
            message = (
                f"Official TNPDCL confirmation found {len(alerts)} possible power-cut alert(s) "
                f"for {location}. First alert: {alerts[0].get('title') or alerts[0].get('snippet', '')}"
            )
            try:
                NotificationTool().run(
                    title="CUBY Power Cut Alert",
                    message=message[:250],
                )
            except Exception:
                pass
        else:
            message = (
                f"Official TNPDCL confirmation completed. No matching power-cut notice was found "
                f"for {location} on the submitted TRICHY METRO result page."
            )
        base_data["summary"] = message
        return self._ok(base_data, message)

    @staticmethod
    def _normalize_kind(kind: str) -> str:
        kind = (kind or "all").lower().strip()
        if kind in {"power", "electricity", "electric", "eb", "tneb", "tnpdcl", "tangedco"}:
            return "power"
        if kind in {"water", "drinking water", "supply"}:
            return "water"
        return "all"

    def _sources_for_kind(self, kind: str) -> list[dict]:
        if kind == "all":
            return self._OFFICIAL_SOURCES
        return [
            source for source in self._OFFICIAL_SOURCES
            if source.get("kind") in {kind, "all"}
        ]

    def _fetch_source_text(self, source: dict) -> tuple[str, dict]:
        url = source["url"]
        status = {
            "name": source["name"],
            "url": url,
            "official": source.get("official", False),
            "status": "checked",
            "note": "",
        }
        try:
            resp = requests.get(url, timeout=self._REQUEST_TIMEOUT, headers=self._HEADERS)
            resp.raise_for_status()
            text = self._html_to_text(resp.text)
            if "enter text shown in the image" in text.lower() or "captcha" in text.lower():
                status["status"] = "captcha_protected"
                status["note"] = "Official form requires captcha/manual selection."
                return "", status
            return text, status
        except Exception as exc:
            status["status"] = "failed"
            status["note"] = str(exc)
            return "", status

    @staticmethod
    def _html_to_text(html: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n")
        return re.sub(r"[ \t\r\f\v]+", " ", text)

    def _alerts_from_text(
        self,
        text: str,
        source: dict,
        kind: str,
        aliases: list[str],
        location: str,
    ) -> list[dict]:
        chunks = self._chunks(text)
        alerts = []
        for chunk in chunks:
            alert_kind = self._detect_kind(chunk, fallback=kind)
            if kind != "all" and alert_kind != kind:
                continue
            score, matched_areas = self._score(chunk, alert_kind, aliases)
            if score < 36:
                continue
            confidence, rank = self._confidence(score, bool(source.get("official")), matched_areas)
            alerts.append({
                "type": alert_kind,
                "title": self._title_from_snippet(chunk, alert_kind, location),
                "snippet": self._shorten(chunk, 460),
                "source": source["name"],
                "url": source["url"],
                "official": bool(source.get("official")),
                "confidence": confidence,
                "confidence_rank": rank,
                "matched_areas": matched_areas,
                "score": score,
            })
        return alerts

    def _alerts_from_google_news(
        self,
        kind: str,
        location: str,
        city: str,
        aliases: list[str],
        days: int,
    ) -> list[dict]:
        from xml.etree import ElementTree as ET

        searches = []
        if kind in {"all", "power"}:
            searches.append(("power", f"TANGEDCO TNPDCL power shutdown {city} {location}"))
        if kind in {"all", "water"}:
            searches.append(("water", f"Trichy Corporation water supply suspended cut {location}"))

        alerts = []
        for search_kind, search_query in searches:
            params = {
                "q": f"{search_query} when:{days}d",
                "hl": "en-IN",
                "gl": "IN",
                "ceid": "IN:en",
            }
            try:
                resp = requests.get(
                    _GOOGLE_NEWS_SEARCH_RSS,
                    params=params,
                    timeout=self._REQUEST_TIMEOUT,
                    headers=self._HEADERS,
                )
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
            except Exception:
                continue

            for item in root.findall(".//item")[:12]:
                title = (item.findtext("title") or "").strip()
                description = self._html_to_text(item.findtext("description") or "").strip()
                published = (item.findtext("pubDate") or "").strip()
                if not self._is_recent_pubdate(published, days):
                    continue
                snippet = re.sub(r"\s+", " ", f"{title}. {description}").strip()
                score, matched_areas = self._score(snippet, search_kind, aliases)
                if score < 30:
                    continue
                confidence, rank = self._confidence(score, False, matched_areas)
                alerts.append({
                    "type": search_kind,
                    "title": title or self._title_from_snippet(snippet, search_kind, location),
                    "snippet": self._shorten(snippet, 420),
                    "source": (item.findtext("source") or "Google News RSS").strip(),
                    "url": (item.findtext("link") or "").strip(),
                    "published": published,
                    "official": False,
                    "confidence": confidence,
                    "confidence_rank": rank,
                    "matched_areas": matched_areas,
                    "score": score,
                })
        return alerts

    def _score(self, text: str, kind: str, aliases: list[str]) -> tuple[int, list[str]]:
        lowered = text.lower()
        utility_terms = self._POWER_TERMS if kind == "power" else self._WATER_TERMS
        utility_hits = self._term_hits(utility_terms, lowered)
        outage_hits = self._term_hits(self._OUTAGE_TERMS, lowered)
        strong_outage_hits = self._term_hits(self._STRONG_OUTAGE_TERMS, lowered)
        date_hits = self._term_hits(self._DATE_TERMS, lowered)
        city_aliases = {"trichy", "tiruchirappalli", "tiruchi"}
        matched_areas = [
            alias for alias in aliases
            if alias and alias not in city_aliases and self._has_term(alias, lowered)
        ]
        city_hit = any(self._has_term(term, lowered) for term in ("trichy", "tiruchirappalli", "tiruchi"))

        if utility_hits == 0 or outage_hits == 0:
            return 0, matched_areas
        if strong_outage_hits == 0 and not (matched_areas and date_hits):
            return 0, matched_areas

        score = 18 + utility_hits * 8 + outage_hits * 5 + strong_outage_hits * 6 + date_hits * 3
        if matched_areas:
            score += 28 + min(len(matched_areas), 4) * 4
        elif city_hit:
            score += 14
        else:
            score -= 18
        return score, matched_areas

    @staticmethod
    def _has_term(term: str, lowered_text: str) -> bool:
        term = (term or "").lower().strip()
        if not term:
            return False
        if re.search(r"[a-z0-9]", term):
            return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lowered_text))
        return term in lowered_text

    @classmethod
    def _term_hits(cls, terms: tuple[str, ...], lowered_text: str) -> int:
        return sum(1 for term in terms if cls._has_term(term, lowered_text))

    @staticmethod
    def _confidence(score: int, official: bool, matched_areas: list[str]) -> tuple[str, int]:
        if official and matched_areas and score >= 70:
            return "high", 3
        if official or (matched_areas and score >= 55):
            return "medium", 2
        return "low", 1

    def _detect_kind(self, text: str, fallback: str = "all") -> str:
        lowered = text.lower()
        power_hits = self._term_hits(self._POWER_TERMS, lowered)
        water_hits = self._term_hits(self._WATER_TERMS, lowered)
        if power_hits > water_hits:
            return "power"
        if water_hits > power_hits:
            return "water"
        return "power" if fallback == "power" else "water" if fallback == "water" else "power"

    @staticmethod
    def _area_aliases(location: str, city: str) -> list[str]:
        raw = f"{location} {city}".lower()
        aliases = {
            "ponnagar", "pon nagar", "ponnager", "pon nagar", "ponagar",
            "karumandapam", "karumandabam", "karumandapam main road",
            "junction", "trichy", "tiruchirappalli", "tiruchi",
        }
        for part in re.split(r"[,/]| and |&|\s+", raw):
            part = part.strip(" .,-")
            if len(part) >= 4:
                aliases.add(part)
        return sorted(aliases, key=len, reverse=True)

    @staticmethod
    def _chunks(text: str) -> list[str]:
        clean = re.sub(r"\s+", " ", text or "").strip()
        if not clean:
            return []
        sentences = re.split(r"(?<=[.!?])\s+|\s{2,}", clean)
        chunks = []
        current = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(current) + len(sentence) > 620:
                if current:
                    chunks.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            chunks.append(current.strip())
        if len(chunks) <= 1 and len(clean) > 620:
            chunks = [clean[i:i + 620] for i in range(0, min(len(clean), 6200), 520)]
        return chunks[:80]

    @staticmethod
    def _title_from_snippet(snippet: str, kind: str, location: str) -> str:
        label = "Power cut" if kind == "power" else "Water supply cut"
        first = re.split(r"(?<=[.!?])\s+", snippet.strip())[0]
        first = re.sub(r"\s+", " ", first).strip(" .,-")
        if first and len(first) <= 130:
            return first
        return f"{label} update for {location}"

    @staticmethod
    def _shorten(text: str, limit: int) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit].rsplit(" ", 1)[0].rstrip(" .,-") + "..."

    @staticmethod
    def _is_recent_pubdate(pubdate: str, days: int) -> bool:
        if not pubdate:
            return True
        try:
            parsed = parsedate_to_datetime(pubdate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            age = datetime.datetime.now(datetime.timezone.utc) - parsed.astimezone(datetime.timezone.utc)
            return age <= datetime.timedelta(days=max(1, days + 1))
        except Exception:
            return True

    @staticmethod
    def _dedupe_alerts(alerts: list[dict]) -> list[dict]:
        seen = set()
        deduped = []
        for alert in alerts:
            key = (
                re.sub(r"\W+", "", (alert.get("title") or "").lower())[:90]
                or re.sub(r"\W+", "", (alert.get("snippet") or "").lower())[:90]
                or alert.get("url", "")
            )
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(alert)
        return deduped


class BriefingTool(MCPTool):
    """
    Build a compact daily briefing by combining multiple MCP tools.
    """

    name = "briefing"
    description = "Generate a daily briefing from weather, calendar, Gmail, reminders, and optional news."

    def _safe_run(self, tool, **kwargs) -> dict:
        try:
            return tool.run(**kwargs)
        except Exception as exc:
            return self._err(str(exc))

    @staticmethod
    def _first_items(result: dict, data_key: str, count: int) -> list:
        if result.get("status") != "ok":
            return []
        data = result.get("data") or {}
        items = data.get(data_key, [])
        return items[:count] if isinstance(items, list) else []

    @staticmethod
    def _brief_list(items: list, key: str, count: int = 3) -> str:
        values = [
            str(item.get(key, "")).strip()
            for item in items[:count]
            if isinstance(item, dict) and str(item.get(key, "")).strip()
        ]
        return "; ".join(values)

    @staticmethod
    def _is_google_connection_warning(result: dict) -> bool:
        data = (result or {}).get("data") or {}
        if isinstance(data, dict) and data.get("browser_fallback"):
            return True
        message = str((result or {}).get("message", "")).lower()
        return (
            "not connected on this deployment" in message
            or "not connected on the live server" in message
            or ("google_credentials" in message and "token" in message)
        )

    def run(
        self,
        city: str = "",
        include_news: bool = False,
        include_gmail: bool = True,
        include_calendar: bool = True,
        include_reminders: bool = True,
        include_utility: bool = False,
        news_category: str = "india",
        interactive_calendar: bool = False,
        utility_location: str = "",
    ) -> dict:
        city = (city or app_settings.WEATHER_ALERT_CITY or "Chennai").strip()
        utility_location = (
            utility_location
            or getattr(app_settings, "UTILITY_ALERT_LOCATION", "")
            or UtilityAlertTool._DEFAULT_LOCATION
        )

        weather_result = self._safe_run(
            WeatherTool(),
            city=city,
            forecast=False,
            rain_alert_hours=max(app_settings.WEATHER_ALERT_HOURS, 24),
        )

        calendar_result = (
            self._safe_run(
                CalendarTool(base_dir=app_settings.BASE_DIR),
                action="upcoming",
                timeframe="today",
                max_results=5,
                interactive=interactive_calendar,
            )
            if include_calendar else self._ok({}, "Calendar skipped.")
        )

        gmail_result = (
            self._safe_run(
                GmailTool(base_dir=app_settings.BASE_DIR),
                action="check_interviews",
                timeframe="today",
            )
            if include_gmail else self._ok({}, "Gmail skipped.")
        )

        reminder_result = (
            self._safe_run(
                ReminderTool(base_dir=app_settings.BASE_DIR),
                action="list",
                max_results=5,
            )
            if include_reminders else self._ok({}, "Reminders skipped.")
        )

        news_result = (
            self._safe_run(
                NewsTool(),
                category=news_category or "india",
                count=3,
            )
            if include_news else self._ok({}, "News skipped.")
        )

        utility_result = (
            self._safe_run(
                UtilityAlertTool(),
                kind="all",
                location=utility_location,
                city=city,
                days=3,
                max_results=3,
            )
            if include_utility else self._ok({}, "Utility alerts skipped.")
        )

        weather_data = weather_result.get("data") or {}
        calendar_events = self._first_items(calendar_result, "calendar_events", 5)
        emails = self._first_items(gmail_result, "interviews", 5)
        reminders = self._first_items(reminder_result, "reminders", 5)
        articles = self._first_items(news_result, "articles", 3)
        utility_alerts = self._first_items(utility_result, "alerts", 3)

        overview_parts = []
        if include_calendar and calendar_result.get("status") == "ok":
            overview_parts.append(f"{len(calendar_events)} calendar event(s)")
        if include_reminders and reminder_result.get("status") == "ok":
            overview_parts.append(f"{len(reminders)} active reminder(s)")
        if (
            include_gmail
            and gmail_result.get("status") == "ok"
            and not self._is_google_connection_warning(gmail_result)
        ):
            overview_parts.append(f"{len(emails)} scheduled Gmail item(s)")
        if utility_alerts:
            overview_parts.append(f"{len(utility_alerts)} utility alert(s)")

        sections = [{
            "title": "Overview",
            "text": (
                "No major events, reminders, or important emails found right now."
                if not overview_parts else "Today: " + ", ".join(overview_parts) + "."
            ),
        }]

        if weather_result.get("status") == "ok" and weather_data:
            weather_text = (
                f"{weather_data.get('city', city)}: "
                f"{weather_data.get('temperature_c')} C, "
                f"{weather_data.get('condition', 'unknown')}."
            )
            if weather_data.get("rain_expected") and weather_data.get("rain_summary"):
                weather_text += f" {weather_data.get('rain_summary')}"
            elif weather_data.get("heat_alert") and weather_data.get("heat_summary"):
                weather_text += f" {weather_data.get('heat_summary')}"
            sections.append({
                "title": "Weather",
                "text": weather_text,
            })

        if include_calendar and calendar_result.get("status") == "ok":
            if calendar_events:
                event_lines = []
                for event in calendar_events[:3]:
                    title = event.get("summary", "No title")
                    when = event.get("start_text", "")
                    event_lines.append(f"{title} at {when}" if when else title)
                sections.append({
                    "title": "Calendar",
                    "text": (
                        f"{len(calendar_events)} event(s) today. "
                        f"Next: {'; '.join(event_lines)}."
                    ),
                })
            else:
                sections.append({"title": "Calendar", "text": "No calendar events found today."})
        elif include_calendar and not self._is_google_connection_warning(calendar_result):
            sections.append({"title": "Calendar", "text": calendar_result.get("message", "Calendar unavailable.")})

        if include_reminders and reminder_result.get("status") == "ok":
            if reminders:
                reminder_text = self._brief_list(reminders, "text", 3)
                sections.append({
                    "title": "Reminders",
                    "text": f"{len(reminders)} active reminder(s). {reminder_text}.",
                })
            else:
                sections.append({"title": "Reminders", "text": "No active reminders."})

        if (
            include_gmail
            and gmail_result.get("status") == "ok"
            and not self._is_google_connection_warning(gmail_result)
        ):
            if emails:
                email_subjects = self._brief_list(emails, "subject", 3)
                sections.append({
                    "title": "Gmail",
                    "text": (
                        f"{len(emails)} scheduled interview, assessment, or meeting email(s) found. "
                        f"{email_subjects}."
                    ),
                })
            else:
                sections.append({"title": "Gmail", "text": "No scheduled interview, assessment, or meeting emails found today."})
        elif include_gmail and not self._is_google_connection_warning(gmail_result):
            sections.append({"title": "Gmail", "text": gmail_result.get("message", "Gmail unavailable.")})

        if news_result.get("status") == "ok" and articles:
            headlines = self._brief_list(articles, "title", 3)
            sections.append({
                "title": "News",
                "text": f"Top headlines: {headlines}",
            })

        if include_utility and utility_result.get("status") == "ok" and utility_alerts:
            utility_text = "; ".join(
                (
                    f"{item.get('type', 'utility')} - "
                    f"{item.get('title') or item.get('snippet', 'alert')}"
                )
                for item in utility_alerts[:3]
            )
            sections.append({
                "title": "Utility Alerts",
                "text": utility_text,
            })

        briefing = {
            "city": city,
            "generated_at": datetime.datetime.now().astimezone().isoformat(),
            "weather": weather_result,
            "calendar": calendar_result,
            "gmail": gmail_result,
            "reminders": reminder_result,
            "news": news_result,
            "utility_alerts": utility_result,
            "sections": sections,
        }

        return self._ok(
            {"briefing": briefing},
            f"Daily briefing ready with {len(sections)} section(s)."
        )


class MCPRegistry:
    """Central registry of all MCP tools."""

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        for tool_cls in [
            AppLauncherTool,
            DesktopSystemTool,
            FileSystemTool,
            WeatherTool,
            NewsTool,
            FlightTool,
            TrainTool,
            UtilityAlertTool,
            BriefingTool,
            MediaControlTool,
            lambda: GmailTool(base_dir=app_settings.BASE_DIR), # Pass BASE_DIR to GmailTool
            lambda: CalendarTool(base_dir=app_settings.BASE_DIR),
            lambda: ReminderTool(base_dir=app_settings.BASE_DIR),
            NotificationTool,
            JobTool
        ]:
            t = tool_cls()
            self._tools[t.name] = t

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [{"name": t.name, "description": t.description}
                for t in self._tools.values()]

    def run(self, tool_name: str, **kwargs) -> dict:
        tool = self.get(tool_name)
        if tool is None:
            return {"status": "error", "data": None,
                    "message": f"Tool '{tool_name}' not found."}
        try:
            return tool.run(**kwargs)
        except Exception as exc:
            return {"status": "error", "data": None, "message": str(exc)}


# Singleton instance
mcp = MCPRegistry()
