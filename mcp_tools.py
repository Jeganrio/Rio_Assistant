"""
mcp_tools.py
============
MCP (Model Context Protocol) inspired tool integrations for CUBY AI Assistant.

Provides:
  - AppLauncherTool      : open VS Code, Chrome, Notepad, any app or file/folder
  - FileSystemTool       : list, read, create, delete files/folders
  - WeatherTool          : current weather + forecast via Open-Meteo (free, no key)
  - NewsTool             : top headlines via GNews API (free tier) or RSS fallback
  - FlightTool           : real-time flight info via AviationStack (free tier)

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
import requests
from pathlib import Path
from typing import Any

from AI_logic_app.mcp_gmail import GmailTool
from AI_logic_app.mcp_notification import NotificationTool
from AI_logic_app.mcp_jobs import JobTool
from AI_logic_app.mcp_media import MediaControlTool

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


# ---------------------------------------------------------------------------
# 1. App / File / Folder Launcher
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 1. Dynamic App / File / Folder Launcher
# ---------------------------------------------------------------------------

import webbrowser


class AppLauncherTool(MCPTool):

    """
    Dynamically open installed applications,
    websites, files and folders.
    """

    name = "app_launcher"

    description = (
        "Launch installed apps, websites, files and folders dynamically."
    )

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

    # -------------------------------------------------------
    # MAIN
    # -------------------------------------------------------

    def run(
        self,
        target: str = "",
        url: str = ""
    ) -> dict:

        try:

            # ------------------------------------------------
            # URL
            # ------------------------------------------------

            if url:

                webbrowser.open(url)

                return self._ok(
                    {"url": url},
                    f"Opened URL: {url}"
                )

            if not target:

                return self._err(
                    "No target specified."
                )

            target = (
                target.lower()
                .replace("open", "")
                .replace("launch", "")
                .strip()
            )

            # ------------------------------------------------
            # WEBSITE SHORTCUTS
            # ------------------------------------------------

            websites = {

                "youtube": "https://youtube.com",
                "gmail": "https://mail.google.com",
                "spotify": "https://open.spotify.com",
                "linkedin": "https://linkedin.com",
                "github": "https://github.com",
                "google": "https://google.com",
                "chatgpt": "https://chat.openai.com",
                "netflix": "https://netflix.com",
                "amazon": "https://amazon.in",
                "hotstar": "https://hotstar.com"
            }

            if target in websites:

                webbrowser.open(
                    websites[target]
                )

                return self._ok(
                    {"website": target},
                    f"Opened {target}"
                )

            # ------------------------------------------------
            # EXECUTABLE ON PATH
            # ------------------------------------------------

            exe = shutil.which(target)

            if exe:

                subprocess.Popen(exe)

                return self._ok(
                    {"exe": exe},
                    f"Opened {target}"
                )

            # ------------------------------------------------
            # SCAN INSTALLED APPS
            # ------------------------------------------------

            apps = self._scan_apps()

            # EXACT MATCH
            if target in apps:

                os.startfile(apps[target])

                return self._ok(
                    {"app": target},
                    f"Opened {target}"
                )

            # PARTIAL MATCH
            for app_name, app_path in apps.items():

                if target in app_name:

                    os.startfile(app_path)

                    return self._ok(
                        {"app": app_name},
                        f"Opened {app_name}"
                    )

            # ------------------------------------------------
            # FILE OR FOLDER
            # ------------------------------------------------

            path = Path(target)

            if path.exists():

                os.startfile(str(path))

                return self._ok(
                    {"path": str(path)},
                    f"Opened {path.name}"
                )

            # ------------------------------------------------
            # NOT INSTALLED
            # ------------------------------------------------

            search_url = (
                "https://www.google.com/search?q="
                f"download+{target}"
            )

            webbrowser.open(search_url)

            return self._ok(
                {"search": search_url},
                f"{target} not installed. Opened install page."
            )

        except Exception as e:

            return self._err(str(e))

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
    description = "Get current weather and forecast for any city. No API key required."

    def run(self, city: str = "Chennai", forecast: bool = False) -> dict:
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
            "hourly": "relativehumidity_2m,apparent_temperature",
            "timezone": "auto",
        }
        if forecast:
            params["daily"] = (
                "weathercode,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,windspeed_10m_max"
            )

        try:
            raw = requests.get(_WEATHER_URL, params=params, timeout=10).json()
        except Exception as exc:
            return self._err(f"Weather fetch failed: {exc}")

        cw = raw.get("current_weather", {})
        result: dict = {
            "city": display_name,
            "temperature_c": cw.get("temperature"),
            "windspeed_kmh": cw.get("windspeed"),
            "condition": _WMO_CODES.get(cw.get("weathercode", -1), "Unknown"),
            "is_day": bool(cw.get("is_day", 1)),
            "time": cw.get("time", ""),
        }

        # humidity from first hourly slot
        try:
            result["humidity_pct"] = raw["hourly"]["relativehumidity_2m"][0]
            result["feels_like_c"] = raw["hourly"]["apparent_temperature"][0]
        except Exception:
            pass

        if forecast and "daily" in raw:
            d = raw["daily"]
            result["forecast_7day"] = [
                {
                    "date": d["time"][i],
                    "condition": _WMO_CODES.get(d["weathercode"][i], "Unknown"),
                    "max_c": d["temperature_2m_max"][i],
                    "min_c": d["temperature_2m_min"][i],
                    "rain_mm": d["precipitation_sum"][i],
                    "wind_kmh": d["windspeed_10m_max"][i],
                }
                for i in range(len(d["time"]))
            ]

        return self._ok(result, f"Weather for {display_name}")


# ---------------------------------------------------------------------------
# 4. News Tool  (GNews free API + RSS fallback)
# ---------------------------------------------------------------------------

_GNEWS_URL = "https://gnews.io/api/v4/top-headlines"
_RSS_FEEDS = {
    "general":     "https://feeds.bbci.co.uk/news/rss.xml",
    "technology":  "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "sports":      "https://feeds.bbci.co.uk/sport/rss.xml",
    "science":     "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "health":      "https://feeds.bbci.co.uk/news/health/rss.xml",
    "business":    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "india":       "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
}


class NewsTool(MCPTool):
    """
    Fetch top news headlines.
    Uses GNews API if GNEWS_API_KEY env var is set; otherwise falls back to BBC RSS.

    kwargs:
      category : "general" | "technology" | "sports" | "science" | "health"
                 | "business" | "india"  (default "general")
      query    : optional keyword search string
      count    : number of articles to return (default 5)
      api_key  : GNews API key (overrides env var)
    """
    name = "news"
    description = "Fetch real-time top news headlines by category or keyword."

    def run(self, category: str = "general", query: str = "",
            count: int = 5, api_key: str = "") -> dict:

        key = api_key or os.environ.get("GNEWS_API_KEY", "")

        if key:
            return self._gnews(key, category, query, count)
        else:
            return self._rss_fallback(category, count)

    # --- GNews ---
    def _gnews(self, key: str, category: str, query: str, count: int) -> dict:
        params = {
            "token": key, "lang": "en", "max": count,
            "topic": category if not query else None,
            "q": query or None,
        }
        params = {k: v for k, v in params.items() if v is not None}
        try:
            resp = requests.get(_GNEWS_URL, params=params, timeout=10).json()
            articles = [
                {
                    "title":       a["title"],
                    "description": a.get("description", ""),
                    "source":      a["source"]["name"],
                    "url":         a["url"],
                    "published":   a.get("publishedAt", ""),
                }
                for a in resp.get("articles", [])
            ]
            return self._ok({"category": category, "articles": articles},
                            f"Fetched {len(articles)} articles")
        except Exception as exc:
            return self._err(f"GNews error: {exc}")

    # --- BBC RSS fallback (no key needed) ---
    def _rss_fallback(self, category: str, count: int) -> dict:
        from xml.etree import ElementTree as ET
        feed_url = _RSS_FEEDS.get(category, _RSS_FEEDS["general"])
        try:
            resp = requests.get(feed_url, timeout=10,
                                headers={"User-Agent": "CubyAI/1.0"})
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:count]
            articles = []
            for item in items:
                articles.append({
                    "title":       (item.findtext("title") or "").strip(),
                    "description": (item.findtext("description") or "").strip(),
                    "source":      "BBC News",
                    "url":         (item.findtext("link") or "").strip(),
                    "published":   (item.findtext("pubDate") or "").strip(),
                })
            return self._ok({"category": category, "articles": articles},
                            f"Fetched {len(articles)} articles (RSS)")
        except Exception as exc:
            return self._err(f"RSS fetch error: {exc}")


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

        key = api_key or os.environ.get("AVIATIONSTACK_KEY", "")
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

class MCPRegistry:
    """Central registry of all MCP tools."""

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        for tool_cls in [
            AppLauncherTool,
            FileSystemTool,
            WeatherTool,
            NewsTool,
            FlightTool,
            MediaControlTool,
            GmailTool,
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


