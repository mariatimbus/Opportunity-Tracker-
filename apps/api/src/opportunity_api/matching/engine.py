"""Explainable matching engine v1 (A10).

Ranks one opportunity for one student with a deterministic, explainable
score — no AI, no embeddings (those come in A11/A12).

The A9 eligibility engine is the gate:

- ``not_eligible`` → score 0, always. A hard requirement failure can never
  surface as a good recommendation, no matter how strong the skill overlap.
- ``possibly_eligible`` / ``unknown`` → the raw component sum is capped at
  ``UNCONFIRMED_CAP``: an unconfirmed match can never outrank a confirmed
  eligible one.
- ``eligible`` → no cap.

Only eligibility rules backed by real data gate the score (degree level,
study year, location). Graduation currently has no structured source
anywhere in the pipeline, so — per „unknown must remain unknown" — it
cannot block matching either; it stays out of the gate until a source
exists.
"""

from collections.abc import Sequence

from opportunity_api.eligibility.engine import evaluate
from opportunity_api.eligibility.rules import (
    check_degree_level,
    check_location,
    check_study_year,
)
from opportunity_api.schemas.eligibility import (
    EligibilityResult,
    EligibilityStatus,
    OpportunityInput,
    StudentInput,
)
from opportunity_api.schemas.matching import (
    ComponentScores,
    MatchingOpportunity,
    MatchingProfile,
    MatchResult,
)

from .scoring import score_field_fit, score_interests, score_location, score_skills

GATE_RULES = (check_degree_level, check_study_year, check_location)

UNCONFIRMED_CAP = 49
_NOT_ELIGIBLE_GATE = (
    EligibilityStatus.possibly_eligible,
    EligibilityStatus.unknown,
)


def to_student_input(profile: MatchingProfile) -> StudentInput:
    return StudentInput(
        degree_level=profile.degree_level,
        study_year=profile.study_year,
        graduation_year=profile.graduation_year,
        location=profile.location,
    )


def to_opportunity_input(opportunity: MatchingOpportunity) -> OpportunityInput:
    return OpportunityInput(
        degree_level=opportunity.degree_level,
        study_year=opportunity.study_year,
        location=opportunity.location,
    )


def score_match(
    profile: MatchingProfile,
    opportunity: MatchingOpportunity,
    eligibility: EligibilityResult | None = None,
) -> MatchResult:
    """Deterministic, explainable score for one (student, opportunity) pair."""
    if eligibility is None:
        eligibility = evaluate(
            to_student_input(profile),
            to_opportunity_input(opportunity),
            rules=GATE_RULES,
        )

    components, reasons = _components(profile, opportunity)

    if eligibility.status == EligibilityStatus.not_eligible:
        failed = next(
            (r for r in eligibility.reasons if r.status == EligibilityStatus.not_eligible),
            None,
        )
        gate_reason = f"Not eligible: {failed.reason}" if failed else "Not eligible"
        return MatchResult(
            score=0,
            eligibility=eligibility.status,
            components=components,
            reasons=[gate_reason],
        )

    score = sum(components.model_dump().values())
    if eligibility.status in _NOT_ELIGIBLE_GATE:
        score = min(score, UNCONFIRMED_CAP)
        reasons.append("Eligibility not fully confirmed; score capped")

    reasons = _dedupe_preserve_order(reasons)
    return MatchResult(
        score=score,
        eligibility=eligibility.status,
        components=components,
        reasons=reasons,
    )


def _components(
    profile: MatchingProfile, opportunity: MatchingOpportunity
) -> tuple[ComponentScores, list[str]]:
    skills_points, skills_reasons = score_skills(profile, opportunity)
    field_points, field_reasons = score_field_fit(profile, opportunity)
    interest_points, interest_reasons = score_interests(profile, opportunity)
    location_points, location_reasons = score_location(profile, opportunity)
    components = ComponentScores(
        skills=skills_points,
        field_fit=field_points,
        interests=interest_points,
        location=location_points,
    )
    reasons = skills_reasons + field_reasons + interest_reasons + location_reasons
    return components, reasons


def _dedupe_preserve_order(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique
