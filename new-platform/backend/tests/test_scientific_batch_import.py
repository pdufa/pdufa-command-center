"""Offline safety and progress tests for the bounded scientific batch importer."""
import json
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from app.scientific_batch_import import MAX_TRIALS, main, parse_batch_file, run_batch

TRIAL_A = "NCT04280705"
TRIAL_B = "NCT02142738"
TRIAL_C = "NCT00000003"


def test_parse_valid_file_comments_blank_lines(tmp_path):
    path = tmp_path / "batch.txt"
    path.write_text("# explicit trial list\n\nNCT04280705\n  NCT02142738  \n")
    assert parse_batch_file(path) == [TRIAL_A, TRIAL_B]


@pytest.mark.parametrize("body,reason", [
    ("", "no NCT"),
    ("NCT01234\n", "exact NCT"),
    ("NCT04280705 NCT02142738\n", "exact NCT"),
    ("NCT04280705\nNCT04280705\n", "Duplicate"),
    (("NCT00000001\n" * (MAX_TRIALS + 1)), "exceeds"),
    ("x" * 4097, "size limit"),
])
def test_entire_batch_rejected_before_any_import(tmp_path, body, reason):
    path = tmp_path / "bad.txt"
    path.write_text(body)
    with pytest.raises(ValueError, match=reason):
        parse_batch_file(path)


def test_mixed_import_results_are_reported_without_aborting():
    events = []
    def fake_import(nct_id):
        if nct_id == TRIAL_A:
            return "imported"
        if nct_id == TRIAL_B:
            raise HTTPError("https://example.invalid", 429, "Too Many Requests", {}, None)
        return "already_exists"

    with patch("app.scientific_batch_import.scientific_import.DATABASE_URL",
               "postgresql+psycopg://example.invalid/test"):
        summary = run_batch([TRIAL_A, TRIAL_B, TRIAL_C], import_trial=fake_import, emit=events.append)
    assert [item["event"] for item in events] == [
        "batch_started", "trial_finished", "trial_finished", "trial_finished", "batch_finished"
    ]
    assert summary["total"] == summary["processed"] == 3
    assert summary["imported"] == summary["already_exists"] == summary["failed"] == 1
    assert events[2]["nct_id"] == TRIAL_B
    assert events[2]["http_status"] == 429
    assert events[2]["error_type"] == "HTTPError"
    assert events[3]["status"] == "already_exists"
    assert events[3]["processed"] == 3
    assert "example.invalid" not in json.dumps(events)


def test_sqlite_refused_before_trial_fetch():
    called = []
    with patch("app.scientific_batch_import.scientific_import.DATABASE_URL", "sqlite:///ephemeral.db"):
        with pytest.raises(RuntimeError, match="Persistent PostgreSQL"):
            run_batch([TRIAL_A], import_trial=called.append, emit=lambda event: None)
    assert called == []


def test_invalid_batch_before_trial_fetch():
    with pytest.raises(ValueError, match="Duplicate"):
        run_batch([TRIAL_A, TRIAL_A], import_trial=lambda _: "imported")


def test_cli_emits_rejection_safely(tmp_path, capsys):
    path = tmp_path / "bad.txt"
    path.write_text("BAD_IDENTIFIER\n")
    result = main(["--batch-file", str(path)])
    output = capsys.readouterr().out
    assert result == 1
    assert "batch_rejected" in output
    assert str(path) not in output


def test_cli_failed_trial_returns_nonzero(tmp_path, capsys):
    path = tmp_path / "batch.txt"
    path.write_text(TRIAL_A + "\n" + TRIAL_B + "\n")
    def fake_import(nct_id):
        if nct_id == TRIAL_B:
            raise TimeoutError("network refused")
        return "imported"

    with patch("app.scientific_batch_import.scientific_import.DATABASE_URL",
               "postgresql+psycopg://example.invalid/test"), \
         patch("app.scientific_batch_import.scientific_import.import_one", side_effect=fake_import), \
         patch("app.scientific_batch_import.time.sleep"):
        result = main(["--batch-file", str(path)])
    output = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert result == 2
    assert output[-1]["failed"] == 1
    assert output[-1]["imported"] == 1
    assert output[-1]["processed"] == 2
    assert "network refused" not in json.dumps(output)
