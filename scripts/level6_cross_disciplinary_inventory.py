#!/usr/bin/env python3
"""Level 6: read-only cross-disciplinary evidence *gap* inventory.

A verified ClinicalTrials.gov record provides the clinical registry source only.
Trial-linked preclinical publications and FDA regulatory documents require separate
primary-source retrieval, identity mapping and source receipts before counting
as independently verified. Nothing here is an application-level scientific
integration, clinical efficacy judgement or FDA prediction.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from fetch_focus_registry_evidence import retrieve
from level4_scientific_evidence import NCT, summarize

MAX_BATCH = 32
REGULATORY_SEARCH_HINT = "FDA_APPLICATION_SOURCE_NOT_YET_VERIFIED"
PRECLINICAL_SEARCH_HINT = "PRECLINICAL_PRIMARY_SOURCE_NOT_YET_VERIFIED"


def obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def phase_from_registry(record: dict) -> dict:
    """Report phase as a source *attribute*, not as application approval status."""
    protocol = obj(record.get("protocolSection"))
    design = obj(protocol.get("designModule"))
    status = obj(protocol.get("statusModule"))
    phases = design.get("phases")
    if not isinstance(phases, list):
        phases = []
    observed = [p for p in phases if isinstance(p, str) and
                p in {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"}]
    if "PHASE4" in observed:
        stage = "PHASE4"
    elif "PHASE3" in observed:
        stage = "PHASE3"
    elif "PHASE2" in observed:
        stage = "PHASE2"
    elif "PHASE1" in observed:
        stage = "PHASE1"
    elif "EARLY_PHASE1" in observed:
        stage = "EARLY_PHASE1"
    else:
        stage = "UNKNOWN_OR_NOT_APPLICABLE"
    return {
        "registry_phases": observed,
        "phase_bucket": stage,
        "registry_overall_status": status.get("overallStatus"),
        "phase_not_independently_adjudicated": True,
    }


def missing_classification(stage: str) -> dict:
    """Don't demand NDA files from studies that have not reached application stage."""
    if stage in {"PHASE1", "EARLY_PHASE1", "PHASE2"}:
        regulatory = "APPLICATION_DOCUMENTS_NOT_YET_EXPECTED_BY_TRIAL_PHASE"
    elif stage in {"PHASE3", "PHASE4"}:
        regulatory = "APPLICATION_STATUS_UNKNOWN_NOT_PROOF_OF_MISSING_FILING"
    else:
        regulatory = "APPLICATION_STATUS_UNKNOWN_PHASE_UNVERIFIED"
    return {
        "clinical_full_study_report": "NOT_IN_REGISTRY_NOT_ADJUDICATED",
        "preclinical_sources": PRECLINICAL_SEARCH_HINT,
        "regulatory_sources": regulatory,
        "nonpublic_CMC_or_inspection": "UNKNOWN_NOT_A_DEFICIENCY",
        "application_cycle_linkage": "UNVERIFIED",
        "integrated_safety_efficacy_adjudication": "NOT_DONE",
    }


def collect(record: dict, receipt: dict) -> dict:
    prior = summarize(record, receipt)
    phase = phase_from_registry(record)
    protocol = obj(record.get("protocolSection"))
    refs = obj(protocol.get("referencesModule")).get("references")
    references = [r for r in refs if isinstance(r, dict)] if isinstance(refs, list) else []
    # Registry bibliography may be outdated or irrelevant; no publication is
    # independently retrieved or classified as preclinical here.
    return {
        "nct": prior["nct"],
        "level": 6,
        "status": "CROSS_DISCIPLINARY_SOURCE_GAPS_INVENTORIED_REVIEW_REQUIRED",
        "clinical_sources": [{
            "domain": "CLINICAL_REGISTRY_ONLY",
            "source_url": prior["source"]["url"],
            "source_sha256": prior["source"]["raw_sha256"],
            "retrieved_at_utc": prior["source"]["retrieved_at_utc"],
            "source_revision": "CURRENT_STATE_NOT_HISTORICAL_FREEZE",
            "verified_receipt": True,
            "independently_reviewed": False,
            "full_trial_report_available": False,
        }],
        "preclinical_sources": [],
        "regulatory_sources": [],
        "registry_phase_context": phase,
        "registry_reference_count": len(references),
        "registry_references": {
            "status": "CITATION_LEADS_ONLY_NOT_FETCHED_NOT_CLASSIFIED",
            "source_evidence_count": 0,
        },
        "missing_or_unverified_by_phase": missing_classification(phase["phase_bucket"]),
        "clinical_preclinical_regulatory_integrated": False,
        "application_level_linkage_verified": False,
        "scientific_stage_complete": False,
        "independent_review": "REQUIRED",
        "fda_prediction": None,
        "approval_probability": None,
        "clinical_score": None,
        "interpretation_notes": [
            "ClinicalTrials.gov primary source is not proof of full clinical study report.",
            "Preclinical studies and FDA application documents need separate primary-source receipts.",
            "An absent public source is not a negative trial finding or a regulatory deficiency.",
            "Phase 1/2 study registry is not grounds to demand NDA/BLA approval letters.",
            "Current registry state cannot be used as blind historical evidence.",
        ],
    }


def process_ncts(ncts: list[str], *, fetcher=retrieve) -> dict:
    if (not isinstance(ncts, list) or not 1 <= len(ncts) <= MAX_BATCH or
            any(not isinstance(n, str) or not NCT.fullmatch(n) for n in ncts) or
            len(set(ncts)) != len(ncts)):
        raise ValueError("Expected 1-32 unique exact NCT identifiers")
    reports = []
    for nct in ncts:
        try:
            record, receipt = fetcher(nct)
            if obj(obj(record.get("protocolSection")).get("identificationModule")).get("nctId") != nct:
                raise ValueError("Requested/returned NCT identity mismatch")
            reports.append(collect(record, receipt))
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError) as exc:
            reports.append({
                "nct": nct, "level": 6,
                "status": "SOURCE_RETRIEVAL_OR_IDENTITY_VALIDATION_BLOCKED",
                "reason": type(exc).__name__, "scientific_stage_complete": False,
                "fda_prediction": None,
            })
    return {
        "level": 6,
        "status": "CROSS_DISCIPLINARY_EVIDENCE_GAP_INVENTORY_NOT_SCIENTIFIC_SIGNOFF",
        "total": len(ncts),
        "retrieved": sum(row.get("status") ==
                         "CROSS_DISCIPLINARY_SOURCE_GAPS_INVENTORIED_REVIEW_REQUIRED"
                         for row in reports),
        "reports": reports,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "preclinical_primary_sources_verified": 0,
        "regulatory_primary_sources_verified": 0,
        "scientific_level_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nct", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    batch = process_ncts(args.nct)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(batch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"total": batch["total"], "retrieved": batch["retrieved"],
                      "scientific_level_complete": False}))
    return 0 if batch["total"] == batch["retrieved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
