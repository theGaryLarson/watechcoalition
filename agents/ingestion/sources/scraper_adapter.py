"""Crawl4AI scraper adapter with fixture fallback.

When ``SCRAPING_TARGETS`` is empty (or unset), falls back to the fixture
file at ``agents/data/fixtures/fallback_scrape_sample.json``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import structlog

from agents.ingestion.sources.base_adapter import SourceAdapter

log = structlog.get_logger()

_FALLBACK_SCRAPE = (
    Path(__file__).parent.parent.parent  # agents/
    / "data"
    / "fixtures"
    / "fallback_scrape_sample.json"
)


def _map_fixture_record(raw: dict) -> dict:
    """Map a fallback fixture record to our canonical raw record shape."""
    return {
        "external_id": str(raw.get("posting_id", "")),
        "source": "crawl4ai",
        "title": raw.get("title", ""),
        "company": raw.get("company", ""),
        "location": raw.get("location"),
        "raw_text": raw.get("raw_text", ""),
        "url": raw.get("url", ""),
        "date_posted": raw.get("timestamp", ""),
        "raw_payload": raw,
    }


class ScraperAdapter(SourceAdapter):
    """Fetches job postings via Crawl4AI or fixture fallback."""

    source_name = "crawl4ai"

    def __init__(self) -> None:
        targets = os.getenv("SCRAPING_TARGETS", "")
        self._targets = [t.strip() for t in targets.split(",") if t.strip()]

    async def fetch(self, *, limit: int = 50, query: str = "", location: str = "") -> list[dict]:
        if self._targets:
            return await self._fetch_live(limit=limit)
        return self._fetch_fixture(limit=limit)

    async def _fetch_live(self, *, limit: int = 50) -> list[dict]:
        """Fetch from real scraping targets using Crawl4AI."""
        records: list[dict] = []
        try:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler() as crawler:
                for url in self._targets:
                    if len(records) >= limit:
                        break
                    try:
                        result = await crawler.arun(url=url)
                        if result.success and result.markdown:
                            records.append({
                                "external_id": url,
                                "source": "crawl4ai",
                                "title": "",
                                "company": "",
                                "location": None,
                                "raw_text": result.markdown,
                                "url": url,
                                "date_posted": "",
                                "raw_payload": {"url": url, "markdown_length": len(result.markdown)},
                            })
                    except Exception as exc:
                        log.warning("scraper_target_failed", url=url, error=str(exc))

        except ImportError:
            log.warning("crawl4ai_not_installed", note="falling back to fixture")
            return self._fetch_fixture(limit=limit)

        log.info("scraper_live_fetch_complete", count=len(records))
        return records

    def _fetch_fixture(self, *, limit: int = 50) -> list[dict]:
        """Load job postings from the fallback fixture file."""
        if not _FALLBACK_SCRAPE.exists():
            log.warning("scraper_fixture_missing", path=str(_FALLBACK_SCRAPE))
            return []

        raw_list: list[dict] = json.loads(_FALLBACK_SCRAPE.read_text(encoding="utf-8"))
        records = [_map_fixture_record(r) for r in raw_list[:limit]]
        log.info("scraper_fixture_loaded", count=len(records), path=str(_FALLBACK_SCRAPE))
        return records

    async def health_check(self) -> bool:
        if self._targets:
            return True
        return _FALLBACK_SCRAPE.exists()
