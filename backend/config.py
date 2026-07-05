"""
NARAD - Neural Agentic Real-time Advisor for Decisions
Configuration module
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── AI / Gemini ─────────────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL        = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# google-adk / google-genai reads GEMINI_API_KEY or GOOGLE_API_KEY from the
# environment automatically. Ensure it's set even if only passed via .env.
if GEMINI_API_KEY:
    os.environ.setdefault("GEMINI_API_KEY", GEMINI_API_KEY)
    os.environ.setdefault("GOOGLE_API_KEY", GEMINI_API_KEY)

# ─── Google Cloud ─────────────────────────────────────────────────────────────
GCP_PROJECT_ID      = os.getenv("GCP_PROJECT_ID", "narad-city-ai")
GCP_REGION          = os.getenv("GCP_REGION", "us-central1")
BIGQUERY_DATASET    = os.getenv("BIGQUERY_DATASET", "narad_city_data")

# ─── External Data APIs (free tiers) ─────────────────────────────────────────
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENAQ_API_KEY      = os.getenv("OPENAQ_API_KEY", "")
NEWS_API_KEY        = os.getenv("NEWS_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ─── City Configuration ───────────────────────────────────────────────────────
DEFAULT_CITY        = os.getenv("DEFAULT_CITY", "Hyderabad")
DEFAULT_LAT         = float(os.getenv("DEFAULT_LAT", "17.3850"))
DEFAULT_LNG         = float(os.getenv("DEFAULT_LNG", "78.4867"))

# ─── Application ──────────────────────────────────────────────────────────────
APP_NAME            = "NARAD"
APP_VERSION         = "1.0.0"
DEBUG               = os.getenv("DEBUG", "false").lower() == "true"
PORT                = int(os.getenv("PORT", "8080"))

# Parliament simulation interval (seconds)
PARLIAMENT_INTERVAL = int(os.getenv("PARLIAMENT_INTERVAL", "60"))
DATA_REFRESH_INTERVAL = int(os.getenv("DATA_REFRESH_INTERVAL", "30"))

# ─── RAPIDS / GPU ─────────────────────────────────────────────────────────────
USE_GPU             = os.getenv("USE_GPU", "auto")  # auto | true | false
SCENARIO_COUNT      = int(os.getenv("SCENARIO_COUNT", "1000"))
