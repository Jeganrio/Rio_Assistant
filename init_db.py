"""
FastAPI Application Initialization Script

This script sets up the database and initializes the FastAPI application.
Run this before starting the server for the first time.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import Base, engine, SessionLocal
import models
from config import settings

def initialize_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")

def create_directories():
    """Create required directories"""
    directories = [
        settings.DATA_DIR,
        settings.SONGS_DIR,
        settings.SCREENSHOTS_DIR,
        settings.REMEMBER_DIR,
    ]
    
    print("\nCreating required directories...")
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}")

def verify_json_files():
    """Verify essential JSON files exist"""
    print("\nVerifying JSON configuration files...")
    cuby_json = settings.DATA_DIR / 'cuby.json'
    
    if not cuby_json.exists():
        print(f"⚠ Warning: {cuby_json} not found")
        print("  The chatbot won't work properly without this file.")
        return False
    else:
        print(f"✓ Found: {cuby_json}")
    
    return True

def main():
    """Run all initialization steps"""
    print("=" * 60)
    print("Cuby Assistant - FastAPI Initialization")
    print("=" * 60)
    
    try:
        # Initialize database
        initialize_database()
        
        # Create directories
        create_directories()
        
        # Verify configuration
        verify_json_files()
        
        print("\n" + "=" * 60)
        print("✓ Initialization Complete!")
        print("=" * 60)
        print("\nYou can now start the server with:")
        print("  python main.py")
        print("\nOr with uvicorn directly:")
        print("  uvicorn main:app --reload")
        print("\nAPI documentation will be available at:")
        print("  http://localhost:8000/docs")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Error during initialization: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
