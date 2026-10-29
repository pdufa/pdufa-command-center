"""Research-only unresolved official-source locator triage.

Consumes the existing six-case acquisition manifest. This module performs no
network access, authenticates no evidence, and changes no case eligibility.
"""
import argparse
import json
from pathlib import Path

from research.official_acquisition_manifest import build_acquisition_manifest

REASON_BY_FAMILY = {
    "ORIGINAL_TARGET_DATE": "EXACT_ORIGINAL_TARGET_NOTICE_NOT_LOCATED",
    "FORMAL_TARGET_REVISION": "FORMAL_REVISION_DOCUMENT_NOT_LOCATED_OR_NOT_APPLICABLE",
    "MULTIDISCIPLINARY_REVIEW": "EXACT_REVIEW_DOCUMENT_NOT_LOCATED",
    "TRIAL_HISTORICAL_RECORD": "TIME_SPECIFIC_HISTORICAL_SNAPSHOT_NOT_LOCATED",
    "APPROVAL_LETTER": "EXACT_ACTION_LETTER_NOT_LOCATED",
    "COMPLETE_RESPONSE_LETTER": "EXACT_ACTION_LETTER_NOT_LOCATED",
    "APPLICATION_ACTION_DATASET": "EXACT_DATASET_SOURCE_NOT_LOCATED",
    "TRIAL_CURRENT_RECORD": "CURRENT_REGISTRY_LOCATOR_NOT_LOCATED",
}
SEARCH_ROUTE_BY_SOURCE = {
    "fda_document": "FDA application review/letter archive; verify NDA/BLA, indication and exact cycle",
    "trial_history": "ClinicalTrials.gov archived versions; verify NCT ID and historical publication clock",
    "clinical_trials": "ClinicalTrials.gov official registry index; current record is not historical proof",
    "drugs_fda": "FDA Drugs@FDA original application/action bulk data release",
}


def build_locator_triage(manifest=None):
    manifest = build_acquisition_manifest() if manifest is None else manifest
    rows = []
    for case in manifest["cases"]:
        for document in case["documents"]:
            url = document["source_url"]
            family = document["family"]
            if url:
                status = "DERIVED_LEAD_NOT_AUTHENTICATED" if document["locator_status"].startswith("DERIVED_") else "KNOWN_LEAD_NOT_AUTHENTICATED"
                reason = "SOURCE_LEAD_REQUIRES_ORIGINAL_BYTES_AND_CYCLE_REVIEW"
            else:
                status = "UNRESOLVED_LOCATOR"
                reason = REASON_BY_FAMILY.get(family, "OFFICIAL_LOCATOR_NOT_ESTABLISHED")
            rows.append({
                "case_id": case["record_id"],
                "application_id": case["application_id"],
                "claimed_review_cycle_id": case["claimed_review_cycle_id"],
                "document_id": document["document_id"],
                "family": family,
                "locator_status": status,
                "reason": reason,
                "official_source_route": SEARCH_ROUTE_BY_SOURCE.get(document["adapter_source"], "Manual official-source review"),
                "source_lead": url,
                "operator_next_action": ("Locate original official document for exact application and review cycle"
                    if url is None else "Acquire original bytes from authorized official source and verify source identity"),
                "original_bytes_acquired": False,
                "publication_clock_verified": False,
                "independently_verified": False,
            })
    rows.sort(key=lambda row: (row["case_id"], row["document_id"]))
    unresolved = sum(row["locator_status"] == "UNRESOLVED_LOCATOR" for row in rows)
    return {
        "schema_version": "official-locator-triage-v1",
        "case_count": len(manifest["cases"]),
        "requirement_count": len(rows),
        "unresolved_locator_count": unresolved,
        "source_lead_count": len(rows) - unresolved,
        "rows": rows,
        "verified_decisions": 0,
        "prediction_readiness": "NOT_READY",
        "prediction_action": "ABSTAIN",
        "research_only": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_locator_triage()
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
