import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("BEEHIVE_MODEL", "claude-haiku-4-5-20251001")
CONTACT = os.getenv("CRAWLER_CONTACT", "beehive-crawler")
USER_AGENT = f"BeehiveCrawler/0.1 (+student job search; contact: {CONTACT})"

COMPANIES_FILE = ROOT / "companies.yaml"
CANDIDATES_FILE = ROOT / "candidates.txt"
LOCAL_STORE = ROOT / "data" / "jobs.json"
ENRICH_CACHE = ROOT / "data" / "enrich_cache.json"

def supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)
