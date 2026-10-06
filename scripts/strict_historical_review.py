#!/usr/bin/env python3
"""Run the fixed 126-event manifest through FDA-V3.2, without outcome inputs.

Search candidates are provenance, never gate evidence. Only explicitly verified,
dated, cycle-matched evidence is admitted. Unknown fields remain blank. Actual
outcomes are joined by the precision gate after these directions are selected.
"""
import json
from collections import Counter
from datetime import date
from pathlib import Path
import pandas as pd
from fda_decision_engine import evaluate, load_config

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ALLOWED_FIELDS = {
    "fda_primary_endpoint_status", "fda_multiplicity_status", "fda_missing_data_status",
    "fda_effect_size_status", "fda_replication_status", "fda_process_validation_status",
    "fda_stability_status", "fda_analytical_methods_status", "fda_comparability_status",
    "fda_supplier_status", "fda_warning_letter_status", "fda_import_alert_status",
    "fda_form483_status", "fda_facility_classification", "fda_preapproval_inspection_status",
    "fda_bimo_status", "fda_clinical_score", "fda_safety_score", "fda_regulatory_score",
    "fda_meaningfulness_score", "fda_benefit_risk_score",
}

def assess_event(event, cfg):
    if event["event_key"].split("|")[:2] != [event["ticker"], event["pdufa_date"]]:
        raise ValueError("Strict event identity differs from its ticker/date")
    # Deliberate allowlist: no outcome, broad probability, or market variable.
    row = {k: event[k] for k in ("event_key", "ticker", "drug", "pdufa_date")}
    cutoff = event.get("evidence_cutoff", "")
    action = event.get("action_date", "")
    safe_cutoff = bool(cutoff and action and event.get("action_date_source"))
    if safe_cutoff:
        safe_cutoff = date.fromisoformat(cutoff) < date.fromisoformat(action)
    accepted, rejected = [], []
    for e in event.get("gate_evidence", []):
        field = e.get("field", "")
        valid = (safe_cutoff and field in ALLOWED_FIELDS and e.get("source_url")
                 and e.get("identity_verified") is True
                 and e.get("availability_verified") is True and e.get("published_date"))
        if valid:
            valid = date.fromisoformat(e["published_date"]) <= date.fromisoformat(cutoff)
        if valid:
            row[field] = e["value"]
            accepted.append(e)
        else:
            rejected.append(e)
    row["fda_application_identity"] = "PASS" if accepted else "UNKNOWN"
    row["fda_evidence_freshness"] = "FROZEN" if accepted and safe_cutoff else "UNKNOWN"
    result = evaluate(row, cfg)
    result.pop("fda_last_evaluated_at", None)
    result.pop("fda_match_result", None)
    result.update({
        "run_id": "STRICT-126-20261006", "evidence_cutoff": cutoff,
        "action_date": action, "action_date_source": event.get("action_date_source", ""),
        "imported_evidence_cutoff": event.get("imported_evidence_cutoff", ""),
        "cutoff_status": "VERIFIED_DATE_ONLY" if safe_cutoff else "REQUIRES_VERIFICATION",
        "admitted_evidence_count": len(accepted), "rejected_evidence_count": len(rejected),
        "source_urls": " | ".join(e["source_url"] for e in accepted),
        "context_source_url": event.get("context_source_url", ""),
        "evidence_summary": " | ".join(e["summary"] for e in accepted),
        "review_note": event["evidence_review_note"],
        "review_status": "STRICT_ENGINE_EVALUATED_SOURCE_SCREENED",
        "missing_cmc_subchecks": " | ".join(k.removeprefix("fda_") for k in (
            "fda_process_validation_status", "fda_stability_status", "fda_analytical_methods_status",
            "fda_comparability_status", "fda_supplier_status") if not row.get(k)),
        "missing_statistics_subchecks": " | ".join(k.removeprefix("fda_") for k in (
            "fda_primary_endpoint_status", "fda_multiplicity_status", "fda_missing_data_status",
            "fda_effect_size_status", "fda_replication_status") if not row.get(k)),
        "missing_facility_subchecks": "warning/import/Form483 clearance; named sites/FEI; NAI classification; passed preapproval inspection",
        "validation_status": "RETROSPECTIVE_DEVELOPMENT_NOT_BLIND",
    })
    return result

def run_review(payload, cfg):
    events = payload["events"]
    keys = [e["event_key"] for e in events]
    if len(keys) != payload["expected_count"] or len(set(keys)) != len(keys):
        raise ValueError("Strict manifest coverage/identity mismatch")
    if payload["model_version"] != cfg["model_version"]:
        raise ValueError("Strict model version changed; review inputs before rerunning")
    return pd.DataFrame([assess_event(e, cfg) for e in events]).fillna("")

def main():
    payload = json.loads((DATA / "strict_historical_126_inputs.json").read_text())
    result = run_review(payload, load_config())
    result.to_csv(DATA / "strict_historical_126_review.csv", index=False)
    counts = Counter(result["fda_prediction"])
    summary = {"run_id": payload["run_id"], "model_version": payload["model_version"],
               "requested": payload["expected_count"], "evaluated": len(result),
               "approved": counts["APPROVED"], "crl": counts["CRL"], "review": counts["REVIEW"],
               "source_screened": len(result),
               "complete_affirmative_clearance_dossiers": int(result["fda_hard_gate"].eq("PASS").sum()),
               "note": "All 126 evaluated; source screening is not exhaustive dossier verification. Candidate URLs do not pass gates. Unverified fields remain REVIEW. Original 20 qualifications are outside this run."}
    (DATA / "strict_historical_126_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return result

if __name__ == "__main__":
    main()
