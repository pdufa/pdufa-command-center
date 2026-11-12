#!/usr/bin/env python3
"""Level 5 — independent contradictory-evidence *leads* inventory.

Read-only original-source triage. Records exact registry source receipts and
candidate inconsistency/limitation questions; it does NOT conclude that an FDA
application is weak, that a trial failed, or that a medical scientific level
has passed. Independent negative finding and multi-source corroboration remain
unverified until separate cited primary sources are reviewed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from fetch_focus_registry_evidence import retrieve
from level4_scientific_evidence import summarize as level4_inventory, NCT, _measure

MAX_BATCH = 32
KNOWN_STATUSES = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}

def obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}

def entries(value: Any) -> list[dict]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []

def collect(record: dict, receipt: dict, *, historical_cutoff: str | None = None) -> dict:
    """Build review questions, not scientific/clinical conclusions.

    The validated Level-4 source receipt is reused without inventing a
    second original source or pretending current state is historical.
    """
    prior = level4_inventory(record, receipt, as_of=historical_cutoff)
    protocol = obj(record.get("protocolSection"))
    status = obj(protocol.get("statusModule"))
    design = obj(protocol.get("designModule"))
    design_info = obj(design.get("designInfo"))
    registered = entries(obj(protocol.get("outcomesModule")).get("primaryOutcomes"))
    results = obj(record.get("resultsSection"))
    posted = [x for x in entries(obj(results.get("outcomeMeasuresModule"))
              .get("outcomeMeasures")) if x.get("type") == "PRIMARY"]

    registered_tokens = {k for row in registered if all(k := _measure(row))}
    posted_tokens = {k for row in posted if all(k := _measure(row))}
    # In fact _measure may not exist for records without a time frame;
    # these fields are *search leads*, not endpoint discordance proofs.
    candidate_missing_registered = len(registered_tokens - posted_tokens)
    candidate_unmatched_posted = len(posted_tokens - registered_tokens)

    flags: list[dict] = []
    if registered and posted and candidate_missing_registered:
        flags.append({
            "flag": "REGISTERED_PRIMARY_ENDPOINT_WITHOUT_EXACT_TEXT_POSTED_MATCH",
            "count": candidate_missing_registered,
            "interpretation": "TEXT_COMPARISON_ONLY_NOT_CONFIRMED_DISCORDANCE",
        })
    if registered and posted and candidate_unmatched_posted:
        flags.append({
            "flag": "POSTED_PRIMARY_ENDPOINT_WITHOUT_EXACT_TEXT_REGISTERED_MATCH",
            "count": candidate_unmatched_posted,
            "interpretation": "TEXT_COMPARISON_ONLY_NOT_CONFIRMED_DISCORDANCE",
        })
    trial_status = status.get("overallStatus")
    if trial_status in KNOWN_STATUSES:
        flags.append({
            "flag": "REGISTRY_OVERALL_STATUS_REQUIRES_CONTEXT",
            "observed_status": trial_status,
            "interpretation": "NOT_PROOF_OF_DRUG_FAILURE_OR_REGULATORY_OUTCOME",
        })
    allocation = obj(design_info).get("allocation")
    if allocation in ("NON_RANDOMIZED", "NA"):
        flags.append({
            "flag": "TRIAL_DESIGN_LIMITATION_REVIEW_LEAD",
            "allocation": allocation,
            "interpretation": "LIMITATION_NOT_ADJUDICATED",
        })
    if not registered:
        flags.append({"flag": "REGISTERED_PRIMARY_OUTCOME_ABSENT",
                      "interpretation": "SOURCE_GAP_NOT_NEGATIVE_FINDING"})
    if not posted:
        flags.append({"flag": "POSTED_PRIMARY_RESULTS_ABSENT",
                      "interpretation": "SOURCE_GAP_NOT_NEGATIVE_FINDING"})

    gap = [
        "INDEPENDENT_NEGATIVE_FINDINGS_WITH_ORIGINAL_SOURCE_CITATIONS",
        "INDEPENDENT_CONTRADICTORY_SOURCES_BEYOND_CURRENT_REGISTRY",
        "QUALIFIED_REVIEW_OF_TRIAL_LIMITATIONS_AND_AMENDMENTS",
        "EXACT_APPLICATION_AND_REVIEW_CYCLE_LINKAGE",
        "TRIAL_STATISTICAL_ANALYSIS_PLAN_AND_PRESPECIFICATION_TIMING",
        "PRIMARY_SOURCE_CONCORDANCE_AND_CONFLICT_ADJUDICATION",
        "INDEPENDENT_SCIENTIFIC_AND_CODE_REVIEW",
    ]
    return {
        "level": 5,
        "nct": prior["nct"],
        "status": "CRITICAL_CHALLENGE_LEADS_COLLECTED_REVIEW_REQUIRED",
        "source": prior["source"],
        "prior_level4_source_inventory": prior["observed_registry_fields"],
        "observed_original_source": {
            "registry_overall_status": trial_status,
            "registration_primary_endpoint_count": len(registered),
            "registry_posted_primary_outcome_count": len(posted),
            "registry_allocation": allocation,
            "registry_has_results": bool(results),
            "registry_endpoint_textual_mismatch_candidates":
                candidate_missing_registered + candidate_unmatched_posted,
        },
        "candidate_challenges": flags,
        "missing_or_unverified": gap,
        "negative_evidence_adjudicated": False,
        "contradiction_independently_verified": False,
        "study_limitations_independently_adjudicated": False,
        "source_facts_independently_verified": False,
        "scientific_stage_complete": False,
        "independent_review": "REQUIRED",
        "historical_blinding": "CURRENT_REGISTRY_NOT_AS_OF_CUTOFF",
        "fda_prediction": None,
        "approval_probability": None,
        "clinical_score": None,
        "interpretation_notes": [
            "No adverse or negative trial finding is inferred from missing results.",
            "Mismatch of registry endpoint text is not proof of clinical contradiction.",
            "A registry record cannot substitute for independent FDA/sponsor primary sources.",
            "Current registry source must not enter outcome-blind historical assessment.",
        ],
    }

def process_ncts(ncts: list[str], *, fetcher=retrieve) -> dict:
    if not isinstance(ncts, list) or not 1 <= len(ncts) <= MAX_BATCH:
        raise ValueError("Expected 1-32 exact NCT identifiers")
    if any(not isinstance(x, str) or not NCT.fullmatch(x) for x in ncts):
        raise ValueError("Invalid exact ASCII NCT identifier")
    if len(set(ncts)) != len(ncts):
        raise ValueError("Duplicate NCT identifier")
    reports: list[dict] = []
    for nct in ncts:
        try:
            record, receipt = fetcher(nct)
            reports.append(collect(record, receipt))
        except (ValueError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            reports.append({
                "level": 5, "nct": nct,
                "status": "ORIGINAL_SOURCE_UNAVAILABLE_OR_INVALID",
                "reason": type(exc).__name__, "scientific_stage_complete": False,
                "independent_review": "REQUIRED",
                "fda_prediction": None,
            })
    return {
        "level": 5,
        "status": "REVIEWABLE_NEGATIVE_EVIDENCE_CHALLENGE_INVENTORY_NOT_SCIENTIFIC_SIGNOFF",
        "total": len(ncts),
        "retrieved": sum(
            row.get("status") == "CRITICAL_CHALLENGE_LEADS_COLLECTED_REVIEW_REQUIRED"
            for row in reports
        ),
        "reports": reports,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_level_complete": False,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nct", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = process_ncts(args.nct)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": report["total"], "retrieved": report["retrieved"],
                      "scientific_level_complete": False}))
    return 0 if report["total"] == report["retrieved"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
