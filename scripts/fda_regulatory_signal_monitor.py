#!/usr/bin/env python3
"""Derive structured regulatory-interaction / public blind-spot signals.

This monitor is separate from strict FDA-V3.2. It converts already-collected
decision-safe FDA review notes into auditable structured fields that can be
used by later prospective directional-model versions.

It does not use market/trading variables or known FDA outcomes to assign risk.
Typical runtime: under 5 seconds for the current saved live feed.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REVIEWS = DATA / "fda_review_engine.csv"
OUT = DATA / "fda_regulatory_signal_monitor.csv"

COLUMNS = [
    "event_key","fda_regulatory_case_id","ticker","drug","pdufa_date",
    "review_extension_status","extension_reason","deficiency_notice_status",
    "late_cycle_open_questions","inspection_readiness","prior_crl_remediation",
    "evidence_sufficiency_risk","dose_consistency_risk",
    "analytical_lab_relocation","remote_records_review","immunogenicity_signal",
    "adcom_signal","blindspot_risk_level","blindspot_flags",
    "source_note","generated_at",
]

def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan","none","<na>"} else s

def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def contains(text, *parts):
    return any(p in text for p in parts)

def classify(row):
    source = clean(row.get("fda_source_note"))
    gate_reason = clean(row.get("fda_gate_reason"))
    text = f"{source} {gate_reason}".lower()
    flags = []

    extension = contains(text, "pdufa extended", "extended to", "review extension", "extension after", "pdufa date extension")
    extension_status = "YES" if extension else "NO"
    extension_reason = "NONE"
    if extension:
        if contains(text, "manufacturing", "cmc", "product quality", "facility"):
            extension_reason = "CMC_MANUFACTURING"
            flags.append("REVIEW_EXTENSION_CMC_MANUFACTURING")
        elif contains(text, "sensitivity analyses", "additional analyses", "additional data", "longer-term data", "clinical data"):
            extension_reason = "CLINICAL_DATA_ANALYSIS"
            flags.append("REVIEW_EXTENSION_CLINICAL_DATA")
        elif contains(text, "labeling", "post-marketing", "postmarketing"):
            extension_reason = "LABELING_POSTMARKETING"
            flags.append("REVIEW_EXTENSION_LABELING")
        elif contains(text, "information request", "information requests", "major amendment"):
            extension_reason = "GENERAL_INFO_REQUEST"
            flags.append("REVIEW_EXTENSION_INFORMATION_REQUEST")
        else:
            extension_reason = "UNKNOWN"
            flags.append("REVIEW_EXTENSION_REASON_UNKNOWN")

    explicit_deficiency = (
        contains(text, "deficiency", "deficiencies") and
        contains(text, "preclud", "unresolved", "remains a major regulatory risk", "additional evidence")
    )
    deficiency_status = "OPEN" if explicit_deficiency else "NONE"
    if explicit_deficiency:
        flags.append("FDA_DEFICIENCY_NOTICE_OPEN")

    late_cycle = contains(text, "late-cycle", "late cycle", "mid-cycle", "mid cycle")
    late_open = late_cycle and contains(text, "remaining questions", "unresolved", "review issues", "major safety or efficacy concerns")
    late_cycle_status = "YES" if late_open else ("NO" if late_cycle else "UNKNOWN")
    if late_open:
        flags.append("LATE_CYCLE_OPEN_QUESTIONS")

    facility_gate = clean(row.get("fda_facility_gate")).upper()
    pai = clean(row.get("fda_preapproval_inspection_status")).upper()
    form483 = clean(row.get("fda_form483_status")).upper()
    classification = clean(row.get("fda_facility_classification")).upper()
    import_alert = clean(row.get("fda_import_alert_status")).upper()
    if facility_gate == "FAIL" or classification in {"OAI","FAIL","FAILED"} or pai in {"FAIL","FAILED"} or import_alert in {"ACTIVE","FAIL","FAILED"}:
        inspection = "FAIL"
        flags.append("INSPECTION_FAILURE")
    elif contains(text, "still being scheduled", "scheduling required inspections", "inspection outcome unavailable", "outcome unknown") or form483 in {"OPEN","FORM483_OPEN"}:
        inspection = "REVIEW"
        flags.append("INSPECTION_READINESS_UNRESOLVED")
    elif facility_gate == "PASS":
        inspection = "PASS"
    else:
        inspection = "UNKNOWN"

    prior_crl = contains(text, "prior crl", "after prior crl", "resubmission", "complete response")
    if prior_crl and contains(text, "unresolved", "remains a major regulatory risk", "additional evidence of effectiveness was required", "until fda accepts"):
        remediation = "UNRESOLVED"
        flags.append("PRIOR_CRL_REMEDIATION_UNRESOLVED")
    elif prior_crl and contains(text, "addressed", "remediation", "reinspection", "complete response"):
        remediation = "VERIFIED_OR_CLAIMED"
        flags.append("PRIOR_CRL_REMEDIATION_SIGNAL")
    elif prior_crl:
        remediation = "UNKNOWN"
        flags.append("PRIOR_CRL_REMEDIATION_UNKNOWN")
    else:
        remediation = "NOT_APPLICABLE"

    primary = clean(row.get("fda_primary_endpoint_status")).upper()
    stats_gate = clean(row.get("fda_statistics_gate")).upper()
    single_pivotal = contains(text, "one pivotal", "single pivotal", "based on one pivotal") and "phase 3" in text
    dose_split = contains(text, "did not achieve statistical significance", "not statistically significant") and contains(
        text, "once-weekly", "twice-weekly", "dosing regimen", "tested regimen", "tested dose"
    )
    phase2_external = "full approval" in text and "phase 2" in text and contains(text, "external comparator", "natural-history", "natural history")
    if primary == "FAIL" or phase2_external or (single_pivotal and dose_split):
        evidence_risk = "HIGH"
        flags.append("EVIDENCE_SUFFICIENCY_HIGH")
    elif stats_gate == "REVIEW":
        evidence_risk = "MEDIUM"
    else:
        evidence_risk = "LOW" if stats_gate == "PASS" else "UNKNOWN"

    if single_pivotal and dose_split:
        dose_risk = "HIGH"
        flags.append("DOSE_CONSISTENCY_RISK")
    elif clean(row.get("fda_replication_status")).upper() == "PASS":
        dose_risk = "LOW"
    else:
        dose_risk = "UNKNOWN"

    lab_relocation = "YES" if ("laborator" in text and contains(text, "moved", "relocation", "new location")) else "NO"
    if lab_relocation == "YES":
        flags.append("CRITICAL_LAB_RELOCATION")

    remote_review = "YES" if contains(text, "remote review of records", "remote records review", "remote manufacturing records") else "NO"
    if remote_review == "YES":
        flags.append("REMOTE_RECORDS_REVIEW")

    if contains(text, "immunogenicity", "anti-drug antibod", "antidrug antibod") and contains(text, "high", "77%", "77.1%", "persistent"):
        immunogenicity = "HIGH"
        flags.append("IMMUNOGENICITY_SIGNAL")
    elif contains(text, "immunogenicity", "anti-drug antibod", "antidrug antibod"):
        immunogenicity = "REVIEW"
    else:
        immunogenicity = "UNKNOWN"

    if contains(text, "adcom", "advisory committee", "advisory-committee"):
        if contains(text, "favorable", "positive vote", "recommended approval", "strong endorsement"):
            adcom = "POSITIVE"
        elif contains(text, "negative", "voted against", "did not recommend"):
            adcom = "NEGATIVE"
            flags.append("NEGATIVE_ADCOM")
        else:
            adcom = "MIXED"
    else:
        adcom = "NONE"

    high_flags = {
        "FDA_DEFICIENCY_NOTICE_OPEN","INSPECTION_FAILURE","PRIOR_CRL_REMEDIATION_UNRESOLVED",
        "EVIDENCE_SUFFICIENCY_HIGH","DOSE_CONSISTENCY_RISK","CRITICAL_LAB_RELOCATION",
        "REMOTE_RECORDS_REVIEW","IMMUNOGENICITY_SIGNAL","NEGATIVE_ADCOM",
        "REVIEW_EXTENSION_CMC_MANUFACTURING",
    }
    medium_flags = {
        "LATE_CYCLE_OPEN_QUESTIONS","INSPECTION_READINESS_UNRESOLVED",
        "PRIOR_CRL_REMEDIATION_UNKNOWN","REVIEW_EXTENSION_CLINICAL_DATA",
        "REVIEW_EXTENSION_INFORMATION_REQUEST","REVIEW_EXTENSION_REASON_UNKNOWN",
    }
    level = "HIGH" if any(f in high_flags for f in flags) else ("MEDIUM" if any(f in medium_flags for f in flags) else "LOW")

    return {
        "event_key": clean(row.get("event_key")),
        "fda_regulatory_case_id": clean(row.get("fda_regulatory_case_id")) or clean(row.get("event_key")),
        "ticker": clean(row.get("ticker")),
        "drug": clean(row.get("drug")),
        "pdufa_date": clean(row.get("pdufa_date")),
        "review_extension_status": extension_status,
        "extension_reason": extension_reason,
        "deficiency_notice_status": deficiency_status,
        "late_cycle_open_questions": late_cycle_status,
        "inspection_readiness": inspection,
        "prior_crl_remediation": remediation,
        "evidence_sufficiency_risk": evidence_risk,
        "dose_consistency_risk": dose_risk,
        "analytical_lab_relocation": lab_relocation,
        "remote_records_review": remote_review,
        "immunogenicity_signal": immunogenicity,
        "adcom_signal": adcom,
        "blindspot_risk_level": level,
        "blindspot_flags": " | ".join(dict.fromkeys(flags)),
        "source_note": source,
        "generated_at": now_utc(),
    }

def main():
    review = pd.read_csv(REVIEWS, dtype=str, keep_default_na=False)
    rows = [classify(r) for _, r in review.iterrows()]
    out = pd.DataFrame(rows, columns=COLUMNS)
    out.to_csv(OUT, index=False)
    print({
        "rows": len(out),
        "high": int((out["blindspot_risk_level"] == "HIGH").sum()),
        "medium": int((out["blindspot_risk_level"] == "MEDIUM").sum()),
        "low": int((out["blindspot_risk_level"] == "LOW").sum()),
    })

if __name__ == "__main__":
    main()
