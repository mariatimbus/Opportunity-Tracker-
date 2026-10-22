"""Explainable internship matching engine (A10 core + A11/A12 AI bonus)."""

from .ai import AI_CAP, AIScorer, cosine_similarity
from .embeddings import Embedder, OllamaEmbedder, StaticEmbedder
from .engine import GATE_RULES, UNCONFIRMED_CAP, score_match
from .scoring import (
    score_field_fit,
    score_interests,
    score_location,
    score_skills,
)

__all__ = [
    "AI_CAP",
    "AIScorer",
    "Embedder",
    "GATE_RULES",
    "OllamaEmbedder",
    "StaticEmbedder",
    "UNCONFIRMED_CAP",
    "cosine_similarity",
    "score_field_fit",
    "score_interests",
    "score_location",
    "score_match",
    "score_skills",
]
