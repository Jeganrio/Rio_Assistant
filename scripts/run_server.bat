@echo off
REM Cuby Assistant - FastAPI Server Startup Script

cd /d "%~dp0.."

echo.
echo ================================================================================
echo Cuby Assistant - FastAPI Server
echo ================================================================================
echo.

REM Check if venv exists
if not exist "venv\" (
    echo Error: Virtual environment not found!
    echo Please run: python -m venv venv
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Initialize database
echo Initializing database...
python scripts\init_db.py

REM Start the server
echo.
echo Starting FastAPI server...
echo.
echo API will be available at: http://localhost:8000
echo Documentation at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py

pause
