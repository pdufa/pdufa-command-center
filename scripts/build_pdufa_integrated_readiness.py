"""Read-only master SCIENCE/OUTCOME/MAIN integration status report.

Combines existing historical FDA evidence artifacts. No inferred prediction
probabilities, unverified historical labels, or production writes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def assemble(ledger, fingerprints, reconciliation):
    candidates = ledger.get("candidate_review_cycles", [])
    reconciled = reconciliation.get("records", [])
    if len(candidates) != len(reconciled):
        raise ValueError("candidate and reconciliation counts differ")
    for candidate, evidence in zip(candidates, reconciled):
        identity = ("application_id", "submission_id", "review_cycle", "official_source_url")
        if any(candidate.get(k) != evidence.get(k) for k in identity):
            raise ValueError("candidate/reconciliation identity mismatch")
    return {
        "system": "PDUFA SCIENCE-OUTCOME-MAIN",
        "readiness": "NOT_VALIDATED_FOR_TRADING",
        "science": {"historical_parallel_matcher": "IMPLEMENTED_CANDIDATE_ONLY",
                    "verified_historical_parallels": 0},
        "outcome": {"candidate_review_cycles": len(candidates),
                    "fingerprint_records": len(fingerprints.get("records", [])),
                    "source_hashed_pending_adjudication": sum(
                        r.get("status") == "SOURCE_HASH_AVAILABLE_ADJUDICATION_PENDING"
                        for r in reconciled),
                    "independently_verified_pass": 0,
                    "independently_verified_fail": 0,
                    "model_eligible_records": 0},
        "main": {"dashboard_prediction_probability": None,
                 "historical_backtest_validated": False,
                 "recommendation_ready": False},
        "blocking_requirements": [
            "Independent FDA document adjudication and review-cycle verification",
            "Sufficient representative verified PASS and FAIL decisions",
            "Leakage-safe historical clinical features and parallel matching",
            "Out-of-time prediction backtesting and calibration",
        ],
        "warning": "This is a research artifact, not a deployed dashboard or investment recommendation.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", required=True, type=Path)
    p.add_argument("--fingerprints", required=True, type=Path)
    p.add_argument("--reconciliation", required=True, type=Path)
    a = p.parse_args()
    inputs = [json.loads(x.read_text(encoding="utf-8")) for x in
              (a.ledger, a.fingerprints, a.reconciliation)]
    print(json.dumps(assemble(*inputs), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
