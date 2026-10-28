"""Research-only append-only, hash-chained prospective prediction ledger.

Hash chaining detects accidental edits when the chain head is anchored
outside this file. It is NOT tamper-proof without external anchoring.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


OUTCOMES = frozenset({"PASS", "CRL", "EXTENSION", "ABSTAIN"})


def _utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("UTC-aware timestamp required")
    return dt.astimezone(timezone.utc)


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def append_prediction(
    path: str | Path, *, trial_id: str, prediction: str,
    cutoff_utc: str, recorded_at_utc: str, model_commit: str,
    evidence_manifest_sha256: str,
) -> str:
    if prediction not in OUTCOMES:
        raise ValueError("Invalid prediction")
    if not trial_id.strip() or not model_commit.strip():
        raise ValueError("Missing trial or model identity")
    if len(evidence_manifest_sha256) != 64 or any(
        ch not in "0123456789abcdef" for ch in evidence_manifest_sha256
    ):
        raise ValueError("Invalid evidence manifest SHA-256")
    if _utc(recorded_at_utc) > _utc(cutoff_utc):
        raise ValueError("Prediction recorded after cutoff")
    path = Path(path)
    previous = "0" * 64
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if item["previous_hash"] != previous:
                raise ValueError("Broken ledger chain")
            digest = item.pop("entry_hash")
            if sha256(_canonical(item)).hexdigest() != digest:
                raise ValueError("Modified ledger entry")
            previous = digest
    event = {
        "trial_id": trial_id, "prediction": prediction,
        "cutoff_utc": cutoff_utc, "recorded_at_utc": recorded_at_utc,
        "model_commit": model_commit,
        "evidence_manifest_sha256": evidence_manifest_sha256,
        "previous_hash": previous,
    }
    digest = sha256(_canonical(event)).hexdigest()
    event["entry_hash"] = digest
    with path.open("a", encoding="utf-8") as stream:
        stream.write(_canonical(event).decode("utf-8") + "\n")
    return digest
