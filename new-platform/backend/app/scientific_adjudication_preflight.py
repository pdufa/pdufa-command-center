"""Fail-closed clinical evidence adjudication preflight.

A reviewer statement is NOT a credential, a source citation is NOT a checked
full-text document, and two reviewer labels are NOT two verified independent
reviewers. This report intentionally cannot approve a question or elevate the
existing FDA/scientific grades. It lists the exact prerequisites for a future
independently authenticated and audited adjudication service.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .scientific_investigation_20 import NCT_PATTERN

PREFLIGHT_VERSION = "adjudication-preflight-2026-10-v1"

GLOBAL_BLOCKERS = (
    ("reviewer_identity_unverified",
     "Reviewer identities and qualifications have not been authenticated.",
     "Integrate verified individual identities, qualifications, and reviewer roles."),
    ("source_content_unverified",
     "Referenced source URLs have not been independently fetched, hashed and inspected.",
     "Acquire dated document versions and preserve independent content hashes and citations."),
    ("independent_adjudication_unavailable",
     "Independent review and a signed second-person decision are not implemented.",
     "Require separate authenticated reviewers and an immutable, signed decision record."),
    ("clinical_reconciliation_unverified",
     "Every source-specific acceptance criterion remains unadjudicated.",
     "Reconcile protocol/SAP, efficacy, safety, multiplicity and contradictory sources "
     "against the exact trial, endpoint, population, and timepoint."),
)


def _latest_threads(items: list[dict]) -> list[dict]:
    """Only the newest version within each audited thread counts as a current claim."""
    latest: dict[str, dict] = {}
    for entry in items:
        identifier = entry["threadId"]
        old = latest.get(identifier)
        if old is None or entry["revision"] > old["revision"]:
            latest[identifier] = entry
    return list(latest.values())


def adjudication_preflight(
    nct_id: str,
    worklist: Mapping[str, Any],
    findings: Mapping[str, Any],
) -> dict:
    """Summarize evidence-blocking questions; do not imply scientific adjudication.

    Call only after verified archive readback and checksum-verified ledger reads.
    Never trust consumer-supplied status/identity/attestation fields as verified.
    """
    if not isinstance(nct_id, str) or not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    if worklist.get("nctId") != nct_id or findings.get("nctId") != nct_id:
        raise ValueError("Adjudication evidence refers to another trial")
    questions = worklist.get("checks")
    statements = findings.get("statements")
    if not isinstance(questions, list) or not isinstance(statements, list):
        raise ValueError("Adjudication evidence collections unavailable")
    if findings.get("truncated") or findings.get("totalStatements") != len(statements):
        raise ValueError("Adjudication preflight requires complete statement history")
    if any(x.get("nctId") != nct_id for x in statements):
        raise ValueError("Adjudication statement identity mismatch")

    grouped: dict[str, list[dict]] = {q["id"]: [] for q in questions}
    if len(grouped) != len(questions):
        raise ValueError("Duplicate adjudication question identifier")
    for statement in statements:
        question_id = statement.get("questionId")
        if question_id not in grouped:
            raise ValueError("Reviewer statement references unknown question")
        if statement.get("independentlyVerified") is not False:
            raise ValueError("Reviewer statements cannot claim independent verification")
        grouped[question_id].append(statement)

    checks = []
    disputed_count = 0
    with_observations = 0
    for question in questions:
        qid = question["id"]
        latest = _latest_threads(grouped[qid])
        classifications = {item["findingType"] for item in latest}
        disputed = "supports" in classifications and "contradicts" in classifications
        uncertain = "uncertain" in classifications or "not_assessable" in classifications
        observed = len(latest) > 0
        disputed_count += int(disputed)
        with_observations += int(observed)
        # Self-declared reviewer names cannot fulfill independent-review gates.
        reported_reviewers = sorted({item.get("reviewerLabel", "") for item in latest})
        sources = sorted({item["sourceUrl"] for item in latest})
        blockers = [
            "reviewer_identity_unverified",
            "source_content_unverified",
            "independent_adjudication_unavailable",
            "clinical_reconciliation_unverified",
        ]
        if not observed:
            blockers.append("no_source_anchored_reviewer_observation")
        if disputed:
            blockers.append("conflicting_current_reviewer_statements")
        if uncertain:
            blockers.append("uncertainty_or_unassessable_statement")
        checks.append({
            "questionId": qid,
            "gateId": question["gateId"],
            "priority": question["priority"],
            "question": question["title"],
            "reviewObservationsRecorded": observed,
            "sourceUrlsCited": sources,
            "distinctSourceCount": len(sources),
            "currentReviewerThreadCount": len(latest),
            "selfDeclaredReviewerLabels": reported_reviewers,
            "currentStatementTypes": sorted(classifications),
            "conflictingCurrentStatements": disputed,
            "hasUncertainStatement": uncertain,
            "blockerIds": blockers,
            "adjudicationStatus": "blocked_unverified",
            "criteriaIndependentlySatisfied": 0,
            "readyToResolve": False,
            "independentlyVerified": False,
        })

    # Queue order is advisory. It cannot resolve any scientific evidence gate.
    order = sorted(checks, key=lambda item: (
        not item["conflictingCurrentStatements"],
        not item["hasUncertainStatement"],
        not item["reviewObservationsRecorded"],
        {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(item["priority"], 4),
        item["questionId"],
    ))
    source_index = {q["id"]: q.get("sourceUrls", []) for q in questions}
    review_queue = [
        {
            "questionId": item["questionId"],
            "gateId": item["gateId"],
            "priority": item["priority"],
            "candidateSourceUrls": list(source_index[item["questionId"]]),
            "sourceDocumentsIndependentlyChecked": False,
            "requiresAuthenticatedIndependentReviewer": True,
            "requiresSecondReviewerSignoff": True,
            "nextAction": (
                "Reconcile conflicting source-anchored claims"
                if item["conflictingCurrentStatements"] else
                "Locate missing source information"
                if item["hasUncertainStatement"] else
                "Independently inspect cited sources"
                if item["reviewObservationsRecorded"] else
                "Collect an initial source-anchored observation"
            ),
            "status": "requires_independent_review",
            "sourceUrlsAreOnlyUnverifiedLocators": True,
            "mayAutoResolve": False,
        }
        for item in order
    ]

    return {
        "nctId": nct_id,
        "preflightVersion": PREFLIGHT_VERSION,
        "mode": "read_only_blocker_diagnostic",
        "questionCount": len(checks),
        "questionsWithRecordedObservations": with_observations,
        "questionsWithCurrentDisputes": disputed_count,
        "questionsReadyForAdjudication": 0,
        "questionsIndependentlyResolved": 0,
        "independentlyVerifiedGates": 0,
        "reviewerIdentityAuthenticated": False,
        "sourceContentIndependentlyVerified": False,
        "independentDualReviewImplemented": False,
        "documentedSignoffs": 0,
        "reviewQueue": review_queue,
        "globalBlockers": [
            {"id": key, "reason": reason, "nextAction": action}
            for key, reason, action in GLOBAL_BLOCKERS
        ],
        "questions": checks,
        "readyForScientificConclusion": False,
        "clinicalResult": None,
        "fdaApprovalProbability": None,
        "note": ("This diagnostic tracks recorded source-review observations and "
                 "outstanding safeguards. It cannot authenticate reviewer identity, "
                 "independently inspect cited documents, adjudicate findings, "
                 "or change clinical/FDA grades."),
    }
