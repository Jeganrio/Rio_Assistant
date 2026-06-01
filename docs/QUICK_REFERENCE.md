# Cuby Assistant FastAPI - Quick Reference

## Installation (5 minutes)

```bash
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database
python scripts\init_db.py

# 4. Start server
python main.py
```

## Access Points

| Resource | URL | Purpose |
|----------|-----|---------|
| API Docs | http://localhost:8000/docs | Interactive API testing |
| Home | http://localhost:8000/ | Home page |
| Health | http://localhost:8000/health | Health check |

## Most Used Endpoints

### Start AI
```bash
POST /api/ai/start
```

### Execute Command
```bash
POST /api/ai/command
Body: {"command": "what time is it"}
```

### Make AI Speak
```bash
POST /api/ai/speak
Body: {"text": "Hello", "rate": 125}
```

### Save Query
```bash
POST /api/queries
Body: {"query": "What is Python?", "answers": "Python is a programming language"}
```

### Get All Queries
```bash
GET /api/queries?skip=0&limit=100
```

### Remember Something
```bash
POST /api/ai/remember
Body: {"command": "I like coding"}
```

### Recall Memory
```bash
GET /api/ai/remember
```

## Common Voice Commands

| Command | Function |
|---------|----------|
| "what time is it" | Current time |
| "what is the date" | Current date |
| "check cpu" | CPU/Battery info |
| "take a screenshot" | Capture screen |
| "play [song name]" | Play music |
| "search for [query]" | Google search |
| "tell me a joke" | Technical joke |
| "define [term]" | Get definition |
| "remember that [text]" | Store memory |
| "do you remember" | Recall memory |
| "minimize window" | Minimize |
| "maximize window" | Maximize |
| "shutdown my pc" | Shutdown system |
| "lock my pc" | Lock system |

## Python Usage

```python
import requests

BASE_URL = "http://localhost:8000"

# Execute command
r = requests.post(f"{BASE_URL}/api/ai/command", 
                  json={"command": "what time is it"})
print(r.json())

# Save query
r = requests.post(f"{BASE_URL}/api/queries",
                  json={"query": "Q", "answers": "A"})
print(r.json())

# Get queries
r = requests.get(f"{BASE_URL}/api/queries")
print(r.json())
```

## cURL Usage

```bash
# Start AI
curl -X POST http://localhost:8000/api/ai/start

# Command
curl -X POST http://localhost:8000/api/ai/command \
  -H "Content-Type: application/json" \
  -d '{"command": "what time is it"}'

# Speak
curl -X POST http://localhost:8000/api/ai/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello"}'

# Save query
curl -X POST http://localhost:8000/api/queries \
  -H "Content-Type: application/json" \
  -d '{"query": "Q", "answers": "A"}'

# Get queries
curl http://localhost:8000/api/queries

# Remember
curl -X POST http://localhost:8000/api/ai/remember \
  -H "Content-Type: application/json" \
  -d '{"command": "test"}'

# Recall
curl http://localhost:8000/api/ai/remember
```

## Environment Variables

```env
DEBUG=True                              # Debug mode
DATABASE_URL=sqlite:///./db.sqlite3     # Database
SERVER_HOST=0.0.0.0                     # Host
SERVER_PORT=8000                        # Port
APP_NAME=Cuby Assistant                 # App name
APP_VERSION=1.0.0                       # Version
```

## Directory Structure

```text
|-- main.py              # Compatibility entrypoint
|-- cuby/                # FastAPI backend package
|   |-- main.py          # App setup and routes
|   |-- config.py        # Configuration
|   |-- database.py      # DB setup
|   |-- models.py        # ORM models
|   |-- schemas.py       # Data schemas
|   |-- api_routes.py    # Query endpoints
|   |-- ai_commands.py   # AI endpoints
|   |-- mcp_router.py    # MCP endpoints
|   `-- mcp_tools.py     # MCP tools
|-- scripts/
|   `-- init_db.py       # DB init
|-- docs/                # Documentation
|-- templates/           # HTML pages
|-- AI_logic_app/
|   |-- AI_logic.py      # Core logic
|   |-- data/            # Runtime assistant data
|   `-- static/          # Static assets
|-- requirements.txt     # Dependencies
`-- db.sqlite3           # Local database
```
## Common Issues

| Issue | Solution |
|-------|----------|
| Port 8000 in use | Change port in .env or kill process |
| Database locked | Delete db.sqlite3, run scripts\init_db.py |
| Microphone error | Check sound settings, run as admin |
| Module not found | Activate venv, pip install -r requirements.txt |
| Import error | Check Python path, reinstall dependencies |

## Useful Commands

```bash
# List microphones
python -c "import speech_recognition as sr; sr.Microphone.list_microphone_indexes()"

# Reset database
rm db.sqlite3
python scripts\init_db.py

# Change port
# Edit .env: SERVER_PORT=8080

# Run with specific host
uvicorn main:app --host 127.0.0.1 --port 8000

# Run with auto-reload
uvicorn main:app --reload

# Run with multiple workers (production)
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```

## Database Query Examples

```python
from cuby.database import SessionLocal
from cuby import models

db = SessionLocal()

# Get all queries
queries = db.query(models.CubyQueries).all()

# Get by ID
query = db.query(models.CubyQueries).filter(
    models.CubyQueries.id == 1
).first()

# Search queries
results = db.query(models.CubyQueries).filter(
    models.CubyQueries.query.contains("python")
).all()

# Count
count = db.query(models.CubyQueries).count()

db.close()
```

## Response Examples

### Success Response
```json
{
  "status": "success",
  "message": "Operation completed",
  "data": {...}
}
```

### Error Response
```json
{
  "detail": "Error message"
}
```

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request |
| 404 | Not Found |
| 500 | Server Error |

## Performance Tips

1. Use pagination: `?skip=0&limit=50`
2. Cache responses on client
3. Use background tasks for long operations
4. Batch database operations
5. Use PostgreSQL for production

## Deployment

### Development
```bash
python main.py
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker
```bash
docker build -t cuby .
docker run -p 8000:8000 cuby
```

### Heroku
```bash
git push heroku main
```

## Useful Links

- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/

## File Locations

| Item | Location |
|------|----------|
| Config | cuby/config.py |
| AI Logic | AI_logic_app/AI_logic.py |
| Data | AI_logic_app/data/ |
| Songs | AI_logic_app/data/songs/ |
| Screenshots | AI_logic_app/data/screenshots/ |
| Memory | AI_logic_app/data/remember/ |
| Database | db.sqlite3 |

## Quick Restart

```bash
# Stop server (Ctrl+C)

# Activate venv
.\venv\Scripts\activate

# Start server
python main.py
```

---

For detailed documentation, see:
- docs/README_FASTAPI.md
- docs/API_DOCUMENTATION.md
- docs/CONFIGURATION.md


