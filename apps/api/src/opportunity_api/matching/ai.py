"""AI similarity scoring on top of embeddings (A11/A12).

The AI component is an *optional bonus*: it can raise a strong textual
match that deterministic keyword scoring undervalues, but it can never
rescue a gated ``not_eligible`` result and never blocks scoring when the
embedder is unavailable. The deterministic v1 components remain the core.
"""

import math

from opportunity_api.schemas.matching import MatchingOpportunity, MatchingProfile

from .embeddings import Embedder

AI_CAP = 25


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def profile_text(profile: MatchingProfile) -> str:
    parts = [profile.field_of_study or "", *profile.skills, *profile.interests]
    return ", ".join(part for part in parts if part)


def opportunity_text(opportunity: MatchingOpportunity) -> str:
    return " ".join(
        part for part in (opportunity.title, opportunity.description or "") if part
    )


class AIScorer:
    """Cosine-similarity scorer over an embedding backend.

    Returns ``(points, reason)``; ``points`` is 0 both for a weak match and
    for an unavailable backend, so callers must treat the AI component as
    opportunistic. ``reason`` is ``None`` when the backend was unavailable.
    """

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    def score(
        self, profile: MatchingProfile, opportunity: MatchingOpportunity
    ) -> tuple[int, str | None]:
        texts = [profile_text(profile), opportunity_text(opportunity)]
        if not any(texts):
            return 0, None
        vectors = self._embedder.embed(texts)
        if vectors is None or len(vectors) != 2:
            return 0, None
        similarity = cosine_similarity(vectors[0], vectors[1])
        points = round(similarity * AI_CAP)
        return points, f"AI similarity: {similarity:.2f} (embeddings)"
