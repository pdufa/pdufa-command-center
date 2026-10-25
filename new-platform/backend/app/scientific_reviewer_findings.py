"""Append-only, source-linked scientific reviewer *statements*, not adjudication.

Stored claims may SUPPORT or CONTRADICT one another. Reviewer identities are
self-declared labels, not authentication of medical qualifications. No entry
can resolve a worklist gate, assign efficacy, or predict FDA approval.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from collections.abc import Mapping

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from . import main
from .scientific_evidence_ledger import (
    ID_PATTERN, MAX_RECORDS, _fields as ledger_fields, _hash as ledger_hash,
    pilot_candidates, require_registry_trial_identity, validate_public_https,
)
from .scientific_investigation_20 import NCT_PATTERN
from .scientific_reconciliation_worklist import reconciliation_worklist
from .scientific_stored_record import verified_record_from_archive

KINDS = {"supports", "contradicts", "uncertain", "not_assessable"}
STATUS = "reviewer_statement_pending_independent_confirmation"
_HASH_FIELDS = (
    "id", "nct_id", "question_id", "gate_id", "thread_id", "revision",
    "supersedes_id", "source_url", "source_locator", "finding_type",
    "assertion", "uncertainty", "reviewer_label", "reviewed_at",
)


def _timestamp(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt.tzinfo is None \
        else dt.astimezone(timezone.utc).isoformat()


def _fields(item: main.ScientificReviewerFinding) -> dict:
    return {
        "id": item.id, "nct_id": item.nct_id,
        "question_id": item.question_id, "gate_id": item.gate_id,
        "thread_id": item.thread_id, "revision": item.revision,
        "supersedes_id": item.supersedes_id, "source_url": item.source_url,
        "source_locator": item.source_locator, "finding_type": item.finding_type,
        "assertion": item.assertion, "uncertainty": item.uncertainty,
        "reviewer_label": item.reviewer_label,
        "reviewed_at": _timestamp(item.reviewed_at),
    }


def _hash(fields: Mapping) -> str:
    canonical = json.dumps(
        {key: fields[key] for key in _HASH_FIELDS},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _serialize(item: main.ScientificReviewerFinding) -> dict:
    content = _fields(item)
    if item.content_sha256 != _hash(content):
        raise ValueError("Scientific reviewer statement integrity mismatch")
    return {
        "id": item.id, "nctId": item.nct_id, "questionId": item.question_id,
        "gateId": item.gate_id, "threadId": item.thread_id,
        "revision": item.revision, "supersedesId": item.supersedes_id,
        "sourceUrl": item.source_url, "sourceLocator": item.source_locator,
        "findingType": item.finding_type, "assertion": item.assertion,
        "uncertainty": item.uncertainty, "reviewerLabel": item.reviewer_label,
        "reviewedAt": content["reviewed_at"],
        "contentSha256": item.content_sha256,
        "reviewStatus": STATUS,
        "reviewerIdentityVerified": False,
        "independentlyVerified": False,
        "canResolveQuestion": False,
        "canCountTowardReadiness": False,
    }


def _allowed_sources(session: Session, nct_id: str, question: dict) -> set[str]:
    allowed = set(question["sourceUrls"])
    allowed.update(item["sourceUrl"] for item in pilot_candidates(nct_id)
                   if item["gateId"] == question["gateId"])
    entries = session.scalars(
        select(main.ScientificEvidenceLedgerEntry).where(
            main.ScientificEvidenceLedgerEntry.nct_id == nct_id,
            main.ScientificEvidenceLedgerEntry.gate_id == question["gateId"],
        )
    ).all()
    for item in entries:
        if ledger_hash(ledger_fields(item)) != item.content_sha256:
            raise ValueError("Evidence ledger entry integrity mismatch")
        allowed.add(item.source_url)
    return allowed


def append_reviewer_statement(nct_id: str, data: dict) -> dict:
    if not isinstance(nct_id, str) or not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    worklist = reconciliation_worklist(nct_id)
    question = next((v for v in worklist["checks"]
                     if v["id"] == data["questionId"]), None)
    if question is None:
        raise ValueError("Unknown review question for this exact NCT")
    kind = data["findingType"]
    if kind not in KINDS:
        raise ValueError("Unsupported reviewer statement classification")
    source = validate_public_https(data["sourceUrl"])
    require_registry_trial_identity(source, nct_id)
    prior_id = data.get("supersedesId")
    if prior_id is not None and (not isinstance(prior_id, str)
                                or not ID_PATTERN.fullmatch(prior_id)):
        raise ValueError("Invalid prior reviewer statement identifier")
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4().hex
    with Session(main.ENGINE) as session:
        archive = session.get(main.FullTrialRecord, nct_id)
        if archive is None:
            raise ValueError("Exact trial must already be archived")
        verified_record_from_archive(nct_id, archive.payload_gzip, archive.sha256)
        if source not in _allowed_sources(session, nct_id, question):
            raise ValueError("Source must match a listed question citation or same-gate ledger candidate")
        if prior_id is not None:
            prior = session.get(main.ScientificReviewerFinding, prior_id)
            if prior is None or prior.nct_id != nct_id or prior.question_id != question["id"]:
                raise ValueError("Original reviewer statement not in exact trial/question")
            _serialize(prior)
            child = session.scalar(
                select(main.ScientificReviewerFinding.id).where(
                    main.ScientificReviewerFinding.supersedes_id == prior_id
                ).limit(1)
            )
            if child:
                raise ValueError("Reviewer statement revision already superseded")
            thread_id, revision = prior.thread_id, prior.revision + 1
        else:
            thread_id, revision = uid, 1
        row = main.ScientificReviewerFinding(
            id=uid, nct_id=nct_id, question_id=question["id"],
            gate_id=question["gateId"], thread_id=thread_id,
            revision=revision, supersedes_id=prior_id,
            source_url=source, source_locator=data["sourceLocator"],
            finding_type=kind, assertion=data["assertion"],
            uncertainty=data["uncertainty"],
            reviewer_label=data["reviewerLabel"], reviewed_at=now,
            content_sha256="0"*64,
        )
        row.content_sha256 = _hash(_fields(row))
        session.add(row)
        session.commit()
        return _serialize(row)


def read_reviewer_statements(nct_id: str) -> dict:
    if not isinstance(nct_id, str) or not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    with Session(main.ENGINE) as session:
        total = session.scalar(select(func.count()).select_from(
            main.ScientificReviewerFinding).where(
                main.ScientificReviewerFinding.nct_id == nct_id
            )) or 0
        # Integrity-check ALL entries, including outside presentation cap:
        # conflicts cannot disappear silently if an old row was tampered with.
        records = session.scalars(select(main.ScientificReviewerFinding).where(
            main.ScientificReviewerFinding.nct_id == nct_id
        ).order_by(main.ScientificReviewerFinding.reviewed_at.desc(),
                   main.ScientificReviewerFinding.id.desc())).all()
        findings = [_serialize(item) for item in records]
    worklist = reconciliation_worklist(nct_id)
    grouped: dict[str, list[dict]] = {q["id"]: [] for q in worklist["checks"]}
    for item in findings:
        if item["questionId"] not in grouped:
            raise ValueError("Reviewer statement refers to unknown trial question")
        grouped[item["questionId"]].append(item)
    summaries = []
    disputed_count = 0
    for question in worklist["checks"]:
        history = grouped[question["id"]]
        # Latest revisions per thread only for the conflict diagnostic; all
        # historic revisions remain in the evidence list.
        threads: dict[str, dict] = {}
        for item in history:
            previous = threads.get(item["threadId"])
            if previous is None or previous["revision"] < item["revision"]:
                threads[item["threadId"]] = item
        kinds = {item["findingType"] for item in threads.values()}
        disputed = "supports" in kinds and "contradicts" in kinds
        disputed_count += int(disputed)
        summaries.append({
            "questionId": question["id"],
            "statementCount": len(history),
            "threadCount": len(threads),
            "conflictingReviewerStatements": disputed,
            "reviewStatus": "open_unadjudicated",
            "resolved": False, "independentlyVerified": False,
        })
    return {
        "nctId": nct_id,
        "totalStatements": total,
        "statementsShown": min(len(findings), MAX_RECORDS),
        "truncated": total > MAX_RECORDS,
        "statements": findings[:MAX_RECORDS],
        "questionSummaries": summaries,
        "questionsWithConflictingStatements": disputed_count,
        "questionsIndependentlyResolved": 0,
        "reviewerIdentityAuthenticated": False,
        "independentConfirmationImplemented": False,
        "readinessGradesAutomaticallyPromoted": False,
        "scientificConclusion": None,
        "fdaApprovalProbability": None,
        "note": "Statements are source-linked reviewer assertions, not validated clinical findings or final adjudications.",
    }
