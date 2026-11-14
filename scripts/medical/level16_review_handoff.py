#!/usr/bin/env python3
"""Read-only Level 1–6 scientific REVIEW HANDOFF from FOCUS research coverage.

This is a work queue for qualified humans, never a source attestation,
adjudication, clinical conclusion, FDA forecast, blind backtest or site release.
It cannot create reviewers, permissions, events or live staging resources.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports/scientific-levels1-6"
COVERAGE = REPORTS / "scientific-coverage-20261114.json"
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
APPLICATIONS = ROOT / "new-platform/backend/app/data/focus_application_snapshot.json"
ORCA2 = REPORTS / "orca2-statistical-chronology-20261114.json"
ORCA2_PUBLICATION = REPORTS / "orca2-publication-outcomes-20261114.json"
ORCA3_PUBLICATION = REPORTS / "orca3-publication-outcomes-20261114.json"
NCT_RE = re.compile(r"NCT[0-9]{8}\Z")
LEVEL_NAMES = {
    1: "Original source identity and provenance",
    2: "Phase, indication, status and study identity",
    3: "Phase-specific efficacy and safety",
    4: "Protocol, trial design and execution",
    5: "Statistical plan and methods",
    6: "Disease-specific endpoint clinical relevance",
}
REVIEW_STEPS = [
    "Authorized source verifier authenticates original source ownership, bytes, versions and cutoff",
    "Separately authorized clinician or biostatistician conducts evidence-linked scientific review",
    "Independent qualified challenger reviews findings and contradictory evidence",
    "Separate authorized adjudicator resolves blockers and records the final decision",
]
ORCA_NCT = "NCT04576949"
ORCA3_NCT = "NCT05206370"


def _source_record(record, kind, require_ticker=True):
    if not isinstance(record, dict) or not NCT_RE.fullmatch(str(record.get("nct", ""))):
        raise ValueError(f"{kind}: invalid exact NCT record")
    if require_ticker:
        ticker = record.get("ticker")
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError(f"{kind}: missing ticker")
    return record["nct"]


def _index(records, kind, require_ticker=True):
    if not isinstance(records, list) or not records:
        raise ValueError(f"{kind}: missing records")
    result = {}
    for record in records:
        nct = _source_record(record, kind, require_ticker=require_ticker)
        if nct in result:
            raise ValueError(f"{kind}: duplicate NCT")
        result[nct] = record
    return result


def _status(collected):
    if type(collected) is not bool:
        raise ValueError("Source coverage flags must be actual booleans")
    return "COLLECTED_UNREVIEWED" if collected else "NOT_COLLECTED_AVAILABILITY_UNRESOLVED"


def _level_rows(row, orca_chronology, publication=None, publication3=None):
    fields = {
        "originalRegistry": row["registry"],
        "registeredProtocol": row["protocol"],
        "registeredSAP": row["sap"],
        "postedRegistryResults": row["postedResults"],
    }
    phase = row.get("phaseUnreviewed")
    if (not isinstance(phase, list) or not phase
            or any(p not in ("PHASE1", "EARLY_PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA") for p in phase)):
        raise ValueError("Registry phase must be captured but remains unreviewed")
    earlier_only = bool(set(phase) <= {"EARLY_PHASE1", "PHASE1", "PHASE2"})
    phase_mixed = "PHASE2" in phase and "PHASE3" in phase
    levels = []
    for i, name in LEVEL_NAMES.items():
        evidence_needed = {
            1: ["Original registry/source provenance, true ownership, document versions and amendments"],
            2: ["Independent current phase/status, indication, population and application-cycle reconciliation"],
            3: ["Phase-appropriate original efficacy and safety datasets; analysis populations and uncertainty"],
            4: ["Original protocol, amendments and actual trial conduct/eligibility/controls"],
            5: ["Original SAP, amendment chronology, database lock/unblinding and multiplicity review"],
            6: ["Independent disease-specialist review of endpoint meaningfulness, comparators and harms"],
        }[i]
        if i == 1:
            status = _status(fields["originalRegistry"])
        elif i == 2:
            status = _status(fields["originalRegistry"])
        elif i == 3:
            status = _status(fields["postedRegistryResults"])
        elif i == 4:
            status = _status(fields["registeredProtocol"])
        elif i == 5:
            status = _status(fields["registeredSAP"])
        else:
            status = _status(fields["originalRegistry"])
        if i in (3, 5) and earlier_only:
            applicability = "FUTURE_PIVOTAL_PHASE3_PACKAGE_NOT_YET_EXPECTED"
        elif i in (3, 5) and phase_mixed:
            applicability = "MIXED_PHASE2_PHASE3_REQUIRES_APPLICABILITY_REVIEW"
        else:
            applicability = "REVIEW_AT_CAPTURED_PHASE"
        questions = list(evidence_needed)
        if i == 3 and not row["postedResults"]:
            questions.append("Determine whether results are expected, pending, unpublished or unavailable; do not presume failure")
        if i == 5 and not row["sap"]:
            questions.append("Determine SAP public availability and prespecification timing; absent file is not proof of a statistical flaw")
        if i == 5 and row["nct"] == ORCA_NCT:
            questions.extend([
                "Reconcile published protocol's pre-completion Hochberg plan with later SAP versions",
                "Obtain actual database-lock/unblinding chronology and final signed SAP history",
            ])
        if i == 6:
            questions.append("Interpret actual indication/population and patient-relevant benefit without inventing a conclusion")
        if row["mappingStatus"] == "NOT_MAPPED_APPLICATION_CYCLE" and i == 2:
            questions.append("No verified FDA application-cycle link: do not invent or infer one")
        published = None
        selected_publication = (
            publication if row["nct"] == ORCA_NCT else
            publication3 if row["nct"] == ORCA3_NCT else None
        )
        if i in (3, 4, 6) and selected_publication is not None:
            report = selected_publication
            if row["nct"] == ORCA3_NCT:
                comparisons = [
                    {
                        **item, "classification": item["type"], "interval": item["period"],
                        "activeAbstinent": item["activeCount"],
                        "activeRandomized": item["activeDenom"], "activePct": item["activePercent"],
                        "placeboAbstinent": item["placeboCount"],
                        "placeboRandomized": item["placeboDenom"],
                        "placeboPct": item["placeboPercent"],
                        "oddsRatioReported": item["publishedOddsRatio"],
                    } for item in report["publishedEfficacyComparisons"]
                ]
                safety = report["publishedSafetyObservation"]
                safety_normalized = {
                    **safety,
                    "seriousAdverseEvents": safety["seriousTreatmentEmergentAEs"],
                    "cytisiniclineExposed": safety["combinedCytisiniclineExposed"],
                }
            else:
                comparisons = report["publishedEfficacyComparisons"]
                safety_normalized = report["publishedSafetyObservation"]
            published = {
                "publicationUrl": report["sourceUrl"],
                "publishedDate": report["publishedDate"],
                "status": report["status"],
                "reportedEfficacyComparisons": comparisons if i == 3 else [],
                "reportedSafetyObservations": safety_normalized if i == 3 else None,
                "reportedTrialDesign": report["studyDesign"] if i == 4 else None,
                "reportedClinicalLimitations": (
                    report["documentedLimitationsUnreviewed"] if i == 6 else []
                ),
                "publicationTextDiscrepanciesUnreviewed": (
                    report.get("publicationTextDiscrepanciesUnreviewed", []) if i == 3 else []
                ),
                "independentReviewQuestions": report["independentReviewQuestions"],
                "sourceIndependentlyAuthenticated": False,
                "scientificallyAdjudicated": False,
            }
            questions.extend(report["independentReviewQuestions"])
        levels.append({
            "level": i, "name": name,
            "publicationFindingsUnreviewed": published,
            "evidenceCollectionStatus": status,
            "applicability": applicability,
            "openReviewQuestions": questions,
            "sourceAuthenticationStatus": "NOT_INDEPENDENTLY_AUTHENTICATED",
            "independentScientificReviewStatus": "NOT_ADJUDICATED",
            "independentChallengeStatus": "NOT_COMPLETED",
            "finalAdjudicationStatus": "NOT_COMPLETED",
            "completionPermitted": False,
            "score": None,
            "approvalProbability": None,
            "fdaOutcomeJudgment": None,
            "statisticalChronology": orca_chronology if i == 5 and row["nct"] == ORCA_NCT else None,
        })
    return levels


def build(coverage, roster, application_crosswalk, chronology,
          orca_publication=None, orca3_publication=None):
    """Build an explicitly blocked handoff for the active frozen FOCUS cohort."""
    if not isinstance(coverage, dict) or coverage.get("kind") != "LEVEL16_SCIENTIFIC_COVERAGE_NOT_EVIDENCE_COMPLETENESS":
        raise ValueError("Not an approved source-coverage research report")
    if coverage.get("evidenceCutoffDate") != "2026-11-14":
        raise ValueError("Current-source research cutoff mismatch")
    if (coverage.get("independentlyAuthenticatedSources") != 0
            or coverage.get("independentlyAdjudicatedAssessments") != 0
            or coverage.get("historicalPredictionInputPermitted") is not False
            or coverage.get("approvalProbability") is not None):
        raise ValueError("Research report cannot assert review, blind predictions or probabilities")
    registered = _index(roster.get("records"), "FOCUS roster")
    mapped = _index(application_crosswalk.get("records"), "Application crosswalk", require_ticker=False)
    trials = _index(coverage.get("trials"), "Scientific research coverage")
    if len(registered) != 32 or set(trials) != set(registered) or not set(mapped).issubset(registered):
        raise ValueError("Exact 32-NCT FOCUS roster/crosswalk mismatch")
    if len(mapped) != 29 or coverage.get("focusTrialCount") != 32:
        raise ValueError("Frozen FOCUS cohort or provisional mapping count mismatch")
    cycles = set()
    for nct, record in mapped.items():
        candidates = record.get("candidateApplications")
        if not isinstance(candidates, list):
            raise ValueError("Invalid provisional candidate application mapping")
        for candidate in candidates:
            if candidate.get("ticker") != registered[nct]["ticker"] or not candidate.get("cycleId"):
                raise ValueError("Mismatched candidate application identity")
            cycles.add(candidate["cycleId"])
    if len(cycles) != 23:
        raise ValueError("Unexpected provisional application cycle count")
    unlinked = sorted(set(registered) - set(mapped))
    if unlinked != sorted(("NCT05031780", "NCT06747468", "NCT06553768")):
        raise ValueError("Unexpected unmapped application exceptions")
    if (not isinstance(chronology, dict)
            or chronology.get("nct") != ORCA_NCT
            or chronology.get("status") != "PUBLIC_SOURCE_CHRONOLOGY_ONLY_NOT_SCIENTIFICALLY_ADJUDICATED"
            or chronology.get("finalSapPrespecificationRelativeToUnblinding") != "UNRESOLVED"
            or chronology.get("scientificReviewStatus") != "NOT_ADJUDICATED"
            or chronology.get("fdaPredictionPermitted") is not False
            or chronology.get("sourceIndependentlyAuthenticated") is not False
            or chronology.get("statisticalDeficiencyEstablished") is not False
            or chronology.get("databaseLockDateVerified") is not False
            or chronology.get("unblindingDateVerified") is not False
            or chronology.get("approvalProbability") is not None
            or chronology.get("fdaOutcomeJudgment") is not None
            or chronology.get("sourceEventCount") != 4
            or chronology.get("protocolVersionPredatesRegistryPrimaryCompletion") is not True
            or chronology.get("preCompletionProtocolExplicitlyMentionsPrimaryHochberg") is not True
            or chronology.get("sapVersionDateAfterRegistryPrimaryCompletion") is not True
            or chronology.get("sapExplainsBonferroniForPowerAndHochbergForPrimaryTesting") is not True):
        raise ValueError("ORCA-2 original-source chronology is unreviewed or mismatched")
    publication = None
    if orca_publication is not None:
        spec = importlib.util.spec_from_file_location(
            "level16_orca2_publication_review",
            Path(__file__).with_name("level16_orca2_publication_review.py"),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        publication = module.assess(orca_publication)
        if publication["nct"] != ORCA_NCT:
            raise ValueError("Publication outcome evidence mismatch")
    publication3 = None
    if orca3_publication is not None:
        spec3 = importlib.util.spec_from_file_location(
            "level16_orca3_publication_review",
            Path(__file__).with_name("level16_orca3_publication_review.py"),
        )
        module3 = importlib.util.module_from_spec(spec3)
        spec3.loader.exec_module(module3)
        publication3 = module3.assess(orca3_publication)
        if publication3["nct"] != ORCA3_NCT or ORCA3_NCT not in trials:
            raise ValueError("ORCA-3 publication does not match frozen FOCUS")
    rows = []
    for nct, row in trials.items():
        if (row["ticker"] != registered[nct]["ticker"]
                or row.get("mappingStatus") != (
                    "PROVISIONAL_NOT_VERIFIED" if nct in mapped else "NOT_MAPPED_APPLICATION_CYCLE"
                )
                or row.get("independentSources") != 0
                or row.get("independentlyAdjudicatedAssessments") != 0
                or row.get("preliminaryLevels") != 6
                or row.get("blockedOnIndependentReview") is not True):
            raise ValueError("Research identity or independent-review state was promoted")
        for key in ("registry", "protocol", "sap", "postedResults"):
            if type(row.get(key)) is not bool:
                raise ValueError("Source coverage must be explicit unreviewed booleans")
        if not row["registry"]:
            raise ValueError("Original registry source missing for frozen cohort")
        levels = _level_rows(row, chronology, publication, publication3)
        if len(levels) != 6:
            raise ValueError("Six assessment levels required")
        documentation = sum((row["registry"], row["protocol"], row["sap"], row["postedResults"]))
        rows.append({
            "nct": nct, "company": row["company"], "ticker": row["ticker"],
            "indicationUnreviewed": row["indicationUnreviewed"],
            "phaseUnreviewed": row["phaseUnreviewed"],
            "applicationMappingStatus": row["mappingStatus"],
            "originalSourceCollection": {
                "registry": _status(row["registry"]),
                "protocol": _status(row["protocol"]),
                "sap": _status(row["sap"]),
                "postedResults": _status(row["postedResults"]),
            },
            "documentationBreadthOnly": documentation,
            "firstResearchHandoffCandidate": nct == ORCA_NCT,
            "levels": levels,
            "reviewWorkflow": REVIEW_STEPS[:],
            "actualAuthenticatedSources": 0,
            "actualCompletedLevels": 0,
            "actualIndependentScientificReviews": 0,
            "independentReviewerAccess": "NOT_APPROVED_OR_ACTIVATED",
            "readyForIndependentFinalAdjudication": False,
            "fdaOutcomeJudgment": None,
            "approvalProbability": None,
        })
    # Sort only by available document classes, with ORCA-2 as the first handoff.
    # This order is NOT scientific quality, FDA outcome probability or significance.
    rows.sort(key=lambda t: (not t["firstResearchHandoffCandidate"],
                             -t["documentationBreadthOnly"], t["nct"]))
    return {
        "kind": "FOCUS_LEVELS1_6_INDEPENDENT_REVIEW_HANDOFF_RESEARCH_ONLY",
        "evidenceCutoffDate": coverage["evidenceCutoffDate"],
        "researchIsOutcomeExposed": True,
        "sortDefinition": "ORCA2_FIRST_THEN_SOURCE_DOCUMENT_BREADTH_NOT_APPROVAL_LIKELIHOOD",
        "focusTrialCount": len(rows),
        "provisionalApplicationCycleCount": len(cycles),
        "provisionallyMappedTrialCount": len(mapped),
        "unmappedTrialCount": len(unlinked),
        "reviewPacketsPrepared": len(rows),
        "independentlyAuthenticatedSources": 0,
        "independentlyAdjudicatedLevels": 0,
        "genuineQualifiedReviewersActivated": 0,
        "actualApprovalProbabilities": 0,
        "stagingActivated": False,
        "reviewReleaseStatus": "BLOCKED_ON_OWNER_A01_A14_AND_INDEPENDENT_REVIEW",
        "trials": rows,
    }


def markdown(packet):
    if packet.get("kind") != "FOCUS_LEVELS1_6_INDEPENDENT_REVIEW_HANDOFF_RESEARCH_ONLY":
        raise ValueError("Not a research handoff")
    lines = [
        "# FOCUS Levels 1–6 — independent review handoff (not a completed assessment)",
        "",
        "**UNREVIEWED, OUTCOME-EXPOSED RESEARCH; NO AUTHENTICATED SOURCES, "
        "LIVE REVIEWERS, FDA FORECASTS OR CLINICAL SIGNOFF.**",
        "",
        f"Evidence cutoff: {packet['evidenceCutoffDate']}. "
        f"FOCUS: {packet['focusTrialCount']} exact NCTs; "
        f"{packet['provisionallyMappedTrialCount']} provisionally mapped, "
        f"{packet['unmappedTrialCount']} unmapped. No live deployment.",
        "",
        "Order reflects document collection only, not trial strength or FDA likelihood.",
        "",
    ]
    for trial in packet["trials"]:
        lines.extend([
            f"## {trial['nct']} — {trial['ticker']} ({trial['company']})",
            f"Registry phases, unreviewed: {', '.join(trial['phaseUnreviewed'])}. "
            f"Application link: {trial['applicationMappingStatus']}.",
            f"Original-source collection: {', '.join(f'{k}={v}' for k, v in trial['originalSourceCollection'].items())}.",
        ])
        for level in trial["levels"]:
            lines.extend([
                f"### Level {level['level']}: {level['name']}",
                f"Evidence: {level['evidenceCollectionStatus']}. "
                f"Applicability: {level['applicability']}. "
                "Scientific review: NOT_ADJUDICATED.",
            ])
            for question in level["openReviewQuestions"]:
                lines.append("- " + question)
            if level.get("publicationFindingsUnreviewed") is not None:
                pub = level["publicationFindingsUnreviewed"]
                lines.append("- Published trial evidence (" + trial["nct"]
                             + ", NOT independently reviewed): " + pub["publicationUrl"])
                for discrepancy in pub.get("publicationTextDiscrepanciesUnreviewed", []):
                    lines.append(
                        "- ORIGINAL ARTICLE DISCREPANCY REQUIRES SOURCE CHECK: "
                        + discrepancy["endpointId"] + " " + discrepancy["field"]
                        + " Table 2=" + discrepancy["table2"]
                        + " narrative=" + discrepancy["narrative"]
                    )
                if level["level"] == 3:
                    for comparison in pub["reportedEfficacyComparisons"]:
                        lines.append(
                            "- " + comparison["classification"] + " " + comparison["interval"]
                            + " (" + comparison["arm"] + " vs placebo): "
                            + str(comparison["activeAbstinent"]) + "/" + str(comparison["activeRandomized"])
                            + " (" + str(comparison["activePct"]) + "%) vs "
                            + str(comparison["placeboAbstinent"]) + "/" + str(comparison["placeboRandomized"])
                            + " (" + str(comparison["placeboPct"]) + "%). Published odds ratio "
                            + str(comparison["oddsRatioReported"])
                            + "; original Table 2; not independent analysis."
                        )
                    safety = pub["reportedSafetyObservations"]
                    lines.append("- Published serious adverse events: "
                                 + str(safety["seriousAdverseEvents"]["cytisinicline"])
                                 + "/" + str(safety["cytisiniclineExposed"]) + " cytisinicline vs "
                                 + str(safety["seriousAdverseEvents"]["placebo"])
                                 + "/" + str(safety["placeboExposed"])
                                 + " placebo; reported investigator attribution is NOT proof of causality.")
                if level["level"] == 6:
                    for limitation in pub["reportedClinicalLimitations"]:
                        lines.append("- Published limitation (unreviewed): " + limitation)
            if level["statisticalChronology"] is not None:
                lines.append("- ORCA-2 chronology: Hochberg in pre-completion protocol; "
                             "later SAP date; final SAP approval relative to unblinding UNRESOLVED.")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--nct", help="Emit only one trial from the validated complete FOCUS roster")
    args = parser.parse_args()
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location(
        "level16_orca2_statistical_timeline",
        Path(__file__).with_name("level16_orca2_statistical_timeline.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    packet = build(read(COVERAGE), read(ROSTER), read(APPLICATIONS),
                   mod.assess(read(ORCA2)),
                   orca_publication=read(ORCA2_PUBLICATION),
                   orca3_publication=read(ORCA3_PUBLICATION))
    if args.nct:
        if not NCT_RE.fullmatch(args.nct) or args.nct not in {t["nct"] for t in packet["trials"]}:
            parser.error("NCT not in current exact FOCUS roster")
        packet["trials"] = [t for t in packet["trials"] if t["nct"] == args.nct]
        packet["selectedNctOnly"] = args.nct
    if args.format == "json":
        print(json.dumps(packet, indent=2))
    else:
        print(markdown(packet), end="")


if __name__ == "__main__":
    main()
