# CUBY AI Assistant

CUBY is a local FastAPI-based desktop assistant with voice and typed command support. It includes English/Tamil language switching, male/female voice preference, weather and rain advice, current news, Gmail and Calendar integrations, reminders, media control, train/job helpers, and local utility alert checks.

## Quick Start

```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
python scripts\init_db.py
uvicorn main:app --reload
```

Open the app at:

```text
http://127.0.0.1:8000/
```

API docs:

```text
http://127.0.0.1:8000/docs
```

You can also run:

```powershell
scripts\run_server.bat
```

## Project Structure

```text
Cuby_Assistant-main/
|-- main.py                  # Compatibility entrypoint for uvicorn main:app
|-- cuby/                    # FastAPI backend package
|   |-- main.py              # Application setup, routes, static pages
|   |-- config.py            # App settings and paths
|   |-- database.py          # SQLAlchemy engine/session
|   |-- models.py            # SQLAlchemy models
|   |-- schemas.py           # Pydantic schemas
|   |-- api_routes.py        # Query/database API routes
|   |-- ai_commands.py       # Assistant command API routes
|   |-- mcp_router.py        # MCP REST API routes
|   `-- mcp_tools.py         # MCP-style tool registry and tools
|-- requirements.txt         # Python dependencies
|-- Procfile                 # Deployment command
|-- scripts/                 # Setup and local run helpers
|-- docs/                    # API/config/reference documentation
|-- templates/               # FastAPI-served HTML pages
`-- AI_logic_app/
    |-- AI_logic.py          # Core assistant loop and command routing
    |-- interview_scheduler.py
    |-- llm.py
    |-- mcp_calendar.py
    |-- mcp_gmail.py
    |-- mcp_jobs.py
    |-- mcp_media.py
    |-- mcp_notification.py
    |-- mcp_reminders.py
    |-- data/                # Local assistant data
    `-- static/              # Assets served at /static
```

## Useful Commands

```powershell
# Initialize local folders and database
python scripts\init_db.py

# Run development server
uvicorn main:app --reload

# Check dependencies
python -m pip check

# Run container locally
docker compose up --build
```

## Documentation

- [FastAPI guide](docs/README_FASTAPI.md)
- [API documentation](docs/API_DOCUMENTATION.md)
- [Configuration guide](docs/CONFIGURATION.md)
- [Quick reference](docs/QUICK_REFERENCE.md)
- [Deployment guide](docs/DEPLOYMENT.md)

## Runtime Notes

- Keep `.env`, `credentials.json`, `token.json`, and `calendar_token.json` private.
- Static files are served from `AI_logic_app/static`.
- The current app no longer uses Django files or dependencies.
