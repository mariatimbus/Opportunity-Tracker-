"""Explainable scoring components for A10.

Every scorer is deterministic, independently testable and returns both
points and the reasons behind them. Matching is substring-free: terms are
matched on word boundaries so "ai" does not fire on "said" and "cad" does
not fire on "academy".

Caps (documented contract, mirrored by tests):

- skills:     6 points per matched skill, capped at 30
- field_fit:  25 for a full field-of-study phrase match, else 12 per
              significant token (>= 4 chars), capped at 25
- interests:  5 points per matched interest, capped at 20
- location:   10 exact match, 7 remote-friendly, else 0
"""

import re

from opportunity_api.schemas.matching import MatchingOpportunity, MatchingProfile

SKILL_POINTS = 6
SKILLS_CAP = 30
FIELD_PHRASE_POINTS = 25
FIELD_TOKEN_POINTS = 12
FIELD_CAP = 25
INTEREST_POINTS = 5
INTERESTS_CAP = 20
LOCATION_MATCH_POINTS = 10
LOCATION_REMOTE_POINTS = 7

_WORD = re.compile(r"[a-z0-9+#.\-]+")


def _terms(text: str | None) -> list[str]:
    return _WORD.findall((text or "").lower())


def _haystack(profile: MatchingProfile, opportunity: MatchingOpportunity) -> str:
    parts = [
        opportunity.title,
        opportunity.description or "",
        " ".join(opportunity.skills),
    ]
    return " ".join(parts).lower()


def _matched_terms(needles: list[str], haystack: str) -> list[str]:
    haystack_terms = set(_terms(haystack))
    return [needle for needle in needles if needle.strip().lower() in haystack_terms]


def score_skills(
    profile: MatchingProfile, opportunity: MatchingOpportunity
) -> tuple[int, list[str]]:
    matched = _matched_terms(profile.skills, _haystack(profile, opportunity))
    points = min(SKILLS_CAP, SKILL_POINTS * len(matched))
    reasons = []
    if matched:
        listed = ", ".join(matched)
        reasons.append(f"Skill overlap: {listed}")
    return points, reasons


def score_field_fit(
    profile: MatchingProfile, opportunity: MatchingOpportunity
) -> tuple[int, list[str]]:
    field = (profile.field_of_study or "").strip().lower()
    if not field:
        return 0, []
    haystack = _haystack(profile, opportunity)
    reasons: list[str] = []
    if field in haystack:
        return FIELD_PHRASE_POINTS, [f"Field of study matches: {field}"]
    tokens = [token for token in _terms(field) if len(token) >= 4]
    matched = _matched_terms(tokens, haystack)
    points = min(FIELD_CAP, FIELD_TOKEN_POINTS * len(matched))
    if matched:
        reasons.append(f"Field keywords found: {', '.join(matched)}")
    return points, reasons


def score_interests(
    profile: MatchingProfile, opportunity: MatchingOpportunity
) -> tuple[int, list[str]]:
    matched = _matched_terms(profile.interests, _haystack(profile, opportunity))
    points = min(INTERESTS_CAP, INTEREST_POINTS * len(matched))
    reasons = []
    if matched:
        reasons.append(f"Matches interests: {', '.join(matched)}")
    return points, reasons


def score_location(
    profile: MatchingProfile, opportunity: MatchingOpportunity
) -> tuple[int, list[str]]:
    location = (opportunity.location or "").strip().lower()
    if not location:
        return 0, []
    if "remote" in location:
        return LOCATION_REMOTE_POINTS, ["Remote-friendly location"]
    student_location = (profile.location or "").strip().lower()
    if student_location and student_location in location:
        return LOCATION_MATCH_POINTS, ["Location matches the student's preference"]
    return 0, []
