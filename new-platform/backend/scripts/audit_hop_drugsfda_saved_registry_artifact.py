"""Reproduce the saved official FDA-registry source artifact audit, offline only."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.hop_drugsfda_registry_artifact_audit import audit_registry_artifact


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit original NDA/BLA submissions in saved FDA registry artifact"
    )
    parser.add_argument("registry_artifact_zip", type=Path,
                        help="Saved Actions ZIP, not the source FDA ZIP")
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--expected-payload-sha256", required=True,
                        help="Exact SHA256 of archived quarantined JSON payload")
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    report = audit_registry_artifact(
        args.registry_artifact_zip, as_of=args.as_of,
        expected_payload_sha256=args.expected_payload_sha256,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        key: report[key] for key in (
            "status", "approved_registry_application_records",
            "original_nda_bla_submission_entries",
            "distinct_nda_bla_applications_with_original_submission",
            "applications_with_multiple_original_submissions",
            "source_data_warning_counts", "independently_adjudicated_review_cycles",
            "complete_original_nda_bla_denominator_verified",
            "model_eligible_records", "prediction_probability",
        )
    }, indent=2, sort_keys=True))
    # A well-formed source inventory is NOT FDA model-eligible decision data.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
