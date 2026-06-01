import os
import re
import time
import webbrowser
try:
    import pyautogui as py
except Exception:
    py = None
try:
    import pygetwindow as gw
except Exception:
    gw = None
try:
    import pywhatkit
except Exception:
    pywhatkit = None
import requests
from pathlib import Path
from urllib.parse import quote_plus

class MediaControlTool:
    name = "media_control"

    description = (
        "Control Spotify, YouTube, VLC and system media playback."
    )

    def _ok(self, data=None, message="Success"):
        return {
            "status": "ok",
            "data": data or {},
            "message": message
        }

    def _err(self, message):
        return {
            "status": "error",
            "data": None,
            "message": message
        }

    def _play_youtube(self, query):
        search_url = (
            "https://www.youtube.com/results?search_query="
            f"{quote_plus(query)}"
        )
        try:
            response = requests.get(search_url, timeout=6)
            match = re.search(r'"url":"(/watch\?v=[^"]+)"', response.text)
            if match:
                video_url = (
                    "https://www.youtube.com"
                    + match.group(1).replace(r"\u0026", "&")
                )
                webbrowser.open(video_url)
                return video_url
        except Exception:
            pass

        webbrowser.open(search_url)
        return search_url

    def _open_spotify_app(self):
        possible_paths = [
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
            r"C:\Program Files\Spotify\Spotify.exe",
            r"C:\Program Files (x86)\Spotify\Spotify.exe"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                os.startfile(path)
                return "app"

        start_menu_paths = [
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
            / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("APPDATA", ""))
            / r"Microsoft\Windows\Start Menu\Programs",
        ]
        for start_path in start_menu_paths:
            if not start_path.exists():
                continue
            for file in start_path.rglob("*"):
                if file.suffix.lower() == ".lnk" and "spotify" in file.stem.lower():
                    os.startfile(str(file))
                    return "shortcut"

        try:
            os.startfile("spotify:")
            return "protocol"
        except Exception:
            webbrowser.open("https://open.spotify.com")
            return "web"

    def _focus_spotify_window(self):
        if gw is None:
            return None
        for _ in range(10):
            windows = [
                w for w in gw.getAllWindows()
                if "spotify" in (w.title or "").lower()
            ]
            if windows:
                window = windows[0]
                try:
                    if window.isMinimized:
                        window.restore()
                    window.activate()
                    if not window.isMaximized:
                        window.maximize()
                except Exception:
                    pass
                time.sleep(0.5)
                return window
            time.sleep(0.5)
        return None

    def _spotify_bounds(self, window):
        if window:
            return window.left, window.top, window.width, window.height
        if py is None:
            return 0, 0, 1200, 800
        screen = py.size()
        return 0, 0, screen.width, screen.height

    def _play_first_spotify_song_result(self, query):
        if py is None:
            raise RuntimeError("Desktop automation is unavailable in this environment.")
        window = self._focus_spotify_window()
        left, top, width, height = self._spotify_bounds(window)

        # Search inside Spotify.
        py.hotkey("ctrl", "l")
        time.sleep(0.3)
        py.hotkey("ctrl", "a")
        py.write(query, interval=0.03)
        py.press("enter")
        time.sleep(2.2)

        # Use the Songs filter so the first row is a song, not a playlist/card.
        py.click(left + int(width * 0.135), top + int(height * 0.11))
        time.sleep(1.2)

        # Double-click the first visible song row. This avoids resuming the
        # previous queue/current track from the bottom playback bar.
        first_song_x = left + int(width * 0.17)
        first_song_y = top + int(height * 0.245)
        py.click(first_song_x, first_song_y)
        time.sleep(0.25)
        py.press("enter")
        time.sleep(0.25)
        py.doubleClick(first_song_x, first_song_y, interval=0.08)
        return {
            "x": first_song_x,
            "y": first_song_y,
            "window": window.title if window else "screen"
        }

    def run(self,
            action="",
            platform="youtube",
            query=""):

        try:

            # PLAY SONG / VIDEO
            if action == "play":

                if platform == "youtube":
                    url = self._play_youtube(query)
                    return self._ok(
                        {"query": query, "url": url},
                        f"Playing {query} on YouTube"
                    )

                elif platform == "spotify":
                    opened_with = self._open_spotify_app()

                    # WAIT FOR SPOTIFY LOAD
                    time.sleep(8)

                    click_info = self._play_first_spotify_song_result(query)

                    return self._ok(
                        {
                            "query": query,
                            "opened_with": opened_with,
                            "clicked": click_info
                        },
                        f"Playing {query} on Spotify"
                    )
            # PAUSE
            elif action == "pause":
                if py is None:
                    return self._err("Desktop media keys are unavailable in this environment.")
                py.press("playpause")
                return self._ok(message="Playback paused")

            # RESUME
            elif action == "resume":
                if py is None:
                    return self._err("Desktop media keys are unavailable in this environment.")
                py.press("playpause")
                return self._ok(message="Playback resumed")

            # NEXT SONG
            elif action == "next":
                if py is None:
                    return self._err("Desktop media keys are unavailable in this environment.")
                py.press("nexttrack")
                return self._ok(message="Next track")

            # PREVIOUS SONG
            elif action == "previous":
                if py is None:
                    return self._err("Desktop media keys are unavailable in this environment.")
                py.press("prevtrack")
                return self._ok(message="Previous track")

            # VOLUME UP
            elif action == "volume_up":
                if py is None:
                    return self._err("Desktop media keys are unavailable in this environment.")
                py.press("volumeup")
                return self._ok(message="Volume increased")

            # VOLUME DOWN
            elif action == "volume_down":
                if py is None:
                    return self._err("Desktop media keys are unavailable in this environment.")
                py.press("volumedown")
                return self._ok(message="Volume decreased")

            # MUTE
            elif action == "mute":
                if py is None:
                    return self._err("Desktop media keys are unavailable in this environment.")
                py.press("volumemute")
                return self._ok(message="Muted")

            # CLOSE APP
            elif action == "close":

                apps = {
                    "spotify": "Spotify.exe",
                    "chrome": "chrome.exe",
                    "vlc": "vlc.exe"
                }

                exe = apps.get(platform)

                if exe:
                    os.system(f'taskkill /IM {exe} /F')
                    return self._ok(
                        message=f"{platform} closed"
                    )

                return self._err("Unknown app")

            return self._err("Unknown action")

        except Exception as e:
            return self._err(str(e))
