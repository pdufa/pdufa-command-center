"""Concise GEM research-lead preview for collapsed overview card #1.

This is a source-audit preview, not an independent verified Phase 3 readout,
program-specific financing-sequence approval, or a trade recommendation.
"""
from __future__ import annotations

import csv
from pathlib import Path


def _read(path):
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error):
        return []


def _unique(records, key_field):
    values, duplicated = {}, set()
    for row in records:
        key = str(row.get(key_field) or "").strip()
        if not key:
            continue
        if key in values:
            duplicated.add(key)
        else:
            values[key] = row
    for key in duplicated:
        values.pop(key, None)
    return values


def research_preview(root="data"):
    root = Path(root)
    events = _unique(_read(root / "pdufa_candidates.csv"), "event_key")
    clinical = _unique(_read(root / "gem_phase3_exact_recheck.csv"), "event_key")
    financing = _unique(_read(root / "gem_two_close_recheck.csv"), "event_key")
    grouped = {
        "Both source leads": [],
        "Financing source lead": [],
        "Phase 3 source lead": [],
    }
    for event, info in events.items():
        ticker = str(info.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        study = clinical.get(event, {})
        audited = financing.get(event, {})
        clinical_lead = (
            study.get("source_recheck_status") == "POSTED_RESULTS_DISCOVERY_ONLY"
            and study.get("saved_phase3_status") != "PHASE_1_2_NOT_PHASE_3"
        )
        financing_lead = (
            audited.get("historical_audit_status")
            == "VERIFIED_SECOND_POST_PHASE3_FINANCING"
        )
        if not (clinical_lead or financing_lead):
            continue
        category = (
            "Both source leads" if clinical_lead and financing_lead else
            "Financing source lead" if financing_lead else "Phase 3 source lead"
        )
        fresh_sec_transactions = sum(
            audited.get(x) == "VERIFIED"
            for x in ("first_sec_status", "second_sec_status")
        )
        grouped[category].append((ticker, fresh_sec_transactions))
    output = {}
    for category, records in grouped.items():
        records.sort(key=lambda x: (-x[1], x[0]))
        output[category] = list(dict.fromkeys(ticker for ticker, _ in records))
    return output
