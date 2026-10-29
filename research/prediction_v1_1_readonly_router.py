"""Read-only v1.1 research evidence endpoint adapter.

Not mounted into production FastAPI. Authentication and database binding must
be implemented by the hosting application before mounting this router.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException

from research.prediction_v1_1_evidence_projection import program_evidence_summary

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
    if not getattr(principal, "is_authenticated", False):
        raise HTTPException(status_code=403, detail="Authentication required")
    if "evidence_reader" not in getattr(principal, "roles", ()):
        raise HTTPException(status_code=403, detail="Evidence reader role required")
    allowed_programs = getattr(principal, "program_ids", ())
    if program_id not in allowed_programs:
        raise HTTPException(status_code=403, detail="Program access denied")
    result = program_evidence_summary(db, catalog, program_id)
    return result
