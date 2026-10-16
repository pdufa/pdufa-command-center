"""Regression coverage for source-identified stage lineage and missing chart data."""
import csv
import json
from datetime import date

from chart_indicator_sheet import build_chart_indicator_rows


def _csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_program_identity_and_wt_tags_are_not_trade_authorization(tmp_path):
    _csv(tmp_path / "phase_pipeline.csv", [
        {"nct_id": "NCT00000001", "ticker": "XYZ", "drug": "therapy one",
         "pdufa_date": ""},
        {"nct_id": "NCT00000002", "ticker": "XYZ", "drug": "therapy two",
         "pdufa_date": ""},
    ])
    _csv(tmp_path / "pdufa_candidates.csv", [
        {"event_key": "XYZ|THERAPY_ONE", "ticker": "XYZ",
         "drug": "therapy one", "pdufa_date": "2026-12-01"},
    ])
    _csv(tmp_path / "phase_pipeline_market_caps.csv", [
        {"ticker": "XYZ", "market_cap": "900000000",
         "market_cap_status": "VERIFIED", "market_cap_source": "https://example.test/cap"},
    ])
    membership = {"schema_version": 1, "stages": {
        "GEM_JR": {"entries": {
            "TRIAL|NCT00000001": {
                "ticker": "XYZ", "nct_id": "NCT00000001", "status": "ACTIVE",
                "first_found": "2026-10-14"},
        }},
        "GEM": {"entries": {
            "APPLICATION|XYZ|THERAPY_ONE": {
                "ticker": "XYZ", "status": "ACTIVE", "first_found": "2026-10-15"},
        }},
    }}
    (tmp_path / "gem_stage_membership.json").write_text(
        json.dumps(membership), encoding="utf-8")
    records = build_chart_indicator_rows(
        tmp_path, date(2026, 10, 16), watch=["XYZ"], trade=["XYZ"])
    keyed = {item["Pipeline ID"]: item for item in records}
    assert len(records) == 3
    assert keyed["TRIAL|NCT00000001"]["Current stage"] == "GEM JR"
    assert keyed["TRIAL|NCT00000002"]["Current stage"] == "PIPELINE"
    assert keyed["APPLICATION|XYZ|THERAPY_ONE"]["Current stage"] == "GEM"
    assert all(item["WT decision label"] == "W + T — CHECK" for item in records)
    assert all(item["Market-cap gate"] == "WITHIN $300M–$10B" for item in records)
    assert all(item["Priority 4 — ATR(14)"] == "UNAVAILABLE — OHLC REQUIRED"
               for item in records)
    assert all(item["Reward / risk"] == "NO VERIFIED TRADE PLAN"
               for item in records)
    assert all(item["Saved EOD close $"] is None for item in records)


def test_unverified_market_cap_and_inactive_stage_do_not_promote(tmp_path):
    _csv(tmp_path / "pdufa_candidates.csv", [
        {"event_key": "ABC|THERAPY", "ticker": "ABC", "drug": "abc therapy",
         "pdufa_date": ""},
    ])
    (tmp_path / "gem_stage_membership.json").write_text(
        json.dumps({"schema_version": 1, "stages": {"GEM": {"entries": {
            "APPLICATION|ABC|THERAPY": {
                "ticker": "ABC", "status": "LEFT", "left_date": "2026-10-15"}
        }}}}), encoding="utf-8")
    result = build_chart_indicator_rows(
        tmp_path, date(2026, 10, 16), trade=["ABC"])
    assert len(result) == 1
    assert result[0]["Current stage"] == "PIPELINE"
    assert result[0]["In GEM"] == "NO"
    assert result[0]["Market-cap gate"] == "UNVERIFIED"
    assert result[0]["WT decision label"] == "T — TRADING RESEARCH"
    assert "needs manual entry/stop/target" in result[0]["Data completeness / next action"]
