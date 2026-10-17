"""Original Streamlit inventory and the complete hosted-response regression."""
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from app import source_workspace

ROOT = Path(__file__).resolve().parents[3]
TODAY = date(2026, 10, 16)


def published(name):
    return (ROOT / "data" / name).read_text(encoding="utf-8-sig")


def test_original_streamlit_full_fixture_and_hosted_response_budget(monkeypatch):
    monkeypatch.setattr(source_workspace, "fetch", published)
    snapshot = source_workspace.gather(TODAY)
    rows = snapshot["pipeline"]
    assert len(rows) == len({row["id"] for row in rows}) == 9948
    assert Counter(row["stage"] for row in rows) == {
        "Early Phase 1": 11, "Phase 1": 1646, "Phase 1/2": 710,
        "Phase 2": 2017, "Phase 2/3": 136, "Phase 3": 1592,
        "Phase 3 Results": 2528, "PDUFA Decision": 42,
        "Post-Decision": 149, "Phase 4": 427, "Not Applicable": 690,
    }
    canonical = sorted([
        [row["id"], row["ticker"], row.get("drug", ""), row["stage"], row.get("pdufaDate", "")]
        for row in rows
    ])
    digest = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    # Independently captured from main/e459f54 pipeline_universe.load_universe,
    # not from the new adapter. Update only with a reviewed source-fixture change.
    assert digest == "fdb428d46b8358153d74ec870fd57b4df71fcea7b87a99a50347725237694f56"
    assert sum(bool(row.get("capInRange")) for row in rows) == 2389
    assert len(snapshot["members"]["GEM_JR"]["rows"]) == 14
    assert len(snapshot["members"]["GEM"]["rows"]) == 5
    # The API adds permanent IDs before proxying this JSON through Vercel.
    for index, row in enumerate(rows, start=1):
        row["programId"] = f"PDUFA-{index:06d}"
    assert len(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode()) < 4_400_000


def test_missing_original_feed_cannot_publish_an_artificially_smaller_total(monkeypatch):
    monkeypatch.setattr(source_workspace, "fetch", lambda name: "" if name == "all_phase_trials.csv" else published(name))
    with pytest.raises(RuntimeError, match="Pipeline parity source unavailable"):
        source_workspace.gather(TODAY)
