#!/usr/bin/env python3
"""Recheck only unresolved, exact-event PDUFA source claims.

Never overwrite the independently reconciled source ledger, second-financing
attestations, model scores or trade gates. Publish a dated comparison with
source citations; even a verified financing transaction is NOT financing #2.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from scripts.source_verification import (
    Verifier, read_rows, retry_sec_claim, retryable_sec_failure
)

SOURCES = ("FDA", "SEC", "FINANCIAL", "ISSUER")
SCOPED_CLAIMS = {
    "FDA": {"PDUFA_TARGET", "FDA_DECISION"},
    "SEC": {"FINANCING_CLOSURE", "FILINGS_INVENTORY"},
    "FINANCIAL": {"CASH_AND_RUNWAY", "CASH_FACT", "RUNWAY_ESTIMATE", "LIQUIDITY_FACT"},
    "ISSUER": {"PRIMARY_RELEASE"},
}
COLUMNS = [
    "event_key", "ticker", "category", "claim", "prior_status",
    "fresh_status", "resolution", "reason", "source_url", "source_sha256",
    "checked_at", "evidence", "expected", "observed",
]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fresh_result(verifier, event, row):
    category = row["category"]
    claim = row["claim"]
    if category == "FDA":
        results = verifier.regulatory(event)
    elif category == "SEC":
        if claim == "FILINGS_INVENTORY":
            # A registry inventory conflict is a company/CIK check, never
            # evidence of a financing transaction or its completion.
            results = [verifier.registry(event)]
        else:
            first = verifier.financing(event)
            if retryable_sec_failure(first):
                url = first.get("source_url", "")
                if isinstance(verifier.cache.get(url), Exception):
                    verifier.cache.pop(url, None)
                first, _ = retry_sec_claim(first, lambda: verifier.financing(event))
            results = [first]
    elif category == "FINANCIAL":
        results = verifier.financial(event)
    else:
        results = verifier.issuer(event)
    exact = [r for r in results if r["event_key"] == row["event_key"]
             and r["category"] == category and r["claim"] == claim]
    if len(exact) == 1:
        result = dict(exact[0])
        old_expected = (row.get("expected") or "").strip()
        # Source queues sometimes contain the placeholder UNVERIFIED rather than
        # an asserted transaction date. It is not conflicting primary evidence.
        if old_expected.upper() in {"UNVERIFIED", "UNKNOWN", "PENDING", "REVIEW"}:
            old_expected = ""
        if category == "FDA" and claim == "PDUFA_TARGET":
            # Historical FDA queue rows store the indication in expected,
            # while the fresh verifier stores the target date in expected.
            # Comparing disease text to an ISO date produced false conflicts.
            try:
                old_expected = date.fromisoformat(old_expected).isoformat()
            except (TypeError, ValueError):
                old_expected = ""
        if old_expected and result.get("expected") and old_expected != result["expected"]:
            result["verification_status"] = "CONFLICT"
            result["reason"] = "Comparable expected evidence changed between saved queue and fresh verification"
        if (category == "FDA" and claim == "PDUFA_TARGET"
                and row.get("verification_status") == "CONFLICT"
                and result.get("verification_status") == "VERIFIED"):
            # One new matching release cannot erase an old source conflict.
            result["verification_status"] = "CONFLICT"
            result["reason"] = "Previously conflicting primary target sources require separate reconciliation"
        return result
    # A previous generic cash-and-runway gap may resolve into two individually
    # evidenced claims. Only classify the generic gap as verified if both are
    # verified/not-applicable; retain primary-source fields from the cash claim.
    if category == "FINANCIAL" and claim == "CASH_AND_RUNWAY":
        statuses = {r["claim"]: r["verification_status"] for r in results}
        cash = next((r for r in results if r["claim"] == "CASH_FACT"), None)
        runway = next((r for r in results if r["claim"] == "RUNWAY_ESTIMATE"), None)
        good = (cash and runway and cash["verification_status"] == "VERIFIED"
                and runway["verification_status"] in ("VERIFIED", "NOT_APPLICABLE")
                and cash.get("source_sha256") and runway.get("source_sha256")
                and cash["source_sha256"] == runway["source_sha256"])
        if good:
            return {**cash, "claim": claim, "verification_status": "VERIFIED",
                    "reason": "Both separately verified cash fact and runway result in same SEC document; no independent cash forecast",
                    "evidence": (cash.get("evidence", "") + " | " + runway.get("evidence", ""))[:900]}
        if len(results) == 1 and results[0]["claim"] == claim:
            return results[0]
        return verifier.result(event, category, claim, "REVIEW_REQUIRED",
                               "Cash/runway subclaims not all supported: " + str(statuses))
    return verifier.result(event, category, claim, "REVIEW_REQUIRED",
                           "Exact claim not produced by fresh validator; no automatic promotion")


def run(args):
    data = args.data_dir
    report = read_json(data / "pdufa_source_report.json")
    source_id = report.get("latest_run_id")
    if type(source_id) is not str or not source_id.isdigit():
        raise ValueError("Verified source run identity missing")
    if source_id != args.source_run_id:
        raise ValueError("Source report run changed: refuse stale comparison")
    if report.get("full_coverage_verified") is True:
        raise ValueError("Queue source unexpectedly claims full coverage")
    rows = read_rows(data / "pdufa_source_review_queue.csv")
    expected = report.get("required_findings_unresolved")
    if type(expected) is not int or expected < 1 or expected != len(rows):
        raise ValueError("Review queue length does not match source audit")
    events = read_rows(data / "pdufa_candidates.csv")
    companies = read_rows(data / "company_registry.csv")
    financing_path = data / "second_financing_status.csv"
    financing = ({r["event_key"]: r for r in read_rows(financing_path)}
                 if financing_path.is_file() else {})
    event_map = {e["event_key"]: e for e in events}
    company_map = {c["ticker"].upper(): c for c in companies if c.get("ticker")}
    if (len(event_map) != len(events) or not companies or
            len(company_map) != len([c for c in companies if c.get("ticker")])):
        raise ValueError("Candidate identities/registry incomplete")
    issuer_source_path = args.root / "config" / "issuer_sources.json"
    issuer_sources = read_json(issuer_source_path) if issuer_source_path.is_file() else {}
    verifier = Verifier(companies, issuer_sources=issuer_sources)
    checked = []
    identities = set()
    for source in SOURCES:
        for row in rows:
            if row["category"] != source:
                continue
            identity = (row["event_key"], source, row["claim"])
            if identity in identities:
                raise ValueError("Duplicate unresolved event/claim")
            identities.add(identity)
            if row.get("verification_required") != "YES" or row["claim"] not in SCOPED_CLAIMS[source]:
                raise ValueError("Unexpected unresolved source claim")
            registry_inventory = (source == "SEC" and
                                  row["claim"] == "FILINGS_INVENTORY")
            if registry_inventory:
                # Only SEC's exact REGISTRY:TICKER claim may use company
                # identity. Do not invent a pipeline program or trade gate.
                ticker = row.get("ticker", "").upper()
                if (row["event_key"] != "REGISTRY:" + ticker or
                        not ticker or ticker not in company_map):
                    raise ValueError("Missing/conflicted SEC registry identity")
                candidate = {**company_map[ticker], "event_key": row["event_key"]}
            else:
                candidate = event_map.get(row["event_key"])
            if candidate is None or candidate.get("ticker") != row.get("ticker"):
                raise ValueError("Missing/conflicted exact-event candidate identity")
            event = {**candidate, "_financing_review": financing.get(row["event_key"], {})}
            response = fresh_result(verifier, event, row)
            status = response.get("verification_status", "")
            if status not in {"VERIFIED", "NOT_APPLICABLE", "REVIEW_REQUIRED",
                              "CONFLICT", "TECHNICAL_FAILURE", "UNAVAILABLE"}:
                raise ValueError("Unknown verifier result state")
            # A bare source URL or an index match is never independent evidence.
            if status == "VERIFIED" and not (
                response.get("source_url") and response.get("source_sha256")
                and response.get("checked_at") and response.get("evidence")
            ):
                status = "REVIEW_REQUIRED"
                response["reason"] = "Fresh primary-source evidence incomplete"
            checked.append({
                "event_key": row["event_key"], "ticker": row["ticker"],
                "category": source, "claim": row["claim"],
                "prior_status": row["verification_status"], "fresh_status": status,
                "resolution": ("NEW_SOURCE_VERIFIED_FOR_THIS_CLAIM_ONLY"
                               if status in ("VERIFIED", "NOT_APPLICABLE")
                               else "HOLD_UNRESOLVED"),
                "reason": response.get("reason", ""),
                "source_url": response.get("source_url", ""),
                "source_sha256": response.get("source_sha256", ""),
                "checked_at": response.get("checked_at", ""),
                "evidence": response.get("evidence", ""),
                "expected": response.get("expected", ""),
                "observed": response.get("observed", ""),
            })
    if len(checked) != expected or len(identities) != expected:
        raise ValueError("Missing unresolved items; fail rather than publish partial scope")
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(checked)
    remaining = [r for r in checked if r["resolution"] == "HOLD_UNRESOLVED"]
    cleared = [r for r in checked if r["resolution"] != "HOLD_UNRESOLVED"]
    summary = {
        "source_report_run_id": source_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PARTIAL" if remaining else "COMPLETE",
        "execution_status": "COMPLETE",
        "scope": "Targeted recheck of previously unresolved required claims only",
        "findings_due": expected,
        "findings_verified": len(cleared),
        "required_findings_unresolved": len(remaining),
        "source_observations": len(checked),
        "by_source": {source: {
            "rechecked": sum(r["category"] == source for r in checked),
            "newly_supported": sum(r["category"] == source for r in cleared),
            "still_unresolved": sum(r["category"] == source for r in remaining),
        } for source in SOURCES},
        "states": dict(Counter(r["fresh_status"] for r in checked)),
        "recheck_ledger_sha256": hashlib.sha256(args.csv_output.read_bytes()).hexdigest(),
        "recheck_ledger": str(args.csv_output),
        "source_baseline_unchanged": True,
        "trade_entry_authorized": False,
        "gem_financing_sequence_verified": False,
        "caveat": "New claim evidence is a recheck comparison, not an update to canonical source verification, a certified financing sequence or permission to trade. Independent full-source reconciliation is required before promoting any claims.",
        "unresolved_examples": [{k: r[k] for k in ("ticker", "category", "claim", "reason")} for r in remaining[:20]],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.scan_report:
        args.scan_report.parent.mkdir(parents=True, exist_ok=True)
        args.scan_report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("status", "findings_due",
                                               "findings_verified",
                                               "required_findings_unresolved", "by_source")},
                     indent=2))
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-run-id", required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--output", type=Path, default=Path("data/pdufa_targeted_recheck_report.json"))
    p.add_argument("--csv-output", type=Path, default=Path("data/pdufa_targeted_recheck_results.csv"))
    p.add_argument("--scan-report", type=Path)
    args = p.parse_args()
    if not args.source_run_id.isdecimal() or int(args.source_run_id) < 1:
        p.error("Source run ID must be positive integer")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
