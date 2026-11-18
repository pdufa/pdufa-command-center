#!/usr/bin/env python3
"""Leakage-resistant six-level historical prediction locking and scoring.

Input events CSV MUST exclude outcomes. Each level's required gate columns
are explicit, and unknown evidence results in ABSTAIN. This is an auditable
baseline, not a validated clinical prediction engine.
"""
import argparse
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

GATES = {
    1: ["submission_accepted", "pivotal_primary_endpoint_met",
        "major_safety_signal", "documented_regulatory_deficiency"],
    2: ["trial_design_valid", "multiplicity_controlled",
        "effect_robust", "missing_data_risk"],
    3: ["benefit_clinically_meaningful", "safety_acceptable",
        "subgroups_consistent", "benefit_risk_favorable"],
    4: ["regulatory_precedent_supportive", "adcom_supportive",
        "regulatory_objection_documented"],
    5: ["cmc_acceptable", "inspection_risk_material",
        "labeling_impediment_material"],
    6: ["integrated_efficacy_supportive", "integrated_safety_acceptable",
        "integrated_regulatory_risk_material", "integrated_cmc_risk_material"],
}
BAD = {1: {"major_safety_signal", "documented_regulatory_deficiency"},
       2: {"missing_data_risk"},
       3: set(),
       4: {"regulatory_objection_documented"},
       5: {"inspection_risk_material", "labeling_impediment_material"},
       6: {"integrated_regulatory_risk_material", "integrated_cmc_risk_material"}}
TRUE = {"yes", "true", "1"}
FALSE = {"no", "false", "0"}

def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def flag(value):
    v = (value or "").strip().lower()
    return True if v in TRUE else False if v in FALSE else None

def prepare(args):
    rows = load_csv(args.events)
    if not rows:
        raise ValueError("Empty manifest")
    banned = ("outcome", "actual", "approved", "crl", "correct", "postdecision")
    if any(any(x in k.lower() for x in banned) for k in rows[0]):
        raise ValueError("Outcome-bearing fields prohibited in blind manifest")
    if len(rows) != args.expected_events:
        raise ValueError(f"Expected {args.expected_events} events; got {len(rows)}. No padding.")
    required = {"event_id", "ticker", "drug", "indication",
                "decision_date", "evidence_asof", "source_url",
                "source_publication_date"}
    required.update(k for gates in GATES.values() for k in gates)
    if not required.issubset(rows[0]):
        raise ValueError(f"Missing columns: {sorted(required-set(rows[0]))}")
    output = []
    ids = set()
    for row in rows:
        eid = row["event_id"].strip()
        if not eid or eid in ids:
            raise ValueError(f"Empty or duplicate event ID: {eid}")
        ids.add(eid)
        cutoff = date.fromisoformat(row["decision_date"]) - timedelta(days=args.cutoff_days)
        if date.fromisoformat(row["evidence_asof"]) > cutoff:
            raise ValueError(f"{eid}: evidence snapshot is after cutoff")
        if row["source_publication_date"].strip() and date.fromisoformat(row["source_publication_date"]) > cutoff:
            raise ValueError(f"{eid}: source published after cutoff")
        for level, gates in GATES.items():
            values = {g: flag(row[g]) for g in gates}
            if not row["source_url"].strip() or not row["source_publication_date"].strip():
                pred, reason = "ABSTAIN", "missing_dated_source"
            elif any(v is None for v in values.values()):
                pred, reason = "ABSTAIN", "unknown_evidence_gate"
            elif all(values[g] is False if g in BAD[level] else values[g] is True for g in gates):
                pred, reason = "APPROVE", "all_required_gates_pass"
            else:
                pred, reason = "CRL", "one_or_more_required_gates_fail"
            output.append({"event_id":eid,"ticker":row["ticker"],"drug":row["drug"],
                           "indication":row["indication"],"decision_date":row["decision_date"],
                           "cutoff_date":cutoff.isoformat(),"level":f"L{level:02d}",
                           "prediction":pred,"reason":reason,"protocol":"SIX_LEVEL_GATE_V0"})
    payload = json.dumps(output, sort_keys=True, separators=(",", ":")).encode()
    lock = {"protocol":"SIX_LEVEL_GATE_V0","expected_events":args.expected_events,
            "cutoff_days":args.cutoff_days,"predictions_sha256":hashlib.sha256(payload).hexdigest(),
            "predictions":output}
    Path(args.output).write_text(json.dumps(lock,indent=2)+"\n",encoding="utf-8")
    print(f"Locked {len(output)} level assessments; commit lock before outcomes are introduced.")

def score(args):
    locked = json.loads(Path(args.locked).read_text(encoding="utf-8"))
    preds = locked["predictions"]
    digest = hashlib.sha256(json.dumps(preds,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if digest != locked["predictions_sha256"]:
        raise ValueError("Prediction lock integrity failure")
    outcomes = load_csv(args.outcomes)
    truth = {}
    for row in outcomes:
        eid = row["event_id"]
        if eid in truth:
            raise ValueError(f"Duplicate outcome: {eid}")
        outcome = row["actual_outcome"].strip().upper()
        if outcome not in ("APPROVE","CRL"):
            raise ValueError(f"Unsupported outcome for {eid}: {outcome}")
        truth[eid] = outcome
    if set(truth) != {p["event_id"] for p in preds}:
        raise ValueError("Event IDs differ between prediction lock and outcomes")
    result = []
    for level in range(1,7):
        subset = [p for p in preds if p["level"] == f"L{level:02d}"]
        answered = [p for p in subset if p["prediction"] != "ABSTAIN"]
        correct = sum(p["prediction"] == truth[p["event_id"]] for p in answered)
        result.append({"level":f"L{level:02d}","events":len(subset),
                       "predicted":len(answered),"abstained":len(subset)-len(answered),
                       "correct":correct,"incorrect":len(answered)-correct,
                       "coverage":len(answered)/len(subset) if subset else None,
                       "accuracy":correct/len(answered) if answered else None})
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("prepare")
    a.add_argument("--events",required=True)
    a.add_argument("--output",required=True)
    a.add_argument("--expected-events",type=int,default=196)
    a.add_argument("--cutoff-days",type=int,default=30)
    b=sub.add_parser("score")
    b.add_argument("--locked",required=True)
    b.add_argument("--outcomes",required=True)
    b.add_argument("--output",required=True)
    args=p.parse_args()
    (prepare if args.command=="prepare" else score)(args)

if __name__=="__main__":
    main()
