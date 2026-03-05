"""Tests for normalization field mappers (Week 3 — Pydantic-based)."""

from __future__ import annotations

from agents.common.types.raw_job_record import RawJobRecord
from agents.normalization.mappers.crawl4ai_indeed import Crawl4AIIndeedMapper
from agents.normalization.mappers.crawl4ai_usajobs import Crawl4AIUSAJobsMapper
from agents.normalization.mappers.jsearch import JSearchMapper


def _raw_jsearch() -> RawJobRecord:
    return RawJobRecord(
        external_id="jsearch-abc",
        source="jsearch",
        title="Software Engineer",
        company="Acme Corp",
        description="Build awesome things.",
        city="Seattle",
        state="WA",
        country="US",
        employment_type="FULLTIME",
        salary_raw="$120,000 - $150,000",
        job_url="https://example.com/job/1",
    )


def _raw_indeed() -> RawJobRecord:
    return RawJobRecord(
        external_id="indeed-xyz",
        source="crawl4ai_indeed",
        title="Data Scientist",
        company="BigCo",
        description="Work with data.",
        city="Redmond",
        state="WA",
        country="US",
        job_url="https://indeed.com/viewjob?jk=xyz",
    )


def _raw_usajobs() -> RawJobRecord:
    return RawJobRecord(
        external_id="usajobs-123",
        source="crawl4ai_usajobs",
        title="IT Specialist",
        company="Department of Defense",
        description="Federal IT role.",
        city="Washington",
        state="DC",
        country="US",
        employment_type="FULLTIME",
        salary_raw="$90,000 - $120,000",
        job_url="https://usajobs.gov/job/123",
    )


class TestJSearchMapper:
    def test_maps_core_fields(self) -> None:
        mapper = JSearchMapper()
        result = mapper.map(_raw_jsearch())
        assert result.title == "Software Engineer"
        assert result.company == "Acme Corp"
        assert result.source == "jsearch"
        assert result.mapper_used == "jsearch_mapper"

    def test_maps_location(self) -> None:
        mapper = JSearchMapper()
        result = mapper.map(_raw_jsearch())
        assert result.city == "Seattle"
        assert result.state_province == "WA"
        assert result.country == "US"


class TestCrawl4AIIndeedMapper:
    def test_maps_core_fields(self) -> None:
        mapper = Crawl4AIIndeedMapper()
        result = mapper.map(_raw_indeed())
        assert result.title == "Data Scientist"
        assert result.company == "BigCo"
        assert result.source == "crawl4ai_indeed"
        assert result.mapper_used == "crawl4ai_indeed_mapper"

    def test_handles_minimal_fields(self) -> None:
        raw = RawJobRecord(
            external_id="min-1",
            source="crawl4ai_indeed",
            title="Dev",
            company="Co",
        )
        mapper = Crawl4AIIndeedMapper()
        result = mapper.map(raw)
        assert result.title == "Dev"
        assert result.company == "Co"


class TestCrawl4AIUSAJobsMapper:
    def test_maps_core_fields(self) -> None:
        mapper = Crawl4AIUSAJobsMapper()
        result = mapper.map(_raw_usajobs())
        assert result.title == "IT Specialist"
        assert result.company == "Department of Defense"
        assert result.source == "crawl4ai_usajobs"
        assert result.mapper_used == "crawl4ai_usajobs_mapper"

    def test_defaults_country_to_us(self) -> None:
        raw = RawJobRecord(
            external_id="uj-1",
            source="crawl4ai_usajobs",
            title="Analyst",
            company="GSA",
            country=None,
        )
        mapper = Crawl4AIUSAJobsMapper()
        result = mapper.map(raw)
        assert result.country == "US"

    def test_defaults_currency_to_usd(self) -> None:
        raw = RawJobRecord(
            external_id="uj-2",
            source="crawl4ai_usajobs",
            title="Engineer",
            company="NASA",
            salary_raw="$100,000",
        )
        mapper = Crawl4AIUSAJobsMapper()
        result = mapper.map(raw)
        assert result.salary_currency == "USD"
