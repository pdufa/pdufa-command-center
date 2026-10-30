"""Research-only provenance guard for Pipeline export snapshots.

This checks traceability and freshness; it does not authenticate external data,
change production restrictions, or authorize predictions.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json

from research.preliminary_pipeline_batch import triage_pipeline_export


def _aware(value):
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    except ValueError:
        return None


def triage_pipeline_snapshot(snapshot, *, now, max_age_hours=24):
    if not isinstance(snapshot, dict) or set(snapshot) != {
            "source_system", "exported_at", "records", "restriction_snapshot_sha256"}:
        raise ValueError("exact snapshot schema required")
    if snapshot["source_system"] != "PDUFA_PIPELINE":
        raise ValueError("source must be the existing Pipeline")
    stamp = _aware(snapshot["exported_at"])
    current = _aware(now)
    if stamp is None or current is None:
        raise ValueError("timezone-aware export and observation clocks required")
    age = (current - stamp).total_seconds()
    if age < 0 or age > max_age_hours * 3600:
        raise ValueError("stale or future Pipeline snapshot")
    digest = snapshot["restriction_snapshot_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(
            c not in "0123456789abcdef" for c in digest):
        raise ValueError("exact restriction configuration digest required")
    result = triage_pipeline_export(snapshot["records"])
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                           allow_nan=False).encode("utf-8")
    return {
        **result,
        "snapshot_sha256": sha256(canonical).hexdigest(),
        "restriction_snapshot_sha256": digest,
        "source_system": snapshot["source_system"],
        "exported_at": snapshot["exported_at"],
        "restriction_settings_verified": False,
        "prediction_status": "ABSTAIN",
    }
