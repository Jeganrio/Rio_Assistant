import os
import time
import webbrowser
import pyautogui as py
import pygetwindow as gw
import pywhatkit
from pathlib import Path

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

    def run(self,
            action="",
            platform="youtube",
            query=""):

        try:

            # PLAY SONG / VIDEO
            if action == "play":

                if platform == "youtube":
                    pywhatkit.playonyt(query)
                    return self._ok(
                        {"query": query},
                        f"Playing {query} on YouTube"
                    )

                elif platform == "spotify":

                    possible_paths = [

                        os.path.expandvars(
                            r"%APPDATA%\Spotify\Spotify.exe"
                        ),

                        os.path.expandvars(
                            r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"
                        ),

                        r"C:\Program Files\Spotify\Spotify.exe",

                        r"C:\Program Files (x86)\Spotify\Spotify.exe"
                    ]

                    spotify_path = None

                    for p in possible_paths:

                        if os.path.exists(p):
                            spotify_path = p
                            break

                    # OPEN SPOTIFY
                    if spotify_path:

                        os.startfile(spotify_path)

                    else:

                        webbrowser.open("https://open.spotify.com")

                    # WAIT FOR SPOTIFY LOAD
                    time.sleep(8)

                    # OPEN SEARCH
                    py.hotkey("ctrl", "l")

                    time.sleep(1)

                    # TYPE SONG
                    py.write(query, interval=0.05)

                    time.sleep(1)

                    py.press("enter")

                    # WAIT RESULTS LOAD
                    time.sleep(3)

                    # PLAY FIRST RESULT
                    py.press("tab")
                    time.sleep(1)

                    py.press("enter")

                    # EXTRA PLAY SAFETY
                    time.sleep(2)

                    py.press("space")

                    return self._ok(
                        {"query": query},
                        f"Playing {query} on Spotify"
                    )
            # PAUSE
            elif action == "pause":
                py.press("playpause")
                return self._ok(message="Playback paused")

            # RESUME
            elif action == "resume":
                py.press("playpause")
                return self._ok(message="Playback resumed")

            # NEXT SONG
            elif action == "next":
                py.press("nexttrack")
                return self._ok(message="Next track")

            # PREVIOUS SONG
            elif action == "previous":
                py.press("prevtrack")
                return self._ok(message="Previous track")

            # VOLUME UP
            elif action == "volume_up":
                py.press("volumeup")
                return self._ok(message="Volume increased")

            # VOLUME DOWN
            elif action == "volume_down":
                py.press("volumedown")
                return self._ok(message="Volume decreased")

            # MUTE
            elif action == "mute":
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