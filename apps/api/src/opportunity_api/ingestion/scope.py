"""Ingestion scope: which raw records we accept into the pipeline.

Acceptance rule (A14): the role must be an internship-level student role,
the posting must be tech/STEM, and the location must be in Europe
(or explicitly remote). Records outside scope are dropped before any
normalization or persistence work happens.
"""

import re
from dataclasses import dataclass

# Student-role vocabulary. Matched against the title with word boundaries so
# "intern" does not match "internal" and "placement" does not match "replace".
ROLE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bintern(ship)?s?\b",
        r"\bworking\s+student\b",
        r"\bwerkstudent(innen?)?\b",
        r"\bpraktikant(innen?)?\b",
        r"\bpraktikum\b",
        r"\bstage?s?\b",
        r"\bstagiaire?s?\b",
        r"\bplacement(s)?\b",
        r"\bstudent\s+(worker|assistant|job)\b",
    )
)

# Tech/STEM vocabulary, matched against title + description with word
# boundaries (substring matching would let "ai" match "campaigns" and "it "
# is not a real token). Multi-word terms use \s+.
STEM_TERMS: tuple[str, ...] = (
    "tech", "software", "developer", "engineer", "engineering", "devops",
    "frontend", "front-end", "backend", "back-end", "fullstack", "full-stack",
    "data", "sql", "machine learning", "deep learning", "ai", "ml", "cloud",
    "cyber", "security", "embedded", "mobile", "python", "java", "react",
    "research", "science", "scientist", "physics", "math", "mathematics",
    "statistics", "biotech", "chemistry", "electrical", "mechanical",
    "robotics", "automation", "database", "network", "computer", "it",
)

STEM_PATTERN = re.compile(
    r"\b(" + "|".join(term.replace(" ", r"\s+") for term in STEM_TERMS) + r")\b",
    re.IGNORECASE,
)

# European countries, plus common aliases. Matching is case-insensitive on
# the free-text location field. Transcontinental countries are included.
EUROPE_COUNTRIES: frozenset[str] = frozenset(
    {
        "albania", "andorra", "austria", "belarus", "belgium", "bosnia",
        "bulgaria", "croatia", "cyprus", "czechia", "czech republic", "denmark",
        "estonia", "finland", "france", "germany", "greece", "hungary",
        "iceland", "ireland", "italy", "kosovo", "latvia", "liechtenstein",
        "lithuania", "luxembourg", "malta", "moldova", "monaco", "montenegro",
        "netherlands", "holland", "north macedonia", "macedonia", "norway",
        "poland", "portugal", "romania", "russia", "san marino", "serbia",
        "slovakia", "slovenia", "spain", "sweden", "switzerland", "turkey",
        "ukraine", "united kingdom", "uk", "great britain", "britain",
        "england", "scotland", "wales", "vatican",
    }
)

# Locations without a country cannot be geolocated; "remote" postings are
# kept (European students can apply) instead of being silently dropped.
REMOTE_PATTERN = re.compile(r"\bremote\b|\bwork\s+from\s+home\b", re.IGNORECASE)


@dataclass(frozen=True)
class ScopeDecision:
    accepted: bool
    reason: str


def _is_student_role(title: str) -> bool:
    return any(pattern.search(title) for pattern in ROLE_PATTERNS)


def _is_stem(title: str, description: str) -> bool:
    return STEM_PATTERN.search(f"{title}\n{description}") is not None


def _is_europe(location: str) -> bool:
    lowered = location.lower()
    if REMOTE_PATTERN.search(lowered):
        return True
    return any(country in lowered for country in EUROPE_COUNTRIES)


def assess_scope(title: str, description: str | None, location: str | None) -> ScopeDecision:
    """Decide whether a raw posting is inside the ingestion scope."""
    if not _is_student_role(title):
        return ScopeDecision(False, "not an internship-level student role")
    if not _is_stem(title, description or ""):
        return ScopeDecision(False, "not tech/STEM")
    if location is None or not _is_europe(location):
        return ScopeDecision(False, "outside Europe")
    return ScopeDecision(True, "in scope")
