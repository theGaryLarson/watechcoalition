"""
Shared datetime formatting for display (scraper, dashboard, etc.).
Single place for ISO timestamp → human-readable UTC to avoid duplication.
"""
from datetime import datetime


def format_iso_timestamp_for_display(iso_timestamp: str) -> str:
    """Format ISO timestamp for human-readable display (e.g. Feb 27, 2026 at 3:45 PM UTC)."""
    if not iso_timestamp or iso_timestamp == "—":
        return "—"
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %I:%M %p UTC").replace(" 0", " ")
    except (ValueError, TypeError):
        return iso_timestamp
