#!/usr/bin/env python3
"""Reproducible, UNSIGNED research handoff bundle for 32 FOCUS trial review packets.

This only proves that report metadata matches a fixed local set of committed
snapshots. SHA-256 hashes and matching packet bytes do NOT prove original
source authenticity, qualified reviewer identity, scientific adjudication,
predictive validity or the suitability of the packet for a blind backtest.

No external service access, data writes, secrets, review events or approvals.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "coverage": "reports/scientific-levels1-6/scientific-coverage-20261114.json",
    "focusRoster": "new-platform/frontend/data/p3PostDataActive.json",
    "candidateApplications": "new-platform/backend/app/data/focus_application_snapshot.json",
    "orca2Chronology": "reports/scientific-levels1-6/orca2-statistical-chronology-20261114.json",
}
MAX_JSON_BYTES = 5_000_000
KIND = "FOCUS_LEVEL16_UNSIGNED_RESEARCH_REVIEW_BUNDLE"
STATUS = "BYTE_CONSISTENCY_ONLY_NOT_EVIDENCE_AUTHENTICATION"
KEYS = frozenset(("schemaVersion", "kind", "status", "sourceSha256",
                  "packetSha256", "packet"))


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _read_snapshot(root, relative):
    current = Path(root)
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise ValueError("Snapshot must not be a symlink")
    if not current.is_file():
        raise ValueError(f"Missing committed research snapshot: {relative}")
    if current.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("Research snapshot exceeds bounded size")
    raw = current.read_bytes()
    if not raw or len(raw) > MAX_JSON_BYTES:
        raise ValueError("Research snapshot is empty or oversized")
    return raw


def _module(name):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_bundle(root=ROOT):
    """Create a packet with verifiable metadata digests, not approval claims."""
    objects, hashes = {}, {}
    for key, path in SOURCES.items():
        raw = _read_snapshot(root, path)
        objects[key] = json.loads(raw)
        hashes[key] = _sha256(raw)
    statistical = _module("level16_orca2_statistical_timeline")
    handoff = _module("level16_review_handoff")
    packet = handoff.build(
        objects["coverage"], objects["focusRoster"],
        objects["candidateApplications"],
        statistical.assess(objects["orca2Chronology"]),
    )
    if (packet.get("focusTrialCount") != 32 or packet.get("reviewPacketsPrepared") != 32
            or packet.get("independentlyAuthenticatedSources") != 0
            or packet.get("independentlyAdjudicatedLevels") != 0
            or packet.get("genuineQualifiedReviewersActivated") != 0
            or packet.get("actualApprovalProbabilities") != 0
            or packet.get("stagingActivated") is not False):
        raise ValueError("Unsigned research handoff cannot certify clinical review")
    return {
        "schemaVersion": 1,
        "kind": KIND,
        "status": STATUS,
        "sourceSha256": hashes,
        "packetSha256": _sha256(_json_bytes(packet)),
        "packet": packet,
    }


def verify_bundle(bundle, root=ROOT):
    """Verify equality against local frozen source snapshots, fail closed."""
    if (not isinstance(bundle, dict) or set(bundle) != KEYS
            or type(bundle["schemaVersion"]) is not int
            or bundle["schemaVersion"] != 1
            or bundle["kind"] != KIND or bundle["status"] != STATUS
            or not isinstance(bundle["sourceSha256"], dict)
            or set(bundle["sourceSha256"]) != set(SOURCES)
            or not isinstance(bundle["packet"], dict)):
        raise ValueError("Invalid or promoted review handoff bundle")
    expected = build_bundle(root)
    for key in SOURCES:
        digest = bundle["sourceSha256"][key]
        if not isinstance(digest, str) or not hmac.compare_digest(
                digest, expected["sourceSha256"][key]):
            raise ValueError(f"Local source snapshot changed or hash forged: {key}")
    digest = bundle["packetSha256"]
    if not isinstance(digest, str) or not hmac.compare_digest(
            digest, expected["packetSha256"]):
        raise ValueError("Review packet no longer matches the frozen sources")
    if not hmac.compare_digest(_json_bytes(bundle["packet"]),
                               _json_bytes(expected["packet"])):
        raise ValueError("Review packet contents differ from the validated handoff")
    return {
        "status": "LOCAL_RESEARCH_SNAPSHOT_AND_PACKET_BYTES_MATCH_ONLY",
        "kind": KIND, "focusTrialCount": 32,
        "independentlyAuthenticatedSources": 0,
        "independentlyAdjudicatedLevels": 0,
        "approvedReviewerCount": 0,
        "fdaPredictionPermitted": False,
        "note": "Unsigned local byte equality is NOT provenance or scientific review.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path,
                        help="Verify an exported bundle against the current checkout")
    args = parser.parse_args()
    if args.verify:
        if args.verify.stat().st_size > MAX_JSON_BYTES:
            parser.error("Review bundle is oversized")
        bundle = json.loads(args.verify.read_text(encoding="utf-8"))
        print(json.dumps(verify_bundle(bundle), indent=2))
    else:
        print(json.dumps(build_bundle(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
