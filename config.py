from pathlib import Path
from pydantic_settings import BaseSettings
from typing import ClassVar

# Build paths
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Cuby Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # OpenAI API Key
    OPENAI_API_KEY: str = ""

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

    # Paths
    BASE_DIR: ClassVar[Path] = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "AI_logic_app" / "data"
    SONGS_DIR: Path = DATA_DIR / "songs"
    SCREENSHOTS_DIR: Path = DATA_DIR / "screenshots"
    REMEMBER_DIR: Path = DATA_DIR / "remember"

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()