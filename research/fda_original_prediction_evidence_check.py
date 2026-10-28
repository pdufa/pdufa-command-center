"""Check externally retrieved original prediction evidence without auto-promoting accuracy.

Evidence records are supplied by an independent reviewer; the checker does not
fetch or authenticate external artifacts and cannot authorize trading.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit
import re


def _instant(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except (ValueError, AttributeError, TypeError):
        return None


def assess_original_prediction_evidence(inventory, evidence_records):
    expected = {case["event_key"]: case for case in inventory["cases"]}
    if len(expected) != len(inventory["cases"]):
        raise ValueError("duplicate inventory event")
    seen = set()
    results = []
    for record in evidence_records:
        key = record.get("event_key")
        if key not in expected or key in seen:
            raise ValueError("unknown or duplicate evidence event")
        seen.add(key)
        action = _instant(record.get("fda_action_at"))
        prediction = _instant(record.get("prediction_created_at"))
        cutoff = _instant(record.get("model_frozen_at"))
        required = ("immutable_prediction_uri", "prediction_sha256", "model_sha256",
                    "independent_reviewer", "source_timestamp_provenance")
        complete = all(isinstance(record.get(field), str) and record[field].strip() for field in required)
        uri = record.get("immutable_prediction_uri")
        parsed_uri = urlsplit(uri) if isinstance(uri, str) else None
        # A generic mutable web page is not an immutable prediction artifact.
        github_commit = bool(parsed_uri and parsed_uri.hostname == "github.com" and re.fullmatch(r"/[^/]+/[^/]+/commit/[0-9a-fA-F]{40}", parsed_uri.path))
        immutable_uri_plausible = bool(
            parsed_uri and parsed_uri.scheme == "https" and parsed_uri.hostname
            and not parsed_uri.username and not parsed_uri.password
            and (
                github_commit
            )
        )
        sha_valid = all(len(record.get(field, "")) == 64 and
                        all(ch in "0123456789abcdefABCDEF" for ch in record[field])
                        for field in ("prediction_sha256", "model_sha256"))
        chronology_ok = bool(action and prediction and cutoff and cutoff <= prediction < action)
        results.append({"event_key": key, "artifact_metadata_complete": bool(complete and sha_valid and immutable_uri_plausible),
                        "chronology_consistent": chronology_ok,
                        "independently_verified": False,
                        "status": "REQUIRES_EXTERNAL_AUTHENTICATION_AND_LEAKAGE_AUDIT"
                        if complete and sha_valid and immutable_uri_plausible and chronology_ok else "INSUFFICIENT_OR_NONPROSPECTIVE_EVIDENCE"})
    return {"research_only": True, "trading_authorized": False,
            "verified_prospective_predictions": 0, "evidence_records_reviewed": len(results),
            "missing_evidence_events": sorted(set(expected) - seen), "cases": results}
