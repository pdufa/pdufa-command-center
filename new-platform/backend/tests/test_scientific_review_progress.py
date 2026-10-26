"""No-network, no-database tests for reviewer-pair technical progress counts."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi import HTTPException, Response

from app import main, scientific_review_progress as progress
from app.scientific_reconciliation_worklist import reconciliation_worklist

NCT = "NCT02142738"


def source(char, gate):
    return {
        "documentId": char * 32,
        "nctId": NCT,
        "gateId": gate,
        "sha256": char * 64,
        "byteIntegrityChecked": True,
        "captureStatus": "byte_integrity_checked_unverified",
    }


def manifest():
    documents = [
        source("a", "protocol_sap"),
        source("b", "published_results"),
        source("c", "official_regulatory"),
    ]
    return {
        "nctId": NCT,
        "sourceDocumentCount": len(documents),
        "allCapturedBytesRehashed": True,
        "independentSourceVerificationCompleted": False,
        "scientificGradePromotionAllowed": False,
        "documents": documents,
    }


def pair(nct_id, question_id, sha):
    assert nct_id == NCT
    assert question_id in {q["id"] for q in reconciliation_worklist(NCT)["checks"]}
    assert sha in {d["sha256"] for d in manifest()["documents"]}
    paired = sha == "a" * 64
    disputed = sha == "b" * 64 and question_id == "pfs_initial_vs_followup"
    return {
        "nctId": nct_id,
        "questionId": question_id,
        "sourceSha256": sha,
        "recordedStatements": 2 if paired or disputed else 0,
        "twoIndependentStatementsRecorded": paired or disputed,
        "twoCurrentlyAuthorizedReviewers": paired,
        "decisionsAgree": paired,
        "auditIntegrityPassed": True,
        "sourceByteIntegrityPassed": True,
        "pairingTechnicalPreflightPassed": paired,
        "scientificAdjudicationComplete": False,
        "clinicalIndependenceVerified": False,
        "sourceContentIndependentlyVerified": False,
        "qualificationsIndependentlyAdjudicated": False,
        "formalSecondPersonSignoff": False,
        "mayPromoteScientificScore": False,
    }


def setup(monkeypatch, archive=None, worklist=None, pairing=None):
    monkeypatch.setattr(progress, "read_document_manifest",
                        lambda _: deepcopy(manifest() if archive is None else archive))
    monkeypatch.setattr(progress, "reconciliation_worklist",
                        lambda _: deepcopy(reconciliation_worklist(NCT) if worklist is None else worklist))
    monkeypatch.setattr(progress, "review_pairing_status", pairing or pair)


def test_frozen_pilot_counts_real_source_question_gate_pairs_without_clinical_signoff(monkeypatch):
    calls = []
    def paired(nct, question, sha):
        calls.append((nct, question, sha))
        return pair(nct, question, sha)
    setup(monkeypatch, pairing=paired)
    report = progress.pilot_review_progress(NCT)
    questions = reconciliation_worklist(NCT)["checks"]
    assert len(questions) == 8
    expected_pairs = sum(1 for d in manifest()["documents"]
                         for q in questions if q["gateId"] == d["gateId"])
    assert report["sourceDocumentCount"] == 3
    assert report["questionCount"] == 8
    assert report["eligibleQuestionSourcePairs"] == expected_pairs == len(calls)
    assert report["pairingTechnicalPreflightPassedCount"] == 1
    assert report["disputedTechnicalPairCount"] == 1
    assert report["historicalAuditCorruptionPairs"] == 0
    assert len(report["gates"]) == 4
    assert [x["gateId"] for x in report["gates"]] == list(progress.GATES)
    assert report["independentClinicalReviewCount"] == 0
    assert report["verifiedClinicalSourceCount"] == 0
    assert report["qualifiedIndependenceAdjudicated"] is False
    assert report["formalSecondPersonSignoffCount"] == 0
    assert report["scientificAdjudicationComplete"] is False
    assert report["readyForScientificConclusion"] is False
    assert report["scientificScore"] is None
    assert report["fdaApprovalProbability"] is None
    assert report["mayPromoteScientificScore"] is False
    assert not any("google" in k.lower() or "email" in k.lower() or "subject" in k.lower()
                   for k in str(report).split(","))


def test_empty_archive_is_zero_technical_pairs_not_complete_review(monkeypatch):
    docs = manifest()
    docs["documents"] = []
    docs["sourceDocumentCount"] = 0
    setup(monkeypatch, archive=docs, pairing=lambda *_: pytest.fail("No pairing calls allowed"))
    report = progress.pilot_review_progress(NCT)
    assert report["sourceDocumentCount"] == 0
    assert report["eligibleQuestionSourcePairs"] == 0
    assert report["pairingTechnicalPreflightPassedCount"] == 0
    assert report["scientificAdjudicationComplete"] is False


def test_reject_corrupt_or_unsupported_archive_before_any_reviewer_count(monkeypatch):
    for mutation in (
        lambda m: m.update(nctId="NCT12345678"),
        lambda m: m.update(allCapturedBytesRehashed=False),
        lambda m: m.update(scientificGradePromotionAllowed=True),
        lambda m: m.update(sourceDocumentCount=2),
        lambda m: m["documents"][0].update(gateId="unsafe"),
        lambda m: m["documents"][0].update(byteIntegrityChecked=False),
        lambda m: m["documents"][0].update(captureStatus="independently_verified"),
        lambda m: m["documents"].append(deepcopy(m["documents"][0])),
        lambda m: m.update(documents=[source(str((i%8)+1), "protocol_sap") for i in range(9)],
                           sourceDocumentCount=9),
    ):
        doc = manifest()
        mutation(doc)
        setup(monkeypatch, archive=doc, pairing=lambda *_: pytest.fail("Unsafe pairing attempt"))
        with pytest.raises(ValueError):
            progress.pilot_review_progress(NCT)


def test_wrong_trial_or_altered_question_status_fails_before_pairing(monkeypatch):
    setup(monkeypatch)
    with pytest.raises(ValueError):
        progress.pilot_review_progress("NCT00000001")
    bad = reconciliation_worklist(NCT)
    bad["checks"][0]["independentlyVerified"] = True
    setup(monkeypatch, worklist=bad, pairing=lambda *_: pytest.fail("Unsafe pairing"))
    with pytest.raises(ValueError):
        progress.pilot_review_progress(NCT)


def test_forged_scientific_completion_or_mismatched_pair_id_fails_closed(monkeypatch):
    for mutation in (
        lambda r: r.update(nctId="NCT12345678"),
        lambda r: r.update(sourceSha256="0" * 64),
        lambda r: r.update(clinicalIndependenceVerified=True),
        lambda r: r.update(scientificAdjudicationComplete=True),
        lambda r: r.update(qualificationsIndependentlyAdjudicated=True),
        lambda r: r.update(formalSecondPersonSignoff=True),
        lambda r: r.update(mayPromoteScientificScore=True),
        lambda r: r.update(pairingTechnicalPreflightPassed=True,
                           twoCurrentlyAuthorizedReviewers=False),
    ):
        def forged(nct, question, sha):
            row = pair(nct, question, sha)
            mutation(row)
            return row
        setup(monkeypatch, pairing=forged)
        with pytest.raises(ValueError):
            progress.pilot_review_progress(NCT)


def test_anonymous_route_never_authorizes_preview_and_no_other_nct(monkeypatch):
    setup(monkeypatch)
    with patch.object(main, "require_isolated_scientific_review_service", return_value=None):
        with pytest.raises(HTTPException) as e:
            main.scientific_pilot_reviewer_progress("NCT00000001", Response())
        assert e.value.status_code == 422
        response = Response()
        report = main.scientific_pilot_reviewer_progress(NCT, response)
        assert report["nctId"] == NCT
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-pdufa-scientific-api-contract"] == "science-review-pair-progress-v1"
        assert report["scientificScore"] is None
        assert report["fdaApprovalProbability"] is None


def test_route_refuses_forged_backend_safety_flags(monkeypatch):
    from app import scientific_review_progress
    with patch.object(main, "require_isolated_scientific_review_service", return_value=None):
        with patch.object(scientific_review_progress, "pilot_review_progress",
                          return_value={"nctId": NCT, "independentClinicalReviewCount": 1,
                          "scientificAdjudicationComplete": False, "mayPromoteScientificScore": False,
                          "scientificScore": None, "fdaApprovalProbability": None}):
            with pytest.raises(HTTPException) as e:
                main.scientific_pilot_reviewer_progress(NCT, Response())
            assert e.value.status_code == 409
