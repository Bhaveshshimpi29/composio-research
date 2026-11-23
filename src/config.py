"""All settings live here (or in .env). Nothing else hard-codes models, paths or limits."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
RAW = DATA / "raw"                 # cached pages (one folder per app)
RAW_LIVE = DATA / "raw_live"       # pages re-read by the browser check
DISCOVERED = DATA / "discovered"   # urls found per app
RESULTS = DATA / "results.jsonl"   # one record per app per pass
RUNS = DATA / "runs.jsonl"         # model, prompt version, date, tokens, seconds per step
APPS_CSV, HINTS_CSV = DATA / "apps.csv", DATA / "hints.csv"
GOLD_CSV, CORRECTIONS_CSV = DATA / "gold.csv", DATA / "corrections.csv"
MISS_NOTES_CSV, REVIEW_QUEUE_CSV = DATA / "miss_notes.csv", DATA / "review_queue.csv"
SITE = ROOT / "site"

MODEL_DISCOVER = os.getenv("MODEL_DISCOVER", "claude-haiku-5-5")
MODEL_EXTRACT = os.getenv("MODEL_EXTRACT", "claude-sonnet-5-5")
MODEL_SECOND = os.getenv("MODEL_SECOND", "claude-opus-5-5")   # a different model on purpose
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "anthropic")   # anthropic | composio
PROMPT_VERSION = "v1"

MAX_URLS_PER_APP = 6
MAX_CHARS_PER_PAGE = 14000      # what the LLM sees per page (the full page is still cached)
MAX_CHARS_TOTAL = 60000
WORKERS = int(os.getenv("WORKERS", "4"))
FETCH_DELAY_SECONDS = 1.0       # politeness delay between requests to the same host
FETCH_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (compatible; ComposioAssignmentResearchBot/1.0; student research)"

def _f(name):
    v = os.getenv(name, "").strip()
    return float(v) if v else None
PRICE_IN_PER_MTOK, PRICE_OUT_PER_MTOK = _f("PRICE_IN_PER_MTOK"), _f("PRICE_OUT_PER_MTOK")
