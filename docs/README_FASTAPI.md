# Cuby AI Assistant - FastAPI Version

A powerful AI-powered desktop assistant built with FastAPI that can listen to voice commands, process them, and respond intelligently. The application includes features like system control, web searching, file manipulation, and much more.

## Features

### Core AI Features
- **Voice Recognition**: Listens and recognizes voice commands using Google Speech Recognition
- **Text-to-Speech**: Responds with natural speech using pyttsx3
- **Intelligent Chatbot**: Uses intent matching from JSON patterns
- **Web Scraping**: Searches the web and extracts information from articles
- **Code Extraction**: Finds and displays relevant code snippets

### System Control
- **System Commands**: Shutdown, restart, lock, and control your PC
- **Window Management**: Minimize, maximize, and control application windows
- **File Explorer**: Navigate through folders and files
- **Settings Access**: Open Windows Control Panel and settings

### Productivity Features
- **Memory System**: Remember and recall information
- **Note Taking**: Writer mode for voice-controlled typing
- **Song Playback**: Play local songs with voice commands
- **Screenshots**: Take screenshots and save them
- **System Info**: Check CPU usage and battery status

### Information Features
- **Definition Lookup**: Get short and long definitions of terms
- **Wikipedia Integration**: Search and read Wikipedia articles
- **Technical Jokes**: Get technical jokes on demand
- **Date & Time**: Tell current date and time
- **Google Search**: Search the web and display results

## Technology Stack

- **Backend**: FastAPI (async Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Voice Processing**: SpeechRecognition, pyttsx3
- **Automation**: pyautogui, pygetwindow
- **Web Scraping**: BeautifulSoup, newspaper3k, requests
- **Server**: Uvicorn
- **API Documentation**: Swagger UI (automatic)

## Installation

### Prerequisites
- Python 3.8+
- pip package manager
- Windows OS (for Windows-specific features)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Cuby_Assistant-main
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   copy .env.example .env
   # Edit .env if needed
   ```

5. **Initialize the database**
   ```bash
   python scripts\init_db.py
   ```

## Running the Application

### Start the FastAPI Server
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload
```

The API will be available at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs` (Swagger UI)
- Alternative Docs: `http://localhost:8000/redoc` (ReDoc)

## API Endpoints

### Core Endpoints
- `GET /` - Home page
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

### Page Endpoints
- `GET /about` - About page
- `GET /user_manual` - User manual
- `GET /troubleshoot` - Troubleshooting guide

### Query Database Endpoints
- `POST /api/queries` - Save a new query and answer
- `GET /api/queries` - Get all queries
- `GET /api/queries/{id}` - Get specific query
- `PUT /api/queries/{id}` - Update a query
- `DELETE /api/queries/{id}` - Delete a query

### AI Command Endpoints
- `POST /api/ai/start` - Start the AI assistant
- `POST /api/ai/speak` - Make AI speak text
- `POST /api/ai/command` - Execute a voice command
- `POST /api/ai/remember` - Remember information
- `GET /api/ai/remember` - Recall remembered information
- `POST /api/ai/write` - Activate writer mode
- `POST /api/ai/define` - Get definition of a term
- `GET /api/ai/shutdown` - Shutdown the system
- `GET /api/ai/lock` - Lock the system
- `GET /api/ai/restart` - Restart the system

## Usage Examples

### Using Python Requests
```python
import requests

# Start the AI
response = requests.post("http://localhost:8000/api/ai/start")

# Make AI speak
response = requests.post(
    "http://localhost:8000/api/ai/speak",
    json={"text": "Hello, this is Cuby", "rate": 125}
)

# Execute a command
response = requests.post(
    "http://localhost:8000/api/ai/command",
    json={"command": "what is the current time"}
)

# Save a query
response = requests.post(
    "http://localhost:8000/api/queries",
    json={"query": "How do I use Python?", "answers": "Python is..."}
)
```

### Using cURL
```bash
# Start the AI
curl -X POST "http://localhost:8000/api/ai/start"

# Get all queries
curl -X GET "http://localhost:8000/api/queries"

# Get health status
curl -X GET "http://localhost:8000/health"
```

## Voice Commands

Once the AI is running, you can use voice commands like:

- "Hey Cuby" - Activate the assistant
- "What time is it?" - Get current time
- "What's the date?" - Get current date
- "Check CPU" - Check CPU usage and battery
- "Take a screenshot" - Capture screen
- "Remember that I like coding" - Store information
- "Do you remember what I said?" - Retrieve stored information
- "Play [song name]" - Play a song from your library
- "Make a search [query]" - Search the web
- "Define [term]" - Get definition of a term
- "Tell me a joke" - Get a technical joke
- "Open settings" - Open Windows Control Panel
- "Turn off" - Shutdown the system

## Project Structure

```text
Cuby_Assistant-main/
|-- main.py                  # Compatibility entrypoint for uvicorn main:app
|-- cuby/                    # FastAPI backend package
|   |-- main.py              # Application setup, routes, static pages
|   |-- config.py            # Configuration settings
|   |-- database.py          # SQLAlchemy setup
|   |-- models.py            # SQLAlchemy ORM models
|   |-- schemas.py           # Pydantic request/response schemas
|   |-- api_routes.py        # Query database endpoints
|   |-- ai_commands.py       # AI command endpoints
|   |-- mcp_router.py        # MCP REST routes
|   `-- mcp_tools.py         # MCP-style tools
|-- scripts/                 # Setup and run helpers
|-- docs/                    # Project documentation
|-- templates/               # HTML templates
|-- AI_logic_app/
|   |-- AI_logic.py          # Core assistant logic
|   |-- data/                # Assistant data, songs, screenshots, memory
|   `-- static/              # Static assets served at /static
|-- requirements.txt         # Python dependencies
|-- Procfile                 # Deployment configuration
`-- README.md                # Root quick start
```
## Database Schema

### CubyQueries Table
```sql
CREATE TABLE cubyqueries (
    id INTEGER PRIMARY KEY,
    query TEXT NOT NULL,
    answers TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Configuration

Edit the `cuby/config.py` file to modify:
- App name and version
- Debug mode
- Database URL
- Server host and port
- Data directory paths

Or set environment variables in `.env`:
```env
DEBUG=True
DATABASE_URL=sqlite:///./db.sqlite3
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

## Troubleshooting

### PyAudio Installation Issues
If you encounter PyAudio errors:
1. Download pre-compiled wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)
2. Install with: `pip install PyAudio-0.2.11-cp311-cp311-win_amd64.whl`
3. Or use: `conda install pyaudio`

### Microphone Issues
- Ensure your microphone is connected and set as default
- Check Windows sound settings
- Run as Administrator if needed

### Database Issues
- Delete `db.sqlite3` to reset the database
- Run initialization command again

## Deployment

### Local Deployment
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Production Deployment
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Heroku Deployment
```bash
git push heroku main
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Changelog

### Version 1.0.0 (FastAPI Migration)
- Complete migration from Django to FastAPI
- All Django functions ported to FastAPI endpoints
- Enhanced API documentation with Swagger UI
- SQLAlchemy ORM implementation
- Background task support
- Improved error handling
- Better configuration management

## Support

For issues, feature requests, or questions:
1. Check the troubleshooting section
2. Open an issue on the repository
3. Check existing issues for solutions

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [SpeechRecognition](https://github.com/Uberi/speech_recognition)
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3)
- And many other open-source libraries

---

Made with â¤ï¸ for voice-controlled automation enthusiasts


