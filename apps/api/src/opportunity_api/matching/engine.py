"""Explainable matching engine (A10 deterministic core + A11/A12 AI bonus).

Ranks one opportunity for one student with an explainable score. The v1
deterministic components (skills, field fit, interests, location) are the
core and work with no external services; the optional AI similarity
component (A11/A12, Ollama embeddings) can raise strong textual matches
that keyword scoring undervalues, and is skipped silently when the
embedder is unavailable.

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

from .ai import AIScorer
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
    ai: AIScorer | None = None,
) -> MatchResult:
    """Deterministic, explainable score for one (student, opportunity) pair.

    ``ai`` is optional: when given, its similarity component is added on
    top of the deterministic components; when absent or unavailable the
    score is the pure v1 deterministic result.
    """
    if eligibility is None:
        eligibility = evaluate(
            to_student_input(profile),
            to_opportunity_input(opportunity),
            rules=GATE_RULES,
        )

    components, reasons = _components(profile, opportunity)
    if ai is not None:
        ai_points, ai_reason = ai.score(profile, opportunity)
        components.ai = ai_points
        if ai_reason is not None:
            reasons.append(ai_reason)
        elif ai_points == 0:
            reasons.append("AI similarity unavailable; deterministic components only")

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

    score = min(100, sum(components.model_dump().values()))
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
