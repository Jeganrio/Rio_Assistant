"""
mcp_router.py
=============
FastAPI router exposing all MCP tools as REST endpoints.
Mount this in your main FastAPI app:

    from mcp_router import router as mcp_router
    app.include_router(mcp_router)
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from mcp_tools import mcp  # the singleton MCPRegistry

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
    target: str = ""          # app name or full file/folder path
    url: str = ""             # optional URL to open in browser


class FileRequest(BaseModel):
    action: str               # list | read | write | delete | create_folder | exists
    path: str = "."
    content: str = ""         # used for "write"
    max_lines: int = 100


class WeatherRequest(BaseModel):
    city: str 
    forecast: bool = False    # True → include 7-day daily forecast


class NewsRequest(BaseModel):
    category: str = "general" # general|technology|sports|science|health|business|india
    query: str = ""           # optional keyword filter
    count: int = 5
    api_key: str = ""         # optional; falls back to GNEWS_API_KEY env var


class FlightRequest(BaseModel):
    flight_iata: str = ""     # e.g. "AI101"
    dep_iata: str = ""        # departure airport IATA
    arr_iata: str = ""        # arrival airport IATA
    airline_name: str = ""
    count: int = 5
    api_key: str = ""         # falls back to AVIATIONSTACK_KEY env var


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
             summary="Launch an app, file, or folder")
async def launch_app(req: AppLaunchRequest):
    """
    Open any application by name or full path.

    **Examples:**
    - `{"target": "vscode"}` → opens Visual Studio Code
    - `{"target": "chrome"}` → opens Google Chrome
    - `{"target": "C:/Projects/MyApp"}` → opens folder in Explorer
    - `{"url": "https://example.com"}` → opens URL in default browser
    """
    result = mcp.run("app_launcher", target=req.target, url=req.url)
    return _respond(result)


@router.get("/launch", response_model=MCPResponse,
            summary="Launch an app via query param")
async def launch_app_get(
    target: str = Query("", description="App name or path"),
    url: str = Query("", description="URL to open"),
):
    result = mcp.run("app_launcher", target=target, url=url)
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
    result = mcp.run("weather", city=req.city, forecast=req.forecast)
    return _respond(result)


@router.get("/weather", response_model=MCPResponse,
            summary="Get weather via query params")
async def get_weather_get(
    city: str = Query("Chennai", description="City name"),
    forecast: bool = Query(False, description="Include 7-day forecast"),
):
    result = mcp.run("weather", city=city, forecast=forecast)
    return _respond(result)


# ──────────────────────────────────────────────
# 4. News
# ──────────────────────────────────────────────

@router.post("/news", response_model=MCPResponse,
             summary="Fetch top news headlines")
async def get_news(req: NewsRequest):
    """
    Fetch top headlines by category or keyword.

    - Without a GNews API key, uses BBC RSS (always free).
    - Set `GNEWS_API_KEY` env var or pass `api_key` in the body for GNews.

    **Categories:** general, technology, sports, science, health, business, india
    """
    result = mcp.run("news",
                     category=req.category, query=req.query,
                     count=req.count, api_key=req.api_key)
    return _respond(result)


@router.get("/news", response_model=MCPResponse,
            summary="Fetch news via query params")
async def get_news_get(
    category: str = Query("general"),
    query: str = Query("", description="Keyword filter"),
    count: int = Query(5, ge=1, le=20),
):
    result = mcp.run("news", category=category, query=query, count=count)
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
