"""A15 ingestion runner: end-to-end flow, idempotency, dry-run, error isolation."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from opportunity_api.core.database import Base
from opportunity_api.ingestion.models import RawOpportunity
from opportunity_api.ingestion.persistence import NormalizedOpportunity, OpportunityStore
from opportunity_api.ingestion.registry import AdapterRegistry
from opportunity_api.ingestion.runner import IngestionRunner
from opportunity_api.ingestion.sources.base import SourceAdapter
from opportunity_api.models import Opportunity


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_raw(source: str, idx: int, **overrides: object) -> RawOpportunity:
    fields: dict[str, object] = {
        "source": source,
        "source_id": f"{source}-job-{idx}",
        "source_url": f"https://example.com/{source}/jobs/{idx}",
        "title": "Software Engineering Intern",
        "organization": "Acme",
        "description": "Python and cloud internship for students.",
        "location": "Berlin, Germany",
        "deadline_raw": "2026-12-01",
        "degree_level_raw": "bachelor or master",
        "study_year_raw": "2-4",
        "fetched_at": datetime(2026, 10, 22, tzinfo=UTC),
    }
    fields.update(overrides)
    return RawOpportunity(**fields)


class StaticAdapter(SourceAdapter):
    """Test adapter yielding a fixed record list, or raising on fetch."""

    def __init__(self, name: str, records: list[RawOpportunity], exc: Exception | None = None):
        self.source_name = name
        self._records = records
        self._exc = exc

    def fetch(self):
        if self._exc is not None:
            raise self._exc
        return iter(self._records)


def count_opportunities(session: Session) -> int:
    return session.execute(select(func.count()).select_from(Opportunity)).scalar_one()


def test_idempotency_second_run_updates_not_duplicates(session):
    records = [make_raw("greenhouse", i) for i in range(10)]
    adapter = StaticAdapter("greenhouse", records)
    runner = IngestionRunner(OpportunityStore(session))

    first = runner.run([adapter])
    assert first.source("greenhouse").created == 10
    assert first.source("greenhouse").updated == 0
    assert count_opportunities(session) == 10

    second = runner.run([StaticAdapter("greenhouse", records)])
    assert second.source("greenhouse").created == 0
    assert second.source("greenhouse").updated == 10
    assert count_opportunities(session) == 10


def test_rerun_with_changed_data_updates_fields(session):
    adapter = StaticAdapter("lever", [make_raw("lever", 1, title="Software Engineering Intern")])
    runner = IngestionRunner(OpportunityStore(session))
    runner.run([adapter])

    changed = make_raw(
        "lever", 1, title="Software Engineering Intern (f/m/d)", deadline_raw="2027-01-15"
    )
    report = runner.run([StaticAdapter("lever", [changed])])
    assert report.source("lever").updated == 1

    row = session.execute(select(Opportunity)).scalar_one()
    assert row.title == "Software Engineering Intern (f/m/d)"
    assert row.deadline is not None and row.deadline.date().isoformat() == "2027-01-15"
    assert count_opportunities(session) == 1


def test_error_isolation_failing_source_does_not_stop_run(session):
    ok_a = StaticAdapter("greenhouse", [make_raw("greenhouse", 1)])
    broken = StaticAdapter("lever", [], exc=RuntimeError("lever API down"))
    ok_b = StaticAdapter("smartrecruiters", [make_raw("smartrecruiters", 1)])

    report = IngestionRunner(OpportunityStore(session)).run([ok_a, broken, ok_b])

    assert report.failed_sources == ["lever"]
    assert report.source("greenhouse").created == 1
    assert report.source("smartrecruiters").created == 1
    assert "lever" in report.render()
    assert count_opportunities(session) == 2


def test_dry_run_reports_would_create_and_writes_nothing(session):
    store = OpportunityStore(session)
    dry = IngestionRunner(store, dry_run=True)
    records = [make_raw("greenhouse", i) for i in range(5)]

    report = dry.run([StaticAdapter("greenhouse", records)])
    source = report.source("greenhouse")
    assert source.would_create == 5
    assert source.would_update == 0
    assert source.created == 0
    assert count_opportunities(session) == 0
    assert "dry run" in report.render()

    # After a real run, the same data classifies as updates — still no writes.
    IngestionRunner(store).run([StaticAdapter("greenhouse", records)])
    second = dry.run([StaticAdapter("greenhouse", records)])
    assert second.source("greenhouse").would_create == 0
    assert second.source("greenhouse").would_update == 5
    assert second.source("greenhouse").created == 0
    assert count_opportunities(session) == 5


def test_out_of_scope_records_are_rejected(session):
    records = [
        make_raw("greenhouse", 1),  # in scope
        make_raw("greenhouse", 2, title="Senior Software Engineer"),  # not a student role
        make_raw("greenhouse", 3, location="Austin, TX, USA"),  # outside Europe
    ]
    report = IngestionRunner(OpportunityStore(session)).run([StaticAdapter("greenhouse", records)])

    source = report.source("greenhouse")
    assert source.fetched == 3
    assert source.accepted == 1
    assert source.rejected == 2
    assert source.created == 1


def test_invalid_record_is_counted_as_failed_not_fatal(session):
    # A normalizer that chokes on one record must not abort the run.
    bad = make_raw("greenhouse", 1)

    def default_normalizer(raw: RawOpportunity) -> dict[str, object]:
        from opportunity_api.ingestion.runner import default_normalize

        return default_normalize(raw)

    def selective(raw: RawOpportunity) -> dict[str, object]:
        if raw.source_id == "greenhouse-job-1":
            raise ValueError("simulated parse failure")
        return default_normalizer(raw)

    runner = IngestionRunner(
        OpportunityStore(session),
        normalizer=selective,
        validate=NormalizedOpportunity.model_validate,
    )
    records = [bad, make_raw("greenhouse", 2)]
    report = runner.run([StaticAdapter("greenhouse", records)])

    source = report.source("greenhouse")
    assert source.fetched == 2
    assert source.failed == 1
    assert source.created == 1
    assert count_opportunities(session) == 1


def test_report_renders_per_source_and_totals(session):
    adapters = [
        StaticAdapter("greenhouse", [make_raw("greenhouse", i) for i in range(3)]),
        StaticAdapter("lever", [make_raw("lever", i) for i in range(2)]),
    ]
    report = IngestionRunner(OpportunityStore(session)).run(adapters)
    text = report.render()

    assert "greenhouse: fetched=3" in text
    assert "lever: fetched=2" in text
    totals = report.totals()
    assert totals.fetched == 5
    assert totals.created == 5
    assert "created=5" in text


def test_registry_resolve_subset_and_all(session):
    registry = AdapterRegistry()
    registry.register(StaticAdapter("greenhouse", []))
    registry.register(StaticAdapter("lever", []))

    assert registry.names() == ["greenhouse", "lever"]
    assert [a.source_name for a in registry.resolve(["lever"])] == ["lever"]
    assert {a.source_name for a in registry.resolve()} == {"greenhouse", "lever"}

    with pytest.raises(KeyError, match="unknown source"):
        registry.resolve(["workday"])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(StaticAdapter("lever", []))


def test_dedupe_callback_skips_records(session):
    seen: set[str] = set()

    def dedupe(record: NormalizedOpportunity) -> bool:
        if record.source_id in seen:
            return True
        seen.add(record.source_id or "")
        return False

    records = [make_raw("greenhouse", 1), make_raw("greenhouse", 1)]
    runner = IngestionRunner(OpportunityStore(session), dedupe=dedupe)
    report = runner.run([StaticAdapter("greenhouse", records)])

    assert report.source("greenhouse").duplicates == 1
    assert report.source("greenhouse").created == 1
