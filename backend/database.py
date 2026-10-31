"""
Database connection, session management, and safe schema initialization.
"""

import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Aqswdefr@123")
DB_NAME = os.getenv("DB_NAME", "supplier_schedule_manager")

# URL encode password for safety
encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# Engine with connection pooling and timeouts
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"connect_timeout": 10}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Verifies that MySQL is reachable and credentials are valid."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"[DB Warning] Could not connect to MySQL: {exc}")
        return False


def ensure_database_exists():
    """Ensures that the target database schema exists on the MySQL instance."""
    server_url = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/?charset=utf8mb4"
    try:
        temp_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with temp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        temp_engine.dispose()
    except Exception as exc:
        print(f"[DB Warning] Could not ensure database '{DB_NAME}' exists: {exc}")


def init_db(safe_only: bool = True):
    """
    Safely initializes tables using SQLAlchemy ORM metadata.
    Does NOT drop tables or delete user data during normal application startup.
    """
    ensure_database_exists()
    # Import models here to register them with Base.metadata
    from backend import models  # noqa
    Base.metadata.create_all(bind=engine)

