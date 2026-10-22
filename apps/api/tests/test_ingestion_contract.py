"""A14 ingestion contract: RawOpportunity, source adapter interface and scope."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from opportunity_api.ingestion.models import RawOpportunity
from opportunity_api.ingestion.scope import ScopeDecision, assess_scope
from opportunity_api.ingestion.sources.base import SourceAdapter


def _raw(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "source": "greenhouse",
        "source_id": "job-123",
        "source_url": "https://boards.greenhouse.io/acme/jobs/123",
        "title": "Software Engineering Intern",
        "organization": "Acme",
        "description": "6-month internship for Bachelor students.",
        "location": "Berlin, Germany",
        "deadline_raw": "2026-12-01",
        "degree_level_raw": "bachelor or master",
        "study_year_raw": "2-4",
        "fetched_at": datetime(2026, 10, 22, tzinfo=UTC),
    }
    base.update(overrides)
    return base


def test_valid_record_parses():
    record = RawOpportunity(**_raw())
    assert record.source == "greenhouse"
    assert record.title == "Software Engineering Intern"
    assert record.deadline_raw == "2026-12-01"
    assert record.fetched_at == datetime(2026, 10, 22, tzinfo=UTC)


def test_missing_optional_fields_default_to_none():
    record = RawOpportunity(**_raw(organization=None, description=None, location=None))
    assert record.organization is None
    assert record.description is None
    assert record.location is None


def test_explicit_null_stays_null():
    record = RawOpportunity(**_raw(deadline_raw=None, degree_level_raw=None, study_year_raw=None))
    assert record.deadline_raw is None
    assert record.degree_level_raw is None
    assert record.study_year_raw is None


def test_blank_strings_become_none_not_empty_string():
    record = RawOpportunity(**_raw(deadline_raw="   ", location=""))
    assert record.deadline_raw is None
    assert record.location is None


def test_record_without_url_or_id_is_rejected():
    with pytest.raises(ValidationError):
        RawOpportunity(**_raw(source_id=None, source_url=None))


def test_record_with_only_source_id_is_accepted():
    record = RawOpportunity(**_raw(source_url=None))
    assert record.source_id == "job-123"
    assert record.source_url is None


def test_scope_accepts_internship_stem_europe():
    decision = assess_scope(
        "Software Engineering Intern",
        "Python and cloud work for students.",
        "Berlin, Germany",
    )
    assert decision == ScopeDecision(True, "in scope")


@pytest.mark.parametrize(
    "title",
    [
        "Senior Software Engineer",
        "Internal Tools Developer",
        "Product Manager",
    ],
)
def test_scope_rejects_non_internship_roles(title: str):
    decision = assess_scope(title, "Python, cloud, engineering.", "Berlin, Germany")
    assert not decision.accepted
    assert decision.reason == "not an internship-level student role"


def test_scope_accepts_german_and_french_student_roles():
    assert assess_scope("Werkstudent Softwareentwicklung", "Python", "Munich, Germany").accepted
    assert assess_scope("Working Student (m/f/d) Data", "SQL", "Vienna, Austria").accepted
    assert assess_scope("Stage ingénieur logiciel", "Python", "Paris, France").accepted


def test_scope_rejects_non_stem_role():
    decision = assess_scope(
        "Marketing Intern",
        "Social media campaigns and brand events.",
        "Amsterdam, Netherlands",
    )
    assert not decision.accepted
    assert decision.reason == "not tech/STEM"


def test_scope_rejects_role_outside_europe():
    decision = assess_scope(
        "Software Engineering Intern",
        "Python and cloud work for students.",
        "Austin, TX, USA",
    )
    assert not decision.accepted
    assert decision.reason == "outside Europe"


def test_scope_rejects_missing_location():
    decision = assess_scope("Software Engineering Intern", "Python", None)
    assert not decision.accepted
    assert decision.reason == "outside Europe"


def test_scope_accepts_remote_posting():
    decision = assess_scope(
        "Software Engineering Intern",
        "Python and cloud work for students.",
        "Remote",
    )
    assert decision.accepted


def test_adapter_interface_is_abstract():
    with pytest.raises(TypeError):
        SourceAdapter()  # type: ignore[abstract]

    class DemoAdapter(SourceAdapter):
        source_name = "demo"

        def fetch(self):
            yield self.parse_record(
                {"source_id": "1", "title": "Software Intern", "location": "Berlin, Germany"}
            )

    adapter = DemoAdapter()
    records = list(adapter.fetch())
    assert len(records) == 1
    assert records[0].source == "demo"
    assert records[0].source_id == "1"
