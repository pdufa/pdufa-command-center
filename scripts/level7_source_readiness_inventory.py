#!/usr/bin/env python3
"""Level 7 read-only original-receipt / temporal-validation readiness gap inventory.

Consumes only the Level6 dated original ClinicalTrials.gov receipts already
retrieved and pinned in the local engineering workflow. Verifies source hashes,
NCT and phase context; audits the Level7 model validation design. This cannot
train, backtest or calibrate a prediction model. A current registry snapshot
is never accepted as historical outcome-blind evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from level7_model_validation_readiness import audit_bundle, NCT, SHA256, timestamp

MAX_TRIALS = 32
REGISTRY_PREFIX = "https://clinicaltrials.gov/"
ALLOWED_PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4",
                  "UNKNOWN_OR_NOT_APPLICABLE"}
LEAD_STATUS = "CROSS_DISCIPLINARY_SOURCE_GAPS_INVENTORIED_REVIEW_REQUIRED"


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def inventory(snapshot: dict, *, ncts: list[str], freeze_as_of: str,
              source_roster_blob_sha1: str) -> dict:
    """Build auditable gap report, not an approved predictive model."""
    if (not isinstance(snapshot, dict) or snapshot.get("level") != 6
            or not isinstance(ncts, list) or len(ncts) != MAX_TRIALS
            or len(set(ncts)) != MAX_TRIALS
            or any(not isinstance(x, str) or not NCT.fullmatch(x) for x in ncts)
            or not isinstance(freeze_as_of, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", freeze_as_of)
            or not isinstance(source_roster_blob_sha1, str)
            or not re.fullmatch(r"[0-9a-f]{40}", source_roster_blob_sha1)):
        raise ValueError("Unverified exact 32-trial research roster")
    reports = snapshot.get("reports")
    if (not isinstance(reports, list) or len(reports) != MAX_TRIALS
            or snapshot.get("retrieved") != MAX_TRIALS
            or snapshot.get("total") != MAX_TRIALS):
        raise ValueError("Level6 source inventory incomplete")
    by_nct = {}
    for row in reports:
        if not isinstance(row, dict) or row.get("nct") not in ncts:
            raise ValueError("Unexpected Level6 original trial ID")
        nct = row["nct"]
        if nct in by_nct:
            raise ValueError("Duplicate Level6 original trial ID")
        if row.get("status") != LEAD_STATUS:
            raise ValueError("Level6 receipt not available")
        by_nct[nct] = row
    if set(by_nct) != set(ncts):
        raise ValueError("Level6 research roster/receipt mismatch")
    cutoff = datetime.now(timezone.utc).isoformat()
    prospective_rows = []
    context = []
    for nct in ncts:
        row = by_nct[nct]
        sources = row.get("clinical_sources")
        if not isinstance(sources, list) or len(sources) != 1:
            raise ValueError("Expected one original registry receipt per NCT")
        source = sources[0]
        if not isinstance(source, dict) or source.get("verified_receipt") is not True:
            raise ValueError("Unverified original registry source")
        if source.get("domain") != "CLINICAL_REGISTRY_ONLY":
            raise ValueError("Unexpected source domain")
        sha = source.get("source_sha256")
        url = source.get("source_url")
        if not isinstance(sha, str) or not SHA256.fullmatch(sha):
            raise ValueError("Missing original registry content hash")
        if not isinstance(url, str) or not url.startswith(REGISTRY_PREFIX):
            raise ValueError("Unsupported purported original-source URL")
        stamp = source.get("retrieved_at_utc")
        retrieved = timestamp(stamp)
        if retrieved > timestamp(cutoff):
            raise ValueError("Source was retrieved after analysis cutoff")
        if source.get("source_revision") != "CURRENT_STATE_NOT_HISTORICAL_FREEZE":
            raise ValueError("Unexpected historic-freeze representation")
        phase = _obj(row.get("registry_phase_context"))
        bucket = phase.get("phase_bucket")
        if bucket not in ALLOWED_PHASES:
            raise ValueError("Missing validated phase classification")
        if source.get("independently_reviewed") is not False:
            raise ValueError("Source independently adjudicated flag not trusted")
        if row.get("clinical_preclinical_regulatory_integrated") is not False:
            raise ValueError("Level6 scientific acceptance falsely asserted")
        prospective_rows.append({
            "nct": nct,
            "mode": "FUTURE_PROSPECTIVE",
            "prediction_cutoff_utc": cutoff,
            "evidence_sources": [{
                "trial_nct": nct, "url": url, "sha256": sha,
                "phase_at_cutoff": bucket,
                "retrieved_at_utc": stamp,
                # The registry snapshot retrieval time is NOT a verified first
                # publication time. Without a versioned publication record,
                # eligibility for a predictive model remains blocked.
                "publicly_available_at_utc": None,
                "source_revision": "CURRENT_STATE_NOT_HISTORICAL_FREEZE",
            }],
        })
        context.append({
            "nct": nct, "phase_bucket": bucket,
            "registry_current_state_not_historical_freeze": True,
            "publication_date_independently_verified": False,
            "fda_application_identity_verified": False,
            "actual_outcome_visible": False,
            "not_yet_expected_phase_data_is_not_a_failure": True,
        })
    audited = audit_bundle({"inputs": prospective_rows, "plan": {}})
    if audited["input_receipts_gate_passed"] != 0:
        raise ValueError("Unverified registry publication time marked as predictive evidence")
    if audited["ready_for_independent_review"] or audited["model_trained"]:
        raise ValueError("Unapproved model validation or training claim")
    return {
        "level": 7,
        "status": "MODEL_VALIDATION_EVIDENCE_GAPS_INVENTORIED_NOT_PREDICTIONS",
        "snapshot_as_of": freeze_as_of,
        "source_roster_git_blob_sha1": source_roster_blob_sha1,
        "total": MAX_TRIALS,
        "original_registry_receipts_audited": MAX_TRIALS,
        "exact_nct_identity_matched": MAX_TRIALS,
        "phase_buckets_reported": len(context),
        "phase_unknown_or_not_applicable_count": sum(
            row["phase_bucket"] == "UNKNOWN_OR_NOT_APPLICABLE" for row in context),
        "source_publication_dates_independently_verified": 0,
        "historical_pre_cutoff_source_freezes_verified": 0,
        "outcome_blind_historical_validations_performed": 0,
        "model_validation_plan_approved": False,
        "calibration_evidence_verified": False,
        "predictive_model_trained": False,
        "approval_probabilities_generated": False,
        "scientific_level_complete": False,
        "current_canonical_focus_verified": False,
        "independently_reviewed": False,
        "plan_gap_codes": audited["plan"]["review_leads"],
        "case_reports": audited["reports"],
        "phase_context": context,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--level6", required=True, type=Path)
    p.add_argument("--roster", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    result = inventory(json.loads(args.level6.read_text(encoding="utf-8")),
                       ncts=[x["nct"] for x in roster["records"]],
                       freeze_as_of=roster["asOf"],
                       source_roster_blob_sha1=roster["source_git_blob_sha1"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"level": 7, "retrieved": result["original_registry_receipts_audited"],
                      "fda_predictions": False, "scientific_level_complete": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
