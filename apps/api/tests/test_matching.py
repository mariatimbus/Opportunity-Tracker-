"""A10 explainable matching engine v1: gate, components, caps, determinism."""

import json
from pathlib import Path

from opportunity_api.matching import UNCONFIRMED_CAP, score_match
from opportunity_api.matching.scoring import (
    score_field_fit,
    score_interests,
    score_location,
    score_skills,
)
from opportunity_api.schemas.eligibility import EligibilityStatus
from opportunity_api.schemas.matching import (
    MatchingOpportunity,
    MatchingProfile,
)

FIXTURES = Path(__file__).parent / "fixtures" / "matching"


def _load(name: str, model: type[MatchingProfile] | type[MatchingOpportunity]) -> dict[str, object]:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return {key: model.model_validate(value) for key, value in data.items()}


PROFILES = _load("profiles", MatchingProfile)
OPPORTUNITIES = _load("opportunities", MatchingOpportunity)


def test_eligible_match_scores_components():
    result = score_match(PROFILES["ana"], OPPORTUNITIES["swe_intern_remote"])

    assert result.eligibility == EligibilityStatus.eligible
    assert result.components.model_dump() == {
        "skills": 12,  # Python + SQL matched (6 each), Java not present
        "field_fit": 25,  # "computer science" phrase present
        "interests": 10,  # AI + research (5 each)
        "location": 7,  # remote-friendly
    }
    assert result.score == 54
    assert any("Skill overlap" in reason for reason in result.reasons)
    assert any("Field of study matches" in reason for reason in result.reasons)
    assert any("interests" in reason for reason in result.reasons)


def test_not_eligible_is_zero_despite_strong_overlap():
    result = score_match(PROFILES["ana"], OPPORTUNITIES["swe_intern_master_only"])

    assert result.eligibility == EligibilityStatus.not_eligible
    assert result.score == 0
    assert result.components.skills == 12  # overlap still reported for transparency
    assert any(reason.startswith("Not eligible") for reason in result.reasons)


def test_unconfirmed_eligibility_caps_score():
    result = score_match(PROFILES["ana"], OPPORTUNITIES["swe_intern_any_year"])

    assert result.eligibility == EligibilityStatus.possibly_eligible
    raw = 12 + 25 + 10 + 7
    assert raw > UNCONFIRMED_CAP
    assert result.score == UNCONFIRMED_CAP
    assert any("capped" in reason for reason in result.reasons)


def test_unconfirmed_below_cap_is_not_lifted():
    # viktor vs mech intern: strong match but study year unknown → cap not reached
    result = score_match(PROFILES["viktor"], OPPORTUNITIES["mech_intern_cluj"])

    assert result.eligibility == EligibilityStatus.possibly_eligible
    assert result.components.model_dump() == {
        "skills": 6,  # CAD
        "field_fit": 25,  # "mechanical engineering" phrase in title
        "interests": 5,  # automotive
        "location": 10,  # exact Cluj, Romania match
    }
    assert result.score == 46


def test_no_overlap_scores_zero():
    result = score_match(PROFILES["ana"], OPPORTUNITIES["marketing_intern"])

    assert result.eligibility == EligibilityStatus.possibly_eligible
    assert result.score == 0
    assert result.components.model_dump() == {
        "skills": 0,
        "field_fit": 0,
        "interests": 0,
        "location": 0,
    }


def test_determinism_same_inputs_same_output():
    first = score_match(PROFILES["ana"], OPPORTUNITIES["swe_intern_remote"])
    second = score_match(
        PROFILES["ana"].model_copy(deep=True),
        OPPORTUNITIES["swe_intern_remote"].model_copy(deep=True),
    )
    assert first == second


def test_precomputed_eligibility_is_used():
    from opportunity_api.eligibility import evaluate
    from opportunity_api.matching.engine import to_opportunity_input, to_student_input

    eligibility = evaluate(
        to_student_input(PROFILES["ana"]), to_opportunity_input(OPPORTUNITIES["swe_intern_remote"])
    )
    result = score_match(
        PROFILES["ana"], OPPORTUNITIES["swe_intern_remote"], eligibility=eligibility
    )
    assert result.eligibility == eligibility.status


def test_skills_cap_at_30():
    profile = MatchingProfile(
        skills=["python", "sql", "java", "git", "docker", "linux", "bash"],
        field_of_study=None,
        interests=[],
        location=None,
    )
    opportunity = MatchingOpportunity(
        title="Engineering Intern",
        description="python sql java git docker linux bash environment.",
        skills=[],
    )
    points, reasons = score_skills(profile, opportunity)
    assert points == 30
    assert len(reasons) == 1 and "7" not in reasons[0]


def test_field_fit_partial_token_match():
    profile = MatchingProfile(field_of_study="Mechanical Engineering")
    opportunity = MatchingOpportunity(
        title="Software Engineering Intern",
        description="Data platform work.",
    )
    points, reasons = score_field_fit(profile, opportunity)
    assert points == 12  # only "engineering" matches
    assert any("engineering" in reason for reason in reasons)


def test_word_boundary_matching_not_substrings():
    profile = MatchingProfile(skills=["AI", "CAD"], interests=["AI"], location="Berlin, Germany")
    opportunity = MatchingOpportunity(
        title="Intern",
        description="Said the academy graduate used cadence in daily standups.",
        location="Berlin, Germany",
    )
    points, _ = score_skills(profile, opportunity)
    assert points == 0  # "ai" ≠ "said", "cad" ≠ "academy"/"cadence"
    interest_points, _ = score_interests(profile, opportunity)
    assert interest_points == 0
    location_points, _ = score_location(profile, opportunity)
    assert location_points == 10


def test_location_remote_partial_points():
    profile = MatchingProfile(location="Bucharest, Romania")
    opportunity = MatchingOpportunity(title="Intern", location="Remote (EU)")
    points, reasons = score_location(profile, opportunity)
    assert points == 7
    assert any("Remote" in reason for reason in reasons)
