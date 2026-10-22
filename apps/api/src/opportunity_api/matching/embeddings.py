"""Embedding backends for AI matching (A11/A12).

The embedder contract returns ``None`` on any failure — an unreachable or
unconfigured Ollama must degrade the pipeline to its deterministic v1
behavior, never break it (AGENTS.md: the core product operates without
optional AI services).
"""

from typing import Protocol

import httpx


class Embedder(Protocol):
    """Text → dense vectors. ``None`` means „unavailable, use fallback"."""

    def embed(self, texts: list[str]) -> list[list[float]] | None: ...


class OllamaEmbedder:
    """Talks to a local Ollama server's /api/embeddings endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        timeout: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/api/embeddings"
        self._model = model
        self._timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        vectors: list[list[float]] = []
        try:
            for text in texts:
                response = self._client.post(
                    self._url,
                    json={"model": self._model, "input": text},
                )
                response.raise_for_status()
                payload = response.json()
                batch = payload.get("embeddings")
                if not batch:
                    return None
                # Single-string input yields one embedding per response.
                vectors.append([float(value) for value in batch[0]])
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None
        if not vectors or any(not vector for vector in vectors):
            return None
        width = len(vectors[0])
        if any(len(vector) != width for vector in vectors):
            return None
        return vectors


class StaticEmbedder:
    """Test/dev embedder: maps text to a caller-provided vector.

    Not for production — exists so tests and local demos exercise the AI
    path deterministically without a running Ollama.
    """

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        try:
            return [list(self._mapping[text]) for text in texts]
        except KeyError:
            return None
