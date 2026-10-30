"""Generate a dated, fail-closed retrospective provenance checkpoint.

A checkpoint reports evidence gaps; it never promotes 2026 archives into
2025 predictions or silently changes production validation metrics.
"""
import json
from pathlib import Path
from research.fda_original_artifact_inventory import build_original_artifact_inventory
from research.fda_original_prediction_evidence_check import assess_original_prediction_evidence


def build_provenance_checkpoint(archive, reconstruction, evidence_records=None):
    inventory = build_original_artifact_inventory(archive, reconstruction)
    assessment = assess_original_prediction_evidence(inventory, evidence_records or [])
    return {
        "research_only": True,
        "trading_authorized": False,
        "historical_accuracy": None,
        "verified_prospective_predictions": 0,
        "total_priority_cases": len(inventory["cases"]),
        "evidence_records_reviewed": assessment["evidence_records_reviewed"],
        "missing_evidence_events": assessment["missing_evidence_events"],
        "retrospective_archive_hashes": sorted({
            row["retrospective_archive_sha256"] for row in inventory["cases"]
        }),
        "status": "BLOCKED_PENDING_INDEPENDENT_PRE_ACTION_EVIDENCE",
        "cases": assessment["cases"],
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) not in (3, 4):
        raise SystemExit("usage: python -m research.fda_provenance_checkpoint archive.json reconstruction.json [external_evidence.json]")
    archive = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    reconstruction = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    evidence = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")) if len(sys.argv) == 4 else None
    if evidence is not None and not isinstance(evidence, list):
        raise SystemExit("external evidence must be a JSON array")
    print(json.dumps(build_provenance_checkpoint(archive, reconstruction, evidence), indent=2))
