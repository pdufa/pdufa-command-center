#!/usr/bin/env python3
"""Read-only Phase 3 registry status and source recency review.

The 741 studies are a dated historical census, NOT 741 current Pipeline
candidates. Registered status and last-posted updates are research signals,
not proof of ongoing sponsor development, commercial rights, FDA/PDUFA,
market capitalization, trial success, or active drug approval.
"""
from __future__ import annotations

from collections import Counter
import csv
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import sys

EXPECTED = 741
SOURCE_PREFIX = "https://clinicaltrials.gov/api/v2/studies/"
TRIAL_PAGE_PREFIX = "https://clinicaltrials.gov/study/"
NCT = re.compile(r"^NCT[0-9]{8}$")
SHA = re.compile(r"^[a-f0-9]{64}$")
DATE_ONLY = re.compile(r"^\d{4}-\d\d-\d\d$")
VALID_CENSUS = {
    "RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION",
    "NOT_YET_RECRUITING", "COMPLETED", "TERMINATED", "WITHDRAWN", "UNKNOWN",
}
REGISTRY_ACTIVE = {
    "RECRUITING", "ACTIVE_NOT_RECRUITING",
    "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING",
}
REGISTRY_ENDED = {"COMPLETED", "TERMINATED", "WITHDRAWN"}
EXPECTED_GATES = (
    "registry_identity", "ticker_drug_indication_identity",
    "current_commercial_rights", "active_phase3_development",
    "public_listing", "market_cap_300m_10b", "us_fda_pathway",
    "verified_pdufa", "original_source_freshness",
)
BUCKETS = (
    "POSTED_LAST_90_DAYS", "POSTED_91_TO_180_DAYS",
    "POSTED_181_TO_365_DAYS", "POSTED_OVER_365_DAYS",
    "POSTED_DATE_MISSING", "POSTED_DATE_IN_FUTURE_REVIEW",
)
PRIORITIES = (
    "P1_REGISTRY_PHASE_OR_STATUS_CHANGED",
    "P2_AMBIGUOUS_REGISTRY_STATUS",
    "P3_MISSING_STALE_OR_FUTURE_UPDATE",
    "P4_STANDARD_REGISTRY_REVIEW",
)
HEADERS = (
    "review_position", "review_priority", "nct_id", "census_ticker",
    "census_company", "census_status", "current_registry_status",
    "registry_status_group", "status_matches_census",
    "phase3_in_current_registry", "registry_source_posted_update_date",
    "source_update_age_days", "source_update_recency_bucket",
    "registered_lead_sponsor", "registry_study_title",
    "original_registry_url", "registry_source_sha256", "source_fetched_at_utc",
    "registry_identity_gate", "commercial_rights_verified",
    "qualified_pipeline",
)


def exact_utc(value, label):
    if not isinstance(value, str) or not 18 <= len(value) <= 50:
        raise ValueError(f"Invalid {label} timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid {label} timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0:
        raise ValueError(f"Expected UTC {label} timestamp")
    return dt.astimezone(timezone.utc)


def bounded_string(value, max_len=1000, nullable=False):
    if value is None and nullable:
        return None
    if (not isinstance(value, str) or not 1 <= len(value) <= max_len
        or not value.strip() or any(ord(ch) < 32 for ch in value)):
        raise ValueError("Unbounded or invalid source string")
    return value


def indexed(items, label):
    if not isinstance(items, list) or len(items) != EXPECTED:
        raise ValueError(f"Expected 741 complete {label} records")
    result = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"Malformed {label} record")
        nct = item.get("nct_id")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in result:
            raise ValueError(f"Duplicate/malformed NCT in {label}")
        result[nct] = item
    return result


def freshness(posted, as_of):
    if posted is None:
        return None, "POSTED_DATE_MISSING"
    if not isinstance(posted, str) or not DATE_ONLY.fullmatch(posted):
        raise ValueError("Malformed ClinicalTrials.gov posted date")
    try:
        day = date.fromisoformat(posted)
    except ValueError as exc:
        raise ValueError("Impossible source posted date") from exc
    days = (as_of.date() - day).days
    if days < 0:
        return days, "POSTED_DATE_IN_FUTURE_REVIEW"
    if days <= 90:
        return days, "POSTED_LAST_90_DAYS"
    if days <= 180:
        return days, "POSTED_91_TO_180_DAYS"
    if days <= 365:
        return days, "POSTED_181_TO_365_DAYS"
    return days, "POSTED_OVER_365_DAYS"


def registry_status_group(status):
    if status in REGISTRY_ACTIVE:
        return "REGISTRY_ACTIVE_STATUS_ONLY"
    if status in REGISTRY_ENDED:
        return "REGISTRY_ENDED_STATUS_ONLY"
    return "OTHER_OR_UNCLEAR_REGISTRY_STATUS"


def build_report(registry, ledger, as_of=None):
    if not isinstance(registry, dict) or not isinstance(ledger, dict):
        raise ValueError("Original research inputs must be JSON objects")
    as_of = as_of or datetime.now(timezone.utc)
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset().total_seconds() != 0:
        raise ValueError("UTC source observation clock required")
    if (registry.get("report_type") != "MAIN_ORIGINAL_PHASE3_FULL_CENSUS_RESEARCH_ONLY"
        or registry.get("census_total") != EXPECTED
        or registry.get("source_identity_verified") != EXPECTED
        or registry.get("source_errors") != []
        or registry.get("qualified_pipeline_total") is not None
        or ledger.get("report_type") != "MAIN_PHASE3_QUALIFICATION_EVIDENCE_LEDGER_RESEARCH_ONLY"
        or ledger.get("total") != EXPECTED
        or ledger.get("qualified_pipeline_total") is not None):
        raise ValueError("Original 741-NCT registry/ledger scope unverified")
    rows = indexed(registry.get("original_source_records"), "registry")
    original = indexed(ledger.get("records"), "qualification ledger")
    if set(rows) != set(original):
        raise ValueError("Registry and qualification ledger NCT identities diverge")

    results = []
    for nct, source in rows.items():
        gate = original[nct]
        ticker = bounded_string(source.get("census_ticker"), 16)
        company = bounded_string(source.get("census_company"), 260)
        title = bounded_string(source.get("registry_study_title"), 1000)
        sponsor = bounded_string(source.get("currently_registered_lead_sponsor"), 260, nullable=True)
        historic = source.get("census_status")
        current = bounded_string(source.get("current_registry_status"), 80)
        if historic not in VALID_CENSUS:
            raise ValueError("Saved dated census contains an unexpected status")
        sha = source.get("source_sha256")
        if (not isinstance(sha, str) or not SHA.fullmatch(sha)
            or source.get("source") != SOURCE_PREFIX + nct
            or source.get("verified_current_commercial_development_rights") is not False
            or source.get("verified_us_fda_pdufa") is not False
            or source.get("qualified_pipeline") is not None
            or source.get("fda_approval_probability") is not None):
            raise ValueError(f"{nct}: registry source identity or nonqualification boundary invalid")
        phase3 = source.get("phase3_in_current_registry")
        matches = source.get("status_matches_dated_census")
        if type(phase3) is not bool or type(matches) is not bool or matches != (current == historic):
            raise ValueError(f"{nct}: malformed or inconsistent registry phase/status flags")
        fetched_at = exact_utc(source.get("fetched_at_utc"), "original registry fetch")
        if fetched_at > as_of.replace(microsecond=as_of.microsecond) and (
            fetched_at - as_of).total_seconds() > 300:
            raise ValueError("Registry fetch timestamp is in the future")
        if (gate.get("ticker") != ticker or gate.get("company") != company
            or gate.get("source_url") != TRIAL_PAGE_PREFIX + nct
            or gate.get("source_sha256") != sha
            or gate.get("source_fetched_at_utc") != source.get("fetched_at_utc")
            or gate.get("qualified_pipeline") is not None
            or gate.get("qualification_status") != "REVIEW"):
            raise ValueError(f"{nct}: qualification ledger does not match exact source")
        gates = gate.get("gates")
        expected_identity = "PASS" if phase3 and matches else "REVIEW"
        if (not isinstance(gates, dict) or set(gates) != set(EXPECTED_GATES)
            or gates["registry_identity"] != expected_identity
            or any(gates[name] != "REVIEW" for name in EXPECTED_GATES if name != "registry_identity")):
            raise ValueError(f"{nct}: registry status cannot establish additional Pipeline gates")

        age, bucket = freshness(source.get("source_posted_update_date"), as_of)
        if not phase3 or not matches:
            priority = PRIORITIES[0]
        elif registry_status_group(current) == "OTHER_OR_UNCLEAR_REGISTRY_STATUS":
            priority = PRIORITIES[1]
        elif bucket in ("POSTED_DATE_MISSING", "POSTED_DATE_IN_FUTURE_REVIEW",
                        "POSTED_OVER_365_DAYS"):
            priority = PRIORITIES[2]
        else:
            priority = PRIORITIES[3]
        results.append({
            "nct_id": nct, "census_ticker": ticker, "census_company": company,
            "census_status": historic, "current_registry_status": current,
            "registry_status_group": registry_status_group(current),
            "status_matches_census": matches, "phase3_in_current_registry": phase3,
            "registry_source_posted_update_date": source.get("source_posted_update_date"),
            "source_update_age_days": age, "source_update_recency_bucket": bucket,
            "registered_lead_sponsor": sponsor, "registry_study_title": title,
            "original_registry_url": source["source"],
            "registry_source_sha256": sha, "source_fetched_at_utc": source["fetched_at_utc"],
            "registry_identity_gate": gates["registry_identity"],
            "review_priority": priority, "commercial_rights_verified": False,
            "qualified_pipeline": None,
        })
    results.sort(key=lambda row: (PRIORITIES.index(row["review_priority"]),
                                  row["census_ticker"], row["nct_id"]))
    for n, row in enumerate(results, 1):
        row["review_position"] = n
    current_counts = Counter(row["current_registry_status"] for row in results)
    original_counts = Counter(row["census_status"] for row in results)
    group_counts = Counter(row["registry_status_group"] for row in results)
    freshness_counts = Counter(row["source_update_recency_bucket"] for row in results)
    priority_counts = Counter(row["review_priority"] for row in results)
    return {
        "report_type": "MAIN_PHASE3_REGISTRY_STATUS_SOURCE_RECENCY_RESEARCH_ONLY",
        "checked_at_utc": as_of.isoformat(),
        "historical_trial_count": EXPECTED,
        "source_identity_verified": EXPECTED,
        "current_registry_status_counts": dict(sorted(current_counts.items())),
        "dated_census_status_counts": dict(sorted(original_counts.items())),
        "registry_status_group_counts": dict(sorted(group_counts.items())),
        "source_posted_update_age_counts": {name: freshness_counts[name] for name in BUCKETS},
        "research_priority_counts": {name: priority_counts[name] for name in PRIORITIES},
        "registry_status_changed_since_saved_census": sum(not r["status_matches_census"] for r in results),
        "not_currently_registered_as_phase3": sum(not r["phase3_in_current_registry"] for r in results),
        "original_source_posted_update_missing": freshness_counts["POSTED_DATE_MISSING"],
        "original_source_posted_update_over_365_days": freshness_counts["POSTED_OVER_365_DAYS"],
        "registry_active_status_only_count": group_counts["REGISTRY_ACTIVE_STATUS_ONLY"],
        "registry_ended_status_only_count": group_counts["REGISTRY_ENDED_STATUS_ONLY"],
        "registration_freshness_gate_verified_count": 0,
        "independently_verified_commercial_rights": 0,
        "qualified_pipeline_total": None,
        "items": results,
        "limitations": (
            "Registered source status is not proof of active drug development or "
            "current U.S. commercial rights. A recent registry posting is not an "
            "independently verified original-source-freshness Pipeline PASS. "
            "Completed studies need not mean ended development; old posted updates "
            "do not prove inactive drugs. This report does not alter the qualified "
            "Pipeline, GEM JR/GEM/FS/FA presets or predict FDA outcomes."
        ),
    }


def safe_cell(value):
    if value is None:
        return ""
    cell = str(value)
    if cell.lstrip().startswith(("=", "+", "-", "@")) or cell.startswith(("\t", "\r")):
        return "'" + cell
    return cell


def write_csv(report, output):
    records = report.get("items")
    if (report.get("report_type") != "MAIN_PHASE3_REGISTRY_STATUS_SOURCE_RECENCY_RESEARCH_ONLY"
        or report.get("historical_trial_count") != EXPECTED
        or report.get("qualified_pipeline_total") is not None
        or not isinstance(records, list) or len(records) != EXPECTED):
        raise ValueError("CSV export requires full, unqualified source report")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS, lineterminator="\n")
        writer.writeheader()
        for row in records:
            writer.writerow({key: safe_cell(row.get(key)) for key in HEADERS})


def main():
    if len(sys.argv) != 5:
        sys.exit("Usage: phase3_registry_status_recency.py <registry> <ledger> <report.json> <worklist.csv>")
    registry, ledger = [
        json.loads(Path(name).read_text(encoding="utf-8")) for name in sys.argv[1:3]
    ]
    report = build_report(registry, ledger)
    target = Path(sys.argv[3])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(report, Path(sys.argv[4]))
    print(
        f"Registry status/recency: {report['historical_trial_count']}/741 original NCTs; "
        f"{report['registry_status_changed_since_saved_census']} changed from dated census; "
        f"{report['not_currently_registered_as_phase3']} no longer Phase 3 in registry; "
        f"{report['original_source_posted_update_over_365_days']} last posted >365 days; "
        "commercial rights 0 verified; qualified Pipeline UNKNOWN"
    )


if __name__ == "__main__":
    main()
