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
MAPLE_HCM = REPORTS / "maple-hcm-source-review-20261114.json"
ORIGIN3_RENAL = REPORTS / "origin3-published-renal-evidence-20261114.json"
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
    "Owner checks original evidence, document identity, phase and date; automated source consistency aids research",
    "AI-assisted scientific analysis presents findings, limitations and contradictory evidence to the owner",
    "Owner evaluates competing explanations and unresolved risks; no outside challenger or credential needed",
    "Owner records self-review decision and publication choice; never calls this independent certification",
]
ORCA_NCT = "NCT04576949"
ORCA3_NCT = "NCT05206370"
MAPLE_NCT = "NCT05767346"
ORIGIN3_NCT = "NCT04716231"


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


def _owner_question(question):
    """Keep the scientific issue; remove withdrawn external-human instructions."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("A bounded evidence issue is required")
    text = question.strip()
    specific = {
        "Obtain genuine authorized source authentication and independent statistical, clinical and disease-specialist review":
            "Owner cross-checks the original source and its limitations, performs statistical, clinical and indication-specific research checks",
        "Assign qualified disease-specialist and independent biostatistician reviews after actual source authentication and owner approvals.":
            "Owner performs indication-specific and statistical research checks after owner source cross-checking; no outside reviewers",
        "Conduct qualified independent statistical and disease-specialist review; challenge and adjudicate":
            "Owner conducts statistical and indication-specific self-review, considers contradictory evidence and records an owner decision",
    }
    if text in specific:
        text = specific[text]
    else:
        text = re.sub(r"^Independently\s+", "Owner checks: ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bindependently\b", "by the owner", text, flags=re.IGNORECASE)
        text = re.sub(r"\bindependent\b", "owner-led", text, flags=re.IGNORECASE)
        text = re.sub(r"\bqualified\b", "owner", text, flags=re.IGNORECASE)
        text = re.sub(r"\bauthorized\b", "owner", text, flags=re.IGNORECASE)
        text = re.sub(r"\breviewers\b", "owner", text, flags=re.IGNORECASE)
        text = re.sub(r"\breviewer\b", "owner", text, flags=re.IGNORECASE)
        text = re.sub(r"\bdisease-specialist\b", "indication-specific", text, flags=re.IGNORECASE)
        text = re.sub(r"\bbiostatistician\b", "statistical methods", text, flags=re.IGNORECASE)
        text = re.sub(r"\badjudicate\b", "record an owner decision", text, flags=re.IGNORECASE)
        text = re.sub(r"\badjudication\b", "owner decision", text, flags=re.IGNORECASE)
        text = re.sub(r"\battestation\b", "source check", text, flags=re.IGNORECASE)
    if not 8 <= len(text) <= 4000:
        raise ValueError("Owner review question exceeded bounds")
    return text


def _level_rows(row, orca_chronology, publication=None, publication3=None,
                maple_paper=None, renal_paper=None):
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
        if i in (3, 4, 6) and row["nct"] == MAPLE_NCT and maple_paper is not None:
            if published is not None:
                raise ValueError("Trial published evidence must never be cross-linked")
            published = {
                "publicationUrl": maple_paper["sourceUrl"],
                "secondaryEvidenceUrl": maple_paper["secondarySourceUrl"],
                "publishedDate": maple_paper["publishedDate"],
                "status": maple_paper["status"],
                "endpointDataType": maple_paper["endpointDataType"],
                "reportedEfficacyComparisons": [],
                "reportedSafetyObservations": (
                    maple_paper["publishedSafetyObservationFromACC"] if i == 3 else None
                ),
                "continuousPrimaryEndpointUnreviewed": (
                    maple_paper["primaryEndpointReported"] if i == 3 else None
                ),
                "secondaryContinuousComparisonsUnreviewed": (
                    maple_paper["secondaryEndpointsFromACC"] if i == 3 else []
                ),
                "reportedTrialDesign": maple_paper["studyDesign"] if i == 4 else None,
                "reportedClinicalLimitations": (
                    maple_paper["documentedLimitationsUnreviewed"] if i == 6 else []
                ),
                "independentReviewQuestions": maple_paper["independentReviewQuestions"],
                "sourceIndependentlyAuthenticated": False,
                "scientificallyAdjudicated": False,
            }
            questions.extend(maple_paper["independentReviewQuestions"])
        renal = None
        if row["nct"] == ORIGIN3_NCT and renal_paper is not None:
            renal = {
                "status": renal_paper["status"],
                "nct": renal_paper["nct"],
                "sourceLinks": [
                    {"publishedOnline": renal_paper["interimPublicationDate"],
                     "url": renal_paper["interimSource"],
                     "sourceStatus": "UNREVIEWED_INTERIM_JOURNAL"},
                    {"publishedOnline": renal_paper["finalPublicationDate"],
                     "url": renal_paper["finalSource"],
                     "sourceStatus": "UNREVIEWED_LATER_JOURNAL"}
                ],
                "historicalBlindBacktestPermitted": False,
                "originalSourcesIndependentlyAuthenticated": False,
                "scientificallyAdjudicated": False,
                "studyPhaseContextUnreviewed": (
                    renal_paper["studyContext"] if i in (1, 2, 4) else None
                ),
                "interimPrimaryProteinuriaUnreviewed": (
                    renal_paper["interimAnalysis"] if i in (3, 5, 6) else None
                ),
                "laterSecondaryKidneyFunctionUnreviewed": (
                    renal_paper["finalAnalysis"] if i in (3, 5, 6) else None
                ),
                "distinctPopulationAndCutoffWarning": (
                    "203 prespecified interim patients are NOT the full 431 randomized / 428 treated cohort; "
                    "the Oct 22 2026 final report is outcome-exposed later evidence, never blind historical input."
                ),
                "independentReviewQuestions": renal_paper["independentReviewQuestions"],
            }
            questions.extend(renal_paper["independentReviewQuestions"])
        questions = [_owner_question(question) for question in questions]
        levels.append({
            "level": i, "name": name,
            "renalEvidenceUnreviewed": renal,
            "publicationFindingsUnreviewed": published,
            "evidenceCollectionStatus": status,
            "applicability": applicability,
            "openReviewQuestions": questions,
            "sourceAuthenticationStatus": "NOT_INDEPENDENTLY_AUTHENTICATED",
            "independentScientificReviewStatus": "NOT_ADJUDICATED",
            "independentChallengeStatus": "NOT_COMPLETED",
            "ownerReviewStatus": "OWNER_NOT_REVIEWED",
            "externalReviewerRequired": False,
            "ownerCanReviewWithoutExternalVerification": True,
            "finalAdjudicationStatus": "NOT_COMPLETED",
            "completionPermitted": False,
            "score": None,
            "approvalProbability": None,
            "fdaOutcomeJudgment": None,
            "statisticalChronology": orca_chronology if i == 5 and row["nct"] == ORCA_NCT else None,
        })
    return levels


def build(coverage, roster, application_crosswalk, chronology,
          orca_publication=None, orca3_publication=None,
          maple_publication=None, origin3_renal=None):
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
    maple_paper = None
    if maple_publication is not None:
        spec_maple = importlib.util.spec_from_file_location(
            "level16_maple_hcm_publication_review",
            Path(__file__).with_name("level16_maple_hcm_publication_review.py"),
        )
        maple_mod = importlib.util.module_from_spec(spec_maple)
        spec_maple.loader.exec_module(maple_mod)
        maple_paper = maple_mod.assess(maple_publication)
        if (maple_paper["nct"] != MAPLE_NCT or MAPLE_NCT not in trials
                or trials[MAPLE_NCT]["ticker"] != "CYTK"
                or "PHASE3" not in trials[MAPLE_NCT]["phaseUnreviewed"]):
            raise ValueError("MAPLE-HCM clinical publication and FOCUS phase mismatch")
    renal_paper = None
    if origin3_renal is not None:
        spec_renal = importlib.util.spec_from_file_location(
            "level16_origin3_renal_publication",
            Path(__file__).with_name("level16_origin3_renal_publication.py"),
        )
        renal_mod = importlib.util.module_from_spec(spec_renal)
        spec_renal.loader.exec_module(renal_mod)
        renal_paper = renal_mod.assess(origin3_renal)
        if (renal_paper["nct"] != ORIGIN3_NCT or ORIGIN3_NCT not in trials
                or trials[ORIGIN3_NCT]["ticker"] != "VERA"
                or "PHASE3" not in trials[ORIGIN3_NCT]["phaseUnreviewed"]):
            raise ValueError("ORIGIN 3 original renal evidence and FOCUS phase mismatch")
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
        levels = _level_rows(row, chronology, publication, publication3,
                             maple_paper, renal_paper)
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
            "ownerOnlyAssessmentMode": True,
            "outsideReviewerCountRequired": 0,
            "ownerAssessmentNotBlockedByExternalSignoff": True,
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
        "reviewReleaseStatus": "OWNER_RESEARCH_PREPARED_NO_EXTERNAL_SIGNOFF_REQUIRED",
        "ownerOnlyAssessmentMode": True,
        "externalReviewerGateCount": 0,
        "externalSignoffsRequiredForScoring": 0,
        "ownerReviewNotYetEntered": True,
        "trials": rows,
    }


def markdown(packet):
    if packet.get("kind") != "FOCUS_LEVELS1_6_INDEPENDENT_REVIEW_HANDOFF_RESEARCH_ONLY":
        raise ValueError("Not a research handoff")
    lines = [
        "# FOCUS Levels 1–6 — owner-only review handoff (not a completed assessment)",
        "",
        "**OWNER-ONLY, UNREVIEWED AND OUTCOME-EXPOSED RESEARCH. "
        "NO EXTERNAL SIGNOFF IS REQUIRED. "
        "No owner review, FDA forecast or independent medical certification has been recorded.**",
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
                "Owner review: OWNER_NOT_REVIEWED. No external approval required.",
            ])
            for question in level["openReviewQuestions"]:
                lines.append("- " + question)
            if level.get("publicationFindingsUnreviewed") is not None:
                pub = level["publicationFindingsUnreviewed"]
                lines.append("- Published trial evidence (" + trial["nct"]
                             + ", published evidence NOT owner-checked yet): " + pub["publicationUrl"])
                for discrepancy in pub.get("publicationTextDiscrepanciesUnreviewed", []):
                    lines.append(
                        "- ORIGINAL ARTICLE DISCREPANCY REQUIRES SOURCE CHECK: "
                        + discrepancy["endpointId"] + " " + discrepancy["field"]
                        + " Table 2=" + discrepancy["table2"]
                        + " narrative=" + discrepancy["narrative"]
                    )
                if level["level"] == 3 and pub.get("endpointDataType") == (
                        "CONTINUOUS_EXERCISE_CAPACITY_NOT_BINARY_ABSTINENCE"):
                    primary = pub["continuousPrimaryEndpointUnreviewed"]
                    lines.append(
                        "- REPORTED CONTINUOUS PRIMARY ENDPOINT — not an odds ratio: "
                        + primary["name"] + ", between-group difference "
                        + str(primary["adjustedBetweenGroupMeanDifference"]) + " "
                        + primary["unit"] + " (95% CI "
                        + str(primary["adjustedBetweenGroup95CI"]) + "); "
                        + "ORIGINAL NEJM ABSTRACT, NOT INDEPENDENTLY REANALYZED."
                    )
                    for secondary in pub["secondaryContinuousComparisonsUnreviewed"]:
                        lines.append(
                            "- ACC secondary trial SUMMARY ONLY: " + secondary["name"]
                            + " " + str(secondary["effect"]) + " " + secondary["unit"]
                            + " (95% CI " + str(secondary["ci95"]) + ")."
                        )
                    safety = pub["reportedSafetyObservations"]
                    lines.append(
                        "- ACC summary serious adverse events: "
                        + str(safety["seriousAdverseEvents"]["aficamten"]) + "/"
                        + str(safety["seriousAdverseEvents"]["aficamtenDenom"])
                        + " aficamten vs "
                        + str(safety["seriousAdverseEvents"]["metoprolol"]) + "/"
                        + str(safety["seriousAdverseEvents"]["metoprololDenom"])
                        + " metoprolol; LVEF difference "
                        + str(safety["lvefBetweenGroupDifferencePercentagePoints"])
                        + " percentage points. No independent safety adjudication."
                    )
                    lines.append("- ACC is secondary commentary, NOT the original NEJM study report: "
                                 + pub["secondaryEvidenceUrl"])
                if level["level"] == 3 and pub.get("endpointDataType") != (
                        "CONTINUOUS_EXERCISE_CAPACITY_NOT_BINARY_ABSTINENCE"):
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
            if level.get("renalEvidenceUnreviewed") is not None:
                renal = level["renalEvidenceUnreviewed"]
                lines.append(
                    "- ORIGIN 3 KIDNEY RESEARCH — NOT independently authenticated or reviewed; "
                    + "2025 interim and 2026 final articles concern ONE Phase 3 trial."
                )
                lines.append(
                    "- Original journals: " + renal["sourceLinks"][0]["url"]
                    + " (" + renal["sourceLinks"][0]["publishedOnline"] + "); "
                    + renal["sourceLinks"][1]["url"]
                    + " (" + renal["sourceLinks"][1]["publishedOnline"] + ")."
                )
                lines.append("- Strict research cutoff warning: "
                             + renal["distinctPopulationAndCutoffWarning"])
                if level["level"] == 3:
                    interim = renal["interimPrimaryProteinuriaUnreviewed"]
                    later = renal["laterSecondaryKidneyFunctionUnreviewed"]
                    upcr = interim["primary"]
                    lines.append(
                        "- PRIMARY INTERIM: week-36 24h UPCR reduction "
                        + str(upcr["ataciceptPercentReduction"]) + "% atacicept vs "
                        + str(upcr["placeboPercentReduction"]) + "% placebo; "
                        + "published adjusted geometric comparison "
                        + str(upcr["publishedBetweenGroupDifferencePercentagePoints"])
                        + " percentage points (95% CI " + str(upcr["difference95CI"])
                        + "); subset 106/97 of 203; this is not direct kidney-function proof."
                    )
                    for k in later["secondaryEfficacy"]:
                        lines.append(
                            "- LATER SECONDARY: " + k["measure"]
                            + ": published between-arm difference "
                            + str(k["reportedBetweenGroupDifference"]) + " " + k["unit"]
                            + " (95% CI " + str(k["difference95CI"]) + "), "
                            + "not a week-36 primary endpoint."
                        )
                    progression = later["progression"]
                    lines.append(
                        "- LATER KIDNEY PROGRESSION COMPOSITE: "
                        + str(progression["atacicept"]) + " vs "
                        + str(progression["placebo"]) + "; published HR "
                        + str(progression["hazardRatio"]) + " (95% CI "
                        + str(progression["hr95CI"]) + "); not mortality-only."
                    )
                    ae = later["safety"]
                    lines.append(
                        "- LATER SAFETY: serious AEs reported "
                        + str(ae["seriousAdverseEventsPercent"]["atacicept"])
                        + "% atacicept vs "
                        + str(ae["seriousAdverseEventsPercent"]["placebo"])
                        + "% placebo in 214/214 treated; no causal signoff."
                    )
                if level["level"] == 5:
                    lines.append("- STATISTICAL REVIEW NEEDED: distinct interim/final estimands, "
                                 "alpha spending, multiplicity, protocol/SAP and unblinding chronology.")
                if level["level"] == 6:
                    lines.append("- MEDICAL REVIEW NEEDED: UPCR biomarker versus later eGFR "
                                 "slope/clinical kidney progression and long-term safety.")
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
                   orca3_publication=read(ORCA3_PUBLICATION),
                   maple_publication=read(MAPLE_HCM),
                   origin3_renal=read(ORIGIN3_RENAL))
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
