#!/usr/bin/env python3
"""Two-stage, auditable historical Level-1 backtest.

Stage 'prepare' accepts an event manifest WITHOUT outcomes and pre-cutoff
features; it emits locked predictions. Stage 'score' accepts a separately
stored outcomes CSV only after prediction lock is committed.
This is a baseline research protocol, NOT a validated FDA prediction model.
"""
import argparse, csv, hashlib, json
from datetime import date, timedelta
from pathlib import Path

FEATURES = ("ticker", "drug", "indication", "decision_date", "evidence_asof",
            "submission_accepted", "pivotal_primary_endpoint_met",
            "major_safety_signal", "documented_regulatory_deficiency")
YES = {"yes", "true", "1"}
NO = {"no", "false", "0"}

def flag(row, key):
    value = (row.get(key) or "").strip().lower()
    return True if value in YES else False if value in NO else None

def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def prepare(args):
    rows = load(args.events)
    if not rows:
        raise ValueError("Empty input")
    if any("outcome" in k.lower() or "approved" in k.lower() or "crl" == k.lower()
           for k in rows[0]):
        raise ValueError("Outcome-bearing columns prohibited in blind input")
    output = []
    ids = set()
    for row in rows:
        if any(k not in row for k in FEATURES):
            raise ValueError("Missing required feature columns")
        key = row.get("event_id", "").strip()
        if not key or key in ids:
            raise ValueError("Missing or duplicate event_id")
        ids.add(key)
        decision = date.fromisoformat(row["decision_date"])
        cutoff = decision - timedelta(days=args.cutoff_days)
        evidence_date = date.fromisoformat(row["evidence_asof"])
        if evidence_date > cutoff:
            raise ValueError(f"{key}: evidence after cutoff {cutoff}")
        accepted = flag(row, "submission_accepted")
        efficacy = flag(row, "pivotal_primary_endpoint_met")
        safety = flag(row, "major_safety_signal")
        deficiency = flag(row, "documented_regulatory_deficiency")
        # Fixed, deliberately conservative Level-1 rule; no invented odds.
        if None in (accepted, efficacy, safety, deficiency):
            prediction, reason = "ABSTAIN", "missing_level1_evidence"
        elif accepted and efficacy and not safety and not deficiency:
            prediction, reason = "APPROVE", "all_four_level1_gates_pass"
        elif not accepted or not efficacy or safety or deficiency:
            prediction, reason = "CRL", "one_or_more_level1_gates_fail"
        else:
            prediction, reason = "ABSTAIN", "indeterminate"
        output.append({"event_id": key, "ticker": row["ticker"],
                       "drug": row["drug"], "indication": row["indication"],
                       "decision_date": row["decision_date"],
                       "cutoff_date": cutoff.isoformat(),
                       "prediction": prediction, "reason": reason,
                       "protocol": "L1_GATE_V1"})
    payload = json.dumps(output, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(payload).hexdigest()
    Path(args.output).write_text(json.dumps(
        {"protocol": "L1_GATE_V1", "cutoff_days": args.cutoff_days,
         "predictions_sha256": digest, "predictions": output}, indent=2) + "\n")
    print(f"Locked {len(output)} assessments; SHA256 {digest}")
    print("Commit prediction file/hash before supplying outcomes to 'score'.")

def score(args):
    locked = json.loads(Path(args.locked).read_text())
    preds = locked["predictions"]
    payload = json.dumps(preds, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(payload).hexdigest() != locked["predictions_sha256"]:
        raise ValueError("Prediction lock hash mismatch")
    outcomes = load(args.outcomes)
    truth = {}
    for r in outcomes:
        key = r["event_id"]
        if key in truth:
            raise ValueError(f"Duplicate outcome: {key}")
        truth[key] = r["actual_outcome"].strip().upper()
    if set(truth) != {p["event_id"] for p in preds}:
        raise ValueError("Outcome and prediction event IDs differ")
    rows = []
    for p in preds:
        actual = truth[p["event_id"]]
        if actual not in ("APPROVE", "CRL"):
            raise ValueError(f"Unrecognized actual outcome: {actual}")
        rows.append({**p, "actual_outcome": actual,
                     "correct": "" if p["prediction"] == "ABSTAIN"
                     else str(p["prediction"] == actual).lower()})
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    answered = [r for r in rows if r["prediction"] != "ABSTAIN"]
    correct = sum(r["correct"] == "true" for r in answered)
    print(json.dumps({"events": len(rows), "predicted": len(answered),
                      "abstained": len(rows) - len(answered),
                      "accuracy_non_abstained": correct / len(answered)
                      if answered else None, "coverage": len(answered)/len(rows)}, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--events", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--cutoff-days", type=int, default=30)
    s = sub.add_parser("score")
    s.add_argument("--locked", required=True)
    s.add_argument("--outcomes", required=True)
    s.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "prepare": prepare(args)
    else: score(args)
