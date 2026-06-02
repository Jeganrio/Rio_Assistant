"""
AI_logic.py  (MCP-enhanced)
===========================
CUBY AI assistant core logic, now integrated with the MCP tool registry.

Key changes vs previous version
--------------------------------
- Imports `mcp` from cuby.mcp_tools and calls tools for: app launch, file ops,
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
import re
import time
import itertools
import requests
import threading
import tempfile
import ctypes
import asyncio
import audioop

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from difflib import SequenceMatcher
from pathlib import Path

import psutil
try:
    import pyjokes
except Exception:
    pyjokes = None
try:
    import pywhatkit
except Exception:
    pywhatkit = None
try:
    import pyautogui as py
except Exception:
    py = None
try:
    import pygetwindow as gw
except Exception:
    gw = None
import wikipedia
from bs4 import BeautifulSoup
from newspaper import Article
from googlesearch import search as google_search_iter

# ── project-local imports ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from cuby.config import settings as app_settings
from cuby import models
from cuby.database import SessionLocal
from AI_logic_app.llm import generate_response

# ── MCP integration ────────────────────────────────────────────────────────
from cuby.mcp_tools import mcp  # MCPRegistry singleton

# ── voice / speech ─────────────────────────────────────────────────────────
try:
    import pyttsx3
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False

try:
    from gtts import gTTS
    _GTTS_AVAILABLE = True
except Exception:
    _GTTS_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    _TRANSLATOR_AVAILABLE = True
except Exception:
    _TRANSLATOR_AVAILABLE = False

try:
    import edge_tts
    _EDGE_TTS_AVAILABLE = True
except Exception:
    edge_tts = None
    _EDGE_TTS_AVAILABLE = False

try:
    import pygame
    _PYGAME_AVAILABLE = True
except Exception:
    pygame = None
    _PYGAME_AVAILABLE = False

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
VOICE_LISTEN_TIMEOUT = 7
VOICE_PHRASE_TIME_LIMIT = 12
VOICE_RECOGNITION_TIMEOUT = 10
VOICE_AFTER_SPEAK_PAUSE = 1.0
VOICE_RECALIBRATE_AFTER = 3
VOICE_ENERGY_MIN = 140
VOICE_ENERGY_MAX = 1200
VOICE_ENERGY_SCALE = 1.05
VOICE_PREROLL_SECONDS = 0.35
VOICE_AMBIENT_SAMPLES = 8

_VOICE_RECOGNIZER = None
_VOICE_LOCK = threading.Lock()
_VOICE_MISSES = 0
_LAST_SPOKE_AT = 0.0
_TTS_LOCK = threading.Lock()
_VOICE_PREF_PATH = BASE_DIR / "AI_logic_app" / "data" / "voice_settings.json"
_VOICE_GENDER = "female"
_ASSISTANT_LANGUAGE = "english"
DEFAULT_ASSISTANT_LANGUAGE = "english"
DEFAULT_VOICE_GENDER = "female"
_TRANSLATION_CACHE: dict[tuple[str, str], str] = {}
_PYGAME_MIXER_READY = False
_UI_EVENT_LOCK = threading.Lock()
_UI_EVENTS: list[dict] = []
_UI_EVENT_SEQ = 0
_LAST_BROWSER_ACTION: dict | None = None
_EDGE_VOICES = {
    ("tamil", "male"): "ta-IN-ValluvarNeural",
    ("tamil", "female"): "ta-IN-PallaviNeural",
    ("english", "male"): "en-IN-PrabhatNeural",
    ("english", "female"): "en-IN-NeerjaNeural",
}


def _record_ui_event(kind: str, text: str = "", payload: dict | None = None) -> None:
    global _UI_EVENT_SEQ
    with _UI_EVENT_LOCK:
        _UI_EVENT_SEQ += 1
        _UI_EVENTS.append({
            "seq": _UI_EVENT_SEQ,
            "kind": kind,
            "text": str(text or ""),
            "payload": payload or {},
            "created_at": datetime.datetime.now().astimezone().isoformat(),
        })
        del _UI_EVENTS[:-80]


def get_ui_events(since: int = 0) -> dict:
    with _UI_EVENT_LOCK:
        events = [event for event in _UI_EVENTS if event.get("seq", 0) > since]
        return {
            "events": events,
            "latest_seq": _UI_EVENT_SEQ,
            "running": RUNNING,
        }


def _set_browser_action(action: dict | None) -> None:
    global _LAST_BROWSER_ACTION
    _LAST_BROWSER_ACTION = action if isinstance(action, dict) else None


def consume_browser_action() -> dict | None:
    global _LAST_BROWSER_ACTION
    action = _LAST_BROWSER_ACTION
    _LAST_BROWSER_ACTION = None
    return action


def _load_voice_settings() -> dict:
    settings = {
        "gender": _VOICE_GENDER,
        "language": _ASSISTANT_LANGUAGE,
    }
    try:
        if _VOICE_PREF_PATH.exists():
            data = json.loads(_VOICE_PREF_PATH.read_text(encoding="utf-8"))
            gender = str(data.get("gender", "")).lower()
            if gender in {"male", "female"}:
                settings["gender"] = gender
            language = str(data.get("language", "")).lower()
            if language in {"english", "tamil"}:
                settings["language"] = language
    except Exception as exc:
        print(f"Voice preference load error: {exc}")
    return settings


def _save_voice_settings(**updates) -> None:
    data = _load_voice_settings()
    data.update({k: v for k, v in updates.items() if v})
    try:
        _VOICE_PREF_PATH.parent.mkdir(parents=True, exist_ok=True)
        _VOICE_PREF_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"Voice preference save error: {exc}")


def _load_voice_gender() -> str:
    return _load_voice_settings()["gender"]


def get_assistant_language() -> str:
    return _load_voice_settings()["language"]


def _recognition_language() -> str:
    return "ta-IN" if get_assistant_language() == "tamil" else "en-IN"


def set_voice_gender(gender: str) -> str:
    global _VOICE_GENDER
    gender = gender.lower().strip()
    if gender not in {"male", "female"}:
        return "Please say male voice or female voice."
    _VOICE_GENDER = gender
    _save_voice_settings(gender=gender)
    if get_assistant_language() == "tamil":
        return "ஆண் குரலுக்கு மாறியது." if gender == "male" else "பெண் குரலுக்கு மாறியது."
    return f"Switched to {gender} voice."


def set_assistant_language(language: str) -> str:
    global _ASSISTANT_LANGUAGE, inp_lang
    language = language.lower().strip()
    if language in {"ta", "ta-in", "தமிழ்", "tamil"}:
        language = "tamil"
    elif language in {"en", "en-in", "english", "ஆங்கிலம்"}:
        language = "english"
    if language not in {"english", "tamil"}:
        return "Please say Tamil language or English language."
    _ASSISTANT_LANGUAGE = language
    inp_lang = "ta-IN" if language == "tamil" else "en-IN"
    _save_voice_settings(language=language)
    if language == "tamil":
        return "தமிழ் மொழிக்கு மாறியது. நான் தமிழில் கேட்பேன், பேசுவேன்."
    return "Switched to English language. I will listen and speak in English."


def reset_assistant_preferences_for_startup() -> None:
    """Every new AI listening session starts in English with the female voice."""
    set_voice_gender(DEFAULT_VOICE_GENDER)
    set_assistant_language(DEFAULT_ASSISTANT_LANGUAGE)


def reset_assistant_language_for_startup() -> None:
    reset_assistant_preferences_for_startup()


def _select_tts_voice(engine) -> str:
    gender = _load_voice_gender()
    language = get_assistant_language()
    if language == "tamil":
        tamil_names = ("Tamil", "Valluvar", "Pallavi", "ta-IN")
        voices = engine.getProperty("voices")
        for preferred in tamil_names:
            for voice in voices:
                haystack = f"{voice.name} {voice.id}".lower()
                if preferred.lower() in haystack:
                    engine.setProperty("voice", voice.id)
                    return voice.name

    preferred_names = {
        "male": ("David", "Mark", "George"),
        "female": ("Zira", "Hazel", "Susan"),
    }
    voices = engine.getProperty("voices")
    for preferred in preferred_names[gender]:
        for voice in voices:
            if preferred.lower() in voice.name.lower():
                engine.setProperty("voice", voice.id)
                return voice.name
    if voices:
        engine.setProperty("voice", voices[0].id)
        return voices[0].name
    return ""


def _contains_tamil(text: str) -> bool:
    return any("\u0b80" <= ch <= "\u0bff" for ch in str(text))


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(str(text).encode("unicode_escape").decode("ascii"))


def _text_for_speech(text: str) -> str:
    text = str(text)
    if get_assistant_language() != "tamil":
        return text
    if _contains_tamil(text) or not _TRANSLATOR_AVAILABLE:
        return text

    key = (text, "ta")
    if key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[key]

    try:
        translated = GoogleTranslator(source="auto", target="ta").translate(text)
        if translated:
            _TRANSLATION_CACHE[key] = translated
            return translated
    except Exception as exc:
        print(f"Translation error: {exc}")
    return text


def _run_async_blocking(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result = {}

    def runner():
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result["value"] = loop.run_until_complete(coro)
        except Exception as exc:
            result["error"] = exc
        finally:
            loop.close()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


def _play_mp3_with_pygame(path: Path) -> bool:
    global _PYGAME_MIXER_READY
    if not _PYGAME_AVAILABLE:
        return False

    try:
        if not _PYGAME_MIXER_READY:
            pygame.mixer.init()
            _PYGAME_MIXER_READY = True

        pygame.mixer.music.stop()
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        return True
    except Exception as exc:
        print(f"pygame MP3 playback error: {exc}")
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        _PYGAME_MIXER_READY = False
        return False


def _play_mp3_with_mci(path: Path) -> bool:
    if os.name != "nt":
        return False

    alias = f"cuby_tts_{int(time.time() * 1000)}"
    winmm = ctypes.windll.winmm

    def mci(command: str) -> tuple[int, str]:
        error_buffer = ctypes.create_unicode_buffer(512)
        code = winmm.mciSendStringW(command, error_buffer, 511, 0)
        return code, error_buffer.value

    safe_path = str(path)
    opened = False
    try:
        code, _ = mci(f'open "{safe_path}" type mpegvideo alias {alias}')
        if code != 0:
            code, _ = mci(f'open "{safe_path}" alias {alias}')
            if code != 0:
                return False
        opened = True

        code, _ = mci(f"play {alias} from 0 wait")
        if code != 0:
            return False
        return True
    except Exception as exc:
        print(f"MCI MP3 playback error: {exc}")
        return False
    finally:
        if opened:
            try:
                mci(f"stop {alias}")
                mci(f"close {alias}")
            except Exception:
                pass


def _play_mp3_with_powershell(path: Path) -> bool:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        return False

    safe_path = str(path).replace("'", "''")
    script = (
        "Add-Type -AssemblyName PresentationCore;"
        f"$path = '{safe_path}';"
        f"$player = New-Object System.Windows.Media.MediaPlayer;"
        "$player.Open([Uri](Resolve-Path -LiteralPath $path));"
        "$player.Play();"
        "while (-not $player.NaturalDuration.HasTimeSpan) { Start-Sleep -Milliseconds 50 };"
        "$duration = [int]$player.NaturalDuration.TimeSpan.TotalMilliseconds + 250;"
        "Start-Sleep -Milliseconds $duration;"
        "$player.Stop();"
        "$player.Close();"
    )
    try:
        args = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass"]
        if Path(powershell).name.lower() == "powershell.exe":
            args.append("-STA")
        args.extend(["-Command", script])
        completed = subprocess.run(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=90,
        )
        return completed.returncode == 0
    except Exception as exc:
        print(f"PowerShell MP3 playback error: {exc}")
        return False


def _play_mp3_blocking(path: Path) -> bool:
    if _play_mp3_with_pygame(path):
        return True
    if _play_mp3_with_mci(path):
        return True
    return _play_mp3_with_powershell(path)


def _speak_with_google_tts(text: str, lang: str) -> bool:
    if not _GTTS_AVAILABLE:
        return False
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            temp_path = Path(tmp.name)
        gTTS(text=text, lang=lang).save(str(temp_path))
        return _play_mp3_blocking(temp_path)
    except Exception as exc:
        print(f"gTTS error: {exc}")
        return False
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


def _speak_with_edge_tts(text: str, language: str) -> bool:
    if not _EDGE_TTS_AVAILABLE:
        return False

    language = "tamil" if language == "tamil" else "english"
    gender = _load_voice_gender()
    voice = _EDGE_VOICES.get((language, gender))
    if not voice:
        return False

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            temp_path = Path(tmp.name)

        async def synthesize():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(temp_path))

        _run_async_blocking(synthesize())
        return _play_mp3_blocking(temp_path)
    except Exception as exc:
        print(f"Edge TTS error: {exc}")
        return False
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


def _normalize_local_language_query(query: str) -> str:
    import re

    query = str(query or "").lower().strip()

    number_replacements = {
        "ஜீரோ": "0",
        "ஒன்று": "1",
        "ஒன்": "1",
        "வண்": "1",
        "ரெண்டு": "2",
        "இரண்டு": "2",
        "டூ": "2",
        "மூன்று": "3",
        "த்ரீ": "3",
        "நான்கு": "4",
        "ஃபோர்": "4",
        "ஐந்து": "5",
        "ஃபைவ்": "5",
        "பைவ்": "5",
        "ஆறு": "6",
        "சிக்ஸ்": "6",
        "ஏழு": "7",
        "செவன்": "7",
        "எட்டு": "8",
        "எய்ட்": "8",
        "ஒன்பது": "9",
        "நைன்": "9",
        "பத்து": "10",
        "டென்": "10",
        "இருபது": "20",
        "டுவென்டி": "20",
        "ஐம்பது": "50",
        "ஹண்ட்ரட்": "100",
        "நூறு": "100",
    }
    for src, dst in number_replacements.items():
        query = query.replace(src, dst)

    # Keep common Tamil/Tanglish "top N" phrases action-friendly.
    top_phrase_replacements = {
        "டாப் 100": "top 100",
        "டாப் நூறு": "top 100",
        "டாப் ஹண்ட்ரட்": "top 100",
        "டாப் 50": "top 50",
        "டாப் ஐம்பது": "top 50",
        "டாப் 20": "top 20",
        "டாப் இருபது": "top 20",
        "டாப் டுவென்டி": "top 20",
        "டாப் 10": "top 10",
        "டாப் பத்து": "top 10",
        "டாப் டென்": "top 10",
        "டாப் 5": "top 5",
        "டாப் ஐந்து": "top 5",
        "டாப் ஃபைவ்": "top 5",
        "டாப் பைவ்": "top 5",
        "டாப்5": "top 5",
        "டாப்பைவ்": "top 5",
        "டாப்பை 5": "top 5",
        "டாப்பை ஃபைவ்": "top 5",
        "டாப்பை பைவ்": "top 5",
        "டாப்பை5": "top 5",
    }
    for src, dst in top_phrase_replacements.items():
        query = query.replace(src, dst)
    query = re.sub(r"\b(?:டாப்|டாப்பை)\s*(\d{1,3})\b", r"top \1", query)

    replacements = {
        "தமிழ்நாடு": "tamil nadu",
        "தமிழ் நாடு": "tamil nadu",
        "தமிழக": "tamil nadu",
        "தமிழகம்": "tamil nadu",
        "தமிழில் பேசு": "switch tamil language",
        "தமிழ் மொழிக்கு மாறு": "switch tamil language",
        "தமிழுக்கு மாறு": "switch tamil language",
        "தமிழ் பேசு": "switch tamil language",
        "தமிழ்": "tamil",
        "ஆங்கிலத்தில் பேசு": "switch english language",
        "ஆங்கில மொழிக்கு மாறு": "switch english language",
        "ஆங்கிலத்துக்கு மாறு": "switch english language",
        "ஆங்கிலம் பேசு": "switch english language",
        "ஆங்கிலம்": "english",
        "இங்கிலீஷ் பேசு": "switch english language",
        "இங்கிலிஷ் பேசு": "switch english language",
        "இங்கிலீஷ்": "english",
        "இங்கிலிஷ்": "english",
        "இங்க்லீஷ்": "english",
        "english பேசு": "switch english language",
        "tamil பேசு": "switch tamil language",
        "ஸ்விட்ச் டு": "switch to",
        "சுவிட்ச் டு": "switch to",
        "ஸ்விட்ச்": "switch",
        "சுவிட்ச்": "switch",
        "சேஞ்ச்": "change",
        "இன்றோடு": "and also",
        "அண்ட்": "and",
        "அல்சோ": "also",
        "லாங்குவேஜ்": "language",
        "லேங்குவேஜ்": "language",
        "லேங்க்வேஜ்": "language",
        "டுடே": "today",
        "டே": "today",
        "நவ்": "now",
        "இப்போ": "now",
        "என்ன": "what",
        "எது": "what",
        "எப்படி": "how",
        "இருக்கு": "",
        "இருக்கிறது": "",
        "இன்று": "today",
        "இன்றைக்கு": "today",
        "இன்னைக்கு": "today",
        "ன்னைக்கு": "today",
        "நாளைக்கு": "tomorrow",
        "நாளை": "tomorrow",
        "அடுத்த வாரம்": "next week",
        "இந்த வாரம்": "this week",
        "டு": "to",
        "டூ": "to",
        "ஸ்பீக்": "speak",
        "ஸ்பீக்கு": "speak",
        "லிசன்": "listen",
        "கேட்கவில்லை": "not hearing",
        "கேட்க": "listen",
        "கேள்": "listen",
        "மைக்": "microphone",
        "மைக்ரோபோன்": "microphone",
        "மோட்": "mode",
        "இன்": "in",
        "ஆண் குரல்": "male voice",
        "ஆண் வாய்ஸ்": "male voice",
        "மேல் வாய்ஸ்": "male voice",
        "மேல் குரல்": "male voice",
        "மேல் voice": "male voice",
        "மேல்": "male",
        "மெயில் voice": "male voice",
        "பெண் குரல்": "female voice",
        "பெண் வாய்ஸ்": "female voice",
        "ஃபீமேல் வாய்ஸ்": "female voice",
        "பீமேல் வாய்ஸ்": "female voice",
        "ஃபீமேல்": "female",
        "பீமேல்": "female",
        "மொழி": "language",
        "பேசு": "speak",
        "மாறு": "switch",
        "மாற்று": "switch",
        "மோடு": "mode",
        "குரல்": "voice",
        "வாய்ஸ்": "voice",
        "வணக்கம் கியூபி": "hey cuby",
        "ஹே கியூபி": "hey cuby",
        "ஹே கியுபி": "hey cuby",
        "ஹே க்யூபி": "hey cuby",
        "ஹே குபி": "hey cuby",
        "ஹே கூபி": "hey cuby",
        "ஹே கோபி": "hey cuby",
        "கியூபி": "cuby",
        "கியுபி": "cuby",
        "க்யூபி": "cuby",
        "குபி": "cuby",
        "கூபி": "cuby",
        "கோபி": "cuby",
        "நேரம் என்ன": "time",
        "இப்போ நேரம்": "time",
        "நேரம்": "time",
        "மணி": "time",
        "தேதி": "date",
        "வானிலை": "weather",
        "வெதர்": "weather",
        "மழை": "rain",
        "பேட்டரி": "battery",
        "சார்ஜ்": "battery",
        "சிபியு": "cpu",
        "நினைவூட்டு": "remind me",
        "ஞாபகப்படுத்து": "remind me",
        "ரிமைண்டர்": "reminder",
        "பாட்டு": "song",
        "பாடல்": "song",
        "இசை": "music",
        "நிறுத்து": "stop",
        "திற": "open",
        "திறக்க": "open",
        "யூடியூப்": "youtube",
        "யூட்யூப்": "youtube",
        "ஸ்பாட்டிபை": "spotify",
        "நாக்ரி": "naukri",
        "நௌக்ரி": "naukri",
        "நாகுரி": "naukri",
        "வேலை": "job",
        "வேலைகள்": "jobs",
        "ஜாப்": "job",
        "ஜாப்ஸ்": "jobs",
        "அப்ளை": "apply",
        "அப்ளை பண்ணு": "apply",
        "பண்ணு": "",
        "பண்ணுங்கள்": "",
        "காலண்டர்": "calendar",
        "மீட்டிங்": "meeting",
        "தலைப்பு செய்திகள்": "headlines",
        "செய்திகள்": "news",
        "செய்தி": "news",
        "நியூஸ்": "news",
        "நியூசு": "news",
        "நியூஸு": "news",
        "ஹெட்லைன்": "headline",
        "ஹெட்லைன்ஸ்": "headlines",
        "அரசியல் செய்திகள்": "politics news",
        "அரசியல்": "politics",
        "பைனான்ஸ்": "finance",
        "நிதி": "finance",
        "பிசினஸ்": "business",
        "வியாபாரம்": "business",
        "மார்க்கெட்": "market",
        "விளையாட்டு": "sports",
        "கிரிக்கெட்": "cricket",
        "டெக்னாலஜி": "technology",
        "டெக்": "technology",
        "உலக": "global",
        "உலகம்": "global",
        "இந்தியா": "india",
        "இந்திய": "india",
        "திருச்சி": "trichy",
        "trichyல": "trichy",
        "trichyல்": "trichy",
        "சென்னை": "chennai",
        "chennaiல": "chennai",
        "chennaiல்": "chennai",
        "மதுரை": "madurai",
        "maduraiல": "madurai",
        "maduraiல்": "madurai",
        "கோயம்புத்தூர்": "coimbatore",
        "coimbatoreல": "coimbatore",
        "coimbatoreல்": "coimbatore",
        "பெங்களூர்": "bangalore",
        "bangaloreல": "bangalore",
        "bangaloreல்": "bangalore",
    }
    normalized = query
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    utility_phrase_replacements = {
        "கரண்ட் கட்": "current cut",
        "பவர் கட்": "power cut",
        "மின்தடை": "power cut",
        "மின்சாரம்": "power",
        "கரண்ட்": "current",
        "தண்ணீர்": "water",
        "தண்ணி": "water",
        "குடிநீர்": "drinking water",
        "நீர் விநியோகம்": "water supply",
        "நீர் நிறுத்தம்": "water cut",
        "பொன்னகர்": "ponnagar",
        "கருமண்டபம்": "karumandapam",
        "powercut": "power cut",
        "power-cut": "power cut",
        "currentcut": "current cut",
        "karent cut": "current cut",
        "karant cut": "current cut",
        "eb shutdown": "power shutdown",
        "eb current": "power",
        "tneb current": "tneb power",
        "tnpdcl current": "tnpdcl power",
        "watercut": "water cut",
        "water-cut": "water cut",
        "thanni": "water",
        "tanni": "water",
        "thanneer": "water",
        "ponnager": "ponnagar",
        "pon nagar": "ponnagar",
        "karumandabam": "karumandapam",
    }
    for src, dst in utility_phrase_replacements.items():
        normalized = normalized.replace(src, dst)
    normalized = re.sub(r"\btop\s+(\d{1,3})\s*(?:news|headlines)", r"top \1 news", normalized)
    normalized = re.sub(r"(?<!top )\b(\d{1,3})\s+(news|headlines)\b", r"top \1 \2", normalized)
    normalized = " ".join(normalized.split())
    return normalized


def _translate_remaining_tamil_query(query: str) -> str:
    query = str(query or "").strip()
    if not query or not _contains_tamil(query) or not _TRANSLATOR_AVAILABLE:
        return query

    key = (query, "en-intent")
    if key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[key]

    try:
        translated = GoogleTranslator(source="auto", target="en").translate(query)
        if translated:
            normalized = _normalize_local_language_query(translated.lower())
            _TRANSLATION_CACHE[key] = normalized
            return normalized
    except Exception as exc:
        print(f"Tamil command translation error: {exc}")
    return query


def normalize_user_query(query: str) -> str:
    normalized = _normalize_local_language_query(str(query).lower().strip())
    return _translate_remaining_tamil_query(normalized)


def _wake_aliases() -> tuple[str, ...]:
    return (
        "hey cuby", "hi cuby", "ok cuby", "hello cuby",
        "hey cupy", "hi cupy", "ok cupy", "hello cupy",
        "hey cuppy", "hey kuby", "hey kubi", "hey cubie", "hey cubi",
        "hey cubby", "hi cubby", "ok cubby", "hello cubby",
        "hey copy", "hi copy", "ok copy", "hello copy",
        "hey cubey", "hey quby", "hey qby", "hey cooby", "hey coby",
        "hey kavi", "hey gopi", "hey gobi", "hey goby", "hey gooby",
        "hey cube", "hi cube", "ok cube", "hello cube",
        "cuby", "cupy", "cuppy", "kuby", "kubi", "cubie", "cubi",
        "cubby", "cubey", "quby", "qby", "cooby", "coby",
        "kavi", "gopi", "gobi", "goby", "gooby", "cube",
    )


def _strip_wake_prefix(command: str) -> str:
    command = _normalize_local_language_query(str(command).lower().strip())
    for alias in sorted(_wake_aliases(), key=len, reverse=True):
        match = re.match(rf"^\s*{re.escape(alias)}[\s,.:;\-]+(.+)$", command)
        if match:
            return match.group(1).strip()
    return command


def _is_wake_command(command: str) -> bool:
    command = _normalize_local_language_query(command.lower()).strip()
    tamil_wake_names = (
        "கியூபி", "கியுபி", "க்யூபி", "குபி", "கூபி", "கோபி"
    )
    return (
        command in _wake_aliases()
        or command in {"wake", "wake up"}
        or command == "வணக்கம்"
        or (command.startswith("ஹே") and any(name in command for name in tamil_wake_names))
    )

# ── DB ─────────────────────────────────────────────────────────────────────
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
    global _LAST_SPOKE_AT
    speech_text = _text_for_speech(str(text))
    _record_ui_event("assistant", str(text))
    _safe_print(f"[CUBY] {text}")
    if get_assistant_language() == "tamil" and speech_text != str(text):
        _safe_print(f"[CUBY Tamil] {speech_text}")

    if get_assistant_language() == "tamil":
        if _speak_with_edge_tts(speech_text, "tamil"):
            _LAST_SPOKE_AT = time.monotonic()
            return
        if _speak_with_google_tts(speech_text, "ta"):
            _LAST_SPOKE_AT = time.monotonic()
            return
        print("Tamil TTS playback failed. Falling back to installed system voice.")

    if not _TTS_AVAILABLE:
        _LAST_SPOKE_AT = time.monotonic()
        return
    with _TTS_LOCK:
        engine = None
        try:
            engine = pyttsx3.init()
            _select_tts_voice(engine)
            engine.setProperty("rate", rate)
            engine.setProperty("volume", 1.0)
            engine.say(speech_text)
            engine.runAndWait()
        except Exception as exc:
            print(f"TTS error: {exc}")
        finally:
            if engine:
                try:
                    engine.stop()
                except Exception:
                    pass
            _LAST_SPOKE_AT = time.monotonic()


def _get_voice_recognizer():
    """Return one recognizer instance so mic sensitivity does not drift every turn."""
    global _VOICE_RECOGNIZER
    if _VOICE_RECOGNIZER is None:
        _VOICE_RECOGNIZER = sr.Recognizer()
        _VOICE_RECOGNIZER.pause_threshold = 0.9
        _VOICE_RECOGNIZER.phrase_threshold = 0.18
        _VOICE_RECOGNIZER.non_speaking_duration = 0.45
        _VOICE_RECOGNIZER.dynamic_energy_threshold = False
        _VOICE_RECOGNIZER.dynamic_energy_adjustment_damping = 0.12
        _VOICE_RECOGNIZER.dynamic_energy_ratio = 1.18
        _VOICE_RECOGNIZER.energy_threshold = 260
        _VOICE_RECOGNIZER.operation_timeout = VOICE_RECOGNITION_TIMEOUT
    return _VOICE_RECOGNIZER


def _clamp_voice_threshold(recognizer) -> None:
    recognizer.energy_threshold = max(
        VOICE_ENERGY_MIN,
        min(VOICE_ENERGY_MAX, recognizer.energy_threshold),
    )


def _reset_voice_recognizer():
    global _VOICE_RECOGNIZER
    _VOICE_RECOGNIZER = None
    return _get_voice_recognizer()


def _calibrate_microphone(recognizer, duration: float = 1.0) -> None:
    """Calibrate briefly and clamp threshold to a useful speech range."""
    try:
        with sr.Microphone() as source:
            print("calibrating microphone...")
            recognizer.adjust_for_ambient_noise(source, duration=duration)
            calibrated = recognizer.energy_threshold * VOICE_ENERGY_SCALE
            recognizer.energy_threshold = calibrated
            _clamp_voice_threshold(recognizer)
            print(f"microphone energy threshold: {recognizer.energy_threshold:.0f}")
    except Exception as exc:
        print(f"Microphone calibration skipped: {exc}")


def _voice_recognition_languages() -> list[str]:
    primary = _recognition_language()
    fallback = "en-IN" if primary.lower().startswith("ta") else "ta-IN"
    languages = [primary, fallback, "en-US"]
    unique = []
    for language in languages:
        if language not in unique:
            unique.append(language)
    return unique


def _pick_transcript(response) -> tuple[str, float]:
    if not response:
        return "", 0.0
    alternatives = response.get("alternative", []) if isinstance(response, dict) else []
    if not alternatives:
        return "", 0.0
    best = max(alternatives, key=lambda item: item.get("confidence", 0.0))
    transcript = str(best.get("transcript", "")).strip()
    confidence = float(best.get("confidence", 0.0) or 0.0)
    if transcript and confidence <= 0:
        confidence = 0.01
    return transcript, confidence


def _recognize_voice_audio(recognizer, audio) -> str:
    last_error = None
    best_transcript = ""
    best_confidence = 0.0
    for language in _voice_recognition_languages():
        try:
            response = recognizer.recognize_google(
                audio,
                language=language,
                show_all=True,
            )
            transcript, confidence = _pick_transcript(response)
            if transcript and confidence >= best_confidence:
                best_transcript = transcript
                best_confidence = confidence
                print(f"recognized candidate with {language} confidence={confidence:.2f}")
        except sr.UnknownValueError as exc:
            last_error = exc
            continue
        except sr.RequestError:
            raise
        except Exception as exc:
            last_error = exc
            continue
    if best_transcript:
        print(f"recognized best confidence={best_confidence:.2f}")
        return best_transcript.lower()
    if last_error:
        raise last_error
    raise sr.UnknownValueError()


def _capture_voice_audio(recognizer, source, seconds: int) -> sr.AudioData:
    timeout_seconds = max(2.0, min(float(seconds), float(VOICE_LISTEN_TIMEOUT)))
    phrase_limit = max(3.0, min(float(seconds), float(VOICE_PHRASE_TIME_LIMIT)))
    threshold = int(recognizer.energy_threshold)
    chunk = source.CHUNK
    sample_width = source.SAMPLE_WIDTH
    sample_rate = source.SAMPLE_RATE
    phrase_threshold = max(0.15, float(recognizer.phrase_threshold))
    pause_threshold = max(0.45, float(recognizer.pause_threshold))
    preroll_limit = max(1, int(sample_rate / chunk * VOICE_PREROLL_SECONDS))
    ambient = []
    preroll = []
    frames = []
    started = False
    speech_started_at = 0.0
    last_loud_at = 0.0
    start = time.monotonic()
    wait_deadline = start + timeout_seconds

    while True:
        now = time.monotonic()
        if not started and now >= wait_deadline:
            if ambient:
                ambient_peak = max(ambient)
                recognizer.energy_threshold = max(
                    VOICE_ENERGY_MIN,
                    min(VOICE_ENERGY_MAX, max(threshold, ambient_peak * 2.2)),
                )
            raise sr.WaitTimeoutError("listening timed out while waiting for phrase to start")
        if started and now - speech_started_at >= phrase_limit:
            break

        buffer = source.stream.read(chunk)
        if not buffer:
            continue
        rms = audioop.rms(buffer, sample_width)

        if not started:
            ambient.append(rms)
            if len(ambient) > VOICE_AMBIENT_SAMPLES:
                ambient.pop(0)
            preroll.append(buffer)
            if len(preroll) > preroll_limit:
                preroll.pop(0)
            if rms > threshold:
                started = True
                speech_started_at = now
                last_loud_at = now
                frames.extend(preroll)
                frames.append(buffer)
            continue

        frames.append(buffer)
        if rms > threshold * 0.72:
            last_loud_at = now
        elif now - speech_started_at >= phrase_threshold and now - last_loud_at >= pause_threshold:
            break

    if not frames:
        raise sr.WaitTimeoutError("no audio captured")
    return sr.AudioData(b"".join(frames), sample_rate, sample_width)


def takecommandexceptional(seconds: int = 5) -> str:
    """Listen for a voice command and return it as lowercase text."""
    global _VOICE_MISSES
    if not VOICE_AVAILABLE:
        return ""
    with _VOICE_LOCK:
        recognizer = _get_voice_recognizer()
        if _VOICE_MISSES >= VOICE_RECALIBRATE_AFTER:
            recognizer = _reset_voice_recognizer()
            _calibrate_microphone(recognizer)
            _VOICE_MISSES = 0
        _clamp_voice_threshold(recognizer)

        since_speech = time.monotonic() - _LAST_SPOKE_AT
        if since_speech < VOICE_AFTER_SPEAK_PAUSE:
            time.sleep(VOICE_AFTER_SPEAK_PAUSE - since_speech)

        try:
            with sr.Microphone() as source:
                print(f"listening... threshold={recognizer.energy_threshold:.0f}")
                audio = _capture_voice_audio(recognizer, source, seconds)
            query = _recognize_voice_audio(recognizer, audio)

            aliases = [
                "qb", "cubi", "cubie", "kibi", "kooby", "cooby",
                "koobie", "cubye", "cuban", "kirban", "hey google",
                "killbe", "killby", "cubic", "cubyc", "hey cupy",
                "hey cuppy", "hey kuby", "hey cubby", "hey copy",
                "hi copy", "ok copy", "hello copy", "hey cubey",
                "hey kubi", "hey kavi", "hey gopi", "hey gobi",
                "hey goby", "hey gooby", "hey cube", "hi cube",
                "ok cube", "hello cube", "hey quby", "hey qby",
                "cupy", "cuppy", "kuby", "kubi", "cubby", "cubey",
                "quby", "qby", "kavi", "gopi", "gobi", "goby", "gooby", "cube",
            ]
            for alias in aliases:
                if alias in query:
                    query = query.replace(alias, "hey cuby")
            query = _normalize_local_language_query(query)
            _VOICE_MISSES = 0
            print(f"[heard] {query}")
            _record_ui_event("user", query)
            return query
        except sr.WaitTimeoutError:
            _VOICE_MISSES += 1
            _clamp_voice_threshold(recognizer)
            print("No speech detected.")
            return ""
        except sr.UnknownValueError:
            _VOICE_MISSES += 1
            recognizer.energy_threshold = min(
                VOICE_ENERGY_MAX,
                max(VOICE_ENERGY_MIN, recognizer.energy_threshold * 1.08),
            )
            print("Could not understand audio.")
            return ""
        except sr.RequestError as exc:
            _VOICE_MISSES += 1
            print(f"Recognition service error: {exc}")
            return ""
        except Exception as exc:
            _VOICE_MISSES += 1
            print(f"Recognition error: {exc}")
            return ""


# ══════════════════════════════════════════════════════════════════════════
# Startup / shutdown
# ══════════════════════════════════════════════════════════════════════════

def startup() -> None:
    global RUNNING
    reset_assistant_language_for_startup()
    if not VOICE_AVAILABLE:
        print("CUBY started (no voice — PyAudio missing).")
        return
    RUNNING = True
    _calibrate_microphone(_get_voice_recognizer())
    print("CUBY started. Listening…")
    while RUNNING:
        try:
            command = takecommandexceptional(5)
            if not command:
                continue
            if _is_wake_command(command):
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
            break
        except Exception as exc:
            print(f"CUBY loop error: {exc}")
            speak("Sorry, that command failed. I am still listening.")


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
    action = data.get("browser_action") if isinstance(data, dict) else None
    if isinstance(action, dict):
        _set_browser_action(action)
    elif isinstance(data, dict) and data.get("url"):
        _set_browser_action({
            "type": "open_url",
            "url": data["url"],
            "target": "_blank",
        })

    # --- daily briefing ---
    if "briefing" in data:
        briefing = data["briefing"]
        sections = briefing.get("sections", [])
        if not sections:
            summary = "Daily briefing is ready, but I could not find anything important right now."
            _record_ui_event("briefing", summary, briefing)
            speak(summary)
            return summary

        _record_ui_event("briefing", "Daily briefing", briefing)
        speak("Here is your daily briefing.")
        for section in sections[:8]:
            title = section.get("title", "")
            text = section.get("text", "")
            speak(f"{title}. {text}" if title else text)
        return "\n".join(
            f"{section.get('title', 'Update')}: {section.get('text', '')}"
            for section in sections
        )

    # --- weather ---
    if "temperature_c" in data:
        summary = data.get("summary") or (
            f"Weather in {data.get('city', '')}: "
            f"{data['temperature_c']} degrees Celsius, "
            f"{data.get('condition', '')}, "
            f"wind {data.get('windspeed_kmh', '')} km/h."
        )
        is_future_or_week = bool(data.get("target_forecast") or data.get("weekly_summary"))
        if "humidity_pct" in data and not is_future_or_week:
            summary += f" Humidity {data['humidity_pct']} percent."
        if data.get("target_forecast") and data["target_forecast"].get("rain_periods"):
            grouped = {}
            for item in data["target_forecast"]["rain_periods"]:
                period = item.get("period", "that day")
                current = grouped.setdefault(period, {
                    "period": period,
                    "time_label": item.get("time_label", "soon"),
                    "rain_probability_pct": item.get("rain_probability_pct", 0),
                })
                if (item.get("rain_probability_pct") or 0) > (current.get("rain_probability_pct") or 0):
                    current["rain_probability_pct"] = item.get("rain_probability_pct", 0)
            timing = "; ".join(
                f"{item['period']} from {item['time_label']} {item['rain_probability_pct']} percent chance"
                for item in list(grouped.values())[:3]
            )
            summary += f" Rain timing: {timing}."
        elif not is_future_or_week and data.get("rain_periods_today"):
            timing = "; ".join(
                (
                    f"{item.get('period', 'today')} from "
                    f"{item.get('first_time_label', 'soon')} "
                    f"{item.get('max_probability_pct', 0)} percent chance"
                )
                for item in data["rain_periods_today"][:3]
            )
            summary += f" Rain timing today: {timing}."
        if data.get("smart_advice"):
            advice = data["smart_advice"]
            if data.get("rain_expected") and len(advice) > 1:
                summary += " " + advice[1]
            elif not data.get("rain_expected"):
                summary += " " + " ".join(advice[:2])
        _record_ui_event("weather", summary, data)
        speak(summary)
        return summary

    # --- Gmail interviews / meetings ---
    if "interviews" in data:
        emails = data["interviews"]
        if not emails:
            summary = "No interview, assessment, or meeting emails found recently."
            speak(summary)
            return summary
        speak(f"Found {len(emails)} interview, assessment, or meeting emails.")
        for i, email in enumerate(emails[:3], 1):
            speak(f"{i}. {email.get('subject', 'No subject')}")
        return "\n".join(
            f"{i+1}. {email.get('subject', 'No subject')} - {email.get('from', '')}"
            for i, email in enumerate(emails)
        )

    # --- Google Calendar meetings / events ---
    if "calendar_events" in data:
        events = data["calendar_events"]
        timeframe = data.get("timeframe", "today")
        if not events:
            summary = f"No calendar events found for {timeframe}."
            speak(summary)
            return summary
        speak(f"Found {len(events)} calendar event(s) for {timeframe}.")
        for i, event in enumerate(events[:3], 1):
            title = event.get("summary", "No title")
            when = event.get("start_text", "")
            speak(f"{i}. {title} at {when}.")
        return "\n".join(
            f"{i+1}. {event.get('summary', 'No title')} - {event.get('start_text', '')}"
            for i, event in enumerate(events)
        )

    # --- local reminders ---
    if "reminder" in data:
        speak(msg)
        return msg

    if "reminders" in data:
        reminders = data["reminders"]
        if not reminders:
            summary = "No active reminders."
            speak(summary)
            return summary
        speak(f"You have {len(reminders)} reminder(s).")
        for reminder in reminders[:3]:
            due = reminder.get("due_text", "")
            line = f"{reminder.get('number', '')}. {reminder.get('text', '')}"
            if due:
                line += f" at {due}"
            speak(line)
        return "\n".join(
            (
                f"{reminder.get('number', i + 1)}. {reminder.get('text', '')}"
                + (f" - {reminder.get('due_text', '')}" if reminder.get("due_text") else "")
            )
            for i, reminder in enumerate(reminders)
        )

    # --- power / water utility alerts ---
    if "alerts" in data and "source_status" in data:
        alerts = data.get("alerts", [])
        location = data.get("location", "your area")
        if not alerts:
            summary = data.get("summary") or f"No power or water cut notice found for {location} right now."
            _record_ui_event("utility", summary, data)
            speak(summary)
            return summary

        official_count = sum(1 for alert in alerts if alert.get("official"))
        if official_count:
            speak(f"Found {len(alerts)} utility alert(s) for {location}, including {official_count} official match.")
        else:
            speak(f"Found {len(alerts)} possible utility alert(s) for {location} from public sources.")
        for i, alert in enumerate(alerts[:3], 1):
            label = "Power" if alert.get("type") == "power" else "Water"
            title = alert.get("title") or alert.get("snippet", "")
            confidence = alert.get("confidence", "low")
            speak(f"{i}. {label} alert, {confidence} confidence. {title}")
        summary = "\n".join(
            f"{i+1}. {alert.get('type', 'utility').title()} - "
            f"{alert.get('title') or alert.get('snippet', '')} "
            f"({alert.get('confidence', 'low')} confidence)"
            for i, alert in enumerate(alerts)
        )
        _record_ui_event("utility", summary, data)
        return summary

    # --- train pages ---
    if data.get("action") in {"availability", "book", "pnr", "status"} and "url" in data:
        speak(msg)
        return msg

    # --- news ---
    if "articles" in data:
        articles = data["articles"]
        requested = data.get("count_requested") or len(articles)
        topic = data.get("query") or data.get("category") or "latest news"
        fresh_hours = data.get("fresh_hours", 48)
        if not articles:
            summary = f"No current news headlines found for {topic} in the last {fresh_hours} hours."
            speak(summary)
            return summary

        spoken_limit = min(len(articles), 20)
        if len(articles) > spoken_limit:
            speak(
                f"Found {len(articles)} current headlines for {topic} from the last {fresh_hours} hours. "
                f"Reading the first {spoken_limit}."
            )
        else:
            speak(f"Here are the top {len(articles)} current headlines for {topic} from the last {fresh_hours} hours.")

        for i, a in enumerate(articles[:spoken_limit], 1):
            speak(f"{i}. {a.get('title', 'No title')}")
        return "\n".join(f"{i+1}. {a.get('title', 'No title')}"
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
    # --- app launch ---
    speak(msg)
    return msg


# ──────────────────────────────────────────────────────────────────────────
# MCP command classifier  (called from main() and chatbot())
# ──────────────────────────────────────────────────────────────────────────

_WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _calendar_target_date_from_query(q: str) -> str:
    today = datetime.datetime.now().astimezone().date()
    for weekday, index in _WEEKDAY_INDEX.items():
        if weekday in q:
            days_ahead = (index - today.weekday()) % 7
            if days_ahead == 0 and "next" in q:
                days_ahead = 7
            return (today + datetime.timedelta(days=days_ahead)).isoformat()
    return ""


def _gmail_timeframe_for_calendar_fallback(timeframe: str, target_date: str) -> str:
    today = datetime.datetime.now().astimezone().date()
    if target_date:
        try:
            date_value = datetime.date.fromisoformat(target_date)
            if date_value == today:
                return "today"
            if date_value == today + datetime.timedelta(days=1):
                return "tomorrow"
            return "last week"
        except Exception:
            pass
    if timeframe == "today":
        return "today"
    if timeframe == "tomorrow":
        return "tomorrow"
    return "last week"


def _calendar_api_disabled(result: dict) -> bool:
    data = result.get("data") or {}
    return data.get("reason") == "calendar_api_disabled"


def _parse_reminder_due_at(q: str) -> str:
    import re

    now = datetime.datetime.now().astimezone()

    relative = re.search(
        r"\bin\s+(\d+)\s*(minute|minutes|hour|hours|day|days)\b",
        q,
    )
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        if unit.startswith("minute"):
            return (now + datetime.timedelta(minutes=amount)).isoformat()
        if unit.startswith("hour"):
            return (now + datetime.timedelta(hours=amount)).isoformat()
        return (now + datetime.timedelta(days=amount)).isoformat()

    target_date = _calendar_target_date_from_query(q)
    if "tomorrow" in q:
        target_date = (now.date() + datetime.timedelta(days=1)).isoformat()
    elif "today" in q and not target_date:
        target_date = now.date().isoformat()

    time_match = re.search(
        r"\b(?:at|by)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        q,
    )
    if not time_match:
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", q)

    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridian = (time_match.group(3) or "").lower()

        if meridian == "pm" and hour < 12:
            hour += 12
        elif meridian == "am" and hour == 12:
            hour = 0

        date_value = datetime.date.fromisoformat(target_date) if target_date else now.date()
        due = datetime.datetime.combine(
            date_value,
            datetime.time(hour=hour, minute=minute),
            tzinfo=now.tzinfo,
        )
        if not target_date and due <= now:
            due += datetime.timedelta(days=1)
        return due.isoformat()

    if target_date:
        date_value = datetime.date.fromisoformat(target_date)
        return datetime.datetime.combine(
            date_value,
            datetime.time(hour=9),
            tzinfo=now.tzinfo,
        ).isoformat()

    return ""


def _parse_reminder_text(q: str) -> str:
    import re

    text = q
    text = re.sub(r"^\s*(please\s+)?", "", text)
    text = re.sub(r"\b(remind me to|remind me|set a reminder to|set reminder to|set a reminder|set reminder|add a reminder to|add reminder to|add a reminder|add reminder)\b", "", text)
    text = re.sub(r"\bin\s+\d+\s*(minute|minutes|hour|hours|day|days)\b", "", text)
    text = re.sub(r"\b(?:at|by)\s+\d{1,2}(?::\d{2})?\s*(am|pm)?\b", "", text)
    text = re.sub(r"\b\d{1,2}(?::\d{2})?\s*(am|pm)\b", "", text)
    text = re.sub(r"\b(today|tomorrow|this week|next week|please)\b", "", text)
    for weekday in _WEEKDAY_INDEX:
        text = re.sub(rf"\b(next\s+)?{weekday}\b", "", text)
    text = re.sub(r"\s+", " ", text).strip(" .,-")
    if text.startswith("to "):
        text = text[3:].strip()
    if text.startswith("for "):
        text = text[4:].strip()
    return text or "your reminder"


def _reminder_id_from_query(q: str) -> str:
    import re

    if re.search(r"\b(all|everything|every reminder|all reminders)\b", q):
        return "all"

    match = re.search(
        r"\b(?:reminder|task|number|id)\s*(?:number|id)?\s+(\d+|[a-f0-9]{6,})\b",
        q,
    )
    if match:
        return match.group(1)

    cleaned = re.sub(
        r"\b(cancel|delete|remove|complete|done|finish|finished|reminder|"
        r"reminders|task|tasks|number|please|the|and)\b",
        " ",
        q,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    if cleaned:
        return cleaned

    words = re.findall(r"\b[a-z0-9]+\b", q)
    return words[-1] if words else ""


def _detect_voice_gender_switch(q: str) -> str:
    import re

    if "female" in q:
        gender = "female"
    elif re.search(r"\bmale\b", q):
        gender = "male"
    else:
        return ""

    switch_words = ("voice", "switch", "change", "gender", "speak")
    if q.strip() in {"male", "female"} or any(word in q for word in switch_words):
        return gender
    return ""


def _detect_language_switch(q: str) -> str:
    if "tamil" in q:
        language = "tamil"
    elif "english" in q:
        language = "english"
    else:
        return ""

    switch_words = ("language", "speak", "mode", "switch", "change", "listen")
    direct_phrases = {
        "tamil", "english",
        "speak tamil", "speak english",
        "tamil speak", "english speak",
        "tamil language", "english language",
        "switch tamil", "switch english",
    }
    if q.strip() in direct_phrases or any(word in q for word in switch_words):
        return language
    return ""


def _parse_news_request(q: str) -> dict:
    import re

    count_match = re.search(r"\btop\s*(\d{1,3})\b", q)
    if not count_match:
        count_match = re.search(r"\b(?:first|latest|show|get)\s+(\d{1,3})\b", q)
    if not count_match and ("news" in q or "headline" in q):
        count_match = re.search(r"\b(\d{1,3})\b", q)
    count = int(count_match.group(1)) if count_match else 5
    count = max(1, min(count, 100))
    fresh_hours = 48
    if any(word in q for word in ("today", "current", "now", "breaking", "live")):
        fresh_hours = 24
    elif any(word in q for word in ("this week", "weekly", "week")):
        fresh_hours = 168

    def has_alias(text: str, alias: str) -> bool:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text))

    locations = [
        (("trichy", "tiruchirappalli"), "trichy", "Trichy Tamil Nadu"),
        (("tamil nadu", "tamilnadu", "tn", "tamil"), "tamilnadu", "Tamil Nadu"),
        (("indian", "india", "bharat"), "india", "India"),
        (("global", "world", "international"), "global", "world international"),
    ]
    topics = [
        (("political", "politics", "election", "government"), "politics", "politics"),
        (("finance", "financial", "market", "stock", "stocks", "business", "finaus"), "finance", "finance business markets"),
        (("weather", "rain", "climate"), "weather", "weather"),
        (("technology", "tech", "ai"), "technology", "technology"),
        (("sports", "cricket"), "sports", "sports"),
        (("health", "medical"), "health", "health"),
        (("science",), "science", "science"),
    ]

    category = "general"
    query = ""

    location_category = ""
    location_query = ""
    for aliases, cat, search_query in locations:
        if any(has_alias(q, alias) for alias in aliases):
            location_category = cat
            location_query = search_query
            break

    topic_category = ""
    topic_query = ""
    for aliases, cat, search_query in topics:
        if any(has_alias(q, alias) for alias in aliases):
            topic_category = cat
            topic_query = search_query
            break

    if topic_query and location_query:
        category = topic_category
        query = f"{topic_query} {location_query}"
    elif topic_query:
        category = topic_category
        default_location = "" if topic_category == "science" else " India"
        query = f"{topic_query}{default_location}"
    elif location_query:
        category = location_category
        query = location_query

    cleaned = q
    cleaned = re.sub(r"\btop\s*\d{1,3}\b", " ", cleaned)
    cleaned = re.sub(r"\b(?:first|latest|show|get)\s+\d{1,3}\b", " ", cleaned)
    for word in (
        "news", "headline", "headlines", "latest", "top", "please",
        "tell me", "show me", "give me", "today", "current"
    ):
        cleaned = cleaned.replace(word, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned and not query:
        query = cleaned
        category = "search"

    return {
        "category": category,
        "query": query,
        "count": count,
        "fresh_hours": fresh_hours,
    }


def _is_news_request(q: str) -> bool:
    import re

    if "news" in q or "headline" in q:
        return True
    if re.search(r"\btop\s*\d{1,3}\b", q):
        return True
    if "latest" in q:
        if any(word in q for word in ("weather", "rain", "temperature", "forecast")):
            return False
        return any(
            word in q
            for word in (
                "india", "indian", "tamil nadu", "tamilnadu", "trichy",
                "tiruchirappalli", "global", "world", "politic", "finance",
                "business", "market", "sports", "cricket", "technology",
                "tech", "health", "science",
            )
        )
    return False


def _is_briefing_request(q: str) -> bool:
    phrases = (
        "briefing",
        "daily brief",
        "morning brief",
        "what is my day",
        "start my day",
        "today summary",
        "daily summary",
        "overall summary",
        "full summary",
        "summarize my day",
        "summarise my day",
        "summarize today",
        "summarise today",
        "important updates",
        "important update",
        "important today",
        "today important",
        "what is important today",
        "anything important",
        "check everything",
        "events and reminders",
        "reminders and events",
        "collective summary",
    )
    return any(phrase in q for phrase in phrases)


def _is_utility_alert_request(q: str) -> bool:
    power_words = (
        "power cut", "powercut", "power shutdown", "power outage",
        "electricity cut", "electric cut", "current cut", "karent cut",
        "karant cut", "eb cut", "tneb", "tangedco", "tnpdcl",
        "no power", "power failure",
    )
    water_words = (
        "water cut", "water shutdown", "water outage", "water supply",
        "water interruption", "water problem", "drinking water",
        "no water", "water not coming", "thanni", "tanni", "thanneer",
        "corporation water",
    )
    alert_words = (
        "alert", "available", "availability", "is there", "any", "today",
        "tomorrow", "this week", "information", "info", "check", "update",
        "cut", "shutdown", "outage", "interruption", "suspended",
        "come", "coming", "not coming", "problem", "issue",
        "varatha", "varaatha", "varātha", "varadhu", "varuma", "varumaa",
    )
    has_power = any(word in q for word in power_words)
    has_water = any(word in q for word in water_words)
    has_alert_context = any(word in q for word in alert_words)
    if has_power or has_water:
        return True
    if ("power" in q or "electricity" in q or "current" in q) and has_alert_context:
        return True
    if "water" in q and has_alert_context:
        return True
    return False


def _parse_utility_alert_request(q: str) -> dict:
    import re

    power_markers = (
        "power", "powercut", "electricity", "electric", "current",
        "eb", "tneb", "tangedco", "tnpdcl",
    )
    water_markers = ("water", "thanni", "tanni", "thanneer", "drinking water")
    has_power = any(marker in q for marker in power_markers)
    has_water = any(marker in q for marker in water_markers)
    if has_power and not has_water:
        kind = "power"
    elif has_water and not has_power:
        kind = "water"
    else:
        kind = "all"
    action = "check"
    if any(word in q for word in ("official", "confirm", "confirmation", "captcha", "tnpdcl", "tangedco", "tneb")) and kind in {"power", "all"}:
        action = "confirm_power"
        kind = "power"

    location_aliases = {
        "ponnager": "Ponnagar",
        "ponnagar": "Ponnagar",
        "pon nagar": "Ponnagar",
        "ponagar": "Ponnagar",
        "karumandapam": "Karumandapam",
        "karumandabam": "Karumandapam",
        "trichy": "Trichy",
        "tiruchirappalli": "Trichy",
        "tiruchi": "Trichy",
    }
    found = []
    for alias, display in location_aliases.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", q):
            if display not in found:
                found.append(display)

    location = ", ".join(found) if found else getattr(
        app_settings,
        "UTILITY_ALERT_LOCATION",
        "Ponnagar, Karumandapam, Trichy",
    )
    if "Trichy" not in location and "Tiruchirappalli" not in location:
        location = f"{location}, Trichy"

    days = 7
    if "today" in q or "tonight" in q:
        days = 2
    elif "tomorrow" in q:
        days = 3
    elif "week" in q:
        days = 7

    return {
        "action": action,
        "kind": kind,
        "location": location,
        "city": "Trichy",
        "days": days,
        "query": q,
        "max_results": 6,
        "official_wait_seconds": 150,
    }


def _parse_weather_request(q: str) -> dict:
    import re

    now = datetime.datetime.now().astimezone()
    target_date = ""
    timeframe = "today"
    forecast = False

    if "day after tomorrow" in q or "after tomorrow" in q:
        target_date = (now.date() + datetime.timedelta(days=2)).isoformat()
        timeframe = "day_after_tomorrow"
        forecast = True
    elif any(word in q for word in ("tomorrow", "tmorrow", "tomorow")):
        target_date = (now.date() + datetime.timedelta(days=1)).isoformat()
        timeframe = "tomorrow"
        forecast = True
    elif (
        "week after" in q
        or "after week" in q
        or "after a week" in q
        or "after one week" in q
        or "one week later" in q
    ):
        target_date = (now.date() + datetime.timedelta(days=7)).isoformat()
        timeframe = "after_week"
        forecast = True
    elif "next week" in q or "this week" in q or "weekly" in q or "week forecast" in q or "next 7 days" in q:
        timeframe = "week"
        forecast = True

    if "forecast" in q or "7 day" in q or "seven day" in q:
        forecast = True
        if timeframe == "today":
            timeframe = "week"

    cleaned = q
    temporal_phrases = (
        "day after tomorrow", "after tomorrow", "week after", "after a week",
        "after one week", "one week later", "after week", "next week",
        "this week", "week forecast", "next 7 days",
        "tomorrow", "tmorrow", "tomorow", "today", "tonight",
        "morning", "afternoon", "evening", "night",
    )
    for phrase in temporal_phrases:
        cleaned = cleaned.replace(phrase, " ")
    cleaned = re.sub(
        r"\b(?:what|is|the|weather|temperature|forecast|rain|update|live|"
        r"smart|status|condition|conditions|please|tell|me|show|for|in|at|"
        r"on|of|will|there|be|any|now|current)\b",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    city = cleaned or app_settings.WEATHER_ALERT_CITY or "Chennai"

    return {
        "city": city,
        "forecast": forecast,
        "target_date": target_date,
        "timeframe": timeframe,
        "rain_alert_hours": max(app_settings.WEATHER_ALERT_HOURS, 24),
    }


def _clean_train_station(value: str) -> str:
    import re

    value = value or ""
    value = re.sub(r"\b\d{1,2}(?::\d{2})?\b", " ", value)
    value = re.sub(r"\b(?:a\.?m\.?|p\.?m\.?|am|pm)\b", " ", value)
    value = re.sub(
        r"\b(?:check|the|my|train|trains|ticket|tickets|information|info|"
        r"availability|available|seat|seats|please|today|tomorrow|tonight|"
        r"night|morning|evening|at|around|after|before|from|to|on|for|book|"
        r"booking|irctc)\b",
        " ",
        value,
    )
    return re.sub(r"\s+", " ", value).strip()


def _parse_train_route(q: str) -> tuple[str, str]:
    import re

    stop_words = (
        "today", "tomorrow", "tonight", "night", "morning", "evening",
        "availability", "available", "seat", "seats", "ticket", "tickets",
        "train", "trains", "book", "booking", "irctc", "on", "for", "at",
        "around", "after", "before",
    )
    stop_pattern = "|".join(stop_words)

    from_station = ""
    to_station = ""

    from_to_match = re.search(
        rf"\bfrom\s+(.+?)\s+to\s+(.+?)(?=\s+(?:{stop_pattern})\b|$)",
        q,
    )
    if from_to_match:
        from_station = _clean_train_station(from_to_match.group(1))
        to_station = _clean_train_station(from_to_match.group(2))
        return from_station, to_station

    route_match = re.search(
        rf"(.+?)\s+to\s+(.+?)(?=\s+(?:{stop_pattern})\b|$)",
        q,
    )
    if route_match:
        origin_text = re.split(
            r"\b(?:train|trains|ticket|tickets|information|info|availability|"
            r"check|book|booking|irctc)\b",
            route_match.group(1),
        )[-1]
        from_station = _clean_train_station(origin_text)
        to_station = _clean_train_station(route_match.group(2))

    return from_station, to_station


def _parse_job_request(q: str) -> dict:
    import re

    platform = "linkedin"
    if "naukri" in q:
        platform = "naukri"
    elif "indeed" in q:
        platform = "indeed"
    elif "linkedin" in q:
        platform = "linkedin"

    wants_apply = (
        "auto apply" in q
        or "guided apply" in q
        or "apply job" in q
        or "apply jobs" in q
        or ("apply" in q and ("job" in q or "jobs" in q or "naukri" in q))
    )

    max_jobs = 5
    number_match = re.search(r"\b(?:top|first|apply|max|maximum)?\s*(\d{1,2})\s+(?:job|jobs)\b", q)
    if number_match:
        max_jobs = max(1, min(int(number_match.group(1)), 20))

    location_aliases = {
        "tiruchirappalli": "trichy",
        "trichy": "trichy",
        "chennai": "chennai",
        "tamilnadu": "tamil nadu",
        "tamil nadu": "tamil nadu",
        "bangalore": "bangalore",
        "bengaluru": "bangalore",
        "coimbatore": "coimbatore",
        "madurai": "madurai",
        "hyderabad": "hyderabad",
        "pune": "pune",
        "mumbai": "mumbai",
        "india": "india",
        "remote": "remote",
    }
    location = "remote"
    for alias, value in location_aliases.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", q):
            location = value
            break
    if platform == "naukri" and wants_apply and location == "remote":
        location = "tamil nadu"

    role_aliases = [
        (("gen ai", "generative ai"), "Generative AI Engineer"),
        (("ai engineer", "artificial intelligence"), "AI Engineer"),
        (("python developer", "python"), "Python Developer"),
        (("machine learning", "ml engineer", "ml"), "Machine Learning Engineer"),
        (("data scientist",), "Data Scientist"),
        (("data analyst",), "Data Analyst"),
        (("software engineer", "software developer"), "Software Engineer"),
        (("java developer", "java"), "Java Developer"),
        (("frontend", "front end"), "Frontend Developer"),
        (("backend", "back end"), "Backend Developer"),
        (("full stack", "fullstack"), "Full Stack Developer"),
        (("devops",), "DevOps Engineer"),
        (("testing", "qa"), "QA Engineer"),
    ]
    roles = []
    for aliases, mapped_role in role_aliases:
        if any(alias in q for alias in aliases):
            roles.append(mapped_role)

    if not roles and platform == "naukri" and wants_apply:
        roles = ["Generative AI Engineer", "Python Developer"]

    if not roles:
        role_text = ""
        role_match = re.search(
            r"\b(?:for|as|role|position|title)\s+(.+?)(?=\s+(?:in|at|on|near|remote|naukri|linkedin|indeed|job|jobs|apply)\b|$)",
            q,
        )
        if role_match:
            role_text = role_match.group(1)
        else:
            role_text = re.sub(
                r"\b(?:auto|guided|apply|open|search|find|show|get|naukri|linkedin|indeed|"
                r"job|jobs|hiring|vacancy|vacancies|in|at|near|for|as|role|position|"
                r"title|me|please|today)\b",
                " ",
                q,
            )
            for alias in location_aliases:
                role_text = re.sub(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", " ", role_text)
            role_text = re.sub(r"\b\d{1,2}\b", " ", role_text)
        roles = [re.sub(r"\s+", " ", role_text).strip(" .,-").title() or "AI Engineer"]

    return {
        "platform": platform,
        "role": roles[0],
        "roles": roles,
        "location": location,
        "action": "guided_apply" if wants_apply else "search",
        "auto_apply": wants_apply,
        "max_jobs": max_jobs,
    }


def _normalize_mail_command_phrase(q: str) -> str:
    value = f" {q.lower().strip()} "
    replacements = {
        " sentamil ": " send mail ",
        " send tamil ": " send mail ",
        " sent mail ": " send mail ",
        " send a email ": " send email ",
        " send an email ": " send email ",
        " compose mail ": " send mail ",
        " compose email ": " send email ",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    return re.sub(r"\s+", " ", value).strip()


def _extract_voice_email_address(q: str) -> str:
    value = q.lower()
    value = re.sub(r"\bg\s*mail\b", "gmail", value)
    value = re.sub(r"\bdot\b", ".", value)
    value = re.sub(r"\s*\.\s*", ".", value)
    value = re.sub(r"\b(?:at|add|ad)\b", "@", value)
    value = re.sub(r"\b(?:r|are|our)\s+gmail\.com\b", "@gmail.com", value)
    value = re.sub(r"(?<!@)\bgmail\.com\b", "@gmail.com", value)

    candidates = []
    for marker in (" to ", " for "):
        if marker in value:
            candidates.append(value.split(marker, 1)[1])
    candidates.append(value)

    email_pattern = re.compile(
        r"[a-z0-9._%+\-]+@[a-z0-9.\-]+?\.(?:com|in|org|net|edu|co\.in)"
    )
    for candidate in candidates:
        compact = re.sub(r"\s+", "", candidate)
        match = email_pattern.search(compact)
        if match:
            return match.group(0)
    return ""


def _is_app_list_request(query: str) -> bool:
    q = query.strip().lower()
    return (
        q in {
            "list apps",
            "list applications",
            "show apps",
            "show applications",
            "show installed apps",
            "show installed applications",
            "what apps are installed",
        }
        or q.startswith(("list apps ", "show apps ", "find app ", "find apps "))
    )


def _extract_app_list_filter(query: str) -> str:
    q = query.strip().lower()
    for marker in (" matching ", " called ", " named ", " for "):
        if marker in q:
            return q.split(marker, 1)[1].strip()
    for prefix in ("list apps", "show apps", "find apps", "find app"):
        if q.startswith(prefix):
            return q[len(prefix):].strip()
    return ""


def _extract_app_target(query: str, triggers: tuple[str, ...]) -> str:
    q = query.strip()
    for trigger in triggers:
        if q.startswith(trigger):
            target = q[len(trigger):].strip()
            for filler in (
                "the app",
                "application",
                "app",
                "program",
                "software",
                "please",
            ):
                target = re.sub(rf"\b{re.escape(filler)}\b", "", target).strip()
            return re.sub(r"\s+", " ", target)
    return ""


def _open_play_request(query: str) -> tuple[str, str] | None:
    q = query.strip().lower()
    if not q.startswith(("open ", "launch ", "start ", "run ")):
        return None
    if "play" not in q:
        return None

    platform = ""
    if "spotify" in q:
        platform = "spotify"
    elif "youtube" in q:
        platform = "youtube"
    if not platform:
        return None

    song = q.split("play", 1)[1].strip()
    for phrase in (
        f"on {platform}",
        f"in {platform}",
        f"from {platform}",
        platform,
        "song",
        "music",
        "please",
    ):
        song = re.sub(rf"\b{re.escape(phrase)}\b", "", song).strip()
    song = re.sub(r"\s+", " ", song)
    if not song:
        song = q
    return platform, song


def _try_mcp(query: str) -> str | None:
    """
    Parse the voice/text query for MCP intent.
    Returns a spoken response string, or None if no MCP tool matched.
    """
    import re
    q = normalize_user_query(query)
    q = _normalize_mail_command_phrase(q)

    gender = _detect_voice_gender_switch(q)
    language = _detect_language_switch(q)
    if gender and language:
        set_voice_gender(gender)
        set_assistant_language(language)
        msg = f"Switched to {language} language and {gender} voice."
        speak(msg)
        return msg

    if gender:
        msg = set_voice_gender(gender)
        speak(msg)
        return msg

    if language:
        msg = set_assistant_language(language)
        speak(msg)
        return msg

    if (
        "calibrate microphone" in q
        or "calibrate mic" in q
        or "reset microphone" in q
        or "reset mic" in q
        or "mic sensitivity" in q
        or "microphone sensitivity" in q
        or "voice recognition" in q
        or "not hearing" in q
        or "not listening" in q
    ):
        recognizer = _reset_voice_recognizer()
        _calibrate_microphone(recognizer, duration=1.2)
        msg = (
            "Microphone recalibrated. "
            f"Current speech sensitivity threshold is {recognizer.energy_threshold:.0f}."
        )
        speak(msg)
        return msg

    media_open = _open_play_request(q)
    if media_open:
        platform, song = media_open
        result = mcp.run(
            "media_control",
            action="play",
            platform=platform,
            query=song,
        )
        return _speak_result(result)

    if _is_app_list_request(q):
        result = mcp.run(
            "app_launcher",
            action="list",
            target=_extract_app_list_filter(q),
        )
        return _speak_result(result)

    _close_triggers = ("close ", "quit ", "exit ")
    if q.startswith(_close_triggers):
        target = _extract_app_target(q, _close_triggers)
        if target in {"all", "all apps", "everything", "all applications"}:
            msg = "For safety, I will not close every app at once. Tell me the app name to close."
            speak(msg)
            return msg
        result = mcp.run("app_launcher", action="close", target=target)
        return _speak_result(result)

    if _is_briefing_request(q):
        city = app_settings.WEATHER_ALERT_CITY
        for marker in ("for ", "in "):
            if marker in q:
                possible_city = q.split(marker, 1)[1].strip()
                for filler in (
                    "today", "please", "briefing", "daily brief", "morning brief",
                    "summary", "overall", "full", "summarize", "summarise",
                    "important updates", "important update", "collective"
                ):
                    possible_city = possible_city.replace(filler, "")
                possible_city = possible_city.strip()
                if possible_city:
                    city = possible_city
                    break
        result = mcp.run(
            "briefing",
            city=city,
            include_news=False,
            include_gmail=True,
            include_calendar=True,
            include_reminders=True,
            include_utility=False,
            news_category="india",
            interactive_calendar=False,
            utility_location=getattr(app_settings, "UTILITY_ALERT_LOCATION", "Ponnagar, Karumandapam, Trichy"),
        )
        return _speak_result(result)

    if "remind me" in q or "reminder" in q or "reminders" in q:
        if any(word in q for word in ("show", "list", "what", "check")) and "remind me" not in q:
            result = mcp.run("reminders", action="list")
            return _speak_result(result)

        if any(word in q for word in ("complete", "done", "finish", "finished")):
            result = mcp.run(
                "reminders",
                action="complete",
                reminder_id=_reminder_id_from_query(q),
            )
            return _speak_result(result)

        if any(word in q for word in ("delete", "remove", "cancel")) and "remind me" not in q:
            result = mcp.run(
                "reminders",
                action="delete",
                reminder_id=_reminder_id_from_query(q),
            )
            return _speak_result(result)

        if "remind me" in q or "set reminder" in q or "add reminder" in q:
            result = mcp.run(
                "reminders",
                action="add",
                text=_parse_reminder_text(q),
                due_at=_parse_reminder_due_at(q),
            )
            return _speak_result(result)

    if any(phrase in q for phrase in ("stop the song", "stop song", "stop music")) or q == "stop":
        result = mcp.run("media_control", action="pause")
        return _speak_result(result)

    if (
        ("youtube" in q or "spotify" in q)
        and any(word in q for word in ("play", "song", "video", "music"))
    ):
        import re
        platform = "spotify" if "spotify" in q else "youtube"
        item = re.sub(
            rf"\b(open|launch|start|run|{platform}|and|on|play|song|video|music|please)\b",
            " ",
            q
        )
        item = re.sub(r"\s+", " ", item).strip()
        item = (
            item.replace("newyark", "new york")
            .replace("newyork", "new york")
            .replace("nagram", "nagaram")
            .strip()
        )
        if not item:
            return f"What should I play on {platform.title()}?"
        result = mcp.run(
            "media_control",
            action="play",
            platform=platform,
            query=item
        )
        return _speak_result(result)

    # ── App Launch ────────────────────────────────────────────────────────
    if _is_utility_alert_request(q):
        utility_req = _parse_utility_alert_request(q)
        result = mcp.run("utility_alerts", **utility_req)
        return _speak_result(result)

    if "train" in q or "pnr" in q or "irctc" in q:
        import re
        action = "availability"
        if "book" in q or "booking" in q or "irctc" in q:
            action = "book"
        elif "ticket" in q and "availability" not in q and "available" not in q:
            action = "book"
        elif "pnr" in q:
            action = "pnr"
        elif "status" in q or "running" in q:
            action = "status"

        from_station, to_station = _parse_train_route(q)
        date_match = re.search(r"\b(?:on|for)\s+([a-z0-9 /.-]+)$", q)
        train_match = re.search(r"\b(\d{5})\b", q)
        pnr_match = re.search(r"\b(\d{10})\b", q)

        result = mcp.run(
            "train",
            action=action,
            from_station=from_station,
            to_station=to_station,
            date="tomorrow" if "tomorrow" in q else "today" if "today" in q else date_match.group(1).strip() if date_match else "",
            train_no=train_match.group(1) if train_match else "",
            pnr=pnr_match.group(1) if pnr_match else "",
        )
        return _speak_result(result)

    if "add contact" in q and "email" in q:
        import re
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", q)
        name_match = re.search(r"add contact\s+(.+?)\s+email", q)
        if not email_match or not name_match:
            return "Please say: add contact name email address."
        contacts_path = Path(BASE_DIR) / "AI_logic_app" / "data" / "contacts.json"
        try:
            contacts = json.loads(contacts_path.read_text()) if contacts_path.exists() else {}
        except Exception:
            contacts = {}
        name = name_match.group(1).strip()
        contacts[name] = email_match.group(0)
        contacts_path.parent.mkdir(parents=True, exist_ok=True)
        contacts_path.write_text(json.dumps(contacts, indent=2), encoding="utf-8")
        msg = f"Saved contact {name}."
        speak(msg)
        return msg

    calendar_words = (
        "calendar", "meeting", "meetings", "appointment", "appointments",
        "schedule", "event", "events"
    )
    mail_words = ("gmail", "mail", "email")
    if (
        any(word in q for word in calendar_words)
        and not any(word in q for word in mail_words)
        and not q.startswith(("open ", "launch ", "start ", "run "))
    ):
        timeframe = "today"
        window_minutes = 0
        if "tomorrow" in q:
            timeframe = "tomorrow"
        elif "week" in q or "next 7 days" in q:
            timeframe = "week"
        elif "upcoming" in q or "next meeting" in q or "next event" in q:
            timeframe = "upcoming"
        if "next hour" in q or "one hour" in q:
            timeframe = "upcoming"
            window_minutes = 60
        elif "next 30" in q or "half hour" in q:
            timeframe = "upcoming"
            window_minutes = 30

        target_date = _calendar_target_date_from_query(q)
        result = mcp.run(
            "calendar",
            action="upcoming",
            timeframe=timeframe,
            max_results=10,
            window_minutes=window_minutes,
            target_date=target_date,
            interactive=True,
        )
        if result["status"] == "error" and _calendar_api_disabled(result):
            speak(result["message"])
            speak("Until Calendar is enabled, I will check Gmail for meeting invitations.")
            fallback = mcp.run(
                "gmail",
                action="check_interviews",
                timeframe=_gmail_timeframe_for_calendar_fallback(timeframe, target_date)
            )
            if fallback["status"] == "ok":
                return _speak_result(fallback)
        return _speak_result(result)

    mail_check_words = (
        "interview", "interviews", "assessment", "assessments",
        "meeting", "meetings"
    )
    if (
        (
            ("gmail" in q or "mail" in q or "email" in q)
            and any(word in q for word in (*mail_check_words, "available", "check"))
        )
        or (
            any(word in q for word in mail_check_words)
            and any(word in q for word in ("available", "check", "there"))
        )
    ):
        timeframe = ""
        if "today" in q:
            timeframe = "today"
        elif "tomorrow" in q:
            timeframe = "tomorrow"
        elif "week" in q:
            timeframe = "last week"
        result = mcp.run(
            "gmail",
            action="check_interviews",
            timeframe=timeframe
        )
        return _speak_result(result)

    if (
        "send email" in q
        or "send gmail" in q
        or "send a mail" in q
        or "send mail" in q
        or "mail to" in q
        or "email to" in q
    ):
        to_email = _extract_voice_email_address(q)
        if not to_email:
            contacts_path = Path(BASE_DIR) / "AI_logic_app" / "data" / "contacts.json"
            try:
                contacts = json.loads(contacts_path.read_text()) if contacts_path.exists() else {}
            except Exception:
                contacts = {}
            for name, email in contacts.items():
                if name.lower() in q:
                    to_email = email
                    break
        if not to_email:
            return "No email address or saved contact found. Say add contact name email address first."

        subject_match = re.search(r"\bsubject\s+(.+?)(?:\s+body\s+|$)", q)
        body_match = re.search(r"\bbody\s+(.+)$", q)
        subject = subject_match.group(1).strip() if subject_match else "Message from CUBY"
        body = body_match.group(1).strip() if body_match else "Hello from CUBY AI Assistant"

        result = mcp.run(
            "gmail",
            action="send",
            to=to_email,
            subject=subject,
            body=body
        )
        return _speak_result(result)

    _open_triggers = ("open ", "launch ", "start ", "run ")
    for trigger in _open_triggers:
        if q.startswith(trigger):
            target = q[len(trigger):].strip()
            result = mcp.run("app_launcher", action="open", target=target)
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
        or "send mail" in q
        or "mail to" in q
        or "email to" in q
    ):
        to_email = _extract_voice_email_address(q)
        if not to_email:
            return "No email address found"

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
        or "vacancy" in q
        or "vacancies" in q
        or ("apply" in q and "naukri" in q)
    ):

        job_req = _parse_job_request(q)

        result = mcp.run(
            "jobs",
            platform=job_req["platform"],
            role=job_req["role"],
            roles=job_req["roles"],
            location=job_req["location"],
            action=job_req["action"],
            auto_apply=job_req["auto_apply"],
            max_jobs=job_req["max_jobs"],
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

    if _is_news_request(q):
        news_req = _parse_news_request(q)
        result = mcp.run(
            "news",
            category=news_req["category"],
            query=news_req["query"],
            count=news_req["count"],
            fresh_hours=news_req["fresh_hours"],
        )
        return _speak_result(result)

    # ── Weather ───────────────────────────────────────────────────────────
    # ── Weather ─────────────────────────────

    if (
        "weather" in q
        or "temperature" in q
        or "forecast" in q
        or "rain" in q
    ):
        weather_req = _parse_weather_request(q)
        result = mcp.run(
            "weather",
            city=weather_req["city"],
            forecast=weather_req["forecast"],
            rain_alert_hours=weather_req["rain_alert_hours"],
            target_date=weather_req["target_date"],
            timeframe=weather_req["timeframe"],
            forecast_days=16,
        )

        return _speak_result(result)

    # ── News ──────────────────────────────────────────────────────────────
    if _is_news_request(q):
        news_req = _parse_news_request(q)
        result = mcp.run(
            "news",
            category=news_req["category"],
            query=news_req["query"],
            count=news_req["count"],
            fresh_hours=news_req["fresh_hours"],
        )
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

    while RUNNING:
        try:
            query = takecommandexceptional(20).lower()
        except Exception as exc:
            print(f"CUBY listening error: {exc}")
            speak("Voice listening had a problem, but I am still active.")
            continue
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
