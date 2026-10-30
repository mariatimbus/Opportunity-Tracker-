"""Ingestion smoke: pipeline dry-run over fixtures; never touches a real DB."""

import json

from opportunity_api.ingestion.smoke import main

FIXTURES = "tests/fixtures/ingestion_smoke.json"


def test_smoke_run_succeeds_on_healthy_fixtures(capsys):
    assert main(["--fixtures", FIXTURES]) == 0
    out = capsys.readouterr().out
    assert "Ingestion dry run completed" in out
    assert "SMOKE OK" in out
    # 3 in-scope, 1 non-student role, 1 outside Europe
    assert "fetched=5" in out
    assert "accepted=3" in out
    assert "rejected=2" in out
    assert "would_create=3" in out


def test_smoke_fails_on_missing_file(capsys):
    assert main(["--fixtures", "tests/fixtures/does_not_exist.json"]) == 1
    assert "SMOKE FAILED" in capsys.readouterr().out


def test_smoke_fails_on_invalid_records(tmp_path, capsys):
    fixture = tmp_path / "bad.json"
    fixture.write_text(
        json.dumps(
            {"sources": [{"name": "bad", "records": [{"source": "bad", "title": "No identity"}]}]}
        ),
        encoding="utf-8",
    )
    assert main(["--fixtures", str(fixture)]) == 1
    assert "invalid fixtures" in capsys.readouterr().out
