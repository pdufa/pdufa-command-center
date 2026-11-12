#!/usr/bin/env python3
"""Phase-first Level 3 evidence-readiness dossiers from local registry captures.

Runs offline from the exact-NCT, checksum-verified cache. This is research
triage, not clinical/biological adjudication, efficacy scoring, FDA forecasting,
or a change to any production prediction. Missing data means not retrieved or
not source-reported, NOT negative trial evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from windows_local_agent_live_focus_registry import (
    ROOT, ROSTER, REPORTS, CAPTURES, valid_cache, verified_roster, atomic_json,
)

VALID_PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"}
NCT_RE = re.compile(r"NCT[0-9]{8}\Z")
MAX_ENDPOINTS = 30
MAX_INTERVENTIONS = 30


def _object(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Registry evidence structure is not an object")
    return value


def _objects(value: object, limit: int) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(v, dict) for v in value):
        raise ValueError("Registry evidence list invalid or oversized")
    return value


def _short(value: object, max_length: int = 600) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > max_length:
        raise ValueError("Malformed registry source text")
    return value.strip() or None


def _labels(value: object, limit: int = 20) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError("Invalid registry label list")
    result = [_short(v, 250) for v in value]
    if any(not x for x in result):
        raise ValueError("Invalid blank registry label")
    return result


def extract_study_context(nct: str, record: dict) -> dict:
    """Extract reported source fields; never infer trial success from presence."""
    if not isinstance(nct, str) or not NCT_RE.fullmatch(nct):
        raise ValueError("Invalid exact trial identity")
    sections = _object(record)
    protocol = _object(sections.get("protocolSection"))
    identity = _object(protocol.get("identificationModule"))
    if identity.get("nctId") != nct:
        raise ValueError("Registry source does not match trial identity")
    design = _object(protocol.get("designModule") or {})
    status = _object(protocol.get("statusModule") or {})
    outcomes = _object(protocol.get("outcomesModule") or {})
    interventions = _object(protocol.get("armsInterventionsModule") or {})
    conditions = _object(protocol.get("conditionsModule") or {})
    phases = _labels(design.get("phases"), limit=8)
    if any(p not in VALID_PHASES for p in phases):
        raise ValueError("Unrecognized registry trial phase")
    phase3_or_later = any(p in ("PHASE3", "PHASE4") for p in phases)
    earlier_phase = bool(phases) and not phase3_or_later and all(
        p in ("EARLY_PHASE1", "PHASE1", "PHASE2") for p in phases
    )
    if phase3_or_later:
        phase_group = "PHASE3_OR_LATER_SOURCE_REPORTED"
    elif earlier_phase:
        phase_group = "EARLIER_PHASE_SOURCE_REPORTED"
    else:
        phase_group = "PHASE_UNRESOLVED_OR_NOT_APPLICABLE"
    primary = _objects(outcomes.get("primaryOutcomes"), MAX_ENDPOINTS)
    treatments = _objects(interventions.get("interventions"), MAX_INTERVENTIONS)
    result_section = sections.get("resultsSection")
    results = _object(result_section) if result_section is not None else {}
    result_outcomes = _object(results.get("outcomeMeasuresModule") or {})
    result_adverse = _object(results.get("adverseEventsModule") or {})
    result_flow = _object(results.get("participantFlowModule") or {})
    posted_measures = _objects(result_outcomes.get("outcomeMeasures"), 100)
    endpoint_names = []
    for item in primary:
        endpoint_names.append({
            "source_reported_measure": _short(item.get("measure"), 500),
            "source_reported_time_frame": _short(item.get("timeFrame"), 300),
        })
    medication_names = [_short(i.get("name"), 250) for i in treatments]
    review_questions = [
        "Reconcile exact NCT, sponsor/indication and recorded study phase against primary sources",
        "Check original prespecified endpoint definitions, amendments, comparators and analysis plan",
        "Seek independently reviewed biological mechanism, target engagement and competing explanations",
        "Determine whether original efficacy, safety and exposure results support any clinical interpretation",
        "Confirm FDA application cycle, CMC and regulatory evidence separately; registry data cannot establish approval",
    ]
    if phase_group == "EARLIER_PHASE_SOURCE_REPORTED":
        review_questions.extend([
            "Review phase-appropriate pharmacology, PK/PD, target engagement and dose-finding evidence",
            "Do not require Phase 3 readout or final pivotal safety data at an earlier phase",
        ])
    elif phase_group == "PHASE3_OR_LATER_SOURCE_REPORTED":
        review_questions.extend([
            "Review phase-appropriate pivotal results, effect sizes, confidence intervals and multiplicity if available",
            "Review reported serious adverse events, attrition and randomized denominators if available",
        ])
    else:
        review_questions.append("Resolve reported study phase before selecting phase-specific scientific requirements")
    missing = []
    if not phases or phase_group == "PHASE_UNRESOLVED_OR_NOT_APPLICABLE":
        missing.append("phase_not_resolved_from_registry")
    if not primary:
        missing.append("primary_endpoint_not_found_in_registry")
    if not treatments:
        missing.append("intervention_not_found_in_registry")
    if phase3_or_later and not posted_measures:
        missing.append("pivotal_result_measures_not_found_in_registry")
    return {
        "nct": nct,
        "registry_reported_phase": phases,
        "phase_group": phase_group,
        "registry_reported_status": _short(status.get("overallStatus"), 120),
        "registry_reported_conditions": _labels(conditions.get("conditions"), 40),
        "registry_reported_interventions": medication_names,
        "registry_reported_primary_endpoints": endpoint_names,
        "registry_results_module_present": bool(result_section),
        "registry_result_measure_count": len(posted_measures),
        "registry_adverse_events_module_present": bool(result_adverse),
        "registry_participant_flow_module_present": bool(result_flow),
        "missing_registry_source_fields": missing,
        "phase_appropriate_review_questions": review_questions,
        "scientific_signoff": False,
        "source_facts_independently_adjudicated": False,
        "mechanism_validated": False,
        "clinical_efficacy_established": False,
        "fda_prediction": None,
        "approval_probability": None,
        "clinical_score": None,
        "status": "RESEARCH_ONLY_REQUIRES_INDEPENDENT_REVIEW",
    }


def build_readiness(roster_bytes: bytes, directory: Path, now: datetime) -> dict:
    if not isinstance(roster_bytes, bytes) or not isinstance(directory, Path):
        raise ValueError("Invalid source inputs")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Time must be timezone-aware")
    if directory.is_symlink() or directory.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Source captures must stay outside Git checkout")
    roster = json.loads(roster_bytes.decode("utf-8"))
    ncts = verified_roster(roster)
    digest = hashlib.sha256(roster_bytes).hexdigest()
    entries = []
    available = 0
    for row in roster["records"]:
        nct = row["nct"]
        path = directory / f"{nct}.json"
        if not valid_cache(path, nct, digest, now):
            entries.append({
                "nct": nct, "ticker": row.get("ticker"),
                "source_status": "FRESH_EXACT_NCT_REGISTRY_CAPTURE_NOT_AVAILABLE",
                "registry_evidence": None,
                "scientific_signoff": False,
                "fda_prediction": None,
                "approval_probability": None,
                "clinical_score": None,
            })
            continue
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            context = extract_study_context(nct, receipt["record"])
            available += 1
            entries.append({
                "nct": nct, "ticker": row.get("ticker"),
                "source_status": "FRESH_EXACT_NCT_SOURCE_CAPTURED_NOT_SCIENTIFICALLY_ADJUDICATED",
                "registry_record_retrieved_at_utc": receipt["retrieved_at_utc"],
                "registry_source_url": receipt["source_url"],
                "registry_record_sha256": receipt["normalized_record_sha256"],
                "registry_evidence": context,
                "scientific_signoff": False,
                "fda_prediction": None,
                "approval_probability": None,
                "clinical_score": None,
            })
        except (ValueError, TypeError, KeyError, OSError, UnicodeError):
            entries.append({
                "nct": nct, "ticker": row.get("ticker"),
                "source_status": "REGISTRY_CAPTURE_SCHEMA_REQUIRES_REVIEW",
                "registry_evidence": None,
                "scientific_signoff": False,
                "fda_prediction": None,
                "approval_probability": None,
                "clinical_score": None,
            })
    return {
        "schema_version": 1,
        "kind": "LEVEL3_PHASE_FIRST_REGISTRY_EVIDENCE_TRIAGE_NOT_ASSESSMENT",
        "roster_as_of": roster["asOf"],
        "roster_sha256": digest,
        "built_at_utc": now.astimezone(timezone.utc).isoformat(),
        "trial_count": len(ncts),
        "fresh_source_contexts": available,
        "sources_without_usable_fresh_context": len(ncts) - available,
        "scientific_reviews_completed": 0,
        "calibrated_fda_predictions_created": 0,
        "independent_mechanism_reviews_completed": 0,
        "repository_modified": False,
        "production_modified": False,
        "records": entries,
    }


def main() -> int:
    try:
        audit = subprocess.run(
            [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
            cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=240,
        )
        if audit.returncode != 0:
            print("STOP: Retirement safety audit failed")
            return 2
        if ROSTER.is_symlink() or not ROSTER.is_file():
            raise ValueError("No trusted FOCUS roster available")
        if REPORTS.is_symlink() or REPORTS.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Reports location cannot be under repository")
        now = datetime.now(timezone.utc)
        result = build_readiness(ROSTER.read_bytes(), CAPTURES, now)
        REPORTS.mkdir(parents=True, exist_ok=True)
        stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
        target = REPORTS / f"level3-focus-readiness-{stamp}.json"
        atomic_json(target, result)
        print("PASS: Retired systems safety audit")
        print("Level 3 source contexts:", result["fresh_source_contexts"], "of", result["trial_count"])
        print("Unresolved fresh source contexts:", result["sources_without_usable_fresh_context"])
        print("Scientific reviews completed:", result["scientific_reviews_completed"])
        print("FDA predictions created:", result["calibrated_fda_predictions_created"])
        print("Local phase-first evidence report:", target)
        print("No generated efficacy verdicts, calibrated probabilities or production changes")
        return 0
    except (OSError, ValueError, TypeError, UnicodeError, subprocess.TimeoutExpired) as exc:
        print("STOP: Level 3 source readiness failed:", type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
