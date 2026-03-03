"""
Shared path constants for agents (staging, data dirs).
Single source of truth so scraper and dashboard stay in sync.
"""
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_AGENTS_ROOT = _THIS_FILE.parents[1]  # agents/common -> agents/

STAGING_DIR = _AGENTS_ROOT / "data" / "staging"
RAW_SCRAPE_SAMPLE_PATH = STAGING_DIR / "raw_scrape_sample.json"
