#!/usr/bin/env python3
"""Phase-first provisional scoring and leakage-guarded prediction evaluation.

Does NOT train a model, predict FDA actions, or independently certify blind
validity. Clinical source components are research metrics, not FDA probabilities.
Historical outcome-aware cases remain EXCLUDED from genuine blind metrics.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

NCT_RE = re.compile(r"^NCT\d{8}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
COMPONENT_VALUES = {0, 25, 50, 75, 100}
FORBIDDEN_SOURCE_KEYS = {
    "outcome", "actual_outcome", "fda_decision", "fda_outcome",
    "decision_date", "action_date", "fda_action", "postdecision_evidence",
    "post_decision_evidence", "actual_approval",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def utc(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Timestamp must be an ISO UTC datetime ending Z")
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo != dt.timezone.utc:
        raise ValueError("Timestamp must be UTC")
    return result


def check_no_known_outcomes(value: Any, path: str = "root") -> None:
    if isinstance(value, list):
        for i, row in enumerate(value):
            check_no_known_outcomes(row, f"{path}[{i}]")
    elif isinstance(value, dict):
        for key, entry in value.items():
            if key.lower().replace("-", "_") in FORBIDDEN_SOURCE_KEYS:
                raise ValueError(f"Outcome leakage field in scoring input: {path}.{key}")
            check_no_known_outcomes(entry, f"{path}.{key}")


def score_trials(rows: list[dict]) -> dict:
    if not isinstance(rows, list):
        raise ValueError("Scores input must be a list of trial objects")
    check_no_known_outcomes(rows)
    seen = set()
    computed = []
    for row in rows:
        nct = row.get("nct")
        if not isinstance(nct, str) or not NCT_RE.fullmatch(nct) or nct in seen:
            raise ValueError("Every trial requires one unique NCT identifier")
        seen.add(nct)
        if not row.get("ticker") or not row.get("registry_status") or not row.get("phase_evidence"):
            raise ValueError(f"Phase-first source metadata incomplete for {nct}")
        if not re.fullmatch(r"20\d\d-\d\d-\d\d", str(row.get("snapshot_date", ""))):
            raise ValueError(f"Missing source snapshot date for {nct}")
        source = str(row.get("source_url", ""))
        if not source.startswith("https://"):
            raise ValueError(f"Original source link missing/unsafe for {nct}")
        scores = row.get("clinical_components")
        if not isinstance(scores, list) or len(scores) != 5:
            raise ValueError("Exactly five original clinical components are required")
        if any(x is not None and (type(x) is not int or x not in COMPONENT_VALUES) for x in scores):
            raise ValueError("Unsupported score: each component must be 0,25,50,75,100, or null")
        known = [x for x in scores if x is not None]
        coverage = len(known)
        observed = (sum(known) / coverage) if coverage else None
        computed.append({
            "ticker": row["ticker"], "nct": nct,
            "registry_status_from_snapshot": row["registry_status"],
            "source_phase_evidence": row["phase_evidence"],
            "source_snapshot_date": row["snapshot_date"],
            "source_url": source,
            "source_components": scores,
            "component_coverage": f"{coverage}/5",
            "observed_only_mean_100": round(observed, 2) if observed is not None else None,
            "fully_observed_clinical_five_100": round(observed, 2) if coverage == 5 else None,
            "theoretical_min_100": sum(known) / 5 if coverage else None,
            "theoretical_max_100": (sum(known) + (5 - coverage) * 100) / 5 if coverage else None,
            "missing_component_indices": [i + 1 for i, x in enumerate(scores) if x is None],
            "complete_level6_scientific_assessment": False,
            "fda_approval_probability": None,
            "valid_blind_fda_prediction": False,
        })
    return {
        "schema_version": 1,
        "mode": "PROVISIONAL_CLINICAL_EVIDENCE_NOT_FDA_PREDICTION",
        "trials": computed,
        "total": len(computed),
        "five_of_five": sum(x["fully_observed_clinical_five_100"] is not None for x in computed),
        "partial": sum(0 < len([v for v in x["source_components"] if v is not None]) < 5
                       for x in computed),
        "not_scoreable": sum(x["observed_only_mean_100"] is None for x in computed),
        "verified_level6_scientific_completions": 0,
    }


def validate_freeze(predictions: list[dict]) -> dict:
    if not isinstance(predictions, list):
        raise ValueError("Predictions input must be a list")
    check_no_known_outcomes(predictions)
    seen = set()
    verified = []
    for item in predictions:
        key = str(item.get("application_id", ""))
        if not key or key in seen:
            raise ValueError("Every prediction requires a unique FDA application/event identifier")
        seen.add(key)
        ncts = item.get("ncts")
        if not isinstance(ncts, list) or not ncts or any(
            not isinstance(n, str) or not NCT_RE.fullmatch(n) for n in ncts
        ):
            raise ValueError("At least one verified supporting NCT required")
        if not item.get("model_version") or not item.get("phase_verification"):
            raise ValueError("Model version and phase-first verification required")
        category = item.get("validation_class")
        if category not in ("PROSPECTIVE_CANDIDATE", "RETROSPECTIVE_REPLAY"):
            raise ValueError("Validation class must disclose prospective vs historical")
        cutoff = utc(item.get("evidence_cutoff_utc"))
        frozen = utc(item.get("freeze_utc"))
        if cutoff > frozen:
            raise ValueError("Evidence cutoff cannot occur after prediction freeze")
        rec = item.get("evidence_receipts")
        if not isinstance(rec, list) or not rec:
            raise ValueError("Independent original-source receipt dates required")
        for s in rec:
            if not SHA_RE.fullmatch(str(s.get("sha256", ""))):
                raise ValueError("Every original source needs a SHA256 receipt")
            if utc(s.get("published_utc")) > cutoff:
                raise ValueError("Post-cutoff publication leaked into evidence")
            if utc(s.get("accessed_utc")) > frozen:
                raise ValueError("Post-freeze source access cannot justify frozen prediction")
        direction = item.get("direction")
        probability = item.get("approval_probability")
        if direction not in ("APPROVAL", "CRL", "ABSTAIN"):
            raise ValueError("Use APPROVAL, CRL, or ABSTAIN, not an invented FDA outcome")
        if direction == "ABSTAIN" and probability is not None:
            raise ValueError("Abstaining cases cannot claim a probability")
        if direction != "ABSTAIN" and (
            type(probability) not in (float, int) or not 0 <= probability <= 1
        ):
            raise ValueError("Predictions require an explicit calibrated 0-to-1 model output")
        verified.append(item)
    body = {
        "schema_version": 1,
        "mode": "FROZEN_PREDICTIONS_NO_OUTCOMES_INCLUDED",
        "predictions": verified,
        "automatic_scientific_signoff": False,
        "freeze_integrity_only_not_independent_blind_certification": True,
    }
    return {"body": body, "sha256": sha256(canonical_bytes(body))}


def evaluate(frozen: dict, outcomes: list[dict]) -> dict:
    body = frozen.get("body")
    if not isinstance(body, dict) or sha256(canonical_bytes(body)) != frozen.get("sha256"):
        raise ValueError("Frozen prediction manifest tampered or invalid")
    if body.get("mode") != "FROZEN_PREDICTIONS_NO_OUTCOMES_INCLUDED":
        raise ValueError("Not a frozen manifest")
    if not isinstance(outcomes, list):
        raise ValueError("Outcome input must be a separate list")
    by_id = {}
    for record in outcomes:
        key = record.get("application_id")
        if not key or key in by_id:
            raise ValueError("Duplicate or missing FDA application/event outcomes")
        if record.get("outcome") not in ("APPROVAL", "CRL", "WITHDRAWN", "OTHER"):
            raise ValueError("Unrecognized FDA outcome")
        if not str(record.get("verified_fda_source_url", "")).startswith("https://"):
            raise ValueError("FDA outcome source required")
        utc(record.get("decision_utc"))
        by_id[key] = record
    rows = []
    valid = []
    for p in body["predictions"]:
        case = by_id.get(p["application_id"])
        if not case:
            rows.append({"application_id": p["application_id"], "class": "PENDING_OUTCOME"})
            continue
        before = utc(p["freeze_utc"]) < utc(case["decision_utc"])
        genuinely_reviewed = (
            p["validation_class"] == "PROSPECTIVE_CANDIDATE"
            and case.get("independent_blind_freeze_audit") is True
            and bool(case.get("freeze_proof_reference"))
            and before
        )
        scored = p["direction"] in ("APPROVAL", "CRL") and case["outcome"] in ("APPROVAL", "CRL")
        if genuinely_reviewed and scored:
            valid.append((p, case))
            category = "INDEPENDENTLY_AUDITED_PROSPECTIVE"
        elif p["validation_class"] == "RETROSPECTIVE_REPLAY":
            category = "OUTCOME_AWARE_OR_REPLAY_EXCLUDED_FROM_BLIND"
        elif not before:
            category = "PREDICTION_NOT_FROZEN_BEFORE_DECISION"
        elif not genuinely_reviewed:
            category = "UNVERIFIED_BLINDNESS_EXCLUDED"
        else:
            category = "ABSTAIN_OR_NONBINARY_OUTCOME"
        rows.append({"application_id": p["application_id"], "class": category})
    correct = sum(p["direction"] == o["outcome"] for p, o in valid)
    n = len(valid)
    brier = (
        sum((p["approval_probability"] - (1 if o["outcome"] == "APPROVAL" else 0))**2
            for p, o in valid) / n
        if n else None
    )
    return {
        "schema_version": 1,
        "valid_blind_cases": n,
        "blind_accuracy": round(correct / n, 6) if n else None,
        "brier_score": round(brier, 6) if brier is not None else None,
        "always_approve_baseline": (
            round(sum(o["outcome"] == "APPROVAL" for _, o in valid) / n, 6)
            if n else None
        ),
        "records": rows,
        "warning": "Counts require an externally supplied independent audit attestation; this offline program cannot independently authenticate that attestation or prove historical outcomes were unknown. One case per FDA application/event; no 100% accuracy guarantee.",
    }


def write_json(path: Path, value: Any, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, sort_keys=True, indent=2)
        f.write("\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    subs = ap.add_subparsers(dest="command", required=True)
    for cmd in ("score", "freeze", "evaluate"):
        sub = subs.add_parser(cmd)
        if cmd == "evaluate":
            sub.add_argument("--frozen", required=True, type=Path)
            sub.add_argument("--outcomes", required=True, type=Path)
        else:
            sub.add_argument("--input", required=True, type=Path)
        sub.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    if args.command == "score":
        result = score_trials(read_json(args.input))
    elif args.command == "freeze":
        result = validate_freeze(read_json(args.input))
    else:
        result = evaluate(read_json(args.frozen), read_json(args.outcomes))
    write_json(args.out, result, exclusive=(args.command == "freeze"))
    print(json.dumps({"command": args.command, "output": str(args.out),
                      "valid_blind_cases": result.get("valid_blind_cases", 0)}))


if __name__ == "__main__":
    main()
