"""Persistence: create-or-update opportunities without duplicates.

Identity rules (mirror ``models.Opportunity`` constraints):

- primary identity is ``(source, source_id)`` when ``source_id`` exists;
- otherwise the canonical ``url``.

Running the pipeline twice over the same data must yield updates, never
duplicate rows — that is the idempotency guarantee the runner tests assert.

``NormalizedOpportunity`` is the shape the normalize/validate stages (C3)
hand to persistence. It mirrors the persistence schema one-to-one; once
Dalia's ``normalize.py``/``validate.py`` land, they should own this type.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from opportunity_api.models import Opportunity, OpportunityDegreeLevel, OpportunityType

UpsertResult = Literal["created", "updated", "duplicate"]


class NormalizedOpportunity(BaseModel):
    """Validated, typed record ready for persistence."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source: str = Field(min_length=1, max_length=100)
    source_id: str | None = Field(default=None, max_length=255)
    url: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    description: str | None = None
    opportunity_type: OpportunityType = OpportunityType.internship
    location: str | None = Field(default=None, max_length=255)
    deadline: datetime | None = None
    posted_at: datetime | None = None
    degree_level: OpportunityDegreeLevel | None = None
    study_year: list[int] | None = None

    @field_validator("study_year")
    @classmethod
    def _study_year_values(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and not value:
            return None
        return value


def _row_values(record: NormalizedOpportunity) -> dict[str, object]:
    return record.model_dump(exclude={"source_id"})


class OpportunityStore:
    """Session-bound create/update gateway for opportunities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _find(self, record: NormalizedOpportunity) -> Opportunity | None:
        query = select(Opportunity)
        if record.source_id is not None:
            query = query.where(
                Opportunity.source == record.source,
                Opportunity.source_id == record.source_id,
            )
        else:
            query = query.where(Opportunity.url == record.url)
        return self.session.execute(query).scalar_one_or_none()

    def classify(self, record: NormalizedOpportunity) -> Literal["create", "update"]:
        """Read-only dry-run decision: would this record create or update?"""
        return "update" if self._find(record) is not None else "create"

    def upsert(self, record: NormalizedOpportunity) -> UpsertResult:
        """Create or update by identity; never insert a duplicate."""
        existing = self._find(record)
        if existing is None:
            row = Opportunity(
                source_id=record.source_id,
                **_row_values(record),  # type: ignore[arg-type]
            )
            self.session.add(row)
            try:
                self.session.flush()
            except IntegrityError:
                # Concurrent run inserted the same identity first: adopt it.
                self.session.rollback()
                existing = self._find(record)
                if existing is None:
                    raise
                self._apply(existing, record)
                return "duplicate"
            return "created"
        if self._apply(existing, record):
            return "updated"
        return "duplicate"

    def _apply(self, row: Opportunity, record: NormalizedOpportunity) -> bool:
        """Copy mutable fields onto ``row``. Returns True when anything changed."""
        changed = False
        values = _row_values(record)
        for field_name, value in values.items():
            if getattr(row, field_name) != value:
                setattr(row, field_name, value)
                changed = True
        if changed:
            row.updated_at = datetime.now(UTC)
        return changed

    def commit(self) -> None:
        self.session.commit()
