#!/usr/bin/env python3
"""Outcome-isolated L1 predictor. Install in a NEW clean directory/repository.

No access to the outcome-bearing PDUFA repository is permitted for the runtime.
Requires validated 100-case packets, an explicitly configured external predictor,
and an empty, write-once lock directory. Does not fetch the web or FDA outcomes.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ALLOWED = {"APPROVE", "CRL", "ABSTAIN"}
REQUIRED = {"case_id", "prediction", "confidence", "rationale"}
def die(msg): raise SystemExit("BLOCKED: " + msg)

def run(root, predictor, locks):
    if not predictor or not Path(predictor).is_file():
        die("explicit predictor executable missing")
    if not (root / "manifest.csv").is_file():
        die("input manifest missing")
    # Reuse the strict packet verifier; no outcome-bearing file is read.
    validator = Path(__file__).with_name("validate_2026_l1_blind100_packets.py")
    if not validator.is_file():
        die("strict packet validator missing")
    check = subprocess.run([sys.executable, str(validator), str(root)],
                           capture_output=True, text=True)
    if check.returncode:
        die("evidence validation failed: " + (check.stderr or check.stdout)[-1000:])
    with (root / "manifest.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if locks.exists() and any(locks.iterdir()):
        die("lock directory is not empty; never overwrite existing predictions")
    locks.mkdir(parents=True, exist_ok=True)
    for row in rows:
        case = row["case_id"]
        packet = (root / "evidence" / (case + ".json")).read_bytes()
        # The predictor is an independently configured local executable; it sees
        # only one verified pre-cutoff packet on stdin, never the outcome archive.
        env = {"PATH": os.environ.get("PATH", ""),
               "HOME": str(root.resolve()),
               "LANG": "C.UTF-8"}
        proc = subprocess.run([str(Path(predictor).resolve())],
                              input=packet, capture_output=True, timeout=120,
                              env=env)
        if proc.returncode:
            die("predictor failed for " + case)
        try:
            prediction = json.loads(proc.stdout)
        except (ValueError, UnicodeDecodeError):
            die("predictor returned invalid JSON for " + case)
        if set(prediction) != REQUIRED or prediction["prediction"] not in ALLOWED:
            die("predictor schema invalid for " + case)
        if not isinstance(prediction["confidence"], (float, int)) or not 0 <= prediction["confidence"] <= 1:
            die("confidence outside 0..1 for " + case)
        if not isinstance(prediction["rationale"], str) or not prediction["rationale"].strip():
            die("empty rationale for " + case)
        if prediction["case_id"] != case:
            die("case ID mismatch for " + case)
        record = {**prediction,
                  "evidence_sha256": hashlib.sha256(packet).hexdigest(),
                  "predictor_sha256": hashlib.sha256(Path(predictor).read_bytes()).hexdigest(),
                  "locked_at_utc": datetime.now(timezone.utc).isoformat(),
                  "blindness_attestation": "REQUIRES_INDEPENDENT_ACCESS_AUDIT"}
        target = locks / (case + ".json")
        try:
            with target.open("x", encoding="utf-8") as f:
                json.dump(record, f, sort_keys=True, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError:
            die("attempt to overwrite locked prediction " + case)
    print(json.dumps({"predictions_locked": len(rows),
                      "note": "Locking does not independently prove outcome isolation."}))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--predictor", required=True)
    ap.add_argument("--locks", type=Path, required=True)
    a = ap.parse_args()
    run(a.input, a.predictor, a.locks)
