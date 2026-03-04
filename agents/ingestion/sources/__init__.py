"""Source adapters for the Ingestion Agent."""

from agents.ingestion.sources.base_adapter import SourceAdapter
from agents.ingestion.sources.jsearch_adapter import JSearchAdapter
from agents.ingestion.sources.scraper_adapter import ScraperAdapter

__all__ = ["JSearchAdapter", "ScraperAdapter", "SourceAdapter"]
