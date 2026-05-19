"""Application configuration loaded from .env and defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Paths ---
DATA_DIR = PROJECT_ROOT / "data"
CV_UPLOAD_DIR = DATA_DIR / "cvs"
DB_PATH = DATA_DIR / "ai-job-finder.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CV_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.0-flash")  # or "gpt-4"

# --- Email ---
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# --- Matching ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MATCH_TOP_K = 5
SIMILARITY_THRESHOLD = 0.5  # minimum cosine similarity to consider

# --- Scraping ---
SCRAPER_TIMEOUT = 30000  # ms
SCRAPER_DELAY = (2, 5)  # random delay between requests (min, max) seconds
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# --- Auto-Apply ---
MAX_APPLICATIONS_PER_RUN = 5
CONFIRM_BEFORE_SUBMIT = True

# --- App ---
APP_NAME = "JobFinder"
APP_VERSION = "0.1.0"
