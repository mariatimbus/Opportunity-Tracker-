"""Ingestion runner: orchestrates adapters through the pipeline stages.

Flow per record:

    source adapter → RawOpportunity → scope → normalize → dedupe
    → validate → persist → report

Responsibilities of the runner (A15):

- run one or many adapters in sequence;
- isolate failures: a crashing adapter (or record) never aborts the run;
- track every outcome in an :class:`~opportunity_api.ingestion.report.IngestionReport`;
- support ``dry_run``: fetch/scope/normalize/dedupe/validate run normally,
  nothing is written to the database.

The normalize/dedupe/validate stages belong to Dalia's C3; they are
injectable here with defaults that are deliberately simple but correct, so
the runner is fully functional and testable before C3 lands:

- ``normalizer``: ``RawOpportunity`` → dict/``NormalizedOpportunity``;
- ``dedupe``: optional, returns True for records already seen this run
  (DB-level dedupe always happens in persistence via upsert);
- ``validate``: coerces the normalizer output into ``NormalizedOpportunity``.
"""

import re
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from opportunity_api.models import OpportunityDegreeLevel

from .models import RawOpportunity
from .persistence import NormalizedOpportunity, OpportunityStore
from .report import IngestionReport
from .scope import assess_scope
from .sources.base import SourceAdapter

Normalizer = Callable[[RawOpportunity], object]
Dedupe = Callable[[NormalizedOpportunity], bool]
Validate = Callable[[object], NormalizedOpportunity]


def default_normalize(raw: RawOpportunity) -> dict[str, object]:
    """Minimal normalizer: fills the typed fields C3 will own properly.

    Placeholder parsing, documented as such: deadline from ISO text (naive
    values become UTC; date-only strings become midnight), degree level from
    keyword text, study years from "a-b" ranges. Anything unparseable stays
    ``None`` — never guessed.
    """
    deadline: datetime | None = None
    if raw.deadline_raw:
        text = raw.deadline_raw.strip()
        try:
            # fromisoformat accepts both datetimes and date-only strings
            # (the latter become midnight, normalized to UTC below).
            deadline = datetime.fromisoformat(text)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
        except ValueError:
            deadline = None

    lowered = (raw.degree_level_raw or "").lower()
    has_bachelor = "bachelor" in lowered or "bsc" in lowered
    has_master = "master" in lowered or "msc" in lowered
    degree_level: OpportunityDegreeLevel | None = None
    if has_bachelor and has_master:
        degree_level = OpportunityDegreeLevel.both
    elif has_bachelor:
        degree_level = OpportunityDegreeLevel.bachelor
    elif has_master:
        degree_level = OpportunityDegreeLevel.master

    study_year: list[int] | None = None
    if raw.study_year_raw:
        years = [int(part) for part in re.findall(r"\d+", raw.study_year_raw)]
        if len(years) >= 2 and "-" in raw.study_year_raw:
            study_year = list(range(years[0], years[1] + 1))
        elif years:
            study_year = years

    url = raw.source_url or f"urn:{raw.source}:{raw.source_id}"
    return {
        "source": raw.source,
        "source_id": raw.source_id,
        "url": url,
        "title": raw.title,
        "organization": raw.organization,
        "description": raw.description,
        "opportunity_type": "internship",
        "location": raw.location,
        "deadline": deadline,
        "degree_level": degree_level,
        "study_year": study_year,
    }


class IngestionRunner:
    """Coordinates adapters, pipeline stages, persistence and reporting."""

    def __init__(
        self,
        store: OpportunityStore,
        *,
        normalizer: Normalizer = default_normalize,
        validate: Validate = NormalizedOpportunity.model_validate,
        dedupe: Dedupe | None = None,
        dry_run: bool = False,
    ) -> None:
        self.store = store
        self.normalizer = normalizer
        self.validate = validate
        self.dedupe = dedupe
        self.dry_run = dry_run

    def run(self, adapters: Iterable[SourceAdapter]) -> IngestionReport:
        report = IngestionReport(dry_run=self.dry_run)
        for adapter in adapters:
            self._run_adapter(adapter, report)
        return report

    def _run_adapter(self, adapter: SourceAdapter, report: IngestionReport) -> None:
        name = adapter.source_name
        source_report = report.source(name)
        try:
            records = list(adapter.fetch())
        except Exception:
            report.failed_sources.append(name)
            return
        for raw in records:
            source_report.fetched += 1
            decision = assess_scope(raw.title, raw.description, raw.location)
            if not decision.accepted:
                source_report.rejected += 1
                continue
            source_report.accepted += 1
            try:
                normalized = self.validate(self.normalizer(raw))
            except Exception:
                source_report.failed += 1
                continue
            if self.dedupe is not None and self.dedupe(normalized):
                source_report.duplicates += 1
                continue
            if self.dry_run:
                if self.store.classify(normalized) == "create":
                    source_report.would_create += 1
                else:
                    source_report.would_update += 1
                continue
            match self.store.upsert(normalized):
                case "created":
                    source_report.created += 1
                case "updated":
                    source_report.updated += 1
                case "duplicate":
                    source_report.duplicates += 1
        if not self.dry_run:
            self.store.commit()
