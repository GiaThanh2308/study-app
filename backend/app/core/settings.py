"""Local-only runtime configuration loaded from backend/.env and the process env."""

import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env", override=False)

DATA_DIR = Path(os.getenv("STUDYAPP_DATA_DIR", str(BACKEND_DIR / "data"))).expanduser()
if not DATA_DIR.is_absolute():
    DATA_DIR = (BACKEND_DIR / DATA_DIR).resolve()

# Default to a new database inside the local data directory. The legacy DB is left untouched.
DB_PATH = Path(os.getenv("STUDYAPP_DB_PATH", str(DATA_DIR / "studyapp.sqlite3"))).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = (BACKEND_DIR / DB_PATH).resolve()

DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1024"))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
APP_HOST = "127.0.0.1"
APP_PORT = int(os.getenv("APP_PORT", "8000"))
LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
