"""Explainable internship matching engine v1 (A10)."""

from .engine import GATE_RULES, UNCONFIRMED_CAP, score_match
from .scoring import (
    score_field_fit,
    score_interests,
    score_location,
    score_skills,
)

__all__ = [
    "GATE_RULES",
    "UNCONFIRMED_CAP",
    "score_field_fit",
    "score_interests",
    "score_location",
    "score_match",
    "score_skills",
]
