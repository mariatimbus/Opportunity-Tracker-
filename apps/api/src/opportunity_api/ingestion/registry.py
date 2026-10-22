"""Registry of available source adapters.

The registry is the single place that knows which sources exist and which
are active. Scheduled runs (GitHub Actions) resolve sources by name:

    registry.resolve()                          # all active sources
    registry.resolve(["greenhouse", "lever"])   # explicit subset

Adding a new adapter (Dalia, C4) is one line:

    registry.register(GreenhouseAdapter())

The runner never imports adapter classes itself; it only sees what the
registry hands it.
"""

from .sources.base import SourceAdapter


class AdapterRegistry:
    """Name → adapter mapping with selection helpers."""

    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        name = adapter.source_name
        if not name:
            raise ValueError("adapter needs a non-empty source_name")
        if name in self._adapters:
            raise ValueError(f"adapter already registered: {name}")
        self._adapters[name] = adapter

    def get(self, name: str) -> SourceAdapter:
        try:
            return self._adapters[name]
        except KeyError:
            available = ", ".join(self.names()) or "(none)"
            raise KeyError(f"unknown source: {name!r}; available: {available}") from None

    def names(self) -> list[str]:
        return sorted(self._adapters)

    def resolve(self, selection: list[str] | tuple[str, ...] | None = None) -> list[SourceAdapter]:
        """Adapters for ``selection`` (all active sources when ``None``)."""
        if selection is None:
            return [self._adapters[name] for name in self.names()]
        return [self.get(name) for name in selection]


default_registry = AdapterRegistry()


def register(adapter: SourceAdapter) -> None:
    default_registry.register(adapter)


def resolve(selection: list[str] | tuple[str, ...] | None = None) -> list[SourceAdapter]:
    return default_registry.resolve(selection)
