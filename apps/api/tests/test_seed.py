"""Offline ingestion behavior and eligibility evidence regressions."""

import copy
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from opportunity_api.core.database import Base
from opportunity_api.ingestion.seed import (
    AUDIT,
    SEED,
    apply_seed,
    fingerprint,
    identifiers,
    main,
    normalize,
    prepare,
    render_sql,
)
from opportunity_api.models import Application, Opportunity, Skill, User


@pytest.fixture()
def reviewed():
    rows = json.loads(SEED.read_text(encoding="utf-8"))
    evidence = json.loads(AUDIT.read_text(encoding="utf-8"))["rows"]
    return rows, evidence


def test_original_50_preserved_and_all_records_audited(reviewed):
    rows, evidence = reviewed
    assert len(rows) == len(evidence) == 52
    assert sum(r["previous_group"] == "3-4" for r in evidence) == 22
    assert sum(r["type"] in {"internship", "job"} for r in rows[:50]) == 15
    assert {r["status"] for r in evidence} == {"confirmed", "unknown"}
    assert sum(r["study_year"] is not None for r in rows) == 3
    for row, audit in zip(rows, evidence, strict=True):
        assert audit["record_sha256"] == fingerprint(row)
        assert "study_year_group" not in row
        if audit["status"] == "unknown":
            assert row["study_year"] is None
            assert row["degree_level"] is None


def test_priority_records_do_not_inherit_3_4(reviewed):
    rows, _ = reviewed
    assert all(row["study_year"] is None for row in rows[28:])
    assert rows[38]["degree_level"] == "both"  # Stripe year preference != requirement.
    assert "PREFERRED" in rows[38]["eligibility_notes"]
    assert "BEFORE START" in rows[29]["eligibility_notes"]  # Four semesters != current year 2.
    assert "COMPLETED" in rows[43]["eligibility_notes"]
    assert "IDEAL" in rows[43]["eligibility_notes"]  # Master's year preference.
    assert "INTEGRATED MASTER" in rows[48]["eligibility_notes"]
    assert rows[46]["study_year"] is rows[49]["study_year"] is None  # Graduate jobs.
    assert rows[6]["study_year"] is rows[14]["study_year"] is rows[22]["study_year"] is None


def test_dry_run_offline_without_database(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    output = tmp_path / "seed.sql"
    assert main(["--sql-output", str(output)]) == 0
    payloads, rejected = prepare()
    assert rejected == [] and len(payloads) == len(json.loads(SEED.read_text(encoding="utf-8")))
    assert all(not row["is_active"] for row in payloads)
    assert output.read_text(encoding="utf-8") == render_sql(payloads)
    assert render_sql(list(reversed(payloads))) == render_sql(payloads)
    assert (SEED.parents[2] / "supabase/seed.sql").read_text(encoding="utf-8") == render_sql(
        payloads
    )


def test_identifiers_stable_and_posting_specific(reviewed):
    rows, _ = reviewed
    assert len({identifiers(row["source_url"]) for row in rows}) == len(rows)
    url = rows[39]["source_url"]
    assert identifiers(url) == identifiers(url + "?utm_source=mail#anchor")
    assert identifiers(url) == identifiers(url.replace("/en/", "/en-gb/"))
    assert identifiers(rows[31]["source_url"]) != identifiers(rows[47]["source_url"])
    row = copy.deepcopy(rows[0])
    row["title"] = "Updated title"
    assert identifiers(row["source_url"]) == identifiers(rows[0]["source_url"])


def test_changed_eligibility_requires_new_audit(reviewed):
    rows, evidence = reviewed
    row = copy.deepcopy(rows[39])
    row["study_year"] = [2, 3, 4]
    with pytest.raises(ValueError, match="changed after academic audit"):
        normalize(row, evidence[39])


@pytest.mark.parametrize("years", [[], [True], [0], [7], [2, 2], [3, 2], ["2"]])
def test_invalid_study_year_rejected(reviewed, years):
    rows, evidence = reviewed
    row, audit = copy.deepcopy(rows[0]), copy.deepcopy(evidence[0])
    row["study_year"] = years
    audit["record_sha256"] = fingerprint(row)
    with pytest.raises(ValueError):
        normalize(row, audit)


def test_conditional_rule_cannot_be_flattened(reviewed):
    rows, evidence = reviewed
    row, audit = copy.deepcopy(rows[14]), copy.deepcopy(evidence[14])
    row["study_year"] = audit["study_year"] = [2, 3]
    audit["record_sha256"] = fingerprint(row)
    with pytest.raises(ValueError, match="unconditional"):
        normalize(row, audit)


@pytest.mark.parametrize(
    "field,value",
    [
        ("deadline", "2026-02-30"),
        ("source_url", "https://user:pass@example.org/job"),
        ("type", "summer_school"),
        ("years_of_experience", True),
        ("title", " "),
        ("required_skills", [" "]),
    ],
)
def test_invalid_records_rejected(reviewed, field, value):
    rows, evidence = reviewed
    row, audit = copy.deepcopy(rows[0]), copy.deepcopy(evidence[0])
    row[field] = value
    audit["record_sha256"] = fingerprint(row)
    with pytest.raises(ValueError):
        normalize(row, audit)


def test_duplicate_rejected_and_valid_rows_reported(reviewed, tmp_path):
    rows, evidence = reviewed
    seed, audit = tmp_path / "input.json", tmp_path / "audit.json"
    seed.write_text(json.dumps([rows[0], rows[0], 123]))
    audit.write_text(json.dumps({"version": 1, "rows": evidence}))
    payloads, rejected = prepare(seed, audit)
    assert len(payloads) == 1
    assert [r["row"] for r in rejected] == [2, 3]
    output = tmp_path / "seed.sql"
    assert main(["--seed", str(seed), "--audit", str(audit), "--sql-output", str(output)]) == 1
    assert not output.exists()


@pytest.fixture()
def local_db(tmp_path):
    url = f"sqlite:///{tmp_path / 'seed-test.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield url, engine
    engine.dispose()


def test_upsert_rerun_updates_and_preserves_applications(local_db):
    url, engine = local_db
    payloads, _ = prepare()
    count = len(payloads)
    assert apply_seed(payloads, url) == {"inserted": count, "updated": 0, "unchanged": 0}
    assert apply_seed(payloads, url) == {"inserted": 0, "updated": 0, "unchanged": count}
    with Session(engine) as session:
        opportunity = session.scalar(
            select(Opportunity).where(Opportunity.source == payloads[0]["source"])
        )
        stored_id = opportunity.id
        user = User(email="synthetic@example.com", full_name="Fixture")
        application = Application(user=user, opportunity=opportunity)
        session.add_all([user, application])
        session.commit()
        application_id = application.id
    changed = copy.deepcopy(payloads)
    target = next(p for p in changed if p["id"] == str(stored_id))
    target["title"] = "Updated title"
    target["skills"] = ["Python", "SQL"]
    assert apply_seed(changed, url) == {"inserted": 0, "updated": 1, "unchanged": count - 1}
    with Session(engine) as session:
        assert session.get(Application, application_id).opportunity_id == stored_id
        assert {s.name for s in session.get(Opportunity, stored_id).skills} == {"Python", "SQL"}
        assert len(session.scalars(select(Opportunity)).all()) == count
        assert len(session.scalars(select(Skill)).all()) == 2
    assert apply_seed(changed, url)["unchanged"] == count


def test_conflicting_external_url_rolls_back_every_row(local_db):
    url, engine = local_db
    payloads, _ = prepare()
    with Session(engine) as session:
        session.add(
            Opportunity(
                title="Other owner",
                opportunity_type="job",
                url=payloads[-1]["url"],
                source="external",
                source_id="own",
            )
        )
        session.commit()
    with pytest.raises(IntegrityError):
        apply_seed(payloads, url)
    with Session(engine) as session:
        assert len(session.scalars(select(Opportunity)).all()) == 1


def test_api_unknown_year_does_not_match(client, db_factory):
    payloads, _ = prepare()
    with db_factory() as session:
        for payload in payloads:
            fields = {k: v for k, v in payload.items() if k != "skills"}
            from datetime import datetime
            from uuid import UUID

            fields["id"] = UUID(fields["id"])
            for field in ("deadline", "posted_at"):
                if fields[field]:
                    fields[field] = datetime.fromisoformat(fields[field])
            session.add(Opportunity(**fields))
        session.commit()
    response = client.get("/api/v1/opportunities", params={"study_year": 2, "page_size": 100})
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert all(item["study_year"] == [1, 2] for item in response.json()["items"])
    assert client.get("/api/v1/opportunities", params={"study_year": 3}).json()["total"] == 0


def test_skill_only_change_and_literal_escaping(local_db):
    url, engine = local_db
    payloads, _ = prepare()
    payload = copy.deepcopy(payloads[0])
    payload["title"] = "O'Brien \\ 50% ; DROP TABLE users; --"
    assert apply_seed([payload], url)["inserted"] == 1
    payload["skills"] = ["O'Brien \\ 50%"]
    assert apply_seed([payload], url)["updated"] == 1
    assert apply_seed([payload], url)["unchanged"] == 1
    with Session(engine) as session:
        row = session.scalar(select(Opportunity))
        assert row.title == payload["title"]
        assert [s.name for s in row.skills] == payload["skills"]
        assert User.__table__.name in Base.metadata.tables


def test_existing_non_generated_uuid_is_preserved(local_db):
    url, engine = local_db
    payloads, _ = prepare()
    payload = payloads[0]
    with Session(engine) as session:
        row = Opportunity(
            title="Preexisting",
            opportunity_type="job",
            url=payload["url"],
            source=payload["source"],
            source_id=payload["source_id"],
        )
        session.add(row)
        session.commit()
        original_id = row.id
    assert apply_seed([payload], url)["updated"] == 1
    with Session(engine) as session:
        assert session.scalar(select(Opportunity)).id == original_id


def test_review_ids_and_provenance(reviewed):
    from collections import Counter

    from opportunity_api.ingestion.seed import review_identifiers

    rows, _ = reviewed
    assert Counter(r["source"] for r in rows) == {
        "maria_europe_master_2026_10_12": 42,
        "seed_supplemental_2026_10_12": 8,
        "official_review_2026_10_19": 2,
    }
    assert sum(r["eligibility_review_status"] == "conditional_composite" for r in rows[:50]) == 10
    assert rows[48]["degree_level"] is None
    for row in rows:
        assert row["source_id"] == review_identifiers(row["url"], row["source"])[0]
        assert row["ready_for_public_seed"] is False
        assert row["current_source_review"] in {
            "verified", "flagged", "pending_2026_10_15_recheck"
        }
        expected_date = (
            "2026-10-19" if row["source"] == "official_review_2026_10_19" else "2026-10-12"
        )
        assert row["research_provenance"]["as_of"] == expected_date
        assert "NOT" in row["curation_context"]


def test_apply_default_blocks_unapproved_candidates(monkeypatch):
    import opportunity_api.ingestion.seed as importer

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://invalid.invalid/unreachable")
    monkeypatch.setattr(importer, "apply_seed", lambda *args: pytest.fail("Must not open database"))
    assert main(["--apply"]) == 1


def test_forged_identity_and_readiness_rejected(reviewed):
    rows, audits = reviewed
    for changes in (
        {"source_id": "bad"},
        {"url": "https://example.org/different"},
        {"source": "external"},
        {"ready_for_public_seed": True, "current_source_review": "pending"},
        {"study_year_group": "3-4"},
    ):
        row, audit = copy.deepcopy(rows[0]), copy.deepcopy(audits[0])
        row.update(changes)
        audit["record_sha256"] = fingerprint(row)
        with pytest.raises(ValueError):
            normalize(row, audit)


def test_old_manual_identity_adoption_preserves_graph(local_db):
    from opportunity_api.ingestion.seed import SOURCE

    url, engine = local_db
    payloads, _ = prepare()
    payload = payloads[0]
    old_key, _ = identifiers(payload["url"])
    with Session(engine) as session:
        row = Opportunity(
            title="Legacy candidate",
            opportunity_type="job",
            url=payload["url"],
            source=SOURCE,
            source_id=old_key,
        )
        user = User(email="legacy@example.com", full_name="Fixture")
        app = Application(user=user, opportunity=row)
        session.add_all([row, user, app])
        session.commit()
        row_id, app_id = row.id, app.id
    assert apply_seed([payload], url) == {"inserted": 0, "updated": 1, "unchanged": 0}
    assert apply_seed([payload], url) == {"inserted": 0, "updated": 0, "unchanged": 1}
    with Session(engine) as session:
        assert session.get(Opportunity, row_id).source == payload["source"]
        assert session.get(Application, app_id).opportunity_id == row_id
        assert len(session.scalars(select(Opportunity)).all()) == 1


def test_minimum_40_gate_reports_real_shortfall(tmp_path):
    from opportunity_api.ingestion.seed import is_current_candidate, load_verification

    live = load_verification()
    verified = sum(
        is_current_candidate(row, live[row["source_url"]])
        for row in json.loads(SEED.read_text(encoding="utf-8"))
    )
    report = tmp_path / "acceptance.json"
    assert main(["--require-minimum", "40", "--report", str(report)]) == (
        0 if verified >= 40 else 1
    )
    result = json.loads(report.read_text())
    assert result["current_verified"] == verified
    assert result["publication_approved"] == 0
    if verified < 40:
        assert "minimum not met" in result["error"]


def test_approved_only_generation_uses_two_distinct_gates(reviewed, tmp_path):
    from opportunity_api.ingestion.seed import load_verification

    rows, academic = copy.deepcopy(reviewed)
    live = load_verification()
    # Explicit synthetic publication approval for an already verified record; local fixture only.
    target = rows[3]
    target["deadline"] = "2099-12-31"  # Synthetic future window, never production approval.
    target["ready_for_public_seed"] = True
    target["current_source_review"] = "verified"
    academic[3]["record_sha256"] = fingerprint(target)
    live[target["source_url"]]["record_sha256"] = fingerprint(target)
    seed, audit, verification = (tmp_path / n for n in ["seed.json", "academic.json", "live.json"])
    seed.write_text(json.dumps(rows))
    audit.write_text(json.dumps({"version": 1, "rows": academic}))
    verification.write_text(json.dumps({"version": 1, "rows": list(live.values())}))
    output = tmp_path / "approved.sql"
    args = [
        "--seed",
        str(seed),
        "--audit",
        str(audit),
        "--verification",
        str(verification),
        "--approved-only",
        "--sql-output",
        str(output),
    ]
    assert main(args) == 0
    assert "INSERT INTO public.opportunities" not in output.read_text()
    live[target["source_url"]]["publication_approved"] = True
    verification.write_text(json.dumps({"version": 1, "rows": list(live.values())}))
    assert main(args) == 0
    assert output.read_text().count("INSERT INTO public.opportunities") == 1
    assert "TRUE" in output.read_text()
    # The separate candidate workflow must stay inactive even after publication approval.
    assert main([arg for arg in args if arg != "--approved-only"]) == 0
    candidates, rejected = prepare(seed, audit, verification)
    assert rejected == []
    assert output.read_text(encoding="utf-8") == render_sql(candidates)


def test_native_id_adopts_prior_review_hash_without_losing_fk(local_db):
    url, engine = local_db
    payloads, _ = prepare()
    rows = json.loads(SEED.read_text(encoding="utf-8"))
    payload = payloads[39]  # Official Amazon requisition, not a fabricated ID.
    assert payload["source_id"] == "amazon:10555873"
    with Session(engine) as session:
        row = Opportunity(
            title="Previous reviewed hash",
            opportunity_type="internship",
            url=payload["url"],
            source=payload["source"],
            source_id=rows[39]["source_id"],
        )
        user = User(email="native-fixture@example.com", full_name="Fixture")
        app = Application(user=user, opportunity=row)
        session.add_all([row, user, app])
        session.commit()
        original_id, app_id = row.id, app.id
    assert apply_seed([payload], url)["updated"] == 1
    assert apply_seed([payload], url)["unchanged"] == 1
    with Session(engine) as session:
        assert session.get(Opportunity, original_id).source_id == "amazon:10555873"
        assert session.get(Application, app_id).opportunity_id == original_id


def test_public_selection_must_also_meet_minimum(tmp_path):
    report = tmp_path / "approved-minimum.json"
    assert main(["--approved-only", "--require-minimum", "1", "--report", str(report)]) == 1
    result = json.loads(report.read_text())
    assert result["publication_approved"] == 0
    assert "approved selection below minimum" in result["error"]


def test_review_corrections_preserve_conditional_eligibility(reviewed):
    rows, audits = reviewed
    assert rows[12]["deadline"] == "2026-10-17"  # Registration, not competition day.
    assert rows[29]["deadline"] == "2027-01-11"  # Official 15:00 CET cutoff.
    assert rows[15]["deadline"] is None  # UK/Ireland and EU deadlines differ.
    assert "6 December 2026" in rows[15]["description"]
    assert "1 February 2027" in rows[15]["description"]
    assert rows[41]["location"] == "Lisbon, Portugal"
    assert rows[8]["work_mode"] is None  # Remote header versus campus-based body.
    assert rows[23]["study_year"] is None  # Year depends on degree duration.
    assert rows[32]["study_year"] is None and rows[32]["degree_level"] == "both"
    assert "BY START" in rows[32]["eligibility_notes"]
    assert audits[32]["checked_on"] == "2026-10-19"
    assert rows[43]["eligible_countries"] is None  # Citizenship != country of study.


@pytest.mark.parametrize(
    ("outcome", "availability", "deadline", "expected"),
    [
        ("verified", "open", "2026-10-18", False),
        ("verified", "open", "2026-10-19", True),
        ("verified", "closed", None, False),
        ("verified", "unverified", None, False),
        ("flagged", "open", None, False),
        ("verified", "announced", "2027-01-11", True),
    ],
)
def test_current_count_excludes_closed_flagged_and_expired(
    outcome, availability, deadline, expected
):
    from datetime import date

    from opportunity_api.ingestion.seed import is_current_candidate

    # Even a stale/incorrect eligible_for_import=True cannot bypass the other checks.
    review = dict(outcome=outcome, availability=availability, eligible_for_import=True)
    assert is_current_candidate(
        dict(deadline=deadline), review, on_date=date(2026, 10, 19)
    ) is expected


def test_later_review_flag_preserves_corroborated_native_identity(tmp_path):
    from opportunity_api.ingestion.seed import VERIFICATION

    before, _ = prepare()
    ledger = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    ledger["rows"][0].update(outcome="flagged", eligible_for_import=False)
    path = tmp_path / "flagged.json"
    path.write_text(json.dumps(ledger))
    after, rejected = prepare(verification_path=path)
    assert rejected == []
    assert after[0]["source_id"] == before[0]["source_id"] == "blackstone:45529"
    assert after[0]["id"] == before[0]["id"]
    assert after[0]["is_active"] is False


def test_direct_official_additions_are_not_workbook_eligibility(reviewed):
    rows, audits = reviewed
    optiver, cpu = rows[50:]
    assert optiver["organization"] == "Optiver" and cpu["organization"] == "Qualcomm"
    for row, audit in zip(rows[50:], audits[50:], strict=True):
        assert row["source"] == "official_review_2026_10_19"
        assert row["source_excel_row"] is row["source_excel_sheet"] is None
        assert row["maria_audit_verdict"] is None
        assert row["study_year"] is None
        assert audit["previous_group"] is None
        assert audit["record_sha256"] == fingerprint(row)
    assert optiver["degree_level"] is None
    assert "Penultimate-year" in optiver["eligibility_notes"]
    assert "2028" in optiver["eligibility_notes"]
    assert "COMPLETED" in cpu["eligibility_notes"]
    assert "IDEAL" in cpu["eligibility_notes"]
    assert cpu["eligible_countries"] is None  # Citizenship is not country-of-study eligibility.
    payloads, rejected = prepare()
    assert rejected == []
    assert payloads[51]["source_id"] == "qualcomm:3093026"
    assert payloads[43]["source_id"] == "qualcomm:3091774"
    assert payloads[51]["id"] != payloads[43]["id"]
