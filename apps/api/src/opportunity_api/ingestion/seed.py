"""Audited manual seed. Default: offline validation; DB access requires --apply."""

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, date, datetime, time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, field_validator
from sqlalchemy import create_engine, text

from opportunity_api.models import OpportunityDegreeLevel, OpportunityType

ROOT = Path(__file__).resolve().parents[5]
SEED = ROOT / "database/seeds/opportunities_seed.json"
AUDIT = ROOT / "database/seeds/eligibility_audit.json"
VERIFICATION = ROOT / "database/seeds/source_verification.json"
SOURCE = "manual_seed_v1"
SOURCES = {"maria_europe_master_2026_10_12", "seed_supplemental_2026_10_12"}
NAMESPACE = UUID("59a510a0-66f9-5a6a-bfcf-34d9ef2668d8")


def fingerprint(row: dict) -> str:
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def canonical_identity(url: str) -> str:
    """Use immutable ATS IDs where possible; otherwise a conservative normalized URL."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    if host == "amazon.jobs" and (match := re.search(r"/jobs/(\d+)(?:/|$)", path)):
        return f"{host}/jobs/{match[1]}"
    if "myworkdayjobs.com" in host and (match := re.search(r"_([A-Za-z0-9-]+)$", path)):
        return f"{host}/requisition/{match[1]}"
    if host in {"jobs.lever.co", "jobs.ashbyhq.com"}:
        path = re.sub(r"/apply$", "", path)
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in {"gclid", "fbclid", "lang"}
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), "")
    )


def identifiers(url: str) -> tuple[str, str]:
    source_id = "sha256:" + hashlib.sha256(canonical_identity(url).encode()).hexdigest()
    return source_id, str(uuid5(NAMESPACE, f"{SOURCE}:{source_id}"))


def review_canonical(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", parts.query, "")
    )


def review_identifiers(url: str, source: str) -> tuple[str, str]:
    source_id = hashlib.sha256(review_canonical(url).encode()).hexdigest()[:24]
    return source_id, str(uuid5(NAMESPACE, f"{source}:{source_id}"))


class SeedRecord(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    title: str = Field(min_length=1, max_length=255)
    organization: str = Field(min_length=1, max_length=255)
    type: str
    location: str = Field(max_length=255)
    description: str
    source_url: str = Field(max_length=512)
    degree_level: str | None
    study_year: list[StrictInt] | None
    deadline: str | None
    released_date: str | None
    date_checked: str
    required_skills: list[str]
    suggested_skills: list[str]
    eligible_countries: list[str] | None
    years_of_experience: StrictInt | None = Field(ge=0)
    url: str = Field(max_length=512)
    source: str = Field(max_length=100)
    source_id: str = Field(max_length=255)
    ready_for_public_seed: bool
    current_source_review: str
    eligibility_notes: str

    @field_validator("title", "organization", "source_url")
    @classmethod
    def nonblank(cls, value):
        if not value.strip() or "\x00" in value:
            raise ValueError("blank or NUL-containing field")
        return value

    @field_validator("type")
    @classmethod
    def valid_type(cls, value):
        OpportunityType(value)
        return value

    @field_validator("degree_level")
    @classmethod
    def valid_degree(cls, value):
        if value is not None:
            OpportunityDegreeLevel(value)
        return value

    @field_validator("source_url")
    @classmethod
    def valid_url(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 80, 443}
        ):
            raise ValueError("source must be a public HTTP(S) URL without credentials")
        return value

    @field_validator("study_year")
    @classmethod
    def valid_years(cls, value):
        if value is not None and (
            not value or any(y < 1 or y > 6 for y in value) or value != sorted(set(value))
        ):
            raise ValueError("study_year must be null or a sorted unique list of years 1-6")
        return value

    @field_validator("deadline", "released_date", "date_checked")
    @classmethod
    def valid_date(cls, value):
        if value is not None:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("date must be YYYY-MM-DD")
            date.fromisoformat(value)
        return value

    @field_validator("required_skills", "suggested_skills")
    @classmethod
    def valid_skills(cls, value):
        if any(not s.strip() or len(s.strip()) > 100 or "\x00" in s for s in value):
            raise ValueError("skill names must be nonblank and at most 100 characters")
        return value


def normalize(row: dict, evidence: dict) -> dict:
    if "study_year_group" in row:
        raise ValueError("legacy recommendation group must stay in audit, not eligibility input")
    record = SeedRecord.model_validate(row)
    if record.source not in SOURCES:
        raise ValueError("unrecognized reviewed dataset origin")
    SeedRecord.valid_url(record.url)
    if review_canonical(record.url) != review_canonical(record.source_url):
        raise ValueError("url and source_url disagree")
    expected_id, opportunity_id = review_identifiers(record.url, record.source)
    if record.source_id != expected_id:
        raise ValueError("source_id does not match the reviewed canonical URL hash")
    if record.ready_for_public_seed and record.current_source_review != "verified":
        raise ValueError("publication flag requires a completed current-source review")
    if evidence.get("record_sha256") != fingerprint(row):
        raise ValueError("record changed after academic audit; review and refresh its evidence")
    if evidence.get("status") not in {"confirmed", "unknown"}:
        raise ValueError("invalid academic audit status")
    if (
        evidence.get("study_year") != record.study_year
        or evidence.get("degree_level") != record.degree_level
    ):
        raise ValueError("academic fields disagree with audit")
    if record.study_year is not None and (
        evidence["status"] != "confirmed" or evidence.get("rule_kind") != "exact_years"
    ):
        raise ValueError("year lists need confirmed, unconditional exact-year evidence")
    if record.degree_level is not None and evidence["status"] != "confirmed":
        raise ValueError("degree level requires confirmed evidence")
    evidence_date = date.fromisoformat(evidence["checked_on"])
    if evidence_date > date.today():
        raise ValueError("audit check date is in the future")
    evidence_url = SeedRecord.valid_url(evidence["evidence_url"])

    def timestamp(value):
        # Date-only source values use midnight UTC as a storage convention, NOT an exact cutoff.
        return (
            datetime.combine(date.fromisoformat(value), time.min, UTC).isoformat()
            if value
            else None
        )

    return dict(
        id=opportunity_id,
        source=record.source,
        source_id=record.source_id,
        title=record.title,
        organization=record.organization,
        opportunity_type=record.type,
        location=record.location,
        url=record.url,
        description=(
            f"Academic eligibility: {record.eligibility_notes}\n"
            f"Evidence: {evidence_url}\n\n"
            f"Historical research summary (not independently certified): {record.description}"
        ),
        degree_level=record.degree_level,
        study_year=record.study_year,
        deadline=timestamp(record.deadline),
        posted_at=timestamp(record.released_date),
        # This audit certifies academic wording only; never infer availability from old labels.
        is_active=False,
        skills=sorted({skill.strip() for skill in record.required_skills}),
    )


def load_verification(path: Path = VERIFICATION) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("version") != 1 or not isinstance(data.get("rows"), list):
        raise ValueError("unsupported current-source verification format")
    result = {}
    for entry in data["rows"]:
        url = entry["source_url"]
        SeedRecord.valid_url(url)
        SeedRecord.valid_url(entry["evidence_url"])
        if url in result:
            raise ValueError("duplicate current-source verification URL")
        if entry.get("outcome") not in {"verified", "flagged"}:
            raise ValueError("invalid source verification outcome")
        if type(entry.get("eligible_for_import")) is not bool:
            raise ValueError("eligible_for_import must be a boolean")
        if type(entry.get("publication_approved")) is not bool:
            raise ValueError("publication_approved must be a boolean")
        if entry["eligible_for_import"] and entry["outcome"] != "verified":
            raise ValueError("flagged source cannot be import-eligible")
        if date.fromisoformat(entry["checked_on"]) > date.today():
            raise ValueError("source check date is in the future")
        result[url] = entry
    return result


def prepare(
    seed_path: Path = SEED, audit_path: Path = AUDIT, verification_path: Path = VERIFICATION
) -> tuple[list[dict], list[dict]]:
    verification = load_verification(verification_path)
    records = json.loads(seed_path.read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("seed must be a top-level JSON array")
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    if audit.get("version") != 1 or not isinstance(audit.get("rows"), list):
        raise ValueError("unsupported audit format")
    reviews = {}
    for evidence in audit["rows"]:
        url = evidence["source_url"]
        if url in reviews:
            raise ValueError("duplicate audit source URL")
        reviews[url] = evidence
    prepared, rejected = [], []
    seen = set()
    for number, row in enumerate(records, 1):
        try:
            if not isinstance(row, dict):
                raise ValueError("record must be an object")
            evidence = reviews.get(row.get("source_url"))
            if evidence is None:
                raise ValueError("record has no academic audit")
            payload = normalize(row, evidence)
            current = verification.get(row["source_url"])
            if current is None or current.get("record_sha256") != fingerprint(row):
                raise ValueError("record requires a refreshed current-source review")
            if current.get("official_source_id") and current["outcome"] == "verified":
                native = current["official_source_id"]
                if not isinstance(native, str) or not re.fullmatch(r"[a-z]+:[A-Za-z0-9-]+", native):
                    raise ValueError("invalid official source identifier")
                payload["source_id"] = native
                payload["id"] = str(uuid5(NAMESPACE, f"{payload['source']}:{native}"))
            identity = canonical_identity(payload["url"])
            if identity in seen:
                raise ValueError("duplicate canonical source posting")
            seen.add(identity)
            prepared.append(payload)
        except (ValueError, KeyError, TypeError) as exc:
            reason = (
                (
                    "invalid fields: "
                    + ", ".join(".".join(str(p) for p in error["loc"]) for error in exc.errors())
                )
                if isinstance(exc, ValidationError)
                else str(exc)
            )
            rejected.append(dict(row=number, reason=reason))
    return prepared, rejected


def literal(value, *, jsonb=False) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, list):
        value = json.dumps(value, separators=(",", ":"))
    value = str(value)
    if "\x00" in value:
        raise ValueError("NUL in SQL input")
    # PostgreSQL standard_conforming_strings is explicitly set in exported scripts.
    return "'" + value.replace("'", "''") + "'" + ("::jsonb" if jsonb else "")


def statements(payload: dict, dialect: str = "postgresql") -> list[str]:
    fields = [name for name in payload if name != "skills"]
    prefix = "public." if dialect == "postgresql" else ""
    values = [
        literal(
            UUID(payload[name]).hex if name == "id" and dialect == "sqlite" else payload[name],
            jsonb=name == "study_year" and dialect == "postgresql",
        )
        for name in fields
    ]
    mutable = [name for name in fields if name not in {"id", "source", "source_id"}]
    assignments = ", ".join(f"{name} = excluded.{name}" for name in mutable)
    changed = " OR ".join(
        f"opportunities.{name} IS DISTINCT FROM excluded.{name}" for name in mutable
    )
    queries = [
        f"INSERT INTO {prefix}opportunities ({', '.join(fields)}) "
        f"VALUES ({', '.join(values)}) ON CONFLICT (source, source_id) "
        f"DO UPDATE SET {assignments} WHERE {changed} RETURNING id"
    ]
    source_id = literal(payload["source_id"])
    owner = (
        f"SELECT id FROM {prefix}opportunities "
        f"WHERE source = {literal(payload['source'])} AND source_id = {source_id}"
    )
    # Never replace opportunity UUIDs: existing application foreign keys survive re-imports.
    queries.append(f"DELETE FROM {prefix}opportunity_skills WHERE opportunity_id = ({owner})")
    for skill in payload["skills"]:
        skill_uuid = uuid5(NAMESPACE, f"skill:{skill}")
        skill_id = skill_uuid.hex if dialect == "sqlite" else str(skill_uuid)
        queries.append(
            f"INSERT INTO {prefix}skills (id, name) "
            f"VALUES ({literal(skill_id)}, {literal(skill)}) ON CONFLICT (name) DO NOTHING"
        )
        queries.append(
            f"INSERT INTO {prefix}opportunity_skills (opportunity_id, skill_id) "
            f"SELECT ({owner}), id FROM {prefix}skills WHERE name = {literal(skill)} "
            "ON CONFLICT (opportunity_id, skill_id) DO NOTHING"
        )
    legacy_id, _ = identifiers(payload["url"])
    adoption = (
        f"UPDATE {prefix}opportunities SET source = {literal(payload['source'])}, "
        f"source_id = {source_id} WHERE source = {literal(SOURCE)} "
        f"AND source_id = {literal(legacy_id)} AND url = {literal(payload['url'])}"
    )
    previous_review_id, _ = review_identifiers(payload["url"], payload["source"])
    review_adoption = (
        f"UPDATE {prefix}opportunities SET source_id = {source_id} "
        f"WHERE source = {literal(payload['source'])} "
        f"AND source_id = {literal(previous_review_id)} "
        f"AND source_id <> {source_id} AND url = {literal(payload['url'])}"
    )
    return [adoption, review_adoption, *queries]


def render_sql(payloads: list[dict]) -> str:
    lines = [
        "-- Generated from the audited C2 seed; inactive candidates, no user/auth writes.",
        "BEGIN;",
        "SET LOCAL standard_conforming_strings = on;",
    ]
    for payload in sorted(payloads, key=lambda p: p["source_id"]):
        lines.extend(query + ";" for query in statements(payload))
    return "\n".join([*lines, "COMMIT;", ""])


def apply_seed(payloads: list[dict], database_url: str) -> dict:
    """Atomic import, only called explicitly. The caller chooses the approved DB."""
    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name not in {"postgresql", "sqlite"}:
        engine.dispose()
        raise ValueError("only PostgreSQL and SQLite are supported")
    counts = dict(inserted=0, updated=0, unchanged=0)
    try:
        with engine.begin() as connection:
            if engine.dialect.name == "postgresql":
                connection.exec_driver_sql("SET LOCAL standard_conforming_strings = on")
            for payload in payloads:
                queries = statements(payload, engine.dialect.name)
                adopted = connection.exec_driver_sql(
                    queries[0], execution_options={"no_parameters": True}
                ).rowcount
                adopted += connection.exec_driver_sql(
                    queries[1], execution_options={"no_parameters": True}
                ).rowcount
                existing = connection.execute(
                    text(
                        "SELECT id FROM opportunities "
                        "WHERE source = :source AND source_id = :source_id"
                    ),
                    dict(source=payload["source"], source_id=payload["source_id"]),
                ).first()
                changed = connection.exec_driver_sql(
                    queries[2], execution_options={"no_parameters": True}
                ).first()
                previous_skills = (
                    connection.execute(
                        text(
                            "SELECT s.name FROM skills s "
                            "JOIN opportunity_skills links ON links.skill_id = s.id "
                            "JOIN opportunities o ON o.id = links.opportunity_id "
                            "WHERE o.source = :source AND o.source_id = :source_id ORDER BY s.name"
                        ),
                        dict(source=payload["source"], source_id=payload["source_id"]),
                    )
                    .scalars()
                    .all()
                )
                skills_changed = previous_skills != payload["skills"]
                key = (
                    "inserted"
                    if existing is None
                    else "updated"
                    if changed or skills_changed or adopted
                    else "unchanged"
                )
                counts[key] += 1
                for query in queries[3:]:
                    connection.exec_driver_sql(query, execution_options={"no_parameters": True})
        return counts
    finally:
        engine.dispose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=SEED)
    parser.add_argument("--audit", type=Path, default=AUDIT)
    parser.add_argument("--sql-output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--verification", type=Path, default=VERIFICATION)
    parser.add_argument("--approved-only", action="store_true")
    parser.add_argument("--require-minimum", type=int, default=0)
    parser.add_argument(
        "--include-inactive-candidates",
        action="store_true",
        help="explicitly allow candidate-only import to an approved target",
    )
    parser.add_argument(
        "--apply", action="store_true", help="write to DATABASE_URL (requires approval)"
    )
    args = parser.parse_args(argv)
    try:
        payloads, rejected = prepare(args.seed, args.audit, args.verification)
        verification = load_verification(args.verification)
        raw_rows = {
            r["source_url"]: r
            for r in json.loads(args.seed.read_text(encoding="utf-8-sig"))
            if isinstance(r, dict)
        }
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"error": "seed/audit could not be loaded; inspect local input files"}))
        return 2
    verified = [p for p in payloads if verification[p["url"]]["eligible_for_import"]]
    approved = [
        p
        for p in verified
        if verification[p["url"]]["publication_approved"]
        and raw_rows[p["url"]]["ready_for_public_seed"]
        and raw_rows[p["url"]]["current_source_review"] == "verified"
    ]
    selected = (
        approved
        if args.approved_only or (args.apply and not args.include_inactive_candidates)
        else payloads
    )
    # Source verification and human approval are separate; announced calls stay inactive.
    for payload in approved:
        payload["is_active"] = verification[payload["url"]]["availability"] in {"open", "rolling"}
    report = dict(
        mode="apply" if args.apply else "dry-run",
        accepted=len(payloads),
        current_verified=len(verified),
        flagged=len(payloads) - len(verified),
        publication_approved=len(approved),
        selected=len(selected),
        rejected=rejected,
    )
    if args.require_minimum and len(verified) < args.require_minimum:
        report["error"] = (
            f"minimum not met: {len(verified)}/{args.require_minimum} current verified records"
        )
    if (
        args.require_minimum
        and (args.approved_only or args.apply)
        and len(verified) >= args.require_minimum
        and len(selected) < args.require_minimum
    ):
        report["error"] = (
            f"approved selection below minimum: {len(selected)}/{args.require_minimum}"
        )
    if rejected:
        report["error"] = "validation rejected rows; no output or database writes performed"
    if "error" not in report and args.sql_output:
        args.sql_output.write_text(render_sql(selected), encoding="utf-8")
    if args.apply and "error" not in report:
        if not selected:
            report["error"] = "0 publication-approved rows; no database connection attempted"
        elif not os.environ.get("DATABASE_URL"):
            report["error"] = "set DATABASE_URL explicitly for the approved target"
        else:
            try:
                report.update(apply_seed(selected, os.environ["DATABASE_URL"]))
            except Exception:
                report["error"] = "database import failed; transaction rolled back"
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 1 if rejected or "error" in report else 0


if __name__ == "__main__":
    raise SystemExit(main())
