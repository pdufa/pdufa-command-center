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
import os
import tempfile
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

LEGACY_PROTOCOL = "SIX_LEVEL_GATE_V0"
EXPERIMENTAL_RULES = "EXPERIMENTAL_SIX_LEVEL_GATE_BASELINE"
LEVELS = {f"L{level:02d}" for level in GATES}
DIRECTIONS = {"APPROVE", "CRL", "ABSTAIN"}
EVENT_FIELDS = {"event_id", "ticker", "drug", "indication", "decision_date"}
LEGACY_FIELDS = {"evidence_asof", "source_url", "source_publication_date"}
GATE_FIELDS = {gate for gates in GATES.values() for gate in gates}


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        if not columns or len(columns) != len(set(columns)):
            raise ValueError("CSV must have unique column names")
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError("CSV row does not match the header width")
    return rows


def flag(value):
    value = (value or "").strip().lower()
    return True if value in TRUE else False if value in FALSE else None


def canonical_digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def write_new_lock(path, lock):
    """Publish a complete lock file atomically and refuse to replace a prior freeze."""
    path = Path(path)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as staged:
        staged_path = Path(staged.name)
        try:
            json.dump(lock, staged, indent=2)
            staged.write("\n")
            staged.flush()
            os.fsync(staged.fileno())
            if path.exists():
                raise FileExistsError(f"Prediction lock already exists: {path}")
            os.link(staged_path, path)
        finally:
            staged_path.unlink()


def prepare(args):
    rows = load_csv(args.events)
    if not rows:
        raise ValueError("Empty manifest")
    if args.expected_events <= 0 or args.cutoff_days < 1:
        raise ValueError("Specify a positive case count and cutoff lead time")
    if len(rows) != args.expected_events:
        raise ValueError(f"Expected {args.expected_events} events; got {len(rows)}. No padding.")
    required = EVENT_FIELDS | LEGACY_FIELDS | GATE_FIELDS
    columns = set(rows[0])
    if columns - required:
        raise ValueError(f"Unexpected blind manifest columns: {sorted(columns - required)}")
    if required - columns:
        raise ValueError(f"Missing columns: {sorted(required - columns)}")

    events = {}
    for row in rows:
        eid = row["event_id"].strip()
        if not eid or eid in events:
            raise ValueError(f"Empty or duplicate event ID: {eid}")
        events[eid] = {**row, "event_id": eid}

    predictions = []
    feature_snapshots = []
    for eid, row in events.items():
        cutoff = date.fromisoformat(row["decision_date"]) - timedelta(days=args.cutoff_days)
        snapshot_date = date.fromisoformat(row["evidence_asof"])
        if snapshot_date > cutoff:
            raise ValueError(f"{eid}: evidence snapshot is after cutoff")
        source_date = row["source_publication_date"].strip()
        if source_date and date.fromisoformat(source_date) > snapshot_date:
            raise ValueError(f"{eid}: source published after evidence snapshot")
        dated_source_available = bool(row["source_url"].strip() and source_date)
        feature_snapshots.append({"event": row})
        values = {gate: flag(row[gate]) for gate in GATE_FIELDS}

        for level, gates in GATES.items():
            unknown = [gate for gate in gates if values[gate] is None]
            failed = [
                gate for gate in gates
                if values[gate] is not None and values[gate] != (gate not in BAD[level])
            ]
            if not dated_source_available:
                prediction, reason = "ABSTAIN", "missing_dated_source"
            elif unknown:
                prediction, reason = "ABSTAIN", "unknown_evidence_gate"
            elif failed:
                prediction, reason = "CRL", "one_or_more_required_gates_fail"
            else:
                prediction, reason = "APPROVE", "all_required_gates_pass"

            predictions.append({
                **{field: row[field] for field in sorted(EVENT_FIELDS)},
                "cutoff_date": cutoff.isoformat(),
                "level": f"L{level:02d}",
                "prediction": prediction,
                "reason": reason,
                "unknown_gates": unknown,
                "failed_gates": failed,
                "protocol": LEGACY_PROTOCOL,
            })
    lock = {
        "protocol": LEGACY_PROTOCOL,
        "rule_set": EXPERIMENTAL_RULES,
        "expected_events": args.expected_events,
        "cutoff_days": args.cutoff_days,
        "feature_snapshots": feature_snapshots,
        "feature_snapshots_sha256": canonical_digest(feature_snapshots),
        "predictions": predictions,
        "predictions_sha256": canonical_digest(predictions),
    }
    lock["lock_sha256"] = canonical_digest(lock)
    write_new_lock(args.output, lock)
    print(
        f"Locked {len(predictions)} level assessments; SHA256 {lock['lock_sha256']}. "
        "Record the digest independently before outcomes are introduced."
    )


def verify_lock(locked, frozen_digest=None):
    predictions = locked["predictions"]
    protocol = locked["protocol"]
    digest = locked.get("lock_sha256")
    if protocol != LEGACY_PROTOCOL:
        raise ValueError(f"Unknown prediction lock protocol: {protocol}")
    if digest is not None:
        if locked.get("rule_set") != EXPERIMENTAL_RULES:
            raise ValueError("Unexpected frozen rule set")
        payload = {key: value for key, value in locked.items() if key != "lock_sha256"}
        if canonical_digest(payload) != digest:
            raise ValueError("Prediction lock integrity failure")
        if canonical_digest(locked["feature_snapshots"]) != locked["feature_snapshots_sha256"]:
            raise ValueError("Feature snapshot integrity failure")
    if frozen_digest and frozen_digest != digest:
        raise ValueError("Frozen lock digest mismatch")
    if canonical_digest(predictions) != locked["predictions_sha256"]:
        raise ValueError("Prediction lock integrity failure")

    case_levels = {}
    for prediction in predictions:
        eid = prediction["event_id"]
        level = prediction["level"]
        if (not eid or level not in LEVELS or prediction["prediction"] not in DIRECTIONS
                or prediction["protocol"] != protocol):
            raise ValueError("Invalid locked prediction")
        seen = case_levels.setdefault(eid, set())
        if level in seen:
            raise ValueError(f"Duplicate prediction level for {eid}: {level}")
        seen.add(level)
    if (not case_levels or len(case_levels) != locked["expected_events"]
            or any(levels != LEVELS for levels in case_levels.values())):
        raise ValueError("Prediction lock must contain six levels for every expected event")
    if digest is not None:
        snapshot_ids = [snapshot["event"]["event_id"] for snapshot in locked["feature_snapshots"]]
        if len(snapshot_ids) != len(case_levels) or set(snapshot_ids) != set(case_levels):
            raise ValueError("Feature snapshot event IDs differ from locked predictions")
    return predictions


def score(args):
    if not getattr(args, "expected_lock_sha256", None):
        raise ValueError("Provide the independently recorded lock digest before scoring")
    from report_blind_six_levels_2026 import score as score_report

    score_report(args, verify_lock, load_csv)


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
    b.add_argument("--expected-lock-sha256")
    b.add_argument("--summary-csv")
    b.add_argument("--results-csv")
    b.add_argument("--output",required=True)
    args=p.parse_args()
    (prepare if args.command=="prepare" else score)(args)

if __name__=="__main__":
    main()
