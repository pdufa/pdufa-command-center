"""Offline cohort roster audit. No fetching, storage writes or model clearance."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from app.hop_cohort_manifest import audit_cohort_manifest
from app.hop_outcomes_import import _date


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object field")
        result[key] = value
    return result


def audit_file(path: str | Path, *, as_of: date) -> dict:
    """Bind the review to exact input bytes, not to a purported FDA source hash."""
    raw = Path(path).read_bytes()
    payload = json.loads(raw, object_pairs_hook=_unique_object)
    if (not isinstance(payload, dict)
            or set(payload) != {"schema_version", "manifest", "expected_members", "observed_members"}
            or type(payload["schema_version"]) is not int or payload["schema_version"] != 1
            or not isinstance(payload["manifest"], dict)
            or not isinstance(payload["expected_members"], list)
            or not isinstance(payload["observed_members"], list)):
        raise ValueError("schema_version 1, manifest and both exact member arrays required")
    report = audit_cohort_manifest(
        payload["manifest"], expected_members=payload["expected_members"],
        observed_members=payload["observed_members"], as_of=as_of,
    )
    report["input_metadata"] = {
        "schema_version": 1,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "hash_scope": "EXACT_RESEARCH_INPUT_BYTES_NOT_FDA_DOCUMENT_BYTES",
        "audit_as_of": as_of.isoformat(),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a research-only FDA cohort roster")
    parser.add_argument("input_json", help="Version 1 cohort metadata with both member arrays")
    parser.add_argument("--as-of", required=True, type=_date,
                        help="Fixed audit snapshot YYYY-MM-DD; never proof of publication")
    args = parser.parse_args(argv)
    try:
        report = audit_file(args.input_json, as_of=args.as_of)
    except (OSError, ValueError, UnicodeError):
        parser.error("invalid cohort input: inspect schema, repeated keys and local file access")
    print(json.dumps(report, sort_keys=True, indent=2))
    # A reconciled metadata roster still lacks independent source verification.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
