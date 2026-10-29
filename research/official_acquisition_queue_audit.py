"""Validate and summarize the six-case official-source acquisition queue.

Read-only: no network, imports, evidence promotion or prediction activation.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from research.official_acquisition_manifest import build_acquisition_manifest
from research.official_locator_operator_queue import build_operator_queue


def build_queue_audit():
    manifest = build_acquisition_manifest()
    queue = build_operator_queue()
    expected = {
        doc["document_id"]
        for case in manifest["cases"]
        for doc in case["documents"]
    }
    actual = [row["document_id"] for row in queue]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("acquisition queue does not cover each exact document once")
    per_case = {}
    for case in manifest["cases"]:
        rows = [row for row in queue if row["case_id"] == case["record_id"]]
        per_case[case["record_id"]] = {
            "application_id": case["application_id"],
            "requirements": len(rows),
            "known_leads": sum(row["priority"] == 1 for row in rows),
            "derived_leads": sum(row["priority"] == 2 for row in rows),
            "unresolved_locators": sum(row["priority"] == 3 for row in rows),
        }
    return {
        "schema_version": "official-acquisition-queue-audit-v1",
        "case_count": len(per_case),
        "requirement_count": len(queue),
        "priority_counts": {
            "known": sum(row["priority"] == 1 for row in queue),
            "derived": sum(row["priority"] == 2 for row in queue),
            "unresolved": sum(row["priority"] == 3 for row in queue),
        },
        "family_counts": dict(sorted(Counter(row["family"] for row in queue).items())),
        "cases": per_case,
        "source_documents_acquired": 0,
        "independently_verified_decisions": 0,
        "prediction_readiness": "NOT_READY",
        "prediction_action": "ABSTAIN",
        "research_only": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_queue_audit()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
