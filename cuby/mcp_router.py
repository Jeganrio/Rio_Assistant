"""
mcp_router.py
=============
FastAPI router exposing all MCP tools as REST endpoints.
Mount this in your main FastAPI app:

    from cuby.mcp_router import router as mcp_router
    app.include_router(mcp_router)
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from cuby.mcp_tools import mcp  # the singleton MCPRegistry

router = APIRouter(prefix="/api/mcp", tags=["mcp_tools"])


# ──────────────────────────────────────────────
# Shared response schema
# ──────────────────────────────────────────────

class MCPResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None


# ──────────────────────────────────────────────
# Request bodies
# ──────────────────────────────────────────────

class AppLaunchRequest(BaseModel):
    action: str = "open"       # open | close | list
    target: str = ""          # app name or full file/folder path
    url: str = ""             # optional URL to open in browser


class FileRequest(BaseModel):
    action: str               # list | read | write | delete | create_folder | exists
    path: str = "."
    content: str = ""         # used for "write"
    max_lines: int = 100


class WeatherRequest(BaseModel):
    city: str 
    rain_alert_hours: int = 24
    target_date: str = ""
    timeframe: str = "today"
    forecast_days: int = 16
    forecast: bool = False    # True → include 7-day daily forecast


class NewsRequest(BaseModel):
    category: str = "general" # general|technology|sports|science|health|business|india|tamilnadu|trichy
    query: str = ""           # optional keyword/location filter
    count: int = 5
    fresh_hours: int = 48
    api_key: str = ""         # optional; falls back to GNEWS_API_KEY env var


class FlightRequest(BaseModel):
    flight_iata: str = ""     # e.g. "AI101"
    dep_iata: str = ""        # departure airport IATA
    arr_iata: str = ""        # arrival airport IATA
    airline_name: str = ""
    count: int = 5
    api_key: str = ""         # falls back to AVIATIONSTACK_KEY env var


class TrainRequest(BaseModel):
    action: str = "availability"
    from_station: str = ""
    to_station: str = ""
    date: str = ""
    train_no: str = ""
    pnr: str = ""


class UtilityAlertRequest(BaseModel):
    action: str = "check"       # check | confirm_power
    kind: str = "all"          # all | power | water
    location: str = "Ponnagar, Karumandapam, Trichy"
    area: str = ""
    city: str = "Trichy"
    days: int = 7
    query: str = ""
    max_results: int = 6
    official_wait_seconds: int = 150


class CalendarRequest(BaseModel):
    action: str = "upcoming"
    timeframe: str = "today"
    max_results: int = 10
    window_minutes: int = 0
    target_date: str = ""
    interactive: bool = True


class ReminderRequest(BaseModel):
    action: str = "list"
    text: str = ""
    due_at: str = ""
    reminder_id: str = ""
    include_completed: bool = False
    window_minutes: int = 0
    max_results: int = 20
    mark_notified: bool = False


class BriefingRequest(BaseModel):
    city: str = ""
    include_news: bool = False
    include_gmail: bool = True
    include_calendar: bool = True
    include_reminders: bool = True
    include_utility: bool = False
    news_category: str = "india"
    interactive_calendar: bool = False
    utility_location: str = "Ponnagar, Karumandapam, Trichy"


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────

def _respond(result: dict) -> MCPResponse:
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return MCPResponse(
        status=result["status"],
        message=result["message"],
        data=result.get("data"),
    )


# ──────────────────────────────────────────────
# Meta endpoint — list all tools
# ──────────────────────────────────────────────

@router.get("/tools", response_model=MCPResponse, summary="List all MCP tools")
async def list_tools():
    """Return the name and description of every registered MCP tool."""
    tools = mcp.list_tools()
    return MCPResponse(
        status="ok",
        message=f"{len(tools)} tools available",
        data={"tools": tools},
    )


# ──────────────────────────────────────────────
# 1. App / File / Folder Launcher
# ──────────────────────────────────────────────

@router.post("/launch", response_model=MCPResponse,
             summary="Open, close, or list apps, files, and folders")
async def launch_app(req: AppLaunchRequest):
    """
    Open any application by name or full path.

    **Examples:**
    - `{"target": "vscode"}` → opens Visual Studio Code
    - `{"target": "chrome"}` → opens Google Chrome
    - `{"target": "C:/Projects/MyApp"}` → opens folder in Explorer
    - `{"url": "https://example.com"}` → opens URL in default browser
    """
    result = mcp.run("app_launcher", action=req.action, target=req.target, url=req.url)
    return _respond(result)


@router.get("/launch", response_model=MCPResponse,
            summary="Open, close, or list apps via query param")
async def launch_app_get(
    action: str = Query("open", description="open, close, or list"),
    target: str = Query("", description="App name or path"),
    url: str = Query("", description="URL to open"),
):
    result = mcp.run("app_launcher", action=action, target=target, url=url)
    return _respond(result)


# ──────────────────────────────────────────────
# 2. File System
# ──────────────────────────────────────────────

@router.post("/filesystem", response_model=MCPResponse,
             summary="File & folder operations")
async def filesystem_op(req: FileRequest):
    """
    Perform file/folder operations.

    **Actions:**
    - `list`          – list contents of a directory
    - `read`          – read a text file (first `max_lines` lines)
    - `write`         – write text to a file (creates if missing)
    - `delete`        – delete a file or folder
    - `create_folder` – create a folder (including parents)
    - `exists`        – check whether a path exists

    **Examples:**
    ```json
    {"action": "list",  "path": "C:/Users/lenovo/Documents"}
    {"action": "read",  "path": "C:/notes.txt", "max_lines": 50}
    {"action": "write", "path": "C:/notes.txt", "content": "Hello!"}
    ```
    """
    result = mcp.run("filesystem",
                     action=req.action, path=req.path,
                     content=req.content, max_lines=req.max_lines)
    return _respond(result)


@router.get("/filesystem/list", response_model=MCPResponse,
            summary="List directory contents")
async def list_directory(
    path: str = Query(".", description="Folder path to list"),
):
    result = mcp.run("filesystem", action="list", path=path)
    return _respond(result)


# ──────────────────────────────────────────────
# 3. Weather
# ──────────────────────────────────────────────

@router.post("/weather", response_model=MCPResponse,
             summary="Get current weather & optional forecast")
async def get_weather(req: WeatherRequest):
    """
    Fetch real-time weather for any city using Open-Meteo (no API key needed).

    Set `forecast: true` to include a 7-day daily forecast.
    """
    result = mcp.run(
        "weather",
        city=req.city,
        forecast=req.forecast,
        rain_alert_hours=req.rain_alert_hours,
        target_date=req.target_date,
        timeframe=req.timeframe,
        forecast_days=req.forecast_days,
    )
    return _respond(result)


@router.get("/weather", response_model=MCPResponse,
            summary="Get weather via query params")
async def get_weather_get(
    city: str = Query("Chennai", description="City name"),
    forecast: bool = Query(False, description="Include 7-day forecast"),
    rain_alert_hours: int = Query(24, ge=1, le=24),
    target_date: str = Query("", description="Optional YYYY-MM-DD target date"),
    timeframe: str = Query("today", description="today|tomorrow|day_after_tomorrow|week|after_week"),
    forecast_days: int = Query(16, ge=1, le=16),
):
    result = mcp.run(
        "weather",
        city=city,
        forecast=forecast,
        rain_alert_hours=rain_alert_hours,
        target_date=target_date,
        timeframe=timeframe,
        forecast_days=forecast_days,
    )
    return _respond(result)


# ──────────────────────────────────────────────
# 4. News
# ──────────────────────────────────────────────

@router.post("/news", response_model=MCPResponse,
             summary="Fetch top news headlines")
async def get_news(req: NewsRequest):
    """
    Fetch top headlines by category or keyword.

    - Uses Google News RSS for dynamic topics and locations.
    - Set `GNEWS_API_KEY` env var or pass `api_key` for supported GNews topics.

    **Categories:** general, technology, sports, science, health, business,
    india, tamilnadu, trichy, politics, finance, weather, global
    """
    result = mcp.run("news",
                     category=req.category, query=req.query,
                     count=req.count, fresh_hours=req.fresh_hours,
                     api_key=req.api_key)
    return _respond(result)


@router.get("/news", response_model=MCPResponse,
            summary="Fetch news via query params")
async def get_news_get(
    category: str = Query("general"),
    query: str = Query("", description="Keyword filter"),
    count: int = Query(5, ge=1, le=100),
    fresh_hours: int = Query(48, ge=1, le=168),
):
    result = mcp.run(
        "news",
        category=category,
        query=query,
        count=count,
        fresh_hours=fresh_hours,
    )
    return _respond(result)


# ──────────────────────────────────────────────
# 5. Flight Information
# ──────────────────────────────────────────────

@router.post("/flights", response_model=MCPResponse,
             summary="Real-time flight status")
async def get_flights(req: FlightRequest):
    """
    Query real-time flight data via AviationStack.

    Set `AVIATIONSTACK_KEY` env var or pass `api_key`.
    Free tier: 100 requests/month — https://aviationstack.com/signup/free

    **Examples:**
    ```json
    {"flight_iata": "AI101"}
    {"dep_iata": "MAA", "arr_iata": "DEL"}
    {"airline_name": "IndiGo", "count": 10}
    ```
    """
    result = mcp.run(
        "flight_info",
        flight_iata=req.flight_iata,
        dep_iata=req.dep_iata,
        arr_iata=req.arr_iata,
        airline_name=req.airline_name,
        count=req.count,
        api_key=req.api_key,
    )
    return _respond(result)


@router.get("/flights", response_model=MCPResponse,
            summary="Flight status via query params")
async def get_flights_get(
    flight: str = Query("", description="Flight IATA code e.g. AI101"),
    dep: str = Query("", description="Departure airport IATA e.g. MAA"),
    arr: str = Query("", description="Arrival airport IATA e.g. DEL"),
    count: int = Query(5, ge=1, le=20),
):
    result = mcp.run("flight_info",
                     flight_iata=flight, dep_iata=dep,
                     arr_iata=arr, count=count)
    return _respond(result)


@router.post("/trains", response_model=MCPResponse,
             summary="Open train availability, status, PNR, or booking")
async def get_trains(req: TrainRequest):
    result = mcp.run(
        "train",
        action=req.action,
        from_station=req.from_station,
        to_station=req.to_station,
        date=req.date,
        train_no=req.train_no,
        pnr=req.pnr,
    )
    return _respond(result)


@router.post("/utility-alerts", response_model=MCPResponse,
             summary="Check power-cut and water-supply cut alerts")
async def get_utility_alerts(req: UtilityAlertRequest):
    result = mcp.run(
        "utility_alerts",
        action=req.action,
        kind=req.kind,
        location=req.location,
        area=req.area,
        city=req.city,
        days=req.days,
        query=req.query,
        max_results=req.max_results,
        official_wait_seconds=req.official_wait_seconds,
    )
    return _respond(result)


@router.get("/utility-alerts", response_model=MCPResponse,
            summary="Check utility alerts via query params")
async def get_utility_alerts_get(
    kind: str = Query("all", description="all, power, or water"),
    action: str = Query("check", description="check or confirm_power"),
    location: str = Query("Ponnagar, Karumandapam, Trichy"),
    city: str = Query("Trichy"),
    days: int = Query(7, ge=1, le=30),
    max_results: int = Query(6, ge=1, le=20),
    official_wait_seconds: int = Query(150, ge=30, le=300),
):
    result = mcp.run(
        "utility_alerts",
        action=action,
        kind=kind,
        location=location,
        city=city,
        days=days,
        max_results=max_results,
        official_wait_seconds=official_wait_seconds,
    )
    return _respond(result)


@router.post("/calendar", response_model=MCPResponse,
             summary="Check Google Calendar meetings and events")
async def get_calendar(req: CalendarRequest):
    result = mcp.run(
        "calendar",
        action=req.action,
        timeframe=req.timeframe,
        max_results=req.max_results,
        window_minutes=req.window_minutes,
        target_date=req.target_date,
        interactive=req.interactive,
    )
    return _respond(result)


@router.get("/calendar", response_model=MCPResponse,
            summary="Check Google Calendar via query params")
async def get_calendar_get(
    timeframe: str = Query("today", description="today, tomorrow, week, or upcoming"),
    max_results: int = Query(10, ge=1, le=20),
    window_minutes: int = Query(0, ge=0, le=1440),
    target_date: str = Query("", description="Optional YYYY-MM-DD date"),
    interactive: bool = Query(False, description="Allow browser sign-in if needed"),
):
    result = mcp.run(
        "calendar",
        action="upcoming",
        timeframe=timeframe,
        max_results=max_results,
        window_minutes=window_minutes,
        target_date=target_date,
        interactive=interactive,
    )
    return _respond(result)


@router.post("/reminders", response_model=MCPResponse,
             summary="Create, list, complete, or delete reminders")
async def run_reminders(req: ReminderRequest):
    result = mcp.run(
        "reminders",
        action=req.action,
        text=req.text,
        due_at=req.due_at,
        reminder_id=req.reminder_id,
        include_completed=req.include_completed,
        window_minutes=req.window_minutes,
        max_results=req.max_results,
        mark_notified=req.mark_notified,
    )
    return _respond(result)


@router.get("/reminders", response_model=MCPResponse,
            summary="List active reminders")
async def list_reminders(
    include_completed: bool = Query(False),
    max_results: int = Query(20, ge=1, le=100),
):
    result = mcp.run(
        "reminders",
        action="list",
        include_completed=include_completed,
        max_results=max_results,
    )
    return _respond(result)


@router.post("/briefing", response_model=MCPResponse,
             summary="Generate a daily assistant briefing")
async def get_briefing(req: BriefingRequest):
    result = mcp.run(
        "briefing",
        city=req.city,
        include_news=req.include_news,
        include_gmail=req.include_gmail,
        include_calendar=req.include_calendar,
        include_reminders=req.include_reminders,
        include_utility=req.include_utility,
        news_category=req.news_category,
        interactive_calendar=req.interactive_calendar,
        utility_location=req.utility_location,
    )
    return _respond(result)


@router.get("/briefing", response_model=MCPResponse,
            summary="Generate a daily assistant briefing via query params")
async def get_briefing_get(
    city: str = Query("", description="Weather city for the briefing"),
    include_news: bool = Query(False),
    include_gmail: bool = Query(True),
    include_calendar: bool = Query(True),
    include_reminders: bool = Query(True),
    include_utility: bool = Query(False),
    news_category: str = Query("india"),
    utility_location: str = Query("Ponnagar, Karumandapam, Trichy"),
):
    result = mcp.run(
        "briefing",
        city=city,
        include_news=include_news,
        include_gmail=include_gmail,
        include_calendar=include_calendar,
        include_reminders=include_reminders,
        include_utility=include_utility,
        news_category=news_category,
        interactive_calendar=False,
        utility_location=utility_location,
    )
    return _respond(result)
