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
FACILITIES = DATA / "fda_facility_registry.csv"
OUT = DATA / "fda_regulatory_signal_monitor.csv"

COLUMNS = [
    "event_key","fda_regulatory_case_id","ticker","drug","pdufa_date",
    "review_extension_status","extension_reason","deficiency_notice_status",
    "late_cycle_open_questions","inspection_readiness","prior_crl_remediation",
    "prior_crl_unresolved_discipline","facility_site_visibility",
    "third_party_cmo_dependency","postmarketing_study_alignment",
    "late_fda_reversal_exposure","evidence_sufficiency_risk","dose_consistency_risk",
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

def classify(row, facility_rows=None):
    source = clean(row.get("fda_source_note"))
    gate_reason = clean(row.get("fda_gate_reason"))
    source_text = source.lower()
    text = f"{source} {gate_reason}".lower()
    flags = []
    facility_rows = facility_rows or []

    # Regulatory-interaction events must be derived from the actual evidence
    # note, not from generic unresolved-gate boilerplate.
    extension = contains(source_text, "pdufa extended", "extended to", "review extension", "extension after", "pdufa date extension")
    extension_status = "YES" if extension else "NO"
    extension_reason = "NONE"
    if extension:
        if contains(source_text, "manufacturing", "cmc", "product quality", "facility"):
            extension_reason = "CMC_MANUFACTURING"
            flags.append("REVIEW_EXTENSION_CMC_MANUFACTURING")
        elif contains(source_text, "sensitivity analyses", "additional analyses", "additional data", "longer-term data", "clinical data"):
            extension_reason = "CLINICAL_DATA_ANALYSIS"
            flags.append("REVIEW_EXTENSION_CLINICAL_DATA")
        elif contains(source_text, "labeling", "post-marketing", "postmarketing"):
            extension_reason = "LABELING_POSTMARKETING"
            flags.append("REVIEW_EXTENSION_LABELING")
        elif contains(source_text, "information request", "information requests", "major amendment"):
            extension_reason = "GENERAL_INFO_REQUEST"
            flags.append("REVIEW_EXTENSION_INFORMATION_REQUEST")
        else:
            extension_reason = "UNKNOWN"
            flags.append("REVIEW_EXTENSION_REASON_UNKNOWN")

    explicit_deficiency = (
        contains(source_text, "deficiency", "deficiencies") and
        contains(source_text, "preclud", "unresolved", "remains a major regulatory risk", "additional evidence")
    )
    deficiency_status = "OPEN" if explicit_deficiency else "NONE"
    if explicit_deficiency:
        flags.append("FDA_DEFICIENCY_NOTICE_OPEN")

    late_cycle = contains(source_text, "late-cycle", "late cycle", "mid-cycle", "mid cycle")
    late_open = late_cycle and contains(source_text, "remaining questions", "unresolved", "review issues", "major safety or efficacy concerns")
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

    prior_crl = contains(source_text, "prior crl", "after prior crl", "resubmission", "complete response")
    if prior_crl and contains(source_text, "unresolved", "remains a major regulatory risk", "additional evidence of effectiveness was required", "until fda accepts"):
        remediation = "UNRESOLVED"
        flags.append("PRIOR_CRL_REMEDIATION_UNRESOLVED")
    elif prior_crl and contains(source_text, "addressed", "remediation", "reinspection", "complete response"):
        remediation = "VERIFIED_OR_CLAIMED"
        flags.append("PRIOR_CRL_REMEDIATION_SIGNAL")
    elif prior_crl:
        remediation = "UNKNOWN"
        flags.append("PRIOR_CRL_REMEDIATION_UNKNOWN")
    else:
        remediation = "NOT_APPLICABLE"

    # Residual-miss blind spots: keep these advisory. A missing public site or
    # unresolved prior discipline is not itself a CRL, but it should reduce
    # confidence and trigger focused evidence collection.
    if prior_crl and contains(
        source_text,
        "remains a major regulatory risk",
        "additional evidence of effectiveness was required",
        "did not publicly document closure",
        "lacked an equivalent public closure signal",
    ):
        prior_unresolved = "YES"
        flags.append("PRIOR_CRL_DISCIPLINE_UNRESOLVED")
    elif prior_crl:
        prior_unresolved = "UNKNOWN"
    else:
        prior_unresolved = "NOT_APPLICABLE"

    identified_sites = []
    for site in facility_rows:
        name = clean(site.get("site_name"))
        if name and not contains(name.lower(), "not publicly identified", "unknown", "not identified"):
            identified_sites.append(name)
    if facility_rows and len(identified_sites) == len(facility_rows):
        facility_visibility = "IDENTIFIED"
    elif facility_rows and identified_sites:
        facility_visibility = "PARTIAL"
    elif facility_rows:
        facility_visibility = "NOT_PUBLIC"
    else:
        facility_visibility = "UNKNOWN"

    facility_dependency = contains(
        source_text,
        "pre-license inspection", "prelicensure inspection", "pre-licensure inspection",
        "facility inspection", "manufacturing site", "manufacturing facility",
        "scheduled pre-licensure inspections", "required inspections",
    )
    if facility_visibility in {"PARTIAL","NOT_PUBLIC"} and (
        facility_dependency or clean(row.get("fda_facility_gate")).upper() == "REVIEW"
    ):
        flags.append("FACILITY_SITE_VISIBILITY_GAP")

    third_party = contains(
        source_text,
        "third-party cmo", "third party cmo", "third-party manufacturer",
        "third party manufacturer", "contract manufacturer", "contract manufacturing",
    )
    third_party_cmo = "YES" if third_party else "UNKNOWN"
    if third_party and facility_visibility != "IDENTIFIED":
        flags.append("THIRD_PARTY_CMO_VISIBILITY_GAP")

    postmarketing_study = (
        contains(source_text, "post-marketing", "postmarketing") and
        contains(source_text, "study", "trial", "requirement", "commitment")
    )
    postmarketing_alignment = "YES" if postmarketing_study else "NO"
    if postmarketing_study and contains(source_text, "aligned", "agreed", "agreement", "planned"):
        reversal_exposure = "WATCH"
        flags.append("POSTMARKETING_ALIGNMENT_REVERSAL_WATCH")
    else:
        reversal_exposure = "NONE"

    primary = clean(row.get("fda_primary_endpoint_status")).upper()
    stats_gate = clean(row.get("fda_statistics_gate")).upper()
    single_pivotal = contains(source_text, "one pivotal", "single pivotal", "based on one pivotal") and "phase 3" in source_text
    dose_split = contains(source_text, "did not achieve statistical significance", "not statistically significant") and contains(
        source_text, "once-weekly", "twice-weekly", "dosing regimen", "tested regimen", "tested dose"
    )
    phase2_external = "full approval" in source_text and "phase 2" in source_text and contains(source_text, "external comparator", "natural-history", "natural history")
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

    lab_relocation = "YES" if ("laborator" in source_text and contains(source_text, "moved", "relocation", "new location")) else "NO"
    if lab_relocation == "YES":
        flags.append("CRITICAL_LAB_RELOCATION")

    remote_review = "YES" if contains(source_text, "remote review of records", "remote records review", "remote manufacturing records") else "NO"
    if remote_review == "YES":
        flags.append("REMOTE_RECORDS_REVIEW")

    if contains(source_text, "immunogenicity", "anti-drug antibod", "antidrug antibod") and contains(source_text, "high", "77%", "77.1%", "persistent"):
        immunogenicity = "HIGH"
        flags.append("IMMUNOGENICITY_SIGNAL")
    elif contains(source_text, "immunogenicity", "anti-drug antibod", "antidrug antibod"):
        immunogenicity = "REVIEW"
    else:
        immunogenicity = "UNKNOWN"

    if contains(source_text, "adcom", "advisory committee", "advisory-committee"):
        if contains(source_text, "favorable", "positive vote", "recommended approval", "strong endorsement"):
            adcom = "POSITIVE"
        elif contains(source_text, "negative", "voted against", "did not recommend"):
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
        "FACILITY_SITE_VISIBILITY_GAP","THIRD_PARTY_CMO_VISIBILITY_GAP",
        "PRIOR_CRL_DISCIPLINE_UNRESOLVED","POSTMARKETING_ALIGNMENT_REVERSAL_WATCH",
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
        "prior_crl_unresolved_discipline": prior_unresolved,
        "facility_site_visibility": facility_visibility,
        "third_party_cmo_dependency": third_party_cmo,
        "postmarketing_study_alignment": postmarketing_alignment,
        "late_fda_reversal_exposure": reversal_exposure,
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
    facilities = pd.read_csv(FACILITIES, dtype=str, keep_default_na=False) if FACILITIES.exists() else pd.DataFrame()
    facility_by_event = {}
    if not facilities.empty:
        for _, site in facilities.iterrows():
            facility_by_event.setdefault(clean(site.get("event_key")), []).append(site)
    rows = [
        classify(r, facility_by_event.get(clean(r.get("event_key")), []))
        for _, r in review.iterrows()
    ]
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
