from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from cuby.config import settings


def create_database_engine(database_url: str):
    """Create an SQLAlchemy engine with driver-specific connection options."""
    return create_engine(database_url, **database_engine_kwargs(database_url))


def database_engine_kwargs(database_url: str) -> dict:
    """Return SQLAlchemy engine options that match the configured backend."""
    engine_kwargs = {}
    try:
        url = make_url(database_url)
        backend_name = url.get_backend_name()
    except Exception:
        backend_name = ""

    if backend_name == "sqlite":
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_pre_ping"] = True

    return engine_kwargs


engine = create_database_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
