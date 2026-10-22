"""Raw ingestion contract: the shape every source adapter must emit.

A ``RawOpportunity`` is a deliberately un-normalized record. Parsing
deadlines, degree levels and study years into typed values happens later in
the pipeline (normalize/validate); here we only require identity, provenance
and honest absence: a field the source did not provide stays ``None``.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RawOpportunity(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    source: str = Field(min_length=1, max_length=100)
    source_id: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=512)
    title: str = Field(min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    deadline_raw: str | None = None
    degree_level_raw: str | None = None
    study_year_raw: str | None = None
    fetched_at: datetime = Field(default_factory=_utcnow)

    @field_validator(
        "source_id",
        "source_url",
        "organization",
        "location",
        "deadline_raw",
        "degree_level_raw",
        "study_year_raw",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def _has_identity(self) -> "RawOpportunity":
        if self.source_id is None and self.source_url is None:
            raise ValueError("raw opportunity needs at least one of source_id or source_url")
        return self
