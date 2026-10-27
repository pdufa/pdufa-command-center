"""Independent decision-corpus readiness gate.

Consumes an audit report; never treats candidate rows or source URLs as verified
outcomes. Intended for CI and dashboard status, not trading authorization.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def readiness(audit: dict) -> dict:
    if audit.get("audit") != "historical_fda_decision_ingestion":
        raise ValueError("Expected historical FDA decision ingestion audit")
    pass_count = audit.get("independently_verified_pass_count")
    fail_count = audit.get("independently_verified_fail_count")
    eligible = audit.get("model_eligible_records")
    for name, value in [("PASS", pass_count), ("FAIL", fail_count), ("eligible", eligible)]:
        if type(value) is not int or value < 0:
            raise ValueError(f"Invalid {name} count")
    source_verified = audit.get("source_content_verified") is True
    denominator_verified = audit.get("complete_application_denominator_verified") is True
    independently_tested = audit.get("independent_backtest_complete") is True
    model_validated = audit.get("prediction_model_validated") is True
    data_ready = bool(pass_count > 0 and fail_count > 0 and eligible > 0
                      and source_verified and denominator_verified)
    # Readiness is intentionally strict; validation requires an independent report.
    return {
        "status": "DATA_READY_FOR_RESEARCH" if data_ready else "DATA_NOT_READY",
        "verified_pass": pass_count,
        "verified_fail": fail_count,
        "model_eligible_records": eligible,
        "source_content_verified": source_verified,
        "complete_application_denominator_verified": denominator_verified,
        "historical_validation_complete": independently_tested,
        "model_validation_complete": model_validated,
        "paper_trading_ready": False,
        "live_trading_ready": False,
        "reason": ("Research dataset passed basic audit gates; prospective evaluation "
                   "and investment-risk validation still required." if data_ready else
                   "Verified historical outcomes, coverage, or source adjudication incomplete."),
        "note": "This tool never authorizes trading or infers investment profitability from FDA accuracy.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_json", type=Path)
    args = parser.parse_args()
    print(json.dumps(readiness(json.loads(args.audit_json.read_text(encoding="utf-8"))),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
