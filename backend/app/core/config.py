import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# Fallback: check frontend/.env if root .env did not set GEMINI_API_KEY
if not os.getenv("GEMINI_API_KEY"):
    load_dotenv(BASE_DIR / "frontend" / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'celebration_planner.db'}")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "INR")
JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").strip()

