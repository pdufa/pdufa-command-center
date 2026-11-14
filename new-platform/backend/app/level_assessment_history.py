"""Append-only storage for server-executed Levels 1–6 research reports.

No legacy scores, predictions or memberships are read or modified here.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from . import main as db


def _require(condition):
    if not condition:
        raise ValueError("Invalid assessment")


def save(report: dict):
    if os.getenv('PDUFA_MIGRATION_READ_ONLY', '').lower() in {'1', 'true', 'yes'}:
        raise HTTPException(503, 'Assessment history is read-only')
    try:
        UUID(report['runId'])
        _require(report['kind'] == 'TRIAL_LEVEL_ASSESSMENT')
        _require(report['mode'] == 'CURRENT_EVIDENCE')
        _require(re.fullmatch(r'NCT\d{8}', report['nct']))
        _require(type(report['level']) is int and 1 <= report['level'] <= 6)
        _require(report['engineVersion'] == f"phase-first-level-{report['level']}-v1")
        _require(report['result']['levels'][0]['level'] == report['level'])
        _require(len(report['result']['levels']) == 1)
        _require(report['result']['nct'] == report['nct'])
        _require(report['fdaPrediction'] == {'outcome': 'ABSTAIN', 'probability': None, 'calibration': 'NO_VALIDATED_FDA_MODEL'})
        _require(report['score'] is None)
        _require(report['savedToDatabase'] is False)
        _require(report['status'] == 'PARTIAL_RESEARCH_ENGINE')
        _require(report['evidence']['verification'] == 'EXACT_NCT_REGISTRY_RESPONSE_ONLY')
        _require(re.fullmatch(r'[a-f0-9]{64}', report['evidence']['sha256']))
        _require(report['evidence']['url'] == 'https://clinicaltrials.gov/api/v2/studies/' + report['nct'])
        _require(datetime.fromisoformat(report['executedAt'].replace('Z', '+00:00')).tzinfo)
        encoded = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False)
        _require(len(encoded.encode()) <= 1_000_000)
    except (KeyError, ValueError, TypeError, IndexError, AttributeError):
        raise HTTPException(422, 'Invalid server assessment report')
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    with Session(db.ENGINE) as session:
        row = db.LevelAssessmentRun(run_id=report['runId'], nct_id=report['nct'], level=report['level'],
                                    engine_version=report['engineVersion'], evidence_hash=digest,
                                    report=report, saved_at=datetime.now(timezone.utc))
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, 'Run already exists; history cannot be overwritten')
    return {**report, 'savedToDatabase': True, 'reportHash': digest}


def history(nct: str, level: int | None = None):
    if not re.fullmatch(r'NCT\d{8}', nct) or (level is not None and not 1 <= level <= 6):
        raise HTTPException(422, 'Exact NCT and level 1–6 required')
    query = select(db.LevelAssessmentRun).where(db.LevelAssessmentRun.nct_id == nct)
    if level is not None:
        query = query.where(db.LevelAssessmentRun.level == level)
    with Session(db.ENGINE) as session:
        rows = list(session.scalars(query.order_by(db.LevelAssessmentRun.saved_at.desc(), db.LevelAssessmentRun.run_id).limit(51)))
        runs, size = [], 0
        for row in rows[:50]:
            item = {**row.report, 'savedToDatabase': True, 'reportHash': row.evidence_hash}
            size += len(json.dumps(item).encode())
            if size > 3_000_000:
                break
            runs.append(item)
        return {'nct': nct, 'runs': runs, 'hasMore': len(rows) > len(runs)}
