#!/usr/bin/env python3
"""Read-only, phase-first Level 1–6 evidence readiness for the exact FOCUS roster.

This consumes existing registry extraction checkpoints and application identity
*leads*. Neither captured registry fields nor a candidate application crosswalk
constitute source verification, scientific review, an FDA filing, or a forecast.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"}
ROOT = Path(__file__).resolve().parents[2]
ROSTER_PATH = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
APPLICATIONS_PATH = ROOT / "new-platform/backend/app/data/focus_application_snapshot.json"
DEFINITION_PATH = ROOT / "new-platform/frontend/data/deepMedicalTwentyLevelExpansion.json"


def _records(document, label):
    records = document.get("records") if isinstance(document, dict) else None
    if not isinstance(records, list) or not records:
        raise ValueError(f"{label}: expected a nonempty exact-NCT record list")
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{label}: invalid record")
        nct = record.get("nct")
        if not isinstance(nct, str) or not NCT_PATTERN.fullmatch(nct) or nct in indexed:
            raise ValueError(f"{label}: invalid or duplicate exact NCT")
        indexed[nct] = record
    return indexed


def _phase(fields):
    entry = fields.get("phase", {})
    raw = entry.get("value") if isinstance(entry, dict) and entry.get("status") == "CAPTURED_UNREVIEWED" else None
    if not isinstance(raw, list) or not raw or not all(isinstance(x, str) and x in PHASES for x in raw):
        return "UNRESOLVED", []
    if "PHASE3" in raw:
        group = "POTENTIAL_PIVOTAL_PHASE3"
    elif "PHASE4" in raw:
        group = "POSTMARKETING_PHASE4"
    elif any(x in raw for x in ("EARLY_PHASE1", "PHASE1", "PHASE2")):
        group = "EARLIER_PHASE"
    else:
        group = "UNRESOLVED"
    return group, raw


def _field(fields, key):
    item = fields.get(key)
    if not isinstance(item, dict) or item.get("status") != "CAPTURED_UNREVIEWED":
        return None
    value = item.get("value")
    return value if value is not None else None


def _level(number, name, fields, phase_group, indication_leads, source_captured):
    pointers = {
        1: (),
        2: ("phase", "studyOverallStatus", "studyLastUpdatePosted"),
        3: ("primaryEndpoints", "secondaryEndpoints"),
        4: ("allocation", "masking", "enrollment", "arms", "eligibility"),
        5: ("primaryEndpoints",),
        6: ("conditions", "primaryEndpoints"),
    }[number]
    present = [key for key in pointers if _field(fields, key) is not None]
    absent = [key for key in pointers if key not in present]
    evidence_requests = {
        1: ["original_registry_source_and_timestamp", "independent_identity_and_provenance_review"],
        2: ["independent_phase_and_current_study_status_verification"],
        3: ["phase_appropriate_clinical_results_and_safety_sources_if_available",
            "independent_results_and_endpoint_reconciliation"],
        4: ["full_protocol_and_amendments_if_public",
            "design_appropriateness_and_applicability_review"],
        5: ["original_statistical_plan_if_public",
            "phase_appropriate_statistical_methods_review"],
        6: ["indication_specific_endpoint_clinical_meaning",
            "independent_specialist_and_comparator_review"],
    }[number]
    result = {
        "level": number,
        "name": name,
        "registryFieldsCapturedUnreviewed": present,
        "registryFieldsNotCaptured": absent,
        "originalEvidenceRequests": evidence_requests,
        "sourceCaptureStatus": "CAPTURED_UNREVIEWED" if source_captured else "NOT_CAPTURED",
        "scientificReviewStatus": "NOT_ADJUDICATED",
        "readiness": "BLOCKED_ON_INDEPENDENT_EVIDENCE_REVIEW" if source_captured
                     else "BLOCKED_ON_REGISTRY_SOURCE",
        "assessmentCompleted": False,
        "scientificConclusion": None,
        "score": None,
        "approvalProbability": None,
    }
    if number == 2:
        result["currentPhaseReview"] = ("REGISTRY_PHASE_CAPTURED_NOT_VERIFIED"
                                        if phase_group != "UNRESOLVED" else "PHASE_UNRESOLVED")
        result["currentStatusReview"] = ("REGISTRY_STATUS_CAPTURED_NOT_VERIFIED"
                                         if _field(fields, "studyOverallStatus") else "STATUS_UNRESOLVED")
    elif number == 3:
        result["pivotalReadoutRequirement"] = (
            "NOT_YET_EXPECTED_AT_EARLIER_PHASE" if phase_group == "EARLIER_PHASE" else
            "REVIEW_PHASE3_RESULTS_AVAILABILITY" if phase_group == "POTENTIAL_PIVOTAL_PHASE3" else
            "NOT_AUTOMATICALLY_REQUIRED_FOR_PHASE4" if phase_group == "POSTMARKETING_PHASE4" else
            "PHASE_UNRESOLVED"
        )
        result["registeredEndpointsAreNotResults"] = True
    elif number == 4:
        result["designFieldAbsence"] = "REVIEW_NOT_AUTOMATIC_DEFICIENCY"
    elif number == 5:
        result["pivotalSAPRequirement"] = (
            "NOT_YET_EXPECTED_AT_EARLIER_PHASE" if phase_group == "EARLIER_PHASE" else
            "PIVOTAL_SAP_AND_MULTIPLICITY_REVIEW_REQUIRED" if phase_group == "POTENTIAL_PIVOTAL_PHASE3" else
            "REVIEW_APPLICABILITY" if phase_group == "POSTMARKETING_PHASE4" else
            "PHASE_UNRESOLVED"
        )
    elif number == 6:
        result["indicationLeadsNotVerified"] = indication_leads
        result["endpointRelevanceRequiresSpecialist"] = True
    return result


def build(roster, application_snapshot, checkpoint, definition, submissions=None,
          local_receipts=None, evidence_root=None, source_cases=None, review_proposals=None):
    """Return non-predictive, non-mutating readiness for every canonical FOCUS NCT."""
    records = _records(roster, "canonical roster")
    apps = _records(application_snapshot, "application crosswalk")
    if not set(apps).issubset(records):
        raise ValueError("Application crosswalk references NCT outside the current FOCUS roster")
    definitions = definition.get("levels") if isinstance(definition, dict) else None
    if not isinstance(definitions, list) or [x.get("level") for x in definitions[:6]] != list(range(1, 7)):
        raise ValueError("Missing or reordered assessment Levels 1–6 definitions")
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("results", {}), dict):
        raise ValueError("Invalid registry checkpoint")
    captures = checkpoint.get("results", {})
    if not set(captures).issubset(records):
        raise ValueError("Checkpoint contains evidence outside the FOCUS roster")

    submissions_by_nct = {nct: [] for nct in records}
    if submissions is not None:
        spec = importlib.util.spec_from_file_location(
            "level16_source_submissions", Path(__file__).with_name("level16_source_submissions.py")
        )
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        submissions_by_nct = validator.validate(submissions, records, apps, checkpoint)

    if (local_receipts is None) != (evidence_root is None):
        raise ValueError("Local receipt manifest and evidence root must be supplied together")
    if local_receipts is not None and submissions is None:
        raise ValueError("Local receipts require validated source submissions")
    byte_consistency = None
    if local_receipts is not None:
        spec = importlib.util.spec_from_file_location(
            "level16_local_byte_receipts",
            Path(__file__).with_name("level16_local_byte_receipts.py")
        )
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        result = checker.match_local_bytes(
            submissions_by_nct, local_receipts, evidence_root)
        byte_consistency = result["summary"]
        for items in submissions_by_nct.values():
            for source in items:
                source["localByteReceipt"] = result["receipts"].get(
                    source["submissionId"],
                    {"byteMatchStatus": "NO_LOCAL_RECEIPT",
                     "computedSha256": None, "bytesRead": 0}
                )

    dossiers, proposals = {}, {}
    if source_cases is not None or review_proposals is not None:
        if submissions is None:
            raise ValueError("Review cases require validated source submissions")
        spec = importlib.util.spec_from_file_location(
            "level16_review_cases", Path(__file__).with_name("level16_review_cases.py"))
        cases = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cases)
        dossiers, proposals = cases.prepare(submissions_by_nct, submissions["cutoffDate"],
                                            source_cases, review_proposals)
        for items in submissions_by_nct.values():
            for source in items:
                source["sourceVerificationCase"] = dossiers.get(source["submissionId"])

    rows, cycle_ids = [], set()
    for nct, record in records.items():
        app = apps.get(nct)
        candidates = app.get("candidateApplications") if app is not None else []
        if not isinstance(candidates, list):
            raise ValueError("Invalid candidate application links")
        ids, indications = [], set()
        for candidate in candidates:
            if not isinstance(candidate, dict) or candidate.get("ticker") != record.get("ticker"):
                raise ValueError("Candidate application ticker/identity mismatch")
            cycle = candidate.get("cycleId")
            indication = candidate.get("indication")
            if not isinstance(cycle, str) or not cycle.strip() or cycle in ids:
                raise ValueError("Missing or duplicated candidate application cycle")
            ids.append(cycle)
            cycle_ids.add(cycle)
            if isinstance(indication, str) and indication.strip():
                indications.add(indication.strip())
        checkpoint_record = captures.get(nct, {})
        if not isinstance(checkpoint_record, dict):
            raise ValueError("Invalid checkpoint record")
        capture_status = checkpoint_record.get("status", "NOT_CAPTURED")
        if capture_status not in {"CAPTURED_UNREVIEWED", "RETRY_REQUIRED", "NOT_CAPTURED"}:
            raise ValueError("Unrecognized checkpoint capture status")
        source_captured = capture_status == "CAPTURED_UNREVIEWED"
        fields, source = {}, None
        if source_captured:
            evidence = checkpoint_record.get("evidence")
            if not isinstance(evidence, dict) or evidence.get("nct") != nct:
                raise ValueError("Registry source identity mismatch")
            if evidence.get("source") != f"https://clinicaltrials.gov/study/{nct}":
                raise ValueError("Registry source locator mismatch")
            if not isinstance(evidence.get("sha256"), str) or not SHA256_PATTERN.fullmatch(evidence["sha256"]):
                raise ValueError("Missing original-source digest in captured evidence")
            fields = evidence.get("fields")
            if not isinstance(fields, dict):
                raise ValueError("Invalid captured registry fields")
            source = {"url": evidence["source"], "sha256": evidence["sha256"],
                      "independentlyVerified": False}
        phase_group, captured_phases = _phase(fields)
        study_status = _field(fields, "studyOverallStatus")
        levels = [_level(d["level"], d["name"], fields, phase_group,
                         sorted(indications), source_captured) for d in definitions[:6]]
        for level in levels:
            submitted = [item for item in submissions_by_nct[nct]
                         if item["level"] == level["level"]]
            level["reviewProposalsUnreviewed"] = proposals.get(nct, {}).get(level["level"], [])
            level["submittedEvidenceLeads"] = submitted
            level["sourceSubmissionCount"] = len(submitted)
            level["sourceReviewQueueStatus"] = (
                "AWAITING_INDEPENDENT_SOURCE_AUTHENTICATION" if submitted
                else "NO_SOURCE_SUBMISSION"
            )
            if submitted:
                level["readiness"] = "SOURCE_METADATA_SUBMITTED_REVIEW_REQUIRED"
        rows.append({
            "nct": nct, "ticker": record.get("ticker"), "company": record.get("company"),
            "phaseGroup": phase_group,
            "capturedRegistryPhasesUnreviewed": captured_phases,
            "capturedStudyStatusUnreviewed": study_status,
            "registrySource": source, "registryCaptureStatus": capture_status,
            "candidateApplicationCycleIdsUnverified": ids,
            "candidateIndicationsUnverified": sorted(indications),
            "applicationCycleVerification": ("PROVISIONAL_NOT_FDA_VERIFIED" if app is not None
                                             else "NOT_MAPPED_APPLICATION_CYCLE"),
            "sourceSubmissionCount": len(submissions_by_nct[nct]),
            "levels": levels, "completedLevels": 0, "scientificReviews": 0,
            "fdaOutcomeJudgment": None, "fdaTimingJudgment": None,
        })
    return {
        "schemaVersion": 1, "status": "PHASE_FIRST_EVIDENCE_TRIAGE_ONLY",
        "rosterAsOf": roster.get("asOf"),
        "applicationSnapshotAsOf": application_snapshot.get("asOf"),
        "checkpointGeneratedAt": checkpoint.get("generatedAt"),
        "focusTrialCount": len(rows), "provisionalApplicationCycleCount": len(cycle_ids),
        "mappedTrialCount": len(apps), "unmappedTrialCount": len(rows) - len(apps),
        "scientificallyAdjudicatedLevels": 0, "calibratedFdaPredictions": 0,
        "sourceSubmissionCount": sum(len(items) for items in submissions_by_nct.values()),
        "sourceVerificationCaseCount": len(dossiers),
        "unreviewedProposalCount": sum(len(items) for levels in proposals.values() for items in levels.values()),
        "originalSourcesIndependentlyAuthenticated": 0,
        "localByteConsistency": byte_consistency,
        "levelsPerTrial": 6, "trials": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=Path, default=ROSTER_PATH)
    parser.add_argument("--applications", type=Path, default=APPLICATIONS_PATH)
    parser.add_argument("--definition", type=Path, default=DEFINITION_PATH)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--source-submissions", type=Path,
                        help="Optional unreviewed, point-in-time evidence-submission JSON")
    parser.add_argument("--local-byte-receipts", type=Path,
                        help="Optional bounded local document byte-receipt manifest")
    parser.add_argument("--evidence-root", type=Path,
                        help="Existing private directory holding original permitted source files")
    parser.add_argument("--source-cases", type=Path, help="Unreviewed source-verification dossiers")
    parser.add_argument("--review-proposals", type=Path, help="Unreviewed scientific-review proposals")
    args = parser.parse_args()
    inputs = [json.loads(path.read_text(encoding="utf-8")) for path in
              (args.roster, args.applications, args.checkpoint, args.definition)]
    submitted = (json.loads(args.source_submissions.read_text(encoding="utf-8"))
                 if args.source_submissions else None)
    receipt_manifest = (json.loads(args.local_byte_receipts.read_text(encoding="utf-8"))
                        if args.local_byte_receipts else None)
    report = build(*inputs, submissions=submitted,
                   local_receipts=receipt_manifest, evidence_root=args.evidence_root,
                   source_cases=json.loads(args.source_cases.read_text(encoding="utf-8")) if args.source_cases else None,
                   review_proposals=json.loads(args.review_proposals.read_text(encoding="utf-8")) if args.review_proposals else None)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
