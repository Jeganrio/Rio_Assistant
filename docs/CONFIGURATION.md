# Cuby Assistant FastAPI - Configuration Guide

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# App Configuration
DEBUG=True
APP_NAME=Cuby Assistant
APP_VERSION=1.0.0

# Database Configuration
DATABASE_URL=sqlite:///./db.sqlite3
# For PostgreSQL: DATABASE_URL=postgresql://user:password@localhost/cuby_db

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

## Configuration File (cuby/config.py)

The `cuby/config.py` file contains all application settings. Key configurations:

### App Settings
- `APP_NAME`: Name of the application
- `APP_VERSION`: Version of the application
- `DEBUG`: Enable/disable debug mode

### Database
- `DATABASE_URL`: Database connection string
  - SQLite: `sqlite:///./db.sqlite3`
  - PostgreSQL: `postgresql://user:password@host/dbname`
  - MySQL: `mysql+pymysql://user:password@host/dbname`

### Directory Paths
These are automatically detected from the project structure:
- `BASE_DIR`: Root project directory
- `DATA_DIR`: AI logic data directory
- `SONGS_DIR`: Directory containing song files
- `SCREENSHOTS_DIR`: Directory for saving screenshots
- `REMEMBER_DIR`: Directory for storing remembered data

### Server Configuration
- `SERVER_HOST`: Server bind address (0.0.0.0 for all interfaces)
- `SERVER_PORT`: Server port number (default: 8000)

## Customization Examples

### Change Server Port
```env
SERVER_PORT=8080
```

Then access API at `http://localhost:8080`

### Enable Production Mode
```env
DEBUG=False
```

### Use PostgreSQL
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/cuby_assistant
```

Install PostgreSQL driver:
```bash
pip install psycopg2-binary
```

### Change App Name
```env
APP_NAME=My Custom AI Assistant
```

## Database Configuration

### SQLite (Default)
No additional setup needed. Database is created automatically in `db.sqlite3`.

### PostgreSQL (Recommended for Production)

1. **Install PostgreSQL**
2. **Create database**
   ```sql
   CREATE DATABASE cuby_assistant;
   CREATE USER cuby_user WITH PASSWORD 'secure_password';
   ALTER ROLE cuby_user SET client_encoding TO 'utf8';
   ALTER ROLE cuby_user SET default_transaction_isolation TO 'read committed';
   ALTER ROLE cuby_user SET default_transaction_deferrable TO on;
   GRANT ALL PRIVILEGES ON DATABASE cuby_assistant TO cuby_user;
   ```

3. **Update .env**
   ```env
   DATABASE_URL=postgresql://cuby_user:secure_password@localhost:5432/cuby_assistant
   ```

4. **Install driver**
   ```bash
   pip install psycopg2-binary
   ```

5. **Run initialization**
   ```bash
   python scripts\init_db.py
   ```

### MySQL

1. **Install MySQL**
2. **Create database**
   ```sql
   CREATE DATABASE cuby_assistant;
   CREATE USER 'cuby_user'@'localhost' IDENTIFIED BY 'password';
   GRANT ALL PRIVILEGES ON cuby_assistant.* TO 'cuby_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. **Update .env**
   ```env
   DATABASE_URL=mysql+pymysql://cuby_user:password@localhost/cuby_assistant
   ```

4. **Install driver**
   ```bash
   pip install pymysql
   ```

## Speech Recognition Configuration

### Microphone Selection
The application uses the default microphone. To use a specific microphone:

```python
# In AI_logic.py, modify takecommandexceptional()
import speech_recognition as sr

r = sr.Recognizer()
microphones = sr.Microphone.list_microphone_indexes()
print(microphones)  # Lists available microphones

# Use microphone index 0 (or any index)
with sr.Microphone(device_index=0) as source:
    audio = r.listen(source, phrase_time_limit=5)
```

### Language Configuration
Default is English (India). To change:

```python
# In AI_logic.py, change inp_lang variable
inp_lang = 'en-US'  # English (US)
inp_lang = 'fr-FR'  # French
inp_lang = 'de-DE'  # German
inp_lang = 'es-ES'  # Spanish
```

See [language codes](https://www.sitepoint.com/ISO-639-1-language-codes/)

### Voice Configuration
To change the text-to-speech voice:

```python
# In speak() function, modify voice selection
voices = engine.getProperty('voices')
for voice in voices:
    print(f"Voice ID: {voice.id}, Name: {voice.name}")
    # Use the voice you want
    if 'David' in voice.name:  # Windows David voice
        engine.setProperty('voice', voice.id)
```

## Logging Configuration

### Enable File Logging
Create `logging_config.py`:

```python
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # File handler
    file_handler = RotatingFileHandler(
        f'{log_dir}/cuby.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

setup_logging()
```

Then import in `cuby/main.py`:
```python
from logging_config import setup_logging
setup_logging()
```

## CORS Configuration

To enable CORS (for accessing API from other domains):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, specify exact origins:
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com"
]
```

## Static Files Configuration

### Serve Static Files
```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="AI_logic_app/static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
```

## Rate Limiting Configuration

Add to `requirements.txt`:
```
slowapi==0.1.8
```

In `cuby/main.py`:
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

## Authentication Configuration (Optional)

For JWT authentication:

```bash
pip install python-jose[cryptography]
pip install passlib[bcrypt]
```

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key-change-this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

## Performance Tuning

### Database Connection Pooling
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)
```

### Caching
Add to requirements.txt:
```
aioredis==2.0.1
```

```python
import aioredis
from fastapi_cache2 import FastAPICache2
from fastapi_cache2.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache2.init(RedisBackend(redis), prefix="fastapi-cache")
```

## File Upload Configuration

```python
from fastapi import UploadFile, File

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    with open(f"uploads/{file.filename}", "wb") as f:
        f.write(contents)
    return {"filename": file.filename}
```

Create `uploads` directory:
```bash
mkdir uploads
```

## Production Deployment Configuration

### Gunicorn + Uvicorn
```bash
pip install gunicorn

gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Environment Variables for Production
```env
DEBUG=False
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DATABASE_URL=postgresql://user:pass@db.example.com/cuby
SECRET_KEY=your-very-secure-random-key-here
```

### Docker Configuration
Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t cuby-assistant .
docker run -p 8000:8000 cuby-assistant
```

## Troubleshooting Configuration Issues

### Import Errors
- Ensure all files are in the correct directories
- Check `PYTHONPATH` includes the project root
- Verify all dependencies in `requirements.txt` are installed

### Database Connection Errors
- Check database URL in `.env`
- Verify database server is running
- Check database credentials
- Ensure database/user exists

### Static Files Not Loading
- Verify `AI_logic_app/static` directory exists
- Check mount path in `cuby/main.py`
- Ensure file permissions are correct

### Microphone Not Working
- Check Windows sound settings
- Test microphone with other applications
- Run application as Administrator
- Check microphone device index

---

For additional help, see the root README.md or docs/API_DOCUMENTATION.md.
