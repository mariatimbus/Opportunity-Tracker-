"""Common interface for opportunity source adapters.

Every source (Greenhouse, Lever, SmartRecruiters, ...) implements
``SourceAdapter``. The A15 runner iterates registered adapters, calls
``fetch()`` and passes the emitted ``RawOpportunity`` records through the
scope/normalize/dedupe/validate/persistence stages. Adapters must be
idempotent: re-running ``fetch()`` must yield the same ``source_id`` /
``source_url`` identities so downstream dedupe can drop duplicates.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from ..models import RawOpportunity


class SourceAdapter(ABC):
    """Fetches raw postings from one opportunity source."""

    #: Stable source key, stored on ``RawOpportunity.source`` (e.g. "greenhouse").
    source_name: str

    @abstractmethod
    def fetch(self) -> Iterable[RawOpportunity]:
        """Yield raw postings for this source.

        Implementations should tolerate individual malformed records by
        skipping them (with a logged warning) rather than aborting the
        whole run, and must not raise for transient HTTP failures after
        the runner's retry policy has been exhausted.
        """

    def parse_record(self, raw: dict[str, Any]) -> RawOpportunity:
        """Map one source payload dict to a ``RawOpportunity``.

        Adapters with a structured API typically override this to extract
        fields; the default requires an already-valid record.
        """
        return RawOpportunity(source=self.source_name, **raw)
