#!/usr/bin/env python3
"""Fresh, bounded SEC recheck of historically attested GEM financing closes.

This verifies the *individual claimed transactions* with the same primary-SEC
document parser used by the existing source-verification pipeline. It NEVER
upgrades an old financing ledger, a Phase 3 readout, GEM eligibility or scores.
Even two VERIFIED transactions need independent exact-program timeline review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.source_verification import Verifier, read_rows

ATTESTED = "VERIFIED_SECOND_POST_PHASE3_FINANCING"
FIELDS = (
    "event_key", "ticker", "historical_audit_status", "phase3_readout_date",
    "phase3_status", "nct_id", "first_close_date", "second_close_date",
    "first_sec_status", "second_sec_status", "first_sec_url", "second_sec_url",
    "first_sec_sha256", "second_sec_sha256", "recheck_status",
    "recheck_note", "checked_at_utc", "issuer_sec_registry_sha256", "gem_entry_authorized",
)


def safe_date(value):
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except (TypeError, ValueError):
        return None


def unique_event_map(rows):
    events, duplicate = {}, set()
    for row in rows:
        key = str(row.get("event_key") or "").strip()
        if not key:
            continue
        if key in events:
            duplicate.add(key)
        else:
            events[key] = row
    for key in duplicate:
        events.pop(key, None)
    return events, duplicate


def recheck_records(verifier, events, financing_records, *, mode="FULL", prior=None):
    if mode not in {"FULL", "DELTA"}:
        raise ValueError("Unsupported financing recheck mode")
    previous = {r.get("event_key"): r for r in (prior or [])}
    """Exactly one research result per previously attested financing event."""
    events_by_key, duplicate = unique_event_map(events)
    now = datetime.now(timezone.utc).isoformat()
    results = []
    for finance in financing_records:
        if finance.get("second_financing_audit_status") != ATTESTED:
            continue
        key = str(finance.get("event_key") or "").strip()
        event = events_by_key.get(key)
        ticker = key.split("|")[0].upper()
        first = safe_date(finance.get("first_financing_date"))
        second = safe_date(finance.get("second_financing_date"))
        phase3 = safe_date(event.get("phase3_date")) if event else None
        row = {
            "event_key": key, "ticker": ticker,
            "historical_audit_status": ATTESTED,
            "phase3_readout_date": event.get("phase3_date", "") if event else "",
            "phase3_status": event.get("phase3_status", "") if event else "",
            "nct_id": event.get("nct_id", "") if event else "",
            "first_close_date": finance.get("first_financing_date", ""),
            "second_close_date": finance.get("second_financing_date", ""),
            "first_sec_status": "NOT_CHECKED", "second_sec_status": "NOT_CHECKED",
            "first_sec_url": finance.get("first_financing_source", ""),
            "second_sec_url": finance.get("second_financing_source", ""),
            "first_sec_sha256": "", "second_sec_sha256": "",
            "recheck_status": "NOT_VERIFIED", "recheck_note": "",
            "checked_at_utc": now, "issuer_sec_registry_sha256": "",
            "gem_entry_authorized": "NO",
        }
        if key in duplicate or not event or str(event.get("ticker") or "").upper() != ticker:
            row["recheck_status"] = "EXACT_EVENT_MISSING_OR_CONFLICTED"
            row["recheck_note"] = "Refuse to use financing evidence from an ambiguous or unlinked trial"
            results.append(row)
            continue
        if not first or not second or not first < second <= verifier.as_of:
            row["recheck_status"] = "CLOSE_DATES_INVALID"
            row["recheck_note"] = "Two separate, nonfuture funding dates not established"
            results.append(row)
            continue
        # One lightweight issuer SEC index check on weekdays; reopen a
        # previously supported pair if any filing/amendment or trial identity
        # changed. No SEC access or hash => cannot reuse historical proof.
        if mode == "DELTA":
            inventory = verifier.registry({"ticker": ticker})
            if inventory.get("verification_status") == "VERIFIED":
                row["issuer_sec_registry_sha256"] = inventory.get("source_sha256", "")
        prior_row = previous.get(key, {})
        matching = all(prior_row.get(k, "") == row.get(k, "") for k in (
            "event_key", "ticker", "phase3_readout_date", "phase3_status",
            "nct_id", "first_close_date", "second_close_date",
            "first_sec_url", "second_sec_url"))
        carry = (mode == "DELTA" and matching
                 and prior_row.get("recheck_status") == "TRANSACTIONS_RECHECKED_REVIEW"
                 and prior_row.get("first_sec_status") == "VERIFIED"
                 and prior_row.get("second_sec_status") == "VERIFIED"
                 and row["issuer_sec_registry_sha256"]
                 and row["issuer_sec_registry_sha256"] == prior_row.get("issuer_sec_registry_sha256")
                 and all(re.fullmatch(r"[a-f0-9]{64}", prior_row.get(k, "")) for k in (
                     "first_sec_sha256", "second_sec_sha256")))
        if carry:
            for k in ("first_sec_status", "second_sec_status",
                      "first_sec_sha256", "second_sec_sha256", "recheck_status"):
                row[k] = prior_row[k]
            row["recheck_note"] = (
                "CARRIED_FORWARD: issuer SEC index and exact program/closing details "
                "unchanged since prior document verification at "
                + prior_row.get("checked_at_utc", "unknown")
                + "; no trading eligibility or new SEC document verification implied.")
            results.append(row)
            continue
        results_for_closes = []
        for ordinal, close_date, source in (
            ("first", first, finance.get("first_financing_source", "")),
            ("second", second, finance.get("second_financing_source", "")),
        ):
            # _recheck_exact_sec_url disallows replacing this event's source with
            # another filing belonging to the same company.
            probe = dict(event)
            probe.update({
                "financing_evidence_url": source,
                "financing_close_date": close_date.isoformat(),
                "_financing_review": {},
                "_recheck_exact_sec_url": True,
            })
            try:
                outcome = verifier.financing(probe)
            except Exception as exc:
                outcome = {"verification_status": "TECHNICAL_FAILURE",
                           "reason": type(exc).__name__, "source_sha256": ""}
            state = str(outcome.get("verification_status") or "TECHNICAL_FAILURE")
            row[ordinal + "_sec_status"] = state
            row[ordinal + "_sec_sha256"] = str(outcome.get("source_sha256") or "")
            results_for_closes.append(state)
        if "TECHNICAL_FAILURE" in results_for_closes:
            row["recheck_status"] = "SEC_SOURCE_BLOCKED_OR_FAILED"
            row["recheck_note"] = "SEC source collection failed or timed out; historical claim remains unverified"
        elif results_for_closes != ["VERIFIED", "VERIFIED"]:
            row["recheck_status"] = "SEC_TRANSACTION_EVIDENCE_INCOMPLETE"
            row["recheck_note"] = "One or both dated SEC documents did not independently establish funding"
        elif not phase3 or phase3 > first:
            row["recheck_status"] = "PHASE3_DATE_NOT_VERIFIED"
            row["recheck_note"] = "Both funded transactions rechecked; source-linked Phase 3 date preceding both is missing"
        elif not event.get("nct_id") or not event.get("trial_evidence_url"):
            row["recheck_status"] = "PHASE3_TRIAL_ID_OR_SOURCE_MISSING"
            row["recheck_note"] = "Both funded transactions rechecked; exact trial identity/readout source missing"
        else:
            row["recheck_status"] = "TRANSACTIONS_RECHECKED_REVIEW"
            row["recheck_note"] = ("Both claimed dates independently rechecked against SEC documents; "
                                    "separate deal identity and exact-program clinical evidence still "
                                    "require adjudication. No GEM eligibility upgraded.")
        results.append(row)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--mode", choices=("FULL", "DELTA"), default="FULL")
    parser.add_argument("--output", type=Path, default=Path("data/gem_two_close_recheck.csv"))
    parser.add_argument("--summary", type=Path,
                        default=Path("reports/gem_daily/gem_two_close_recheck_summary.json"))
    args = parser.parse_args(argv)
    financing = read_rows(args.data_dir / "second_financing_status.csv")
    events = read_rows(args.data_dir / "pdufa_candidates.csv")
    companies = read_rows(args.data_dir / "company_registry.csv")
    if not financing or not events or not companies:
        parser.error("Mandatory financing, event, or company source file missing")
    verifier = Verifier(companies)
    prior_path = args.data_dir / "gem_two_close_recheck.csv"
    prior = read_rows(prior_path) if args.mode == "DELTA" and prior_path.is_file() else []
    records = recheck_records(verifier, events, financing, mode=args.mode, prior=prior)
    if not records:
        parser.error("No historically attested second financing records to recheck")
    if len(records) != sum(r.get("second_financing_audit_status") == ATTESTED for r in financing):
        parser.error("SEC recheck scope is incomplete")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scan_mode": args.mode,
        "saved_attestations_reviewed": len(records),
        "prior_sec_pairs_carried_forward": sum("CARRIED_FORWARD" in x["recheck_note"] for x in records),
        "saved_attestations_rechecked": sum("CARRIED_FORWARD" not in x["recheck_note"] for x in records),
        "status_counts": dict(Counter(x["recheck_status"] for x in records)),
        "source_complete_eligibility_certified": False,
        "gem_entries_authorized": 0,
        "note": "Research-only fresh SEC document checks; no historical ledger upgraded.",
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
