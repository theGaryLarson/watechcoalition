"""JobRecord — typed representation of a normalized job posting.

Produced by normalization mappers.
Stored in normalized_jobs table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class JobRecord(BaseModel):
    """A single normalized job record ready for storage."""

    # References
    raw_job_id: int = 0
    ingestion_run_id: str = ""
    region_id: str = ""

    # Identity
    source: str
    external_id: str

    # Core fields
    title: str
    company: str
    description: Optional[str] = None
    job_url: Optional[str] = None

    # Location (structured)
    city: Optional[str] = None
    state_province: Optional[str] = None
    country: Optional[str] = None
    work_arrangement: Optional[str] = None
    is_remote: Optional[bool] = None

    # Dates
    date_posted: Optional[datetime] = None

    # Salary
    salary_raw: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None

    # Classification
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    occupation_code: Optional[str] = None

    # Mapper provenance
    mapper_used: str = ""

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()

    @field_validator("company")
    @classmethod
    def company_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("company must not be empty")
        return v.strip()

    @field_validator("salary_max")
    @classmethod
    def salary_max_gte_min(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and info.data.get("salary_min") is not None:
            if v < info.data["salary_min"]:
                raise ValueError("salary_max must be >= salary_min")
        return v
