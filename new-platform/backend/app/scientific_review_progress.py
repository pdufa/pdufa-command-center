"""Frozen-trial aggregate of documented TWO-REVIEWER technical preflight.

Data source: rehashed isolated source archive + reconciliation worklist +
existing audit-verified pairing checks. Produces bounded counts ONLY, never
reviewer identifiers, source locators, evidence merits, grades, or FDA results.
No writes, no reviewer provisioning, no automatic source capture.
"""
from __future__ import annotations

from .scientific_reconciliation_worklist import reconciliation_worklist
from .scientific_review_pairing import review_pairing_status
from .scientific_source_documents import read_document_manifest

PILOT = "NCT02142738"
GATES = ("protocol_sap", "published_results", "independent_replication",
         "official_regulatory")
MAX_DOCUMENTS = 8
MAX_QUESTIONS = 8
MAX_PAIRS = MAX_DOCUMENTS * MAX_QUESTIONS


def pilot_review_progress(nct_id: str) -> dict:
    """Return technical pairing counts; zero independent clinical conclusions.

    Re-validates *every* stored PDF snapshot at read time before considering
    historical review claims. If a captured PDF is corrupted, fail closed.
    """
    if nct_id != PILOT:
        raise ValueError("Exact frozen scientific pilot identity required")
    manifest = read_document_manifest(nct_id)
    worklist = reconciliation_worklist(nct_id)
    docs = manifest["documents"]
    questions = worklist["checks"]
    if (manifest["nctId"] != PILOT
            or manifest["allCapturedBytesRehashed"] is not True
            or manifest["independentSourceVerificationCompleted"] is not False
            or manifest["scientificGradePromotionAllowed"] is not False
            or manifest["sourceDocumentCount"] != len(docs)
            or not isinstance(docs, list) or len(docs) > MAX_DOCUMENTS
            or worklist["nctId"] != PILOT
            or worklist["verifiedChecks"] != 0
            or worklist["readinessMayBePromoted"] is not False
            or not isinstance(questions, list) or len(questions) != MAX_QUESTIONS):
        raise ValueError("Unsafe source archive or reconciliation contract")

    seen_docs, seen_sha, seen_questions = set(), set(), set()
    counts = {
        g: {"capturedSourceCount": 0, "reconciliationQuestionCount": 0,
            "eligibleQuestionSourcePairs": 0, "pairingTechnicalPreflightPassed": 0,
            "twoAuthorizedReviewersRecorded": 0, "disputedTechnicalPairCount": 0,
            "historicalAuditCorruptionPairs": 0} for g in GATES
    }
    for doc in docs:
        if (doc["nctId"] != PILOT or doc["gateId"] not in counts
                or doc["documentId"] in seen_docs or doc["sha256"] in seen_sha
                or doc["byteIntegrityChecked"] is not True
                or doc["captureStatus"] != "byte_integrity_checked_unverified"):
            raise ValueError("Source archive claim cannot be trusted")
        seen_docs.add(doc["documentId"])
        seen_sha.add(doc["sha256"])
        counts[doc["gateId"]]["capturedSourceCount"] += 1
    for question in questions:
        if (question["id"] in seen_questions or question["gateId"] not in counts
                or question["status"] != "open_unadjudicated"
                or question["independentlyVerified"] is not False):
            raise ValueError("Unverified reconciliation worklist changed")
        seen_questions.add(question["id"])
        counts[question["gateId"]]["reconciliationQuestionCount"] += 1

    queried = 0
    for doc in docs:
        for question in questions:
            if question["gateId"] != doc["gateId"]:
                continue
            gate = counts[doc["gateId"]]
            gate["eligibleQuestionSourcePairs"] += 1
            queried += 1
            if queried > MAX_PAIRS:
                raise ValueError("Scientific review comparison budget exceeded")
            check = review_pairing_status(PILOT, question["id"], doc["sha256"])
            if (check["nctId"] != PILOT or check["questionId"] != question["id"]
                    or check["sourceSha256"] != doc["sha256"]
                    or check["scientificAdjudicationComplete"] is not False
                    or check["mayPromoteScientificScore"] is not False
                    or check["clinicalIndependenceVerified"] is not False
                    or check["sourceContentIndependentlyVerified"] is not False
                    or check["qualificationsIndependentlyAdjudicated"] is not False
                    or check["formalSecondPersonSignoff"] is not False
                    or check["pairingTechnicalPreflightPassed"] and not (
                        check["twoCurrentlyAuthorizedReviewers"]
                        and check["auditIntegrityPassed"]
                        and check["sourceByteIntegrityPassed"]
                        and check["decisionsAgree"]
                    )):
                raise ValueError("Scientific pairing safety contract changed")
            if check["twoCurrentlyAuthorizedReviewers"]:
                gate["twoAuthorizedReviewersRecorded"] += 1
            if check["pairingTechnicalPreflightPassed"]:
                gate["pairingTechnicalPreflightPassed"] += 1
            if (check["twoIndependentStatementsRecorded"]
                    and not check["decisionsAgree"]):
                gate["disputedTechnicalPairCount"] += 1
            if check["recordedStatements"] and not check["auditIntegrityPassed"]:
                gate["historicalAuditCorruptionPairs"] += 1

    total = sum(x["eligibleQuestionSourcePairs"] for x in counts.values())
    paired = sum(x["pairingTechnicalPreflightPassed"] for x in counts.values())
    disputed = sum(x["disputedTechnicalPairCount"] for x in counts.values())
    corrupted = sum(x["historicalAuditCorruptionPairs"] for x in counts.values())
    return {
        "nctId": PILOT,
        "mode": "isolated_read_only_technical_reviewer_preflight",
        "sourceDocumentCount": len(docs),
        "questionCount": len(questions),
        "eligibleQuestionSourcePairs": total,
        "pairingTechnicalPreflightPassedCount": paired,
        "disputedTechnicalPairCount": disputed,
        "historicalAuditCorruptionPairs": corrupted,
        "gates": [{"gateId": gate_id, **counts[gate_id]} for gate_id in GATES],
        "capturedBytesRehashed": True,
        "independentClinicalReviewCount": 0,
        "verifiedClinicalSourceCount": 0,
        "qualifiedIndependenceAdjudicated": False,
        "formalSecondPersonSignoffCount": 0,
        "scientificAdjudicationComplete": False,
        "readyForScientificConclusion": False,
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "mayPromoteScientificScore": False,
        "note": (
            "Two currently authorized statements with intact audit trails are "
            "technical preflight ONLY. No independent clinical qualifications, "
            "original authorship, study conclusions or FDA outcomes are validated."
        ),
    }
