# Cuby AI Assistant API Documentation

## Quick Start

### Installation
```bash
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database
python init_db.py

# 4. Start server
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints Overview

### Health & Documentation
- `GET /health` - Health check endpoint
- `GET /docs` - Swagger UI (interactive documentation)
- `GET /redoc` - ReDoc (alternative documentation)

### Static Pages
- `GET /` - Home page
- `GET /about` - About page
- `GET /user_manual` - User manual page
- `GET /troubleshoot` - Troubleshooting page

---

## Query Database API

### Save Query to Database
```http
POST /api/queries
Content-Type: application/json

{
    "query": "What is machine learning?",
    "answers": "Machine learning is a subset of AI..."
}
```

**Response:**
```json
{
    "id": 1,
    "query": "What is machine learning?",
    "answers": "Machine learning is a subset of AI...",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
}
```

### Get All Queries
```http
GET /api/queries?skip=0&limit=100
```

**Response:**
```json
[
    {
        "id": 1,
        "query": "What is machine learning?",
        "answers": "Machine learning is a subset of AI...",
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
    },
    ...
]
```

### Get Specific Query
```http
GET /api/queries/1
```

**Response:**
```json
{
    "id": 1,
    "query": "What is machine learning?",
    "answers": "Machine learning is a subset of AI...",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
}
```

### Update Query
```http
PUT /api/queries/1
Content-Type: application/json

{
    "query": "What is deep learning?",
    "answers": "Deep learning uses neural networks..."
}
```

### Delete Query
```http
DELETE /api/queries/1
```

---

## AI Commands API

### Start AI Assistant
```http
POST /api/ai/start
```

**Response:**
```json
{
    "status": "success",
    "message": "CUBY started successfully",
    "data": {
        "running": true
    }
}
```

### Make AI Speak
```http
POST /api/ai/speak
Content-Type: application/json

{
    "text": "Hello, this is Cuby speaking",
    "rate": 125
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Spoke: Hello, this is Cuby speaking",
    "data": {
        "text": "Hello, this is Cuby speaking"
    }
}
```

**Parameters:**
- `text` (string, required): Text to speak
- `rate` (integer, optional): Speech rate (default: 125)

### Execute Command
```http
POST /api/ai/command
Content-Type: application/json

{
    "command": "what is the current time"
}
```

**Supported Commands:**
- Time: "what is the current time", "tell me the time"
- Date: "what is the current date", "what's the date"
- CPU/Battery: "check cpu", "battery status"
- Screenshot: "take a screenshot"
- Minimize: "minimize window"
- Maximize: "maximize window"
- Search: "search for python programming"
- Jokes: "tell me a technical joke"
- Music: "play [song name]"
- And many more...

**Response:**
```json
{
    "status": "success",
    "message": "Command processed",
    "data": {
        "command": "time"
    }
}
```

### Remember Information
```http
POST /api/ai/remember
Content-Type: application/json

{
    "command": "I like coding in Python"
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Remembered: I like coding in Python",
    "data": {
        "remembered": "I like coding in Python"
    }
}
```

### Recall Information
```http
GET /api/ai/remember
```

**Response:**
```json
{
    "status": "success",
    "message": "Memory recalled",
    "data": {
        "memory": "I like coding in Python"
    }
}
```

### Activate Writer Mode
```http
POST /api/ai/write
```

**Response:**
```json
{
    "status": "success",
    "message": "Writer mode activated",
    "data": {}
}
```

### Get Definition
```http
POST /api/ai/define
Content-Type: application/json

{
    "command": "define python programming"
}
```

**Supported Modes:**
- Short definition: "define [term]"
- Long definition: "define long [term]"
- Full definition: "define full [term]"

**Response:**
```json
{
    "status": "success",
    "message": "Definition of python programming provided",
    "data": {
        "term": "python programming",
        "mode": "short"
    }
}
```

### System Control Commands

#### Shutdown System
```http
GET /api/ai/shutdown
```

#### Lock System
```http
GET /api/ai/lock
```

#### Restart System
```http
GET /api/ai/restart
```

---

## Code Examples

### Python with Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Save a query
def save_query(query, answer):
    response = requests.post(
        f"{BASE_URL}/api/queries",
        json={"query": query, "answers": answer}
    )
    return response.json()

# Get all queries
def get_all_queries():
    response = requests.get(f"{BASE_URL}/api/queries")
    return response.json()

# Make AI speak
def speak(text, rate=125):
    response = requests.post(
        f"{BASE_URL}/api/ai/speak",
        json={"text": text, "rate": rate}
    )
    return response.json()

# Execute a command
def execute_command(command):
    response = requests.post(
        f"{BASE_URL}/api/ai/command",
        json={"command": command}
    )
    return response.json()

# Remember something
def remember(text):
    response = requests.post(
        f"{BASE_URL}/api/ai/remember",
        json={"command": text}
    )
    return response.json()

# Recall memory
def recall():
    response = requests.get(f"{BASE_URL}/api/ai/remember")
    return response.json()

# Usage
if __name__ == "__main__":
    # Save a query
    result = save_query("What is AI?", "AI is artificial intelligence...")
    print(result)
    
    # Execute a command
    result = execute_command("tell me the current time")
    print(result)
    
    # Make AI speak
    result = speak("Hello, I am Cuby")
    print(result)
    
    # Remember something
    result = remember("I like Python")
    print(result)
    
    # Recall memory
    result = recall()
    print(result)
```

### JavaScript/Fetch

```javascript
const BASE_URL = "http://localhost:8000";

// Save a query
async function saveQuery(query, answer) {
    const response = await fetch(`${BASE_URL}/api/queries`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ query, answers: answer })
    });
    return await response.json();
}

// Get all queries
async function getAllQueries() {
    const response = await fetch(`${BASE_URL}/api/queries`);
    return await response.json();
}

// Make AI speak
async function speak(text, rate = 125) {
    const response = await fetch(`${BASE_URL}/api/ai/speak`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ text, rate })
    });
    return await response.json();
}

// Execute a command
async function executeCommand(command) {
    const response = await fetch(`${BASE_URL}/api/ai/command`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ command })
    });
    return await response.json();
}

// Usage
(async () => {
    const result = await saveQuery("What is AI?", "AI is...");
    console.log(result);
    
    const cmd = await executeCommand("tell me the current time");
    console.log(cmd);
})();
```

### cURL

```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Get all queries
curl -X GET "http://localhost:8000/api/queries"

# Save a query
curl -X POST "http://localhost:8000/api/queries" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AI?", "answers": "AI is..."}'

# Make AI speak
curl -X POST "http://localhost:8000/api/ai/speak" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is Cuby", "rate": 125}'

# Execute command
curl -X POST "http://localhost:8000/api/ai/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "what time is it"}'

# Remember something
curl -X POST "http://localhost:8000/api/ai/remember" \
  -H "Content-Type: application/json" \
  -d '{"command": "I like Python"}'

# Recall memory
curl -X GET "http://localhost:8000/api/ai/remember"

# Get definition
curl -X POST "http://localhost:8000/api/ai/define" \
  -H "Content-Type: application/json" \
  -d '{"command": "define machine learning"}'

# Shutdown system
curl -X GET "http://localhost:8000/api/ai/shutdown"
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Successful request
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
    "detail": "Error message describing what went wrong"
}
```

---

## Database Queries

### Query Examples

Get queries created in the last 24 hours:
```python
from datetime import datetime, timedelta
from database import SessionLocal
import models

db = SessionLocal()
yesterday = datetime.now() - timedelta(days=1)
recent_queries = db.query(models.CubyQueries).filter(
    models.CubyQueries.created_at > yesterday
).all()
db.close()
```

Get all queries with a specific keyword:
```python
db = SessionLocal()
keyword_queries = db.query(models.CubyQueries).filter(
    models.CubyQueries.query.contains("Python")
).all()
db.close()
```

---

## Performance Tips

1. **Use pagination** for large query lists:
   ```bash
   GET /api/queries?skip=0&limit=50
   ```

2. **Cache responses** on the client side for frequently accessed data

3. **Use background tasks** for long-running operations:
   - AI startup runs in background
   - System shutdown/restart run in background

4. **Batch operations** when saving multiple queries

---

## Troubleshooting

### Common Issues

1. **Port 8000 already in use**
   ```bash
   # Change port in config.py or .env
   # Or kill the process using the port
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

2. **Database locked error**
   - Delete `db.sqlite3` and reinitialize
   - Or use PostgreSQL for better concurrency

3. **Microphone not working**
   - Check Windows sound settings
   - Run as Administrator
   - Reinstall speech recognition library

4. **API returns 500 error**
   - Check console output for error messages
   - Check database connectivity
   - Verify all dependencies are installed

---

## Security Considerations

1. **Never run with `DEBUG=True` in production**
2. **Use environment variables for sensitive data**
3. **Validate all user inputs**
4. **Use HTTPS in production**
5. **Implement authentication if exposing publicly**
6. **Use database transactions for data consistency**

---

## Rate Limiting (Optional)

To add rate limiting:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/queries")
@limiter.limit("100/minute")
async def get_queries(request: Request):
    ...
```

---

## Monitoring & Logging

The application logs to console. For file logging:

```python
import logging

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

---

For more information, visit the interactive API documentation at `/docs` when the server is running.
