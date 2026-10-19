"""Original Streamlit inventory and the complete hosted-response regression."""
import gzip
import json
import sys
from datetime import date
from pathlib import Path

import pytest

from app import source_workspace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from pipeline_universe import load_universe  # independent published-source merge
TODAY = date(2026, 10, 16)


def published(name):
    return (ROOT / "data" / name).read_text(encoding="utf-8-sig")


def test_original_streamlit_full_fixture_and_hosted_response_budget(monkeypatch):
    monkeypatch.setattr(source_workspace, "fetch", published)
    snapshot = source_workspace.gather(TODAY)
    rows = snapshot["pipeline"]
    # Historically, main/e459f54 contained 9,948 records, with frozen
    # digest fdb428d46b8358153d74ec870fd57b4df71fcea7b87a99a50347725237694f56.
    # The data/ clinical feeds have expanded since that immutable October 16
    # snapshot. Preserve the historical number as a *lower bound* and verify
    # every current row against the INDEPENDENT legacy source merge, not an
    # adapted/current-source count or a new guessed hash.
    original = load_universe(ROOT / "data", today=TODAY)
    by_id = {str(row["record_id"]): row for _, row in original.iterrows()}
    assert len(rows) == len({row["id"] for row in rows}) == len(by_id)
    assert len(rows) >= 9948, "Published Pipeline cannot silently shrink its historic baseline"
    assert set(by_id) == {row["id"] for row in rows}
    for row in rows:
        prior = by_id[row["id"]]
        assert row["ticker"] == prior["ticker"], row["id"]
        assert row["stage"] == prior["current_stage"], row["id"]
        assert row.get("drug", "") == prior["drug"], row["id"]
        assert row.get("pdufaDate", "") == prior["pdufa_date"], row["id"]
    # GEM stage membership is source-driven: never adjust the numeric
    # expectations to conceal candidate additions or removals.
    assert snapshot["members"]["GEM_JR"]["rows"] is not None
    assert snapshot["members"]["GEM"]["rows"] is not None
    # The API adds permanent IDs before proxying this JSON through Vercel.
    for index, row in enumerate(rows, start=1):
        row["programId"] = f"PDUFA-{index:06d}"
    # /api/workspace already sends gzip bytes through Vercel. Check its actual
    # wire budget, including the added trial-evidence fields and permanent IDs.
    encoded = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode()
    assert len(gzip.compress(encoded, compresslevel=6)) < 4_400_000
    assert snapshot["trialFilterSchema"] == 1
    assert all("trialFilters" in row for row in rows)


def test_missing_original_feed_cannot_publish_an_artificially_smaller_total(monkeypatch):
    monkeypatch.setattr(source_workspace, "fetch", lambda name: "" if name == "all_phase_trials.csv" else published(name))
    with pytest.raises(RuntimeError, match="Required PIPELINE source unavailable"):
        source_workspace.gather(TODAY)
