"""Review blockers are diagnostic only: no note or reviewer label resolves science."""
import gzip
import hashlib
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.scientific_adjudication_preflight import (
    PREFLIGHT_VERSION, adjudication_preflight,
)
from app.scientific_evidence_ledger import read_ledger
from app.scientific_reconciliation_worklist import reconciliation_worklist

NCT = "NCT02142738"
OTHER = "NCT04280705"


def history(*entries):
    return {
        "nctId": NCT,
        "totalStatements": len(entries),
        "truncated": False,
        "statements": list(entries),
    }


def observation(thread, version, kind, *, label="Claimed Reviewer", question=None):
    return {
        "nctId": NCT,
        "questionId": question or "protocol_amendment_chronology",
        "gateId": "protocol_sap",
        "threadId": thread,
        "revision": version,
        "findingType": kind,
        "sourceUrl": "https://clinicaltrials.gov/study/" + NCT,
        "reviewerLabel": label,
        "independentlyVerified": False,
    }


def test_no_evidence_all_eight_questions_are_blocked():
    result = adjudication_preflight(
        NCT, reconciliation_worklist(NCT), history()
    )
    assert result["preflightVersion"] == PREFLIGHT_VERSION
    assert result["questionCount"] == 8
    assert result["questionsWithRecordedObservations"] == 0
    assert result["questionsWithCurrentDisputes"] == 0
    assert result["questionsReadyForAdjudication"] == 0
    assert result["questionsIndependentlyResolved"] == 0
    assert result["readyForScientificConclusion"] is False
    assert result["clinicalResult"] is None
    assert result["fdaApprovalProbability"] is None
    assert len(result["globalBlockers"]) == 4
    assert len(result["reviewQueue"]) == 8
    assert [x["priority"] for x in result["reviewQueue"][:2]] == ["critical", "critical"]
    assert all(item["mayAutoResolve"] is False for item in result["reviewQueue"])
    assert all(q["adjudicationStatus"] == "blocked_unverified"
               and q["readyToResolve"] is False
               and q["criteriaIndependentlySatisfied"] == 0
               for q in result["questions"])
    assert all("no_source_anchored_reviewer_observation" in q["blockerIds"]
               for q in result["questions"])


def test_multiple_self_reported_reviewers_are_never_authenticated_independent_reviewers():
    a = observation("thread-a", 1, "supports", label="Reviewer A")
    b = observation("thread-b", 1, "supports", label="Reviewer B")
    result = adjudication_preflight(NCT, reconciliation_worklist(NCT), history(a, b))
    question = result["questions"][0]
    assert question["reviewObservationsRecorded"] is True
    assert question["selfDeclaredReviewerLabels"] == ["Reviewer A", "Reviewer B"]
    assert question["currentReviewerThreadCount"] == 2
    assert question["distinctSourceCount"] == 1
    assert result["questionsWithRecordedObservations"] == 1
    assert result["questionsReadyForAdjudication"] == 0
    assert result["reviewerIdentityAuthenticated"] is False
    assert result["independentDualReviewImplemented"] is False
    assert result["documentedSignoffs"] == 0
    assert all(q["readyToResolve"] is False for q in result["questions"])


def test_conflicting_latest_threads_are_flagged_not_resolved():
    a = observation("thread-a", 1, "supports")
    b = observation("thread-b", 1, "contradicts")
    result = adjudication_preflight(NCT, reconciliation_worklist(NCT), history(a, b))
    assert result["questionsWithCurrentDisputes"] == 1
    assert "conflicting_current_reviewer_statements" in result["questions"][0]["blockerIds"]
    assert result["questions"][0]["readyToResolve"] is False
    assert result["questionsIndependentlyResolved"] == 0
    assert result["reviewQueue"][0]["questionId"] == "protocol_amendment_chronology"
    assert result["reviewQueue"][0]["nextAction"] == "Reconcile conflicting source-anchored claims"


def test_latest_revision_replaces_prior_claim_for_current_dispute_detection():
    a = observation("thread-a", 1, "supports")
    b = observation("thread-b", 1, "contradicts")
    revision = observation("thread-b", 2, "uncertain")
    result = adjudication_preflight(
        NCT, reconciliation_worklist(NCT), history(a, b, revision)
    )
    q = result["questions"][0]
    assert q["currentReviewerThreadCount"] == 2
    assert q["currentStatementTypes"] == ["supports", "uncertain"]
    assert q["conflictingCurrentStatements"] is False
    assert "uncertainty_or_unassessable_statement" in q["blockerIds"]
    assert result["questionsWithCurrentDisputes"] == 0
    assert result["questionsReadyForAdjudication"] == 0


@pytest.mark.parametrize("mutation", [
    {"nctId": OTHER},
    {"independentlyVerified": True},
])
def test_cross_trial_or_self_verified_note_is_refused(mutation):
    note = {**observation("thread-a", 1, "supports"), **mutation}
    with pytest.raises(ValueError):
        adjudication_preflight(NCT, reconciliation_worklist(NCT), history(note))


def test_complete_history_required_and_wrong_trial_worklist_rejected():
    note = observation("thread-a", 1, "supports")
    incomplete = history(note)
    incomplete["totalStatements"] = 2
    with pytest.raises(ValueError, match="complete"):
        adjudication_preflight(NCT, reconciliation_worklist(NCT), incomplete)
    incomplete = history(note)
    incomplete["truncated"] = True
    with pytest.raises(ValueError, match="complete"):
        adjudication_preflight(NCT, reconciliation_worklist(NCT), incomplete)
    with pytest.raises(ValueError, match="another trial"):
        adjudication_preflight(NCT, reconciliation_worklist(OTHER), history(note))
    with pytest.raises(ValueError, match="Exact NCT"):
        adjudication_preflight("NCT12", reconciliation_worklist(NCT), history())


def test_unrecognized_question_fails_closed():
    stray = observation("thread-a", 1, "supports", question="wrong_trial_gate")
    with pytest.raises(ValueError, match="unknown question"):
        adjudication_preflight(NCT, reconciliation_worklist(NCT), history(stray))


def test_empty_archived_trial_integration_is_read_only_and_authenticated(monkeypatch):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://test.invalid/review")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "integration-header-only")
    source = {
        "protocolSection": {"identificationModule": {"nctId": NCT}},
        "hasResults": False,
    }
    raw = json.dumps(source, sort_keys=True).encode()
    with Session(engine) as session:
        session.add(main.FullTrialRecord(
            nct_id=NCT,
            payload_gzip=gzip.compress(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            summary={"nctId": NCT}, statistics=[],
            fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        ))
        session.commit()
    client = TestClient(main.app)
    url = "/api/scientific-assessment?exact_id=TRIAL%7C" + NCT
    assert client.get(url).status_code == 401
    body = client.get(url, headers={
        "x-pdufa-internal-key": "integration-header-only"
    }).json()
    preflight = body["evidenceLedger"]["adjudicationPreflight"]
    assert preflight["questionCount"] == 8
    assert preflight["questionsReadyForAdjudication"] == 0
    assert body["readinessGrades"]["analysisReadiness"]["readyForFullScientificConclusion"] is False
    assert body["readinessGrades"]["scientificReluctance"]["grade"] == "F"
    packet = client.get(
        "/api/scientific-assessment/review-packet/" + NCT,
        headers={"x-pdufa-internal-key": "integration-header-only"},
    ).json()
    assert packet["adjudicationPreflight"] == packet["independentSourceLedger"]["adjudicationPreflight"]
    assert packet["adjudicationPreflight"]["questionsIndependentlyResolved"] == 0
    assert packet["scientificConclusion"] is None
    assert packet["fdaApprovalProbability"] is None
    assert packet["tradingEnabled"] is False
    with Session(engine) as session:
        assert session.query(main.FullTrialRecord).count() == 1
        assert session.query(main.ScientificReviewerFinding).count() == 0
        assert session.query(main.ScientificEvidenceLedgerEntry).count() == 0
    engine.dispose()


@pytest.mark.parametrize("change", [
    {"revision": 0},
    {"revision": "2"},
    {"threadId": ""},
    {"findingType": "verified"},
    {"sourceUrl": None},
])
def test_malformed_reviewer_statement_fails_closed(change):
    bad = {**observation("thread-a", 1, "supports"), **change}
    with pytest.raises(ValueError, match="Malformed adjudication reviewer statement"):
        adjudication_preflight(NCT, reconciliation_worklist(NCT), history(bad))


def test_malformed_question_fails_closed():
    worklist = reconciliation_worklist(NCT)
    worklist["checks"][0]["priority"] = None
    with pytest.raises(ValueError, match="Malformed adjudication question"):
        adjudication_preflight(NCT, worklist, history())


def test_duplicate_thread_revision_fails_closed():
    first = observation("thread-a", 1, "supports")
    duplicate = observation("thread-a", 1, "contradicts")
    with pytest.raises(ValueError, match="Duplicate adjudication reviewer revision"):
        adjudication_preflight(NCT, reconciliation_worklist(NCT), history(first, duplicate))


@pytest.mark.parametrize("invalid", [None, [], "invalid"])
def test_invalid_preflight_payloads_fail_closed(invalid):
    with pytest.raises(ValueError, match="Adjudication evidence payloads unavailable"):
        adjudication_preflight(NCT, invalid, history())
    with pytest.raises(ValueError, match="Adjudication evidence payloads unavailable"):
        adjudication_preflight(NCT, reconciliation_worklist(NCT), invalid)


@pytest.mark.parametrize("invalid", [None, "not-a-list", [None], [123]])
def test_invalid_question_source_url_list_fails_closed(invalid):
    worklist = reconciliation_worklist(NCT)
    worklist["checks"][0]["sourceUrls"] = invalid
    with pytest.raises(ValueError, match="Malformed adjudication question"):
        adjudication_preflight(NCT, worklist, history())


@pytest.mark.parametrize("change", [{"questionId": None}, {"reviewerLabel": None}])
def test_invalid_reviewer_reference_fields_fail_closed(change):
    bad = {**observation("thread-a", 1, "supports"), **change}
    with pytest.raises(ValueError, match="Malformed adjudication reviewer statement"):
        adjudication_preflight(NCT, reconciliation_worklist(NCT), history(bad))
