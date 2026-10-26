#!/usr/bin/env python3
"""Bounded and reproducible 64-study public ClinicalTrials.gov research expansion.

A breadth sampler selects eight dated registry status groups and as many
distinct company tickers as possible from the original 741-row census.
The source script already validates the 741-row population and makes
strict read-only exact-NCT requests. This adds COVERAGE, not qualification.

No writes to production, no authentication, no PDUFA/approval predictions,
no scanning schedule, and no unbounded crawling.
"""
from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from check_phase3_original_registry_pilot import (
    SOURCE_CSV, STATUSES, dated_census_sample, _fetch_catching,
)

SAMPLE_LIMIT = 64
CENSUS_COUNT = 741
CENSUS_TICKERS = 130


def select_64_original_studies(csv_text: str) -> list[dict[str, str]]:
    """Validate entire original census, select broad ticker/status coverage."""
    seeds = dated_census_sample(csv_text)
    rows = list(csv.DictReader(csv_text.splitlines()))
    if len(rows) != CENSUS_COUNT or len(seeds) != len(STATUSES):
        raise ValueError("Original 741-study census could not be reconciled")
    selected = list(seeds)
    ids = {item["nct_id"] for item in seeds}
    tickers = {item["ticker"] for item in seeds}

    # Round robin by registry status so rare groups aren't crowded out by
    # the many completed trials; prioritize a different listed ticker.
    while len(selected) < SAMPLE_LIMIT:
        added = False
        for status in STATUSES:
            if len(selected) >= SAMPLE_LIMIT:
                break
            item = next(
                (row for row in rows if row["status"] == status
                 and row["nct_id"] not in ids and row["ticker"] not in tickers),
                None,
            )
            if item is None:
                continue
            selected.append(item)
            ids.add(item["nct_id"])
            tickers.add(item["ticker"])
            added = True
        if added:
            continue

        # Remaining sample slots may include multiple studies of a company;
        # this never changes unique-trial or qualified Pipeline totals.
        for status in STATUSES:
            if len(selected) >= SAMPLE_LIMIT:
                break
            item = next(
                (row for row in rows
                 if row["status"] == status and row["nct_id"] not in ids),
                None,
            )
            if item is None:
                continue
            selected.append(item)
            ids.add(item["nct_id"])
            tickers.add(item["ticker"])
            added = True
        if not added:
            break

    if (len(selected) != SAMPLE_LIMIT or len(ids) != SAMPLE_LIMIT
        or len(tickers) < 50
        or not set(STATUSES).issubset({item["status"] for item in selected})):
        raise ValueError("64-study status/ticker diversity requirement not met")
    return selected


def summarize_original_source_batch(
    sample: list[dict[str, str]], results: list[dict[str, object]], checked_at: str,
) -> dict[str, object]:
    """Require one disposition per requested exact NCT; never infer FDA outcomes."""
    if len(sample) != SAMPLE_LIMIT or len(results) != SAMPLE_LIMIT:
        raise ValueError("Original registry batch incomplete")
    expected_ids = [item["nct_id"] for item in sample]
    if len(set(expected_ids)) != SAMPLE_LIMIT or not all(
        item.get("nct_id") == nct for item, nct in zip(results, expected_ids)
    ):
        raise ValueError("Original registry batch NCT/source association mismatch")

    ok: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for source, result in zip(sample, results):
        if "error" in result:
            if not isinstance(result["error"], str) or len(result["error"]) > 100:
                raise ValueError("Unbounded external error payload")
            errors.append({"nct_id": source["nct_id"], "error_type": result["error"]})
            continue
        if (result.get("qualified_pipeline") is not None
            or result.get("fda_approval_probability") is not None
            or result.get("verified_us_fda_pdufa") is not False
            or result.get("verified_current_commercial_development_rights") is not False
            or result.get("census_status") != source["status"]
            or result.get("census_ticker") != source["ticker"]
            or result.get("source") !=
                "https://clinicaltrials.gov/api/v2/studies/" + source["nct_id"]
            or not isinstance(result.get("source_sha256"), str)
            or len(result["source_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in result["source_sha256"])
            or not isinstance(result.get("fetched_at_utc"), str)
            or not result.get("fetched_at_utc")):
            raise ValueError("Original source result cannot be promoted or is ungrounded")
        ok.append(result)

    mismatch = [r["nct_id"] for r in ok if r["status_matches_dated_census"] is not True]
    phase = [r["nct_id"] for r in ok if r["phase3_in_current_registry"] is not True]
    return {
        "report_type": "UNVERIFIED_ORIGINAL_REGISTRY_BREADTH_RESEARCH",
        "census_generated_at_utc": "2026-10-26T12:21:15.972309+00:00",
        "checked_at_utc": checked_at,
        "census_total": CENSUS_COUNT,
        "census_unique_tickers": CENSUS_TICKERS,
        "selected_status_groups": list(STATUSES),
        "selected_nct_count": SAMPLE_LIMIT,
        "selected_distinct_tickers": len({r["ticker"] for r in sample}),
        "selected_original_nct_ids": expected_ids,
        "retrieved_exact_identity_count": len(ok),
        "failed_original_source_count": len(errors),
        "status_differences_from_dated_census": mismatch,
        "no_longer_phase3_in_source": phase,
        "source_errors": errors,
        "source_records": ok,
        "all_original_sources_retrieved": len(ok) == SAMPLE_LIMIT and not errors,
        "verified_fda_pdufa_total": None,
        "qualified_pipeline_total": None,
        "calibrated_approval_probabilities": None,
        "claim_limits": (
            "Public registry response bytes/ID only. Not a verified company "
            "program, drug rights, FDA PDUFA target, or Pipeline membership. "
            "Remaining 677 census records are NOT verified by this sample."
        ),
    }


def run_64_source_check(output: Path) -> int:
    sample = select_64_original_studies(SOURCE_CSV.read_text(encoding="utf-8-sig"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        raw_results = list(pool.map(_fetch_catching, sample))
    summary = summarize_original_source_batch(
        sample, raw_results, datetime.now(timezone.utc).isoformat(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        f"Original registry source coverage: {summary['retrieved_exact_identity_count']}"
        f"/{SAMPLE_LIMIT} fetched; {summary['selected_distinct_tickers']} distinct"
        " selected tickers; 741 total dated studies remain unqualified."
    )
    print(
        f"Historical status mismatches: {len(summary['status_differences_from_dated_census'])}; "
        f"registry Phase 3 absence: {len(summary['no_longer_phase3_in_source'])}; "
        f"source fetch failures: {summary['failed_original_source_count']}."
    )
    for nct in summary["status_differences_from_dated_census"]:
        print(f"NEEDS_REVIEW: registry status changed for {nct}")
    for nct in summary["no_longer_phase3_in_source"]:
        print(f"NEEDS_REVIEW: Phase 3 not established by current source for {nct}")
    for entry in summary["source_errors"]:
        print(f"UNVERIFIED: {entry['nct_id']} {entry['error_type']}")
    print("Pipeline qualified total UNKNOWN. FDA PDUFA and approval probabilities NOT VALIDATED.")
    return 0 if summary["all_original_sources_retrieved"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: check_phase3_64_original_sources.py <bounded-json-report>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run_64_source_check(Path(sys.argv[1])))
