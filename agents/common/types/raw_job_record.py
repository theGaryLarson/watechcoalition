"""RawJobRecord — typed representation of a raw job posting from any source.

Produced by source adapters in the ingestion layer.
Consumed by the deduplicator and stored in raw_ingested_jobs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RawJobRecord(BaseModel):
    """A single raw job posting as returned by a source adapter."""

    # Identity
    external_id: str
    source: str
    region_id: str = ""
    raw_payload_hash: str = ""

    # Core fields
    title: str
    company: str
    description: str = ""

    # Location (structured)
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    is_remote: Optional[bool] = None

    # Dates
    date_posted: Optional[datetime] = None
    date_ingested: datetime = Field(default_factory=datetime.utcnow)

    # Salary
    salary_raw: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None

    # Classification
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None

    # URLs
    job_url: Optional[str] = None
    source_url: str = ""

    # Raw payload (full API response)
    raw_payload: dict = Field(default_factory=dict)
