"""Abstract base class for ingestion source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SourceAdapter(ABC):
    """All source adapters (JSearch, Crawl4AI, etc.) implement this interface."""

    source_name: str = "unknown"

    @abstractmethod
    async def fetch(self, *, limit: int = 50, query: str = "", location: str = "") -> list[dict]:
        """Fetch raw job postings from the source.

        Returns a list of dicts with at minimum:
            external_id, source, title, company, location, raw_text, url, date_posted
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the source is reachable."""
