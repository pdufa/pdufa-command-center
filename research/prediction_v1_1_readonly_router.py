"""Read-only v1.1 research evidence endpoint adapter.

Not mounted into production FastAPI. Authentication and database binding must
be implemented by the hosting application before mounting this router.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException

from research.prediction_v1_1_evidence_projection import program_evidence_summary
from research.prediction_v1_1_authorization import authorize_research_read

router = APIRouter(prefix="/research/v1-1/evidence", tags=["research-evidence"])


def _unconfigured_database():
    raise HTTPException(status_code=503, detail="Research evidence database is not connected")


def _unconfigured_identity():
    raise HTTPException(status_code=503, detail="Authenticated research access is not connected")


def _unconfigured_catalog():
    raise HTTPException(status_code=503, detail="Research catalog service is not connected")


@router.get("/{program_id:path}")
def read_evidence_status(program_id: str, db=Depends(_unconfigured_database),
                         principal=Depends(_unconfigured_identity),
                         catalog=Depends(_unconfigured_catalog)):
    """Never disclose evidence without authenticated program-scoped permission."""
    try:
        authorize_research_read(principal, program_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Research evidence access denied")
    result = program_evidence_summary(db, catalog, program_id)
    return result
