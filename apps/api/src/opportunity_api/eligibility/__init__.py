"""Deterministic eligibility engine (A9)."""

from .engine import DEFAULT_RULES, combine, evaluate
from .rules import (
    check_degree_level,
    check_graduation_year,
    check_location,
    check_study_year,
)

__all__ = [
    "DEFAULT_RULES",
    "check_degree_level",
    "check_graduation_year",
    "check_location",
    "check_study_year",
    "combine",
    "evaluate",
]
