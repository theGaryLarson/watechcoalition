"""JSearch API adapter via RapidAPI.

Reads ``JSEARCH_API_KEY`` from environment.  Uses httpx with retry/backoff
per CLAUDE.md retry policy (5 max, exponential + jitter).
"""

from __future__ import annotations

import asyncio
import os
import random

import httpx
import structlog

from agents.common.types.raw_job_record import RawJobRecord
from agents.common.types.region_config import RegionConfig
from agents.ingestion.sources.base_adapter import SourceAdapter

log = structlog.get_logger()

_JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"
_MAX_RETRIES = 5
_BASE_DELAY = 1.0  # seconds


def _map_jsearch_record(raw: dict, region_id: str) -> RawJobRecord:
    """Map a JSearch API result to a typed RawJobRecord."""
    city = raw.get("job_city") or ""
    state = raw.get("job_state") or ""

    return RawJobRecord(
        external_id=str(raw.get("job_id", "")),
        source="jsearch",
        region_id=region_id,
        title=raw.get("job_title", ""),
        company=raw.get("employer_name", ""),
        description=raw.get("job_description", ""),
        city=city or None,
        state=state or None,
        country=raw.get("job_country") or None,
        is_remote=raw.get("job_is_remote"),
        date_posted=raw.get("job_posted_at_datetime_utc"),
        salary_raw=raw.get("job_salary_raw"),
        salary_min=raw.get("job_min_salary"),
        salary_max=raw.get("job_max_salary"),
        salary_currency=raw.get("job_salary_currency"),
        salary_period=raw.get("job_salary_period"),
        employment_type=raw.get("job_employment_type"),
        experience_level=raw.get("job_required_experience", {}).get("required_experience_in_months")
        if isinstance(raw.get("job_required_experience"), dict)
        else None,
        job_url=raw.get("job_apply_link") or raw.get("job_google_link", ""),
        raw_payload=raw,
    )


class JSearchAdapter(SourceAdapter):
    """Fetches job postings from JSearch API (RapidAPI)."""

    @property
    def source_name(self) -> str:
        return "jsearch"

    def __init__(self) -> None:
        self._api_key = os.getenv("JSEARCH_API_KEY", "")

    async def fetch(self, region: RegionConfig) -> list[RawJobRecord]:
        """Fetch job postings from JSearch for the given region."""
        if not self._api_key:
            log.warning("jsearch_no_api_key", note="JSEARCH_API_KEY not set, returning empty")
            return []

        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        keywords = ", ".join(region.keywords) if region.keywords else ""
        roles = ", ".join(region.role_categories) if region.role_categories else "software engineer"
        query_text = keywords or roles
        location = region.query_location

        all_records: list[RawJobRecord] = []
        page = 1
        limit = 50

        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(all_records) < limit:
                params = {
                    "query": f"{query_text} in {location}",
                    "page": str(page),
                    "num_pages": "1",
                }

                data = await self._request_with_retry(client, headers, params)
                if data is None:
                    break

                results = data.get("data", [])
                if not results:
                    break

                for raw in results:
                    if len(all_records) >= limit:
                        break
                    all_records.append(_map_jsearch_record(raw, region.region_id))

                page += 1

        log.info(
            "jsearch_fetch_complete",
            count=len(all_records),
            query=query_text,
            location=location,
        )
        return all_records

    async def _request_with_retry(
        self, client: httpx.AsyncClient, headers: dict, params: dict
    ) -> dict | None:
        """Make a single API request with exponential backoff + jitter."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await client.get(_JSEARCH_BASE_URL, headers=headers, params=params)

                if resp.status_code == 429:
                    delay = _BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    log.warning("jsearch_rate_limited", attempt=attempt, delay_s=round(delay, 2))
                    await asyncio.sleep(delay)
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as exc:
                log.warning("jsearch_http_error", status=exc.response.status_code, attempt=attempt)
                if attempt == _MAX_RETRIES:
                    return None
                delay = _BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                await asyncio.sleep(delay)

            except httpx.RequestError as exc:
                log.warning("jsearch_request_error", error=str(exc), attempt=attempt)
                if attempt == _MAX_RETRIES:
                    return None
                delay = _BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                await asyncio.sleep(delay)

        return None

    async def health_check(self) -> dict:
        """Return adapter readiness status."""
        return {"reachable": bool(self._api_key), "source": self.source_name}
