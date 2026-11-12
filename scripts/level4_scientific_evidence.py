#!/usr/bin/env python3
"""Level 4 original-source experimental/statistical evidence inventory.

Read-only. Detects reviewable clinical-design and endpoint evidence in a CURRENT
ClinicalTrials.gov v2 record. It does NOT decide statistical significance, imply
successful trials, backtest blind predictions, or estimate FDA approval.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fetch_focus_registry_evidence import retrieve

NCT = re.compile(r"NCT[0-9]{8}\Z")
REGISTRY = "https://clinicaltrials.gov/api/v2/studies/"
MAX_BATCH = 32

def _object(value: Any) -> dict:
    return value if isinstance(value, dict) else {}

def _entries(value: Any) -> list[dict]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []

def _measure(entry: dict) -> tuple[str, str]:
    # This is a textual comparison hint, not an endpoint concordance finding.
    return (re.sub(r"\W+", "", str(entry.get("measure", "")).casefold()),
            re.sub(r"\W+", "", str(entry.get("timeFrame", "")).casefold()))

def summarize(record: dict, provenance: dict, *, as_of: str | None = None) -> dict:
    """Inventory primary-source fields, with fail-closed interpretation."""
    if not isinstance(record, dict) or not isinstance(provenance, dict):
        raise ValueError("Expected registry and provenance objects")
    protocol = _object(record.get("protocolSection"))
    ident = _object(protocol.get("identificationModule"))
    nct = ident.get("nctId")
    if not isinstance(nct, str) or not NCT.fullmatch(nct) or provenance.get("nct") != nct:
        raise ValueError("Registry/provenance NCT identity mismatch")
    if provenance.get("source_url") != REGISTRY + nct:
        raise ValueError("Unexpected original-source URL")
    if not re.fullmatch(r"[a-f0-9]{64}", str(provenance.get("sha256", ""))):
        raise ValueError("Missing exact original-source SHA256")
    if as_of is not None:
        # API is current-state, not a point-in-time reconstruction. We may not
        # claim sources were available prior to a past cutoff.
        if not isinstance(as_of, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):
            raise ValueError("Invalid as-of label")
    design = _object(protocol.get("designModule"))
    design_info = _object(design.get("designInfo"))
    status = _object(protocol.get("statusModule"))
    registered = _entries(_object(protocol.get("outcomesModule")).get("primaryOutcomes"))
    results = _object(record.get("resultsSection"))
    posted = _entries(_object(results.get("outcomeMeasuresModule")).get("outcomeMeasures"))
    posted_primary = [row for row in posted if row.get("type") == "PRIMARY"]
    posted_keys = {_measure(p) for p in posted_primary if all(_measure(p))}
    # Programmatic text matches are merely leads; reviewer must verify timing,
    # hierarchy, multiplicity, estimate, denominators, SAP and actual analysis.
    concordance_leads = sum(1 for row in registered
                            if all(_measure(row)) and _measure(row) in posted_keys)
    documents = _entries(_object(record.get("documentSection"))
                          .get("largeDocumentModule", {}).get("largeDocs"))
    document_types = sorted({str(doc.get("type", "")).upper()
                             for doc in documents if isinstance(doc.get("type"), str)})
    source_fields = {
        "study_type": design.get("studyType"),
        "phases": design.get("phases") if isinstance(design.get("phases"), list) else [],
        "allocation": design_info.get("allocation"),
        "masking": _object(design_info.get("maskingInfo")).get("masking"),
        "registered_primary_endpoints": len(registered),
        "posted_primary_outcome_records": len(posted_primary),
        "possible_textual_primary_endpoint_matches": concordance_leads,
        "registry_results_section_present": bool(results),
        "linked_document_types": document_types,
        "last_update_posted": _object(status.get("studyFirstPostDateStruct")).get("date"),
    }
    missing = []
    if not design.get("studyType"):
        missing.append("trial_design")
    if not registered:
        missing.append("registered_primary_endpoint")
    if not posted_primary:
        missing.append("primary_result_statistics")
    if not any(t in ("SAP", "STATISTICAL_ANALYSIS_PLAN") for t in document_types):
        missing.append("statistical_analysis_plan_document")
    # An accessible SAP alone does not verify multiplicity or endpoint analyses.
    missing.extend(("multiplicity_control_independent_review",
                    "prespecification_timing_independent_review",
                    "safety_benefit_risk_independent_review",
                    "independent_statistical_recalculation"))
    return {
        "nct": nct, "level": 4, "status": "SOURCE_FIELDS_INVENTORIED_REVIEW_REQUIRED",
        "source": {"url": provenance["source_url"],
                   "raw_sha256": provenance["sha256"],
                   "retrieved_at_utc": provenance.get("retrieved_at_utc"),
                   "source_type": "CLINICALTRIALS_GOV_PRIMARY_REGISTRY",
                   "source_revision": "CURRENT_STATE_NOT_HISTORICAL_FREEZE",
                   "requested_as_of": as_of},
        "observed_registry_fields": source_fields, "missing_or_unverified": missing,
        "interpretation_notes": [
            "Registered endpoints and posted results may reflect later amendments.",
            "Textual endpoint matches do not establish valid statistical analyses.",
            "Posted results, p-values and trial phase do not establish FDA approval.",
            "Outcome-blind historical assessment requires a separately frozen bundle."
        ],
        "original_source_retrieved": True, "source_facts_independently_verified": False,
        "scientific_stage_complete": False, "independent_review": "REQUIRED",
        "fda_prediction": None, "approval_probability": None, "clinical_score": None,
    }

def retrieve_and_summarize(nct: str, fetcher=retrieve) -> dict:
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Exact ASCII NCT identifier required")
    record, receipt = fetcher(nct)
    return summarize(record, receipt)

def process_ncts(ncts: list[str], fetcher=retrieve) -> dict:
    if not isinstance(ncts, list) or not (1 <= len(ncts) <= MAX_BATCH):
        raise ValueError("Expected between 1 and 32 exact NCT IDs")
    if any(not isinstance(n, str) or not NCT.fullmatch(n) for n in ncts) or len(set(ncts)) != len(ncts):
        raise ValueError("Invalid or duplicate study ID")
    reports = []
    for nct in ncts:
        try:
            reports.append(retrieve_and_summarize(nct, fetcher=fetcher))
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError) as exc:
            reports.append({
                "nct": nct, "status": "SOURCE_RETRIEVAL_OR_VALIDATION_BLOCKED",
                "blocker": type(exc).__name__, "scientific_stage_complete": False,
                "independent_review": "REQUIRED", "fda_prediction": None,
                "approval_probability": None
            })
    return {"level": 4, "status": "ORIGINAL_SOURCE_AUDIT_NOT_SCIENTIFIC_SIGNOFF",
            "retrieved": sum(x["status"] == "SOURCE_FIELDS_INVENTORIED_REVIEW_REQUIRED"
                             for x in reports),
            "total": len(ncts), "reports": reports,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "scientific_level_complete": False}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nct", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    batch = process_ncts(args.nct)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # No experimental source text is executed, and no FOCUS/POOL is modified.
    args.out.write_text(json.dumps(batch, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"status": batch["status"], "retrieved": batch["retrieved"],
                      "total": batch["total"], "scientific_level_complete": False}))
    return 0 if batch["retrieved"] == batch["total"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
