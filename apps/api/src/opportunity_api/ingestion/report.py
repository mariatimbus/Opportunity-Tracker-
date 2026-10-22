"""Ingestion reporting: per-source counters plus a run summary.

The report is the observable output of every run (A15). Skew detection
(C8) and scheduled alerting (A13) read these counters later, so the
vocabulary here — fetched / accepted / created / updated / duplicates /
rejected / failed — is part of the ingestion contract.
"""

from dataclasses import dataclass, field


@dataclass
class SourceReport:
    """Counters for one source adapter in one run."""

    name: str
    fetched: int = 0
    accepted: int = 0
    created: int = 0
    updated: int = 0
    duplicates: int = 0
    rejected: int = 0
    failed: int = 0
    would_create: int = 0
    would_update: int = 0

    def line(self) -> str:
        parts = [f"fetched={self.fetched}", f"accepted={self.accepted}"]
        if self.would_create or self.would_update:
            parts += [f"would_create={self.would_create}", f"would_update={self.would_update}"]
        parts += [
            f"created={self.created}",
            f"updated={self.updated}",
            f"duplicates={self.duplicates}",
            f"rejected={self.rejected}",
            f"failed={self.failed}",
        ]
        return f"{self.name}: " + " ".join(parts)


@dataclass
class IngestionReport:
    """Aggregate result of an ingestion run."""

    sources: dict[str, SourceReport] = field(default_factory=dict)
    failed_sources: list[str] = field(default_factory=list)
    dry_run: bool = False

    def source(self, name: str) -> SourceReport:
        if name not in self.sources:
            self.sources[name] = SourceReport(name=name)
        return self.sources[name]

    def totals(self) -> SourceReport:
        total = SourceReport(name="totals")
        for report in self.sources.values():
            for field_name in (
                "fetched",
                "accepted",
                "created",
                "updated",
                "duplicates",
                "rejected",
                "failed",
                "would_create",
                "would_update",
            ):
                setattr(total, field_name, getattr(total, field_name) + getattr(report, field_name))
        return total

    def render(self) -> str:
        title = "Ingestion dry run completed" if self.dry_run else "Ingestion completed"
        lines = [title, ""]
        for name in sorted(self.sources):
            lines.append(self.sources[name].line())
        lines += ["", "totals: " + self.totals().line().removeprefix("totals: ")]
        if self.failed_sources:
            lines += ["", "failed sources: " + ", ".join(sorted(self.failed_sources))]
        return "\n".join(lines)
