import threading
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cuby.bootstrap import prefer_local_venv, restart_with_local_venv_if_needed


if __name__ == "__main__":
    restart_with_local_venv_if_needed(__file__, PROJECT_ROOT)

prefer_local_venv(PROJECT_ROOT)

from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from cuby.config import settings
from cuby.database import Base, engine

from cuby import models, schemas

from cuby.api_routes import router as api_router
from cuby.ai_commands import router as commands_router
from cuby.mcp_router import router as mcp_router

# Scheduler
from AI_logic_app.interview_scheduler import scheduler

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Cuby AI Assistant API"
)

# Routers
app.include_router(api_router)
app.include_router(commands_router)
app.include_router(mcp_router)

# Static files
staticfiles_path = Path(settings.BASE_DIR) / "AI_logic_app" / "static"

if staticfiles_path.exists():
    app.mount(
        "/static",
        StaticFiles(directory=staticfiles_path),
        name="static"
    )

templates_path = Path(settings.BASE_DIR) / "templates"

# AI Thread
ai_thread = None
ai_thread_lock = threading.Lock()


# =========================================================
# STARTUP EVENT
# =========================================================

@app.on_event("startup")
async def startup_event():

    print("Starting CUBY server...")

    # START SCHEDULER SAFELY
    try:

        if not scheduler.running:
            scheduler.start()
            print("Interview scheduler started")

    except Exception as e:
        print(f"Scheduler startup error: {e}")


# =========================================================
# SHUTDOWN EVENT
# =========================================================

@app.on_event("shutdown")
async def shutdown_event():

    print("Shutting down CUBY server...")

    # STOP AI LOOP
    try:
        from AI_logic_app import AI_logic
        AI_logic.stop()
    except Exception as e:
        print(f"AI stop error: {e}")

    # STOP SCHEDULER
    try:

        if scheduler.running:
            scheduler.shutdown(wait=False)
            print("Scheduler stopped")

    except Exception as e:
        print(f"Scheduler shutdown error: {e}")


# =========================================================
# ROOT
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def root():

    home_path = templates_path / "home.html"

    if home_path.exists():

        with open(home_path, "r", encoding="utf-8") as f:
            return f.read()

    return """
    <html>
        <head>
            <title>Cuby Assistant</title>
        </head>
        <body>
            <h1>Welcome to Cuby AI Assistant</h1>
            <p>API Documentation:
            <a href="/docs">/docs</a></p>
        </body>
    </html>
    """


# =========================================================
# HEALTH
# =========================================================

@app.get("/health", response_model=schemas.HealthResponse)
async def health_check():

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# =========================================================
# STATIC PAGES
# =========================================================

@app.get("/about", response_class=HTMLResponse)
async def about():

    about_path = templates_path / "about.html"

    if about_path.exists():

        with open(about_path, "r", encoding="utf-8") as f:
            return f.read()

    return "<h1>About Cuby Assistant</h1>"


@app.get("/user_manual", response_class=HTMLResponse)
async def user_manual():

    manual_path = templates_path / "user_manual.html"

    if manual_path.exists():

        with open(manual_path, "r", encoding="utf-8") as f:
            return f.read()

    return "<h1>User Manual</h1>"


@app.get("/troubleshoot", response_class=HTMLResponse)
async def troubleshoot():

    troubleshoot_path = templates_path / "troubleshoot.html"

    if troubleshoot_path.exists():

        with open(troubleshoot_path, "r", encoding="utf-8") as f:
            return f.read()

    return "<h1>Troubleshoot</h1>"


# =========================================================
# AI STARTUP THREAD
# =========================================================

def run_startup():

    try:

        from AI_logic_app.AI_logic import startup

        startup()

    except Exception as e:
        print(f"CUBY Startup error: {e}")


# =========================================================
# START AI
# =========================================================

@app.get("/start_ai")
async def start_ai():

    global ai_thread

    try:

        with ai_thread_lock:

            # PREVENT MULTIPLE THREADS
            if ai_thread and ai_thread.is_alive():

                return {
                    "status": "warning",
                    "message": "CUBY already running"
                }

            ai_thread = threading.Thread(
                target=run_startup,
                daemon=True
            )

            ai_thread.start()

        return {
            "status": "success",
            "message": "CUBY started successfully"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "cuby.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False
    )
