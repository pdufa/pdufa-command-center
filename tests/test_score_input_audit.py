"""Regression coverage for the scoring source-lineage and overlap inspector."""
import csv
import json
from pathlib import Path

from score_input_audit import (
    CLINICAL, SOURCES, audit_tests, clinical_agreement, load_sources,
    score_inputs_for_ticker, present, has_saved_gate_pass,
)


def _data():
    points = {domain: maximum for _, domain, maximum in CLINICAL}
    return {
        "PDUFA candidates": [
            {"ticker": "TEST", "event_key": "TEST|EVENT", "trade_score": "",
             "approval_probability": "75", "public_approval_probability": "",
             "science_score": "", "safety_score": ""}
        ],
        "FDA V3 review": [
            {"ticker": "TEST", "event_key": "TEST|EVENT", "fda_probability": "",
             "fda_hard_gate": "REVIEW"}
        ],
        "Post financing gates": [
            {"Ticker": "TEST", "Exact financing event": "TEST|EVENT",
             "Audited gate details": "trial_identity: REVIEW — EVIDENCE MISSING"}
        ],
        "Post market status": [
            {"ticker": "TEST", "relative_volume": "1.5", "trailing_momentum_pct": "2.5"}
        ],
        "PRE pilots": [{"ticker": "TEST", "nct_id": "NCT12345678", "domain_points": points}],
        "Pre-readout evidence": [
            {"ticker": "TEST", "nct_id": "NCT12345678",
             **{domain + "_points": str(value) for domain, value in points.items()}}
        ],
    }


def test_preliminary_reviewed_identical_is_shared_input():
    data = _data()
    value = clinical_agreement(data)
    assert value == {"matched": 1, "equal": 1, "disagreements": []}
    results = {r["Test"]: r for r in audit_tests(data)}
    assert results["Clinical model redundancy"]["Status"] == "SHARED INPUT"
    assert results["Trade Score coverage"]["Status"] == "DATA GAP"
    assert results["Public PoA coverage"]["Status"] == "DATA GAP"
    assert results["FDA V3 calculated probability"]["Status"] == "DATA GAP"


def test_preliminary_reviewed_disagreement_detected():
    data = _data()
    data["Pre-readout evidence"][0]["safety_points"] = "0"
    value = clinical_agreement(data)
    assert value["matched"] == 1 and value["equal"] == 0
    assert value["disagreements"] == ["TEST"]
    assert audit_tests(data)[0]["Status"] == "REVIEW"


def test_stored_and_exact_event_input_inspection_are_kept_distinct():
    data = _data()
    result = score_inputs_for_ticker(data, "TEST")
    assert any(r["Source"] == "PDUFA candidates" and
               r["Input column"] == "trade_score" and r["Present"] == "NO"
               for r in result)
    assert any(r["Source"] == "Post financing (exact event)"
               and r["Event / Trial"] == "TEST|EVENT" for r in result)
    assert any(r["Source"] == "Post market (ticker observation only)"
               for r in result)


def test_financing_gate_pass_must_be_explicit_state_not_incidental_word():
    rejected = (
        "trial_identity: NOT PASS",
        "trial_identity: REVIEW — will PASS only with source",
        "trial_identity: PASS PENDING",
        "trial_identity: COMPASS",
        "trial_identity: RECHECK | phase3_primary: REVIEW — EVIDENCE MISSING",
        "OPTIONAL financing #2: PASS not confirmed",
    )
    for sample in rejected:
        assert not has_saved_gate_pass({"Audited gate details": sample})
    assert has_saved_gate_pass({"Audited gate details":
        "trial_identity: REVIEW — EVIDENCE MISSING | phase3_primary: PASS — reviewed source"})
    assert has_saved_gate_pass({"Audited gate details": "safety: PASS"})


def test_missing_values_do_not_count_as_zero_or_verified():
    assert not present(None)
    assert not present("")
    assert not present("NOT SCORED")
    assert present("0")
    assert present(0)


def test_read_only_loader_supports_missing_sources(tmp_path):
    empty = load_sources(str(tmp_path))
    assert all(rows == [] for rows in empty.values())
    data = _data()
    for label, path in SOURCES.items():
        output = tmp_path / path
        output.parent.mkdir(exist_ok=True, parents=True)
        rows = data[label]
        if not rows:
            continue
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    pilot = tmp_path / "data/pre_phase3_pilot_clinical_reviews.json"
    pilot.write_text(json.dumps({"records": data["PRE pilots"]}), encoding="utf-8")
    reread = load_sources(str(tmp_path))
    assert reread["PRE pilots"] == data["PRE pilots"]
    assert reread["Post financing gates"][0]["Exact financing event"] == "TEST|EVENT"
