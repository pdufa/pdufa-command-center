#!/usr/bin/env python3
"""Fail-closed 100-case blind-backtest packet gate. No network or model invocation.

Run ONLY in a newly initialized, outcome-isolated checkout containing this
script, the candidate manifest and separately prepared pre-cutoff evidence
packets. The outcome-bearing repository is NOT an isolated environment.
"""
import argparse
import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path

MANIFEST_COLUMNS = [
    "case_id", "archive_position", "ticker", "drug_or_event",
    "application_identity_status", "precutoff_evidence_status",
    "blind_prediction", "prediction_lock_status",
]
PACKET_FIELDS = {
    "case_id", "application_id", "indication", "original_pdufa_goal_date",
    "evidence_cutoff", "sources", "clinical_summary", "safety_summary",
    "regulatory_summary", "cmc_summary",
}
FORBIDDEN = re.compile(
    r"(?i)(actual[_ -]?outcome|fda[_ -]?decision|archive[_ -]?action[_ -]?date|"
    r"approval[_ -]?letter|complete response letter|\bCRL issued\b|"
    r"approved on|post[_ -]?decision|decision[_ -]?date)"
)

def fail(message):
    raise SystemExit("BLOCKED: " + message)

def validate(root: Path, expected_count: int = 100):
    if expected_count < 1:
        fail("expected count must be positive")
    manifest = root / "manifest.csv"
    if not manifest.is_file():
        fail("manifest.csv missing")
    with manifest.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != MANIFEST_COLUMNS:
            fail("manifest schema changed")
        rows = list(reader)
    if len(rows) != expected_count or len({r["case_id"] for r in rows}) != expected_count:
        fail(f"expected {expected_count} unique candidate IDs")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", r["case_id"] or "") for r in rows):
        fail("invalid or unsafe case ID")
    if any(r["blind_prediction"] != "NOT_ISSUED" or
           r["prediction_lock_status"] != "NOT_LOCKED" for r in rows):
        fail("manifest includes previously issued predictions or locks")
    if any(r["application_identity_status"] != "VERIFIED" or
           r["precutoff_evidence_status"] != "VERIFIED" for r in rows):
        fail("application identity or pre-cutoff evidence not verified for all candidates")
    evidence_dir = root / "evidence"
    if not evidence_dir.is_dir():
        fail("evidence/ missing")
    packet_hashes = []
    for row in rows:
        path = evidence_dir / (row["case_id"] + ".json")
        if not path.is_file():
            fail("missing evidence packet for " + row["case_id"])
        data = path.read_bytes()
        if FORBIDDEN.search(data.decode("utf-8")):
            fail("possible outcome leakage in " + path.name)
        try:
            packet = json.loads(data)
        except ValueError:
            fail("invalid JSON: " + path.name)
        if set(packet) != PACKET_FIELDS or packet["case_id"] != row["case_id"]:
            fail("invalid packet schema for " + row["case_id"])
        try:
            cutoff = date.fromisoformat(packet["evidence_cutoff"])
            goal = date.fromisoformat(packet["original_pdufa_goal_date"])
        except (TypeError, ValueError):
            fail("invalid cutoff or PDUFA goal date: " + row["case_id"])
        if cutoff >= goal:
            fail("evidence cutoff must precede PDUFA goal: " + row["case_id"])
        if not packet["application_id"] or not packet["indication"]:
            fail("application identity incomplete: " + row["case_id"])
        if not packet["sources"]:
            fail("no pre-cutoff sources: " + row["case_id"])
        for source in packet["sources"]:
            if set(source) != {"url", "publication_date", "sha256"}:
                fail("invalid source metadata: " + row["case_id"])
            try:
                published = date.fromisoformat(source["publication_date"])
            except (TypeError, ValueError):
                fail("invalid source date: " + row["case_id"])
            if published > cutoff:
                fail("post-cutoff source: " + row["case_id"])
            if not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
                fail("source hash invalid: " + row["case_id"])
        packet_hashes.append((row["case_id"], hashlib.sha256(data).hexdigest()))
    print(json.dumps({"status": "PACKETS_SCHEMA_VALIDATED",
                      "candidate_count": expected_count,
                      "packet_sha256": dict(packet_hashes),
                      "warning": "Does NOT certify reviewer isolation or historical blindness"},
                     indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="outcome-isolated input folder")
    parser.add_argument("--expected-count", type=int, default=100)
    args = parser.parse_args()
    validate(args.root, args.expected_count)
