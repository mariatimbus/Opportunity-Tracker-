"""A11/A12 AI matching: cosine scoring, Ollama embedder, deterministic fallback."""

import math

import httpx
import pytest

from opportunity_api.matching import (
    AI_CAP,
    AIScorer,
    OllamaEmbedder,
    StaticEmbedder,
    cosine_similarity,
    score_match,
)
from opportunity_api.matching.ai import opportunity_text, profile_text
from opportunity_api.schemas.matching import MatchingOpportunity, MatchingProfile


def test_cosine_similarity_math():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([1.0, 1.0], [1.0, 1.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0  # mismatched dims
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0  # zero norm
    assert cosine_similarity([], []) == 0.0


def _profile() -> MatchingProfile:
    return MatchingProfile(
        degree_level="bachelor",
        study_year=2,
        field_of_study="Computer Science",
        skills=["Python"],
        interests=["AI"],
    )


def _opportunity() -> MatchingOpportunity:
    return MatchingOpportunity(
        title="Software Engineering Intern",
        description="Python and ML work.",
        location="Remote",
        degree_level="both",
        study_year=[1, 2, 3],
    )


def test_ai_component_raises_score_for_similar_vectors():
    profile = _profile()
    opportunity = _opportunity()
    base = score_match(profile, opportunity)
    assert base.components.ai == 0

    vector = [1.0, 0.0]
    mapping = {profile_text(profile): vector, opportunity_text(opportunity): vector}
    ai = AIScorer(StaticEmbedder(mapping))
    boosted = score_match(profile, opportunity, ai=ai)

    assert boosted.components.ai == AI_CAP  # cosine 1.0 → full cap
    assert boosted.score == min(100, base.score + AI_CAP)
    assert any("AI similarity: 1.00" in reason for reason in boosted.reasons)


def test_ai_component_partial_similarity():
    profile = _profile()
    opportunity = _opportunity()
    ai = AIScorer(
        StaticEmbedder(
            {
                profile_text(profile): [1.0, 0.0],
                opportunity_text(opportunity): [math.sqrt(3) / 2, 0.5],
            }
        )
    )
    result = score_match(profile, opportunity, ai=ai)
    assert result.components.ai == round((math.sqrt(3) / 2) * AI_CAP)
    assert result.components.ai > 0


def test_unavailable_embedder_falls_back_to_deterministic():
    profile = _profile()
    opportunity = _opportunity()
    base = score_match(profile, opportunity)

    ai = AIScorer(StaticEmbedder({}))  # nothing mapped → embed returns None
    fallback = score_match(profile, opportunity, ai=ai)

    assert fallback.score == base.score
    assert fallback.components == base.components
    assert any("unavailable" in reason for reason in fallback.reasons)


def test_ai_cannot_rescue_not_eligible():
    profile = MatchingProfile(degree_level="bachelor", skills=["Python"])
    opportunity = MatchingOpportunity(
        title="Software Engineering Intern",
        degree_level="master",
        study_year=[1, 2],
    )
    vectors = StaticEmbedder(
        {profile_text(profile): [1.0], opportunity_text(opportunity): [1.0]}
    )
    result = score_match(profile, opportunity, ai=AIScorer(vectors))
    assert result.components.ai == AI_CAP
    assert result.score == 0
    assert result.eligibility == "not_eligible"


def test_empty_profile_and_opportunity_text_skips_embedding():
    ai = AIScorer(StaticEmbedder({}))
    profile = MatchingProfile()
    opportunity = MatchingOpportunity(title="Intern", description=None)
    points, reason = ai.score(profile, opportunity)
    assert points == 0 and reason is None


def test_ollama_embedder_happy_path():
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, payload):
            self._payload = payload
            self.calls = 0

        def post(self, url, json):
            self.calls += 1
            return FakeResponse(self._payload)

    client = FakeClient({"embeddings": [[0.1, 0.2, 0.3]]})
    embedder = OllamaEmbedder("http://localhost:11434", "test-model", client=client)
    vectors = embedder.embed(["hello", "world"])
    assert client.calls == 2
    assert vectors == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]


def test_ollama_embedder_failure_returns_none():
    class FailingClient:
        def post(self, url, json):
            raise httpx.ConnectError("ollama down")

    embedder = OllamaEmbedder("http://localhost:11434", "test-model", client=FailingClient())
    assert embedder.embed(["hello"]) is None

    class BadPayloadClient:
        def post(self, url, json):
            return type("R", (), {"raise_for_status": lambda self: None, "json": lambda self: {}})()

    embedder = OllamaEmbedder("http://localhost:11434", "test-model", client=BadPayloadClient())
    assert embedder.embed(["hello"]) is None
