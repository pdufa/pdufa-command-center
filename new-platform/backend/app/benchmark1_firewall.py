"""Benchmark 1 historical evidence firewall.

This module deliberately does NOT predict an FDA outcome. It enforces the
predecision evidence cutoff and makes an auditable frozen input manifest.
Outcome-side data must never be passed into the prediction builder.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json

CUTOFF = datetime.fromisoformat("2024-03-13T23:59:59-04:00")
DECISIONS = {"PASS", "CRL", "EXTENSION", "ABSTAIN"}
OUTCOME_ONLY_DOMAINS = ("accessdata.fda.gov",)
FORBIDDEN_TERMS = (
    "2024/217785orig1s000", "fda approves first treatment for patients with liver scarring",
)


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must have timezone")
    return parsed.astimezone(timezone.utc)


def validate_source(source: dict) -> dict:
    """Fail closed: no undated or retrospective evidence."""
    required = ("source_url", "published_at", "retrieved_at", "sha256", "text")
    if any(not source.get(key) for key in required):
        raise ValueError("Missing source provenance")
    if _time(source["published_at"]) > CUTOFF.astimezone(timezone.utc):
        raise ValueError("Post-cutoff publication")
    if _time(source["retrieved_at"]) < _time(source["published_at"]):
        raise ValueError("Retrieval precedes publication")
    url = source["source_url"].lower()
    if any(term in (url + " " + source["text"].lower()) for term in FORBIDDEN_TERMS):
        raise ValueError("Outcome-side material detected")
    if not str(source["sha256"]).startswith("sha256:"):
        raise ValueError("Missing SHA-256 prefix")
    actual = sha256(source["text"].encode("utf-8")).hexdigest()
    if source["sha256"] != "sha256:" + actual:
        raise ValueError("Evidence text hash mismatch")
    return source


def freeze_input_manifest(sources: list[dict], *, rules_version: str) -> dict:
    if not rules_version or not sources:
        raise ValueError("Rules version and pre-cutoff evidence are required")
    verified = [validate_source(s) for s in sources]
    urls = [s["source_url"] for s in verified]
    if len(urls) != len(set(urls)):
        raise ValueError("Duplicate evidence URL")
    payload = {"benchmark": "B1_REZDIFRA", "cutoff": CUTOFF.isoformat(),
               "rules_version": rules_version, "sources": sorted(verified, key=lambda s: s["source_url"])}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return {"manifest": payload, "sha256": sha256(canonical.encode()).hexdigest()}


def freeze_prediction(decision: str, manifest_sha256: str, assessments: list[dict],
                      *, rules_version: str) -> dict:
    if decision not in DECISIONS:
        raise ValueError("Invalid regulatory decision")
    if len(assessments) != 40 or {a.get("number") for a in assessments} != set(range(1, 41)):
        raise ValueError("Exactly 40 numbered scientific assessments required")
    if any(not a.get("evidence_refs") or not a.get("reason") for a in assessments):
        raise ValueError("Assessments require evidence and reasons")
    if len(manifest_sha256) != 64 or not rules_version:
        raise ValueError("Missing manifest hash or rules version")
    payload = {"benchmark": "B1_REZDIFRA", "decision": decision,
               "manifest_sha256": manifest_sha256, "rules_version": rules_version,
               "assessments": assessments}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"prediction": payload, "sha256": digest}
