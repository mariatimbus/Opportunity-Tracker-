"""Opportunity endpoint tests: list, detail, pagination, filters."""

import itertools
import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from opportunity_api.models import Opportunity, OpportunityDegreeLevel, OpportunityType, Skill

URL = "/api/v1/opportunities"
_counter = itertools.count(1)


def make_opportunity(**overrides) -> Opportunity:
    n = next(_counter)
    fields = dict(
        title=f"Opportunity {n}",
        organization="Example Corp",
        opportunity_type=OpportunityType.internship,
        url=f"https://example.com/{n}",
        source="test",
        source_id=str(n),
        is_active=True,
    )
    fields.update(overrides)
    return Opportunity(**fields)


def seed(db_factory, *opportunities: Opportunity) -> None:
    with db_factory() as session:
        session.add_all(opportunities)
        session.commit()


def test_list_opportunities(client: TestClient, db_factory):
    seed(db_factory, make_opportunity(), make_opportunity(title="Other"))

    response = client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    item = body["items"][0]
    for field in (
        "id",
        "title",
        "description",
        "organization",
        "opportunity_type",
        "location",
        "url",
        "source",
        "source_id",
        "deadline",
        "posted_at",
        "is_active",
        "degree_level",
        "study_year",
        "skills",
    ):
        assert field in item


def test_empty_opportunity_list(client: TestClient, db_factory):
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 20, "total": 0}


def test_get_opportunity_by_id(client: TestClient, db_factory):
    opportunity = make_opportunity(degree_level=OpportunityDegreeLevel.bachelor)
    skill = Skill(name="python")
    opportunity.skills.append(skill)
    seed(db_factory, opportunity)

    response = client.get(f"{URL}/{opportunity.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(opportunity.id)
    assert body["opportunity_type"] == "internship"
    assert body["skills"] == [{"id": str(skill.id), "name": "python"}]


def test_get_missing_opportunity(client: TestClient, db_factory):
    response = client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_opportunity_invalid_uuid(client: TestClient, db_factory):
    response = client.get(f"{URL}/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_filter_by_type(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(opportunity_type=OpportunityType.hackathon),
        make_opportunity(opportunity_type=OpportunityType.internship),
    )

    response = client.get(URL, params={"opportunity_type": "hackathon"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["opportunity_type"] == "hackathon"


def test_filter_by_degree_bachelor_includes_both(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(degree_level=OpportunityDegreeLevel.bachelor),
        make_opportunity(degree_level=OpportunityDegreeLevel.master),
        make_opportunity(degree_level=OpportunityDegreeLevel.both),
        make_opportunity(degree_level=None),
    )

    response = client.get(URL, params={"degree_level": "bachelor"})

    assert response.status_code == 200
    levels = {item["degree_level"] for item in response.json()["items"]}
    assert levels == {"bachelor", "both"}


def test_filter_by_degree_master_includes_both(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(degree_level=OpportunityDegreeLevel.bachelor),
        make_opportunity(degree_level=OpportunityDegreeLevel.master),
        make_opportunity(degree_level=OpportunityDegreeLevel.both),
    )

    response = client.get(URL, params={"degree_level": "master"})

    assert response.status_code == 200
    levels = {item["degree_level"] for item in response.json()["items"]}
    assert levels == {"master", "both"}


def test_filter_by_study_year(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(study_year=[1, 2]),
        make_opportunity(study_year=[3]),
        make_opportunity(study_year=None),
    )

    response = client.get(URL, params={"study_year": 1})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["study_year"] == [1, 2]


def test_filter_by_active(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(is_active=True),
        make_opportunity(is_active=False),
    )

    response = client.get(URL, params={"is_active": "true"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["is_active"] is True


def test_filter_by_location(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(location="Berlin, Germany"),
        make_opportunity(location="Remote"),
    )

    response = client.get(URL, params={"location": "berlin"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["location"] == "Berlin, Germany"


def test_filter_by_deadline_range(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(deadline=datetime(2026, 11, 1)),
        make_opportunity(deadline=datetime(2027, 1, 15)),
    )

    response = client.get(
        URL,
        params={"deadline_after": "2026-12-01T00:00:00", "deadline_before": "2027-02-01T00:00:00"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["deadline"].startswith("2027-01-15")


def test_search_matches_title_organization_description(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(title="Backend Intern"),
        make_opportunity(organization="Biotech GmbH"),
        make_opportunity(description="Focus on robotics and control"),
        make_opportunity(title="Unrelated"),
    )

    for term, expected in [("backend", 1), ("biotech", 1), ("robotics", 1)]:
        response = client.get(URL, params={"search": term})
        assert response.status_code == 200
        assert response.json()["total"] == expected, term


def test_pagination(client: TestClient, db_factory):
    seed(
        db_factory,
        make_opportunity(title="Newest", posted_at=datetime(2026, 10, 3)),
        make_opportunity(title="Middle", posted_at=datetime(2026, 10, 2)),
        make_opportunity(title="Oldest", posted_at=datetime(2026, 10, 1)),
    )

    first = client.get(URL, params={"page": 1, "page_size": 2})
    second = client.get(URL, params={"page": 2, "page_size": 2})

    assert first.status_code == 200
    assert first.json()["total"] == 3
    assert [item["title"] for item in first.json()["items"]] == ["Newest", "Middle"]
    assert second.json()["items"][0]["title"] == "Oldest"


def test_invalid_page_size(client: TestClient, db_factory):
    assert client.get(URL, params={"page_size": 0}).status_code == 422
    assert client.get(URL, params={"page_size": 101}).status_code == 422
    assert client.get(URL, params={"page": 0}).status_code == 422


def test_opportunity_response_contains_skills(client: TestClient, db_factory):
    opportunity = make_opportunity()
    opportunity.skills.append(Skill(name="sql"))
    seed(db_factory, opportunity)

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json()["items"][0]["skills"] == [
        {"id": str(opportunity.skills[0].id), "name": "sql"}
    ]


def test_null_degree_level_serializes_as_null(client: TestClient, db_factory):
    seed(db_factory, make_opportunity(degree_level=None))

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json()["items"][0]["degree_level"] is None


def test_null_study_year_serializes_as_null(client: TestClient, db_factory):
    seed(db_factory, make_opportunity(study_year=None))

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json()["items"][0]["study_year"] is None
