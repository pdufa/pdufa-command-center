#!/usr/bin/env python3
"""Read-only original-registry lead-sponsor name triage across all 741 trials.

This is a *textual registry-to-census identity comparison*, not proof that
a US-listed issuer owns a program, the company is active, or the trial has
a pending FDA application/PDUFA. Original FDA and corporate gates remain open.

Uses 30 bounded ClinicalTrials.gov public API v2 filter.ids queries, each
with at most 25 exact NCT IDs, and checks the API dataVersion before/after.
No credentials, source writes, scheduled scans, trades or changes to Pipeline.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from check_phase3_original_registry_pilot import SOURCE_CSV
from check_phase3_64_original_sources import select_64_original_studies
from check_phase3_remaining_677_sources import (
    BATCH_SIZE, registry_version, safe_fetch_group, select_remaining_677,
)

TOTAL_TRIALS = 741
TOTAL_TICKERS = 130
MAX_WORKERS = 2
CATEGORIES = (
    "EXACT_REGISTERED_SPONSOR_TEXT_MATCH",
    "NORMALIZED_TEXT_VARIANT_REVIEW",
    "REGISTERED_SPONSOR_NAME_DIFFERENCE_REVIEW",
    "REGISTERED_SPONSOR_NOT_REPORTED",
    "ORIGINAL_REGISTRY_SOURCE_UNVERIFIED",
)


def source_population(csv_text: str) -> list[dict[str, str]]:
    """Exhaustively check the dated 741-row research population before I/O."""
    pilot_ids = {x["nct_id"] for x in select_64_original_studies(csv_text)}
    remaining_ids = {x["nct_id"] for x in select_remaining_677(csv_text)}
    rows = list(csv.DictReader(csv_text.splitlines()))
    if (len(rows) != TOTAL_TRIALS
        or {x["nct_id"] for x in rows} != pilot_ids | remaining_ids
        or pilot_ids & remaining_ids
        or len({x["ticker"] for x in rows}) != TOTAL_TICKERS):
        raise ValueError("Original lead-sponsor research source census incomplete")
    return rows


def compare_registered_sponsor(original: str, current: str | None) -> str:
    """String comparison only — never validates legal control or program rights."""
    if not isinstance(original, str) or not original.strip():
        raise ValueError("Dated census sponsor not supplied")
    if current is None or current == "":
        return "REGISTERED_SPONSOR_NOT_REPORTED"
    if not isinstance(current, str) or len(current) > 260:
        raise ValueError("Invalid current registered sponsor content")
    if original == current:
        return "EXACT_REGISTERED_SPONSOR_TEXT_MATCH"
    if " ".join(original.casefold().split()) == " ".join(current.casefold().split()):
        return "NORMALIZED_TEXT_VARIANT_REVIEW"
    return "REGISTERED_SPONSOR_NAME_DIFFERENCE_REVIEW"


def sponsor_research_report(
    population: list[dict[str, str]], observations: list[dict[str, object]],
    before: dict[str, str] | None, after: dict[str, str] | None,
    fetched_at: str,
) -> dict[str, object]:
    """Never silently drop failed sources, and never promote FDA/issuer facts."""
    if len(population) != TOTAL_TRIALS or len(observations) != TOTAL_TRIALS:
        raise ValueError("Original 741-trial sponsor research is incomplete")
    if len({x["nct_id"] for x in population}) != TOTAL_TRIALS:
        raise ValueError("Duplicate dated census trial identity")
    counts = Counter({k: 0 for k in CATEGORIES})
    study_rows = []
    companies_with_review = set()
    failed = []
    changed_status = []
    missing_phase3 = []
    for original, observed in zip(population, observations):
        nct = original["nct_id"]
        ticker = original["ticker"]
        if observed.get("nct_id") != nct:
            raise ValueError("Cross-NCT original source mixup")
        if "error" in observed:
            error = observed["error"]
            if not isinstance(error, str) or len(error) > 100:
                raise ValueError("Invalid source-failure reason")
            reason = "ORIGINAL_REGISTRY_SOURCE_UNVERIFIED"
            failed.append({"nct_id": nct, "error_type": error})
            current = None
        else:
            if (observed.get("census_ticker") != ticker
                or observed.get("census_company") != original["company"]
                or observed.get("census_status") != original["status"]
                or observed.get("source") != "https://clinicaltrials.gov/api/v2/studies/" + nct
                or observed.get("source_retrieval_method") != "batch_filter_ids"
                or not isinstance(observed.get("canonical_returned_study_sha256"), str)
                or len(observed["canonical_returned_study_sha256"]) != 64
                or any(x not in "0123456789abcdef"
                       for x in observed["canonical_returned_study_sha256"])
                or observed.get("qualified_pipeline") is not None
                or observed.get("verified_us_fda_pdufa") is not False
                or observed.get("verified_current_commercial_development_rights") is not False
                or observed.get("fda_approval_probability") is not None):
                raise ValueError("Original sponsor source evidence cannot qualify candidates")
            current = observed.get("currently_registered_lead_sponsor")
            reason = compare_registered_sponsor(original["company"], current)
            if observed.get("status_matches_dated_census") is not True:
                changed_status.append(nct)
            if observed.get("phase3_in_current_registry") is not True:
                missing_phase3.append(nct)
        counts[reason] += 1
        if reason != "EXACT_REGISTERED_SPONSOR_TEXT_MATCH":
            companies_with_review.add(ticker)
        study_rows.append({
            "nct_id": nct, "ticker": ticker,
            "dated_census_registered_sponsor": original["company"],
            "current_registry_lead_sponsor": current,
            "registered_sponsor_comparison": reason,
            "census_registry_status": original["status"],
            "current_registry_status": observed.get("current_registry_status"),
            "current_registry_phase3": observed.get("phase3_in_current_registry"),
            "original_registry_source": "https://clinicaltrials.gov/api/v2/studies/" + nct,
            "canonical_batch_study_sha256": observed.get("canonical_returned_study_sha256"),
            "original_registry_checked_at_utc": observed.get("fetched_at_utc"),
            "original_registry_posted_update_date": observed.get("source_posted_update_date"),
            "qualified_pipeline": None,
            "verified_current_issuer_rights": False,
            "verified_fda_pdufa": False,
            "fda_approval_probability": None,
        })
    version_stable = bool(
        before is not None and after is not None and before == after
        and isinstance(before.get("apiVersion"), str)
        and isinstance(before.get("dataTimestamp"), str)
    )
    exact_matches = counts["EXACT_REGISTERED_SPONSOR_TEXT_MATCH"]
    return {
        "report_type": "ORIGINAL_741_STUDY_REGISTERED_SPONSOR_TEXT_RESEARCH",
        "checked_at_utc": fetched_at,
        "dated_census_trial_denominator": TOTAL_TRIALS,
        "dated_census_company_denominator": TOTAL_TICKERS,
        "selected_exact_nct_count": TOTAL_TRIALS,
        "original_registry_source_identities_retrieved": TOTAL_TRIALS - len(failed),
        "source_errors_count": len(failed),
        "registry_version_before": before,
        "registry_version_after": after,
        "registry_version_stable": version_stable,
        "registered_sponsor_text_categories": dict(counts),
        "registered_sponsor_exact_text_matches": exact_matches,
        "tickers_with_unresolved_registered_sponsor_text_or_sources": len(companies_with_review),
        "tickers_with_unresolved_registered_sponsor_text_list": sorted(companies_with_review),
        "current_status_differs_from_dated_census_ids": changed_status,
        "current_registry_phase3_not_reported_ids": missing_phase3,
        "source_failures": failed,
        "per_nct_source_comparisons": study_rows,
        "completed_read_only_source_comparison": len(failed) == 0 and version_stable,
        "qualified_pipeline_count": None,
        "current_issuer_rights_verified_count": None,
        "fda_pdufa_verified_count": None,
        "fda_approval_probabilities": None,
        "limitations": (
            "Exact and normalized text comparisons of an original registry "
            "leadSponsor and the dated census's sponsor string. Exact strings "
            "are NOT independent validation of current ticker/CIK control, "
            "licensing, active company programs, listing/market cap, FDA "
            "applications, PDUFA review cycles or approval probabilities. "
            "Name differences may be legitimate corporate/formatting changes."
        ),
    }


def run_comparison(output: Path) -> int:
    rows = source_population(SOURCE_CSV.read_text(encoding="utf-8-sig"))
    groups = [rows[i:i+BATCH_SIZE] for i in range(0, TOTAL_TRIALS, BATCH_SIZE)]
    if len(groups) != 30 or any(len(g) > BATCH_SIZE for g in groups):
        raise ValueError("Unbounded original source research batch request")
    try:
        before = registry_version()
    except Exception:
        before = None
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        batches = list(pool.map(safe_fetch_group, groups))
    observations = [obs for group in batches for obs in group]
    try:
        after = registry_version()
    except Exception:
        after = None
    report = sponsor_research_report(
        rows, observations, before, after, datetime.now(timezone.utc).isoformat(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        "Original registered sponsor texts audited: "
        f"{report['original_registry_source_identities_retrieved']}/741 "
        f"across 130 dated tickers; 30 bounded read-only public GETs."
    )
    print("Source version stable:", report["registry_version_stable"])
    print("Exact registered sponsor string matches:", report["registered_sponsor_exact_text_matches"], "/741")
    for key, value in report["registered_sponsor_text_categories"].items():
        print("Research category:", key, value, "/741")
    print(
        "Tickers with textual anomalies or missing sources:",
        report["tickers_with_unresolved_registered_sponsor_text_or_sources"], "/130"
    )
    print("Registry status differences:", len(report["current_status_differs_from_dated_census_ids"]))
    print("Current registry Phase 3 missing:", len(report["current_registry_phase3_not_reported_ids"]))
    print("Pipeline qualified denominator UNKNOWN. Current issuer rights and FDA/PDUFA NOT VERIFIED.")
    return 0 if report["completed_read_only_source_comparison"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: check_phase3_registered_sponsors_741.py <research-report.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run_comparison(Path(sys.argv[1])))
