"""Dry-run smoke test for the ingestion pipeline (A15).

Loads fixture ``RawOpportunity`` records, runs the full pipeline in
dry-run mode against a throwaway in-memory sqlite database, and prints
the report. Exits non-zero when fixtures are invalid, nothing was
processed, or anything failed — used by ``ingestion-ci.yml`` to catch
broken fixtures or pipeline regressions without touching any real
database. As real adapters land (C4), they get registered here.
"""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from opportunity_api.core.database import Base

from .models import RawOpportunity
from .persistence import OpportunityStore
from .runner import IngestionRunner
from .sources.base import SourceAdapter

DEFAULT_FIXTURES = Path("tests/fixtures/ingestion_smoke.json")


class FixtureAdapter(SourceAdapter):
    """Adapter backed by a fixed record list (fixtures, tests, smoke runs)."""

    def __init__(self, name: str, records: list[RawOpportunity]) -> None:
        self.source_name = name
        self._records = records

    def fetch(self):
        return iter(self._records)


def load_adapters(fixtures: Path) -> list[SourceAdapter]:
    payload = json.loads(fixtures.read_text(encoding="utf-8"))
    adapters: list[SourceAdapter] = []
    for source in payload["sources"]:
        records = [RawOpportunity.model_validate(row) for row in source["records"]]
        adapters.append(FixtureAdapter(source["name"], records))
    if not adapters:
        raise ValueError(f"no sources defined in {fixtures}")
    return adapters


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="JSON fixture file with a 'sources' list (run from apps/api).",
    )
    args = parser.parse_args(argv)

    try:
        adapters = load_adapters(args.fixtures)
    except (OSError, ValueError, KeyError) as exc:
        print(f"SMOKE FAILED: invalid fixtures: {exc}")
        return 1

    engine = create_engine("sqlite://")  # throwaway; dry-run never writes
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        runner = IngestionRunner(OpportunityStore(session), dry_run=True)
        report = runner.run(adapters)

    print(report.render())

    totals = report.totals()
    problems: list[str] = []
    if totals.fetched == 0:
        problems.append("no records fetched")
    if totals.failed or report.failed_sources:
        problems.append("failures recorded")
    if totals.would_create == 0:
        problems.append("nothing would be created (scope or normalize regression?)")
    if problems:
        print(f"SMOKE FAILED: {', '.join(problems)}")
        return 1
    print("SMOKE OK: pipeline healthy, no writes performed (dry run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
