from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import ClassVar

# Build paths from the project root, even though this module lives in cuby/.
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Cuby Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # OpenAI API Key
    OPENAI_API_KEY: str = ""
    GNEWS_API_KEY: str = ""
    AVIATIONSTACK_KEY: str = ""

    # Assistant alerts
    WEATHER_ALERT_CITY: str = "Trichy"
    WEATHER_ALERT_HOURS: int = 24
    WEATHER_ALERT_INTERVAL_MINUTES: int = 15
    WEATHER_AUTO_REMINDER_ENABLED: bool = True
    UTILITY_ALERT_ENABLED: bool = True
    UTILITY_ALERT_LOCATION: str = "Ponnagar, Karumandapam, Trichy"
    UTILITY_ALERT_INTERVAL_MINUTES: int = 60
    CALENDAR_ALERT_ENABLED: bool = True
    CALENDAR_ALERT_LOOKAHEAD_MINUTES: int = 30

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Make hosted Postgres URLs compatible with SQLAlchemy."""
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

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
        env_file = str(BASE_DIR / ".env")
        case_sensitive = True


settings = Settings()
