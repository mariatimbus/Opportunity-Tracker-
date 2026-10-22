"""API wiring: eligibility (A9) and match (A10/A11) endpoints per opportunity."""

import pytest
from fastapi.testclient import TestClient

from opportunity_api.models import OpportunityDegreeLevel
from tests.conftest import auth_headers
from tests.test_opportunities import make_opportunity, seed

URL = "/api/v1/opportunities"


@pytest.fixture()
def headers(client):
    return auth_headers(client, "ada@example.com")


def set_profile(client: TestClient, headers: dict[str, str], **fields: object) -> None:
    response = client.put("/api/v1/profile", json=fields, headers=headers)
    assert response.status_code == 200, response.text


def test_eligibility_requires_auth(client):
    response = client.get(f"{URL}/00000000-0000-0000-0000-000000000000/eligibility")
    assert response.status_code == 401


def test_match_requires_auth(client):
    response = client.get(f"{URL}/00000000-0000-0000-0000-000000000000/match")
    assert response.status_code == 401


def test_eligibility_not_eligible_for_degree_mismatch(client, db_factory, headers):
    opportunity = make_opportunity(degree_level=OpportunityDegreeLevel.master)
    seed(db_factory, opportunity)
    set_profile(client, headers, degree_level="bachelor")

    response = client.get(f"{URL}/{opportunity.id}/eligibility", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_eligible"
    degree_reason = next(r for r in body["reasons"] if r["rule"] == "degree_level")
    assert degree_reason["status"] == "not_eligible"
    assert "master" in degree_reason["reason"]


def test_eligibility_uses_full_rules_including_graduation(client, db_factory, headers):
    opportunity = make_opportunity(
        degree_level=OpportunityDegreeLevel.both,
        location="Remote",
        study_year=[1, 2],
    )
    seed(db_factory, opportunity)
    set_profile(client, headers, degree_level="bachelor")

    response = client.get(f"{URL}/{opportunity.id}/eligibility", headers=headers)

    assert response.status_code == 200
    body = response.json()
    # degree eligible, study_year unknown (not on profile yet), graduation
    # unknown (no structured source), location eligible → possibly_eligible
    assert body["status"] == "possibly_eligible"
    rules = {r["rule"]: r["status"] for r in body["reasons"]}
    assert rules["degree_level"] == "eligible"
    assert rules["study_year"] == "unknown"
    assert rules["graduation_year"] == "unknown"
    assert rules["location"] == "eligible"


def test_match_not_eligible_scores_zero(client, db_factory, headers):
    opportunity = make_opportunity(
        degree_level=OpportunityDegreeLevel.master,
        study_year=[1, 2],
    )
    seed(db_factory, opportunity)
    set_profile(client, headers, degree_level="bachelor")

    response = client.get(f"{URL}/{opportunity.id}/match", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 0
    assert body["eligibility"] == "not_eligible"
    assert any(reason.startswith("Not eligible") for reason in body["reasons"])


def test_match_returns_explainable_components(client, db_factory, headers):
    opportunity = make_opportunity(
        title="Software Engineering Intern",
        description="Python and ML work with our computer science AI research team.",
        degree_level=OpportunityDegreeLevel.both,
        study_year=[1, 2],
        location="Remote",
    )
    seed(db_factory, opportunity)
    set_profile(client, headers, degree_level="bachelor", field_of_study="Computer Science")

    response = client.get(f"{URL}/{opportunity.id}/match", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body["components"]) == {"skills", "field_fit", "interests", "location", "ai"}
    # possibly_eligible (study_year not on profile) → capped
    assert body["eligibility"] == "possibly_eligible"
    assert body["score"] <= 49
    # AI is unconfigured in tests → zero AI component, deterministic reasons only
    assert body["components"]["ai"] == 0
    assert any("Field of study matches" in reason for reason in body["reasons"])


def test_match_unknown_opportunity_is_404(client, headers):
    response = client.get(
        f"{URL}/00000000-0000-0000-0000-000000000000/match", headers=headers
    )
    assert response.status_code == 404


def test_eligibility_unknown_opportunity_is_404(client, headers):
    response = client.get(
        f"{URL}/00000000-0000-0000-0000-000000000000/eligibility", headers=headers
    )
    assert response.status_code == 404
