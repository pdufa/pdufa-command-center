"""Offline FDA source acquisition readiness report with actionable per-case blockers.

This module never downloads data, promotes outcomes or asserts source authenticity.
"""
import argparse
import json
from pathlib import Path

from research.official_acquisition_manifest import build_acquisition_manifest
from research.official_locator_operator_queue import build_operator_queue

PRIORITY_DOCUMENTS = (
    "APPLICATION_ACTION_DATASET",
    "APPROVAL_LETTER",
    "COMPLETE_RESPONSE_LETTER",
    "ORIGINAL_TARGET_DATE",
    "FORMAL_TARGET_REVISION",
    "MULTIDISCIPLINARY_REVIEW",
    "TRIAL_HISTORICAL_RECORD",
    "TRIAL_CURRENT_RECORD",
)


def build_acquisition_next_actions():
    manifest = build_acquisition_manifest()
    queue = build_operator_queue()
    by_case = {}
    for case in manifest["cases"]:
        rows = [row for row in queue if row["case_id"] == case["record_id"]]
        rows.sort(key=lambda row: (
            PRIORITY_DOCUMENTS.index(row["family"])
            if row["family"] in PRIORITY_DOCUMENTS else len(PRIORITY_DOCUMENTS),
            row["priority"], row["document_id"]))
        by_case[case["record_id"]] = {
            "application_id": case["application_id"],
            "claimed_cycle": case["claimed_review_cycle_id"],
            "case_evidence_cutoff": case["evidence_cutoff"],
            "required_actions": [{
                "document_id": row["document_id"],
                "family": row["family"],
                "source_lead": row["source_lead"],
                "reason": row["reason"],
                "next_action": row["operator_next_action"],
                "requires_authorized_original_bytes": True,
                "requires_independent_review": True,
            } for row in rows],
            "ready_for_independent_adjudication": False,
            "eligible_for_backtesting": False,
        }
    return {
        "schema_version": "official-acquisition-next-actions-v1",
        "case_count": len(by_case),
        "cases": by_case,
        "external_operator_required": True,
        "official_originals_acquired_by_this_report": 0,
        "independently_verified_decisions": 0,
        "prediction_readiness": "NOT_READY",
        "prediction_action": "ABSTAIN",
        "research_only": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(build_acquisition_next_actions(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
