"""
AI_logic.py  (MCP-enhanced)
===========================
CUBY AI assistant core logic, now integrated with the MCP tool registry.

Key changes vs previous version
--------------------------------
- Imports `mcp` from mcp_tools and calls tools for: app launch, file ops,
  weather, news, and flight queries.
- `main()` and `chatbot()` route voice/text commands to MCP tools when
  applicable, falling back to Google search / LLM as before.
- All MCP results are spoken aloud (speak()) and returned as strings so
  the FastAPI layer can forward them to the UI.
"""

from __future__ import annotations

import os
import subprocess
import shutil
import json
import random
import sys
import datetime
import time
import itertools
import requests

from difflib import SequenceMatcher
from pathlib import Path

import psutil
import pyjokes
import pywhatkit
import pyautogui as py
import pygetwindow as gw
import wikipedia
from bs4 import BeautifulSoup
from newspaper import Article
from googlesearch import search as google_search_iter

# ── project-local imports ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings as app_settings
import models
from AI_logic_app.llm import generate_response

# ── MCP integration ────────────────────────────────────────────────────────
from mcp_tools import mcp  # MCPRegistry singleton

# ── voice / speech ─────────────────────────────────────────────────────────
try:
    import pyttsx3
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False

try:
    import speech_recognition as sr
    import pyaudio  # noqa: F401
    VOICE_AVAILABLE = True
except Exception:
    VOICE_AVAILABLE = False

# ── global state ───────────────────────────────────────────────────────────
RUNNING = False
BASE_DIR = app_settings.BASE_DIR
inp_lang = "en-in"

# ── DB ─────────────────────────────────────────────────────────────────────
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(app_settings.DATABASE_URL,
                       connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def save_data_in_db(query: str, answers) -> None:
    db = SessionLocal()
    try:
        db.add(models.CubyQueries(query=query, answers=str(answers)))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"DB save error: {e}")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# Speech helpers
# ══════════════════════════════════════════════════════════════════════════

def speak(text: str, rate: int = 150) -> None:
    """Convert text to speech (silently skips if pyttsx3 unavailable)."""
    print(f"[CUBY] {text}")
    if not _TTS_AVAILABLE:
        return
    try:
        engine = pyttsx3.init()
        for voice in engine.getProperty("voices"):
            if "Zira" in voice.name:
                engine.setProperty("voice", voice.id)
                break
        engine.setProperty("rate", rate)
        engine.setProperty("volume", 1.0)
        engine.say(str(text))
        engine.runAndWait()
    except Exception as exc:
        print(f"TTS error: {exc}")


def takecommandexceptional(seconds: int = 5) -> str:
    """Listen for a voice command and return it as lowercase text."""
    if not VOICE_AVAILABLE:
        return ""
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("listening…")
            audio = r.listen(source, phrase_time_limit=seconds)
        query = r.recognize_google(audio, language=inp_lang).lower()

        aliases = [
            "qb", "cubi", "cubie", "kibi", "kooby", "cooby",
            "koobie", "cubye", "cuban", "kirban", "hey google",
            "killbe", "killby", "cubic", "cubyc",
        ]
        for alias in aliases:
            if alias in query:
                query = query.replace(alias, "hey cuby")
        print(f"[heard] {query}")
        return query
    except Exception as exc:
        print(f"Recognition error: {exc}")
        return ""


# ══════════════════════════════════════════════════════════════════════════
# Startup / shutdown
# ══════════════════════════════════════════════════════════════════════════

def startup() -> None:
    global RUNNING
    if not VOICE_AVAILABLE:
        print("CUBY started (no voice — PyAudio missing).")
        return
    RUNNING = True
    print("CUBY started. Listening…")
    try:
        while RUNNING:
            command = takecommandexceptional(5)
            if not command:
                continue
            if "hey" in command:
                speak("Hi, welcome back!")
                hour = datetime.datetime.now().hour
                if 6 <= hour < 12:
                    speak("Good morning!")
                elif 12 <= hour < 15:
                    speak("Good afternoon!")
                elif 15 <= hour < 19:
                    speak("Good evening!")
                else:
                    speak("Good night!")
                main()
            elif "turn off" in command:
                shut_down()
    except KeyboardInterrupt:
        speak("Goodbye!")


def shut_down() -> None:
    global RUNNING
    speak("I am available anytime. Feel free to call me. Thank you!")
    RUNNING = False


def stop() -> None:
    global RUNNING
    RUNNING = False


# ══════════════════════════════════════════════════════════════════════════
# MCP dispatch helpers  (voice-friendly wrappers)
# ══════════════════════════════════════════════════════════════════════════

def _speak_result(result: dict) -> str:
    """Speak a human-friendly summary of a MCP tool result and return it."""
    if result["status"] == "error":
        speak(result["message"])
        return result["message"]

    data = result.get("data") or {}
    msg = result.get("message", "Done.")

    # --- weather ---
    if "temperature_c" in data:
        summary = (
            f"Weather in {data.get('city', '')}: "
            f"{data['temperature_c']} degrees Celsius, "
            f"{data.get('condition', '')}, "
            f"wind {data.get('windspeed_kmh', '')} km/h."
        )
        if "humidity_pct" in data:
            summary += f" Humidity {data['humidity_pct']} percent."
        speak(summary)
        return summary

    # --- news ---
    if "articles" in data:
        articles = data["articles"]
        speak(f"Here are the top {len(articles)} headlines.")
        for i, a in enumerate(articles, 1):
            speak(f"{i}. {a['title']}")
        return "\n".join(f"{i+1}. {a['title']}"
                         for i, a in enumerate(articles))

    # --- flights ---
    if "flights" in data:
        flights = data["flights"]
        if not flights:
            speak("No flights found.")
            return "No flights found."
        speak(f"Found {len(flights)} flight(s).")
        for f in flights[:3]:
            dep, arr = f["departure"], f["arrival"]
            status = f.get("status", "unknown")
            delay = dep.get("delay_min")
            delay_str = f", delayed {delay} minutes" if delay else ""
            line = (
                f"Flight {f['flight']} by {f['airline']}: "
                f"{dep.get('airport','?')} to {arr.get('airport','?')}, "
                f"status {status}{delay_str}."
            )
            speak(line)
        return json.dumps(data["flights"][:3], indent=2)

    # --- filesystem list ---
    if "items" in data:
        items = data["items"]
        speak(f"{len(items)} items in {data.get('path', '.')}.")
        return "\n".join(
            f"{'[DIR]' if i['type']=='folder' else '[FILE]'} {i['name']}"
            for i in items
        )

    # --- file read ---
    if "content" in data:
        speak(f"File read: {data.get('path', '')}")
        return data["content"]
    # ── YOUTUBE PLAY ─────────────────────

    if (
        "youtube" in q
        and (
            "play" in q
            or "song" in q
            or "video" in q
        )
    ):

        video = (
            q.replace("open youtube", "")
            .replace("youtube", "")
            .replace("play", "")
            .replace("song", "")
            .replace("video", "")
            .strip()
        )

        if not video:
            return "What should I play on YouTube?"

        result = mcp.run(
            "media_control",
            action="play",
            platform="youtube",
            query=video
        )

        return _speak_result(result)

    # --- app launch ---
    speak(msg)
    return msg


# ──────────────────────────────────────────────────────────────────────────
# MCP command classifier  (called from main() and chatbot())
# ──────────────────────────────────────────────────────────────────────────

def _try_mcp(query: str) -> str | None:
    """
    Parse the voice/text query for MCP intent.
    Returns a spoken response string, or None if no MCP tool matched.
    """
    q = query.lower().strip()

    # ── App Launch ────────────────────────────────────────────────────────
    _open_triggers = ("open ", "launch ", "start ", "run ")
    for trigger in _open_triggers:
        if q.startswith(trigger):
            target = q[len(trigger):].strip()
            result = mcp.run("app_launcher", target=target)
            return _speak_result(result)

    # ── File System ───────────────────────────────────────────────────────
    if q.startswith("list ") or "show files" in q or "show folder" in q:
        path = q.replace("list", "").replace("show files in", "").replace(
            "show folder", "").strip() or "."
        result = mcp.run("filesystem", action="list", path=path)
        return _speak_result(result)

    if q.startswith("read file "):
        path = q.replace("read file", "").strip()
        result = mcp.run("filesystem", action="read", path=path)
        return _speak_result(result)

    if q.startswith("create folder "):
        path = q.replace("create folder", "").strip()
        result = mcp.run("filesystem", action="create_folder", path=path)
        return _speak_result(result)
    
    # EMAIL SEND

    if (
        "send email" in q
        or "send gmail" in q
        or "mail to" in q
    ):

        import re

        email_match = re.search(
            r'[\w\.-]+@[\w\.-]+',
            q
        )

        if not email_match:
            return "No email address found"

        to_email = email_match.group(0)

        result = mcp.run(
            "gmail",
            action="send",
            to=to_email,
            subject="Message from CUBY",
            body="Hello from CUBY AI Assistant"
        )

        return _speak_result(result)

    # INTERVIEW CHECK

    if "check interviews" in q:

        result = mcp.run(
            "gmail",
            action="check_interviews"
        )

        return _speak_result(result)

    # JOB SEARCH
    # ── JOB SEARCH ─────────────────────────

    if (
        "job" in q
        or "jobs" in q
        or "hiring" in q
    ):

        platform = "linkedin"

        if "indeed" in q:
            platform = "indeed"

        elif "naukri" in q:
            platform = "naukri"

        role = "AI Engineer"

        locations = [
            "chennai",
            "tamilnadu",
            "bangalore",
            "remote"
        ]

        location = "remote"

        for loc in locations:
            if loc in q:
                location = loc
                break

        if "gen ai" in q:
            role = "Generative AI Engineer"

        elif "python" in q:
            role = "Python Developer"

        elif "ml" in q:
            role = "Machine Learning Engineer"

        result = mcp.run(
            "jobs",
            platform=platform,
            role=role,
            location=location
        )

        return _speak_result(result)

    if "linkedin jobs" in q:

        result = mcp.run(
            "jobs",
            platform="linkedin",
            role="python developer",
            location="chennai"
        )

        return _speak_result(result)

    if "naukri jobs" in q:

        result = mcp.run(
            "jobs",
            platform="naukri",
            role="python developer"
        )

        return _speak_result(result)
    # ── MEDIA CONTROL ─────────────────────

    if "play" in q:

        if "spotify" in q:
            song = (
                q.replace("play", "")
                .replace("on spotify", "")
                .strip()
            )

            result = mcp.run(
                "media_control",
                action="play",
                platform="spotify",
                query=song
            )

            return _speak_result(result)

        elif "youtube" in q:

            video = (
                q.replace("play", "")
                .replace("on youtube", "")
                .strip()
            )

            result = mcp.run(
                "media_control",
                action="play",
                platform="youtube",
                query=video
            )

            return _speak_result(result)


    if "pause" in q:
        result = mcp.run(
            "media_control",
            action="pause"
        )
        return _speak_result(result)

    if "resume" in q:
        result = mcp.run(
            "media_control",
            action="resume"
        )
        return _speak_result(result)

    if "next song" in q or "next track" in q:
        result = mcp.run(
            "media_control",
            action="next"
        )
        return _speak_result(result)

    if "previous song" in q:
        result = mcp.run(
            "media_control",
            action="previous"
        )
        return _speak_result(result)

    if "mute" in q:
        result = mcp.run(
            "media_control",
            action="mute"
        )
        return _speak_result(result)

    if "volume up" in q:
        result = mcp.run(
            "media_control",
            action="volume_up"
        )
        return _speak_result(result)

    if "volume down" in q:
        result = mcp.run(
            "media_control",
            action="volume_down"
        )
        return _speak_result(result)

    if "close spotify" in q:
        result = mcp.run(
            "media_control",
            action="close",
            platform="spotify"
        )
        return _speak_result(result)

    # ── Weather ───────────────────────────────────────────────────────────
    # ── Weather ─────────────────────────────

    if (
        "weather" in q
        or "temperature" in q
        or "forecast" in q
    ):

        city = None

        patterns = [
            "weather in",
            "temperature in",
            "forecast in",
            "forecast for",
            "weather at"
        ]

        for p in patterns:

            if p in q:
                city = q.split(p)[1].strip()
                break

        if not city:
            city = "Chennai"

        forecast = (
            "forecast" in q
            or "7 day" in q
            or "week" in q
        )

        result = mcp.run(
            "weather",
            city=city,
            forecast=forecast
        )

        return _speak_result(result)

    # ── News ──────────────────────────────────────────────────────────────
    if "news" in q or "headlines" in q or "latest" in q:
        category = "general"
        for cat in ("technology", "tech", "sports", "science",
                    "health", "business", "india"):
            if cat in q:
                category = "technology" if cat == "tech" else cat
                break
        result = mcp.run("news", category=category, count=5)
        return _speak_result(result)

    # ── Flights ───────────────────────────────────────────────────────────
    if "flight" in q or "flights" in q:
        # Try to find IATA code pattern (2-3 letters + 1-4 digits)
        import re
        iata_match = re.search(r'\b([A-Za-z]{2,3}\d{1,4})\b', q)
        flight_iata = iata_match.group(1).upper() if iata_match else ""

        # Try to extract "from X to Y"
        dep, arr = "", ""
        from_match = re.search(r'\bfrom\s+([A-Za-z]{3})\b', q)
        to_match = re.search(r'\bto\s+([A-Za-z]{3})\b', q)
        if from_match:
            dep = from_match.group(1).upper()
        if to_match:
            arr = to_match.group(1).upper()

        result = mcp.run("flight_info",
                         flight_iata=flight_iata,
                         dep_iata=dep, arr_iata=arr)
        return _speak_result(result)

    return None  # no MCP match


# ══════════════════════════════════════════════════════════════════════════
# Core assistant functions (unchanged from original, kept for compatibility)
# ══════════════════════════════════════════════════════════════════════════

def chatbot(query: str) -> str:
    file_path = os.path.join(BASE_DIR, "AI_logic_app", "data", "cuby.json")
    try:
        with open(file_path) as f:
            intents = json.load(f)["intents"]
    except Exception:
        intents = []

    for intent in intents:
        if query in intent.get("patterns", []):
            response = random.choice(intent["responses"])
            speak(response)
            return response

    # MCP fallback
    mcp_response = _try_mcp(query)
    if mcp_response:
        return mcp_response

    # LLM fallback
    try:
        response = generate_response(query)
        if response and not response.startswith("Error:"):
            speak(response)
            try:
                save_data_in_db(query, response)
            except Exception:
                pass
            return response
    except Exception as exc:
        print(f"LLM error: {exc}")

    return ""


def cur_time() -> None:
    speak(f"The current time is {datetime.datetime.now().strftime('%H:%M:%S')}")


def date() -> None:
    now = datetime.datetime.now()
    speak(f"The current date is {now.day} {now.strftime('%B')} {now.year}")


def long_define(query: str) -> None:
    try:
        wikipedia.set_lang("en")
        summary = wikipedia.summary(wikipedia.search(query)[0])
        open_notepad()
        py.write(summary)
    except Exception as exc:
        speak(f"Could not find information on {query}. {exc}")


def short_define(query: str) -> None:
    try:
        result = pywhatkit.info(query, 5, True)
        open_notepad()
        py.write(result)
    except Exception as exc:
        speak(f"Could not find information on {query}.")


def open_notepad() -> None:
    subprocess.run(
        ["start", "", r"C:/ProgramData/Microsoft/Windows/Start Menu/"
                      r"Programs/Accessories/Notepad.lnk"],
        shell=True,
    )
    time.sleep(2)
    try:
        gw.getWindowsWithTitle("Notepad")[0].maximize()
    except Exception:
        pass


def playsongs(query: str) -> None:
    song_path = os.path.join(BASE_DIR, "AI_logic_app", "data", "songs")
    songs = os.listdir(song_path)
    best, best_score = songs[0], 0.0
    for f in songs:
        score = SequenceMatcher(None, query, f).ratio()
        if score > best_score:
            best, best_score = f, score
    os.startfile(os.path.join(song_path, best))


def cpu() -> None:
    usage = psutil.cpu_percent()
    batt = psutil.sensors_battery()
    speak(f"CPU usage is {usage} percent.")
    if batt:
        speak(f"Battery is at {batt.percent:.0f} percent.")


def screenshot() -> None:
    img = py.screenshot()
    ts = datetime.datetime.now().strftime("%H.%M.%S")
    path = os.path.join(BASE_DIR, "AI_logic_app", "data", "screenshots",
                        f"ss {ts}.png")
    img.save(path)
    speak("Screenshot saved.")


def minimizer() -> None:
    try:
        gw.getAllWindows()[1].minimize()
    except Exception:
        speak("Could not minimize window.")


def writter() -> None:
    while True:
        speak("Say…")
        command = takecommandexceptional(10)
        if "exit writer" in command:
            speak("Leaving writer mode.")
            break
        _writer_key(command)


def _writer_key(command: str) -> None:
    mapping = {
        "press space": "space", "colon": ":", "semicolon": ";",
        "open parenthesis": "(", "close parenthesis": ")",
        "single quotes": "'", "double quotes": '"',
        "press enter": "enter", "caps lock": "capslock", "tab": "Tab",
    }
    for phrase, key in mapping.items():
        if phrase in command:
            py.press(key)
            return
    if "triple quotes" in command:
        py.write("'''")
        return
    py.write(command)


# ══════════════════════════════════════════════════════════════════════════
# GenAI  (Google-search scraper, unchanged)
# ══════════════════════════════════════════════════════════════════════════

main_content_answer: list[str] = []
content_words: str = ""


class GenAI:
    def google_search(self, query: str) -> None:
        urls: list[str] = []
        for url in itertools.islice(google_search_iter(query), 5):
            if "geeksforgeeks" in url:
                continue
            if "wikipedia" in url or "programiz" in url:
                urls.insert(0, url)
            else:
                urls.append(url)
        if urls:
            GenAI.get_main_content(urls, query)

    @staticmethod
    def get_main_content(urls: list[str], query: str) -> None:
        try:
            article = Article(urls[0])
            article.download()
            article.parse()
            GenAI.extract_code(urls[0], article.text, query)
        except Exception as exc:
            speak("Could not retrieve that information.")
            print(exc)

    @staticmethod
    def extract_code(url: str, content: str, query: str) -> None:
        try:
            resp = requests.get(url, timeout=8)
            soup = BeautifulSoup(resp.text, "html.parser")
            code_blocks = soup.find_all("code")
            GenAI.split_results(content, query, code_blocks, url)
        except Exception:
            GenAI.split_results(content, query, [], url)

    @staticmethod
    def split_results(content: str, query: str, code_blocks, url: str) -> None:
        global content_words
        words = content.split()[:100]
        content_words = " ".join(words)
        GenAI.print_results(content, query, code_blocks, url, content_words)

    @staticmethod
    def print_results(content: str, query: str, code_blocks,
                      url: str, summary: str) -> None:
        global main_content_answer
        lines = content.splitlines()
        main_content_answer = lines[:5]

        if any(k in query for k in ("define", "what", "tell me about")):
            speak(summary)
        elif "write" in query:
            open_notepad()
            for line in lines[:10]:
                py.write(line)
                py.press("enter")
            py.write(f"Reference: {url}")
        elif code_blocks:
            open_notepad()
            for block in code_blocks:
                py.write(block.get_text())
                py.press("enter")
            py.write(f"Reference: {url}")
        else:
            speak(summary)


# ══════════════════════════════════════════════════════════════════════════
# main()  — voice command loop
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    speak("How can I assist you today?")
    search_obj = GenAI()

    while True:
        query = takecommandexceptional(20).lower()
        if not query:
            continue

        # 1 — try MCP tools first
        mcp_resp = _try_mcp(query)
        if mcp_resp:
            try:
                save_data_in_db(query, mcp_resp)
            except Exception:
                pass
            continue

        # 2 — built-in assistant commands
        if "turn off" in query:
            shut_down()
            break
        elif "time" in query:
            cur_time()
        elif "date" in query:
            date()
        elif "make a search" in query:
            pywhatkit.search(query.replace("make a search", "").strip())
        elif "play offline songs" in query:
            songs_dir = os.path.join(BASE_DIR, "AI_logic_app", "data", "songs")
            os.startfile(os.path.join(songs_dir, os.listdir(songs_dir)[0]))
        elif "play" in query:
            playsongs(query.replace("play", "").strip())
        elif "remember that" in query:
            info = query.replace("remember that", "").strip()
            speak(f"I will remember that {info}")
            p = Path(BASE_DIR) / "AI_logic_app" / "data" / "remember" / "data.txt"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(info)
        elif "do you remember" in query:
            p = Path(BASE_DIR) / "AI_logic_app" / "data" / "remember" / "data.txt"
            if p.exists():
                speak(f"You told me to remember: {p.read_text()}")
            else:
                speak("I don't have anything stored in memory.")
        elif "joke" in query:
            speak(pyjokes.get_joke(category="all"))
        elif "cpu" in query or "battery" in query:
            cpu()
        elif "screenshot" in query:
            screenshot()
        elif "minimise" in query or "minimize" in query:
            minimizer()
        elif "maximize" in query:
            py.hotkey("win", "up")
        elif "youtube" in query:
            try:
                pywhatkit.playonyt(query.replace("youtube", "").strip())
            except Exception:
                speak("Could not play on YouTube.")
        elif "select all" in query:
            py.hotkey("ctrl", "a")
        elif "save" in query:
            py.hotkey("ctrl", "s")
            time.sleep(2)
            py.press("enter")
        elif "activate write" in query:
            writter()
        elif "pause" in query:
            py.press("space")
        elif "close it" in query:
            py.hotkey("alt", "f4")
        elif "shut down my pc" in query:
            speak("Warning! Shutting down. Say yes to confirm.")
            if "yes" in takecommandexceptional(5):
                os.system(r"C:\Windows\System32\shutdown.exe /s /t 0")
        elif "restart my pc" in query:
            speak("Warning! Restarting. Say yes to confirm.")
            if "yes" in takecommandexceptional(5):
                os.system(r"C:\Windows\System32\shutdown.exe /r /t 0")
        elif "log out my pc" in query:
            speak("Warning! Locking system. Say yes to confirm.")
            if "yes" in takecommandexceptional(5):
                os.system(
                    r"C:\Windows\System32\rundll32.exe "
                    r"powrprof.dll,SetSuspendState 0,1,0"
                )

        # 3 — chatbot / LLM / Google fallback
        elif query:
            response = chatbot(query)
            if not response:
                search_obj.google_search(query)
                try:
                    save_data_in_db(query, main_content_answer)
                except Exception:
                    pass