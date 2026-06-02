"""
ai_commands.py  (MCP-enhanced)
================================
FastAPI router for CUBY AI commands.
All original endpoints are preserved; MCP-specific endpoints are added
at the bottom and delegate to mcp_router.router via include_router(),
or you can mount mcp_router separately in cuby/main.py.

Quick-start: in your main FastAPI app do:
    from cuby.ai_commands import router as ai_router
    from cuby.mcp_router import router as mcp_router
    app.include_router(ai_router)
    app.include_router(mcp_router)
"""

from __future__ import annotations

import os
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from cuby.database import get_db
from cuby import models, schemas
from AI_logic_app import AI_logic
from cuby.mcp_tools import mcp  # MCPRegistry singleton

router = APIRouter(prefix="/api/ai", tags=["ai_commands"])


# ══════════════════════════════════════════════════════════════════════════
# Shared schemas
# ══════════════════════════════════════════════════════════════════════════

class CommandRequest(BaseModel):
    command: str


class SpeakRequest(BaseModel):
    text: str
    rate: int = 125


class AIResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None


# ══════════════════════════════════════════════════════════════════════════
# Original endpoints  (unchanged)
# ══════════════════════════════════════════════════════════════════════════

@router.post("/start", response_model=AIResponse)
async def start_ai(background_tasks: BackgroundTasks):
    """Start the AI assistant in background."""
    try:
        if os.getenv("CUBY_CLOUD", "").lower() in {"1", "true", "yes"}:
            return {
                "status": "success",
                "message": "Live server uses browser microphone mode. Press Start Mic on the page.",
                "data": {"running": False, "browser_mic": True},
            }
        background_tasks.add_task(AI_logic.startup)
        return {"status": "success", "message": "CUBY started successfully",
                "data": {"running": True}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CUBY STOPPED: {e}")


@router.get("/status", response_model=AIResponse)
async def status():
    """Return assistant running and voice availability status."""
    return {
        "status": "success",
        "message": "Status retrieved",
        "data": {
            "running":         getattr(AI_logic, "RUNNING", False),
            "voice_available": getattr(AI_logic, "VOICE_AVAILABLE", False),
            "speech_language": getattr(AI_logic, "get_assistant_language", lambda: "english")(),
            "voice_gender":    getattr(AI_logic, "_load_voice_gender", lambda: "female")(),
        },
    }


@router.get("/events", response_model=AIResponse)
async def ui_events(since: int = Query(0, ge=0)):
    """Return recent voice/text events for the frontend live panel."""
    return {
        "status": "success",
        "message": "Events retrieved",
        "data": AI_logic.get_ui_events(since),
    }


@router.post("/stop", response_model=AIResponse)
async def stop_assistant():
    """Stop the AI assistant loop gracefully."""
    try:
        AI_logic.stop()
        return {"status": "success", "message": "Assistant stop requested",
                "data": {"running": getattr(AI_logic, "RUNNING", False)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping: {e}")


@router.post("/speak", response_model=AIResponse)
async def speak(request: SpeakRequest):
    """Make the AI speak a given text."""
    try:
        AI_logic.speak(request.text, rate=request.rate)
        return {"status": "success", "message": f"Spoke: {request.text}",
                "data": {"text": request.text}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error speaking: {e}")


@router.post("/command", response_model=AIResponse)
async def execute_command(request: CommandRequest,
                          db: Session = Depends(get_db)):
    """
    Execute a voice/text command.
    MCP-aware: tries app-launch, weather, news, and flight patterns first.
    """
    try:
        command = AI_logic.normalize_user_query(request.command)

        if getattr(AI_logic, "_is_wake_command", lambda _cmd: False)(command):
            language = getattr(AI_logic, "get_assistant_language", lambda: "english")()
            if language == "tamil" or any("\u0B80" <= char <= "\u0BFF" for char in command):
                response = "வணக்கம்! நான் தயார். எப்படி உதவ வேண்டும்?"
            else:
                response = "Hi, welcome back! How can I assist you today?"
            AI_logic.speak(response)
            return {
                "status": "success",
                "message": "Wake command processed",
                "data": {"command": "wake", "response": response},
            }

        # ── MCP dispatch first ──────────────────────────────────────────
        mcp_resp = AI_logic._try_mcp(command)
        if mcp_resp:
            return {"status": "success", "message": "MCP command processed",
                    "data": {"response": mcp_resp}}

        # ── built-in commands ───────────────────────────────────────────
        if "time" in command:
            response = f"The current time is {datetime.datetime.now().strftime('%H:%M:%S')}"
            AI_logic.speak(response)
            return {"status": "success", "message": "Time spoken",
                    "data": {"command": "time", "response": response}}

        elif "date" in command:
            now = datetime.datetime.now()
            response = f"The current date is {now.day} {now.strftime('%B')} {now.year}"
            AI_logic.speak(response)
            return {"status": "success", "message": "Date spoken",
                    "data": {"command": "date", "response": response}}

        elif "cpu" in command or "battery" in command:
            psutil = getattr(AI_logic, "psutil", None)
            if psutil:
                usage = psutil.cpu_percent()
                batt = psutil.sensors_battery()
                parts = [f"CPU usage is {usage} percent."]
                if batt:
                    parts.append(f"Battery is at {batt.percent:.0f} percent.")
                elif os.getenv("CUBY_CLOUD", "").lower() in {"1", "true", "yes"}:
                    parts.append("Laptop battery is not available from the live server.")
                response = " ".join(parts)
            else:
                response = "System status is not available right now."
            AI_logic.speak(response)
            return {"status": "success", "message": "CPU/Battery info spoken",
                    "data": {"command": "cpu", "response": response}}

        elif "screenshot" in command:
            AI_logic.screenshot()
            return {"status": "success", "message": "Screenshot taken",
                    "data": {"command": "screenshot"}}

        elif "minimise" in command or "minimize" in command:
            AI_logic.minimizer()
            return {"status": "success", "message": "Window minimized",
                    "data": {"command": "minimize"}}

        elif "maximize" in command:
            import pyautogui as py
            py.hotkey("win", "up")
            return {"status": "success", "message": "Window maximized",
                    "data": {"command": "maximize"}}

        elif "search" in command or "google" in command:
            import pywhatkit
            search_query = (command.replace("search", "")
                                   .replace("google", "").strip())
            if search_query:
                pywhatkit.search(search_query)
                return {"status": "success",
                        "message": f"Searching for: {search_query}",
                        "data": {"query": search_query}}

        elif "joke" in command:
            import pyjokes
            joke = pyjokes.get_joke(category="all")
            AI_logic.speak(joke)
            return {"status": "success", "message": "Joke told",
                    "data": {"joke": joke}}

        elif "play" in command:
            song = command.replace("play", "").strip()
            if song:
                AI_logic.playsongs(song)
                return {"status": "success", "message": f"Playing: {song}",
                        "data": {"song": song}}

        # ── chatbot / LLM fallback ──────────────────────────────────────
        response = AI_logic.chatbot(command)
        if response:
            return {"status": "success", "message": "Command processed",
                    "data": {"response": response}}

        AI_logic.GenAI().google_search(command)
        return {"status": "success",
                "message": "Command processed with Google search",
                "data": {"command": command}}

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error executing command: {e}")


@router.post("/query", response_model=AIResponse)
async def query_ai(request: CommandRequest):
    """Return a textual response (LLM → chatbot → Wikipedia fallback)."""
    try:
        response = ""

        # MCP check
        mcp_resp = AI_logic._try_mcp(request.command)
        if mcp_resp:
            return {"status": "success", "message": "Response generated",
                    "data": {"response": mcp_resp}}

        # LLM
        try:
            response = AI_logic.generate_response(request.command)
            if isinstance(response, str) and response.startswith("Error:"):
                response = ""
        except Exception:
            response = ""

        # chatbot
        if not response:
            try:
                response = AI_logic.chatbot(request.command)
            except Exception:
                response = ""

        # Wikipedia
        if not response:
            try:
                import wikipedia
                wikipedia.set_lang("en")
                response = wikipedia.summary(request.command, sentences=2)
            except Exception:
                pass

        return {"status": "success", "message": "Response generated",
                "data": {"response": response}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying AI: {e}")


@router.post("/remember", response_model=AIResponse)
async def remember(request: CommandRequest):
    """Remember a piece of information."""
    try:
        from pathlib import Path
        from cuby.config import settings
        p = Path(settings.BASE_DIR) / "AI_logic_app" / "data" / "remember"
        p.mkdir(parents=True, exist_ok=True)
        (p / "data.txt").write_text(request.command)
        AI_logic.speak(f"I will remember that {request.command}")
        return {"status": "success", "message": f"Remembered: {request.command}",
                "data": {"remembered": request.command}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error remembering: {e}")


@router.get("/remember", response_model=AIResponse)
async def recall():
    """Recall stored memory."""
    try:
        from pathlib import Path
        from cuby.config import settings
        p = Path(settings.BASE_DIR) / "AI_logic_app" / "data" / "remember" / "data.txt"
        if not p.exists():
            return {"status": "success", "message": "No memory found",
                    "data": {"memory": ""}}
        memory = p.read_text()
        AI_logic.speak(f"You told me to remember that {memory}")
        return {"status": "success", "message": "Memory recalled",
                "data": {"memory": memory}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recalling: {e}")


@router.post("/write", response_model=AIResponse)
async def activate_writer():
    """Activate writer mode."""
    try:
        AI_logic.writter()
        return {"status": "success", "message": "Writer mode activated",
                "data": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@router.post("/define", response_model=AIResponse)
async def define(request: CommandRequest):
    """Get a definition (short or long) for a term."""
    try:
        q = request.command.lower()
        mode = "long" if ("long" in q or "full" in q) else "short"
        term = q.replace("long", "").replace("full", "").replace("short", "").strip()
        if mode == "long":
            AI_logic.long_define(term)
        else:
            AI_logic.short_define(term)
        return {"status": "success", "message": f"Definition provided",
                "data": {"term": term, "mode": mode}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@router.get("/shutdown", response_model=AIResponse)
async def shutdown_system():
    """Shutdown the system."""
    try:
        import os
        AI_logic.speak("Shutting down the system")
        os.system(r"C:\Windows\System32\shutdown.exe /s /t 5")
        return {"status": "success", "message": "System shutting down", "data": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@router.get("/lock", response_model=AIResponse)
async def lock_system():
    """Lock the system."""
    try:
        import os
        AI_logic.speak("Locking the system")
        os.system(r"C:\Windows\System32\rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return {"status": "success", "message": "System locked", "data": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@router.get("/restart", response_model=AIResponse)
async def restart_system():
    """Restart the system."""
    try:
        import os
        AI_logic.speak("Restarting the system")
        os.system(r"C:\Windows\System32\shutdown.exe /r /t 5")
        return {"status": "success", "message": "System restarting", "data": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


# ══════════════════════════════════════════════════════════════════════════
# NEW  — inline MCP convenience endpoints  (short-hand on /api/ai/mcp/...)
# ══════════════════════════════════════════════════════════════════════════

class MCPCommandRequest(BaseModel):
    tool: str                          # app_launcher | filesystem | weather | news | flight_info
    params: dict = {}                  # tool-specific kwargs


@router.post("/mcp/run", response_model=AIResponse,
             summary="Run any MCP tool by name")
async def run_mcp_tool(request: MCPCommandRequest):
    """
    Generic MCP tool runner.

    Example — launch VS Code:
    ```json
    {"tool": "app_launcher", "params": {"target": "vscode"}}
    ```
    Example — weather:
    ```json
    {"tool": "weather", "params": {"city": "Mumbai", "forecast": true}}
    ```
    Example — news:
    ```json
    {"tool": "news", "params": {"category": "technology", "count": 5}}
    ```
    Example — flight:
    ```json
    {"tool": "flight_info", "params": {"flight_iata": "AI101"}}
    ```
    Example — list files:
    ```json
    {"tool": "filesystem", "params": {"action": "list", "path": "C:/Users/lenovo/Documents"}}
    ```
    """
    result = mcp.run(request.tool, **request.params)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return AIResponse(
        status=result["status"],
        message=result["message"],
        data=result.get("data"),
    )


@router.get("/mcp/tools", response_model=AIResponse,
            summary="List all registered MCP tools")
async def list_mcp_tools():
    """Return name + description of every MCP tool."""
    tools = mcp.list_tools()
    return AIResponse(
        status="success",
        message=f"{len(tools)} MCP tools registered",
        data={"tools": tools},
    )
