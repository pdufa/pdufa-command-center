"""Authenticated controller state API backed by the existing persistent Neon DB.

No endpoint triggers a GitHub workflow or broker action. A separate, opted-in
worker may claim a stage with optimistic concurrency and then report evidence.
"""
from __future__ import annotations

import copy
import os
from datetime import datetime
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .master_automation import (
    ControllerRun, INDEX, STAGES, claim, finish, new_state, public, resume, utcnow,
)


class NewRun(BaseModel):
    runKey: str = Field(min_length=4, max_length=80)
    sourceSha: str = Field(min_length=40, max_length=40)


class Mutation(BaseModel):
    version: int = Field(ge=1)
    stage: str = Field(min_length=3, max_length=30)


class Claim(Mutation):
    worker: str = Field(min_length=6, max_length=96)


class Complete(Claim):
    conclusion: str
    workflowRunId: int = Field(ge=0)
    evidenceDigest: str | None = None
    errorCode: str | None = None


def _writes_on():
    if os.getenv("PDUFA_MASTER_WRITES_ENABLED") != "1":
        raise HTTPException(503, "Master controller is staged read-only; opt-in required")


def install_routes(app: FastAPI, engine: Callable, require_key: Callable,
                   require_storage: Callable, require_writes_enabled: Callable):
    read = [Depends(require_key), Depends(require_storage)]
    write = [*read, Depends(require_writes_enabled), Depends(_writes_on)]

    def serialize(row):
        return public(row.state, row.version)

    def mutate(run_id: str, expected: int, apply):
        with Session(engine()) as session:
            record = session.get(ControllerRun, run_id)
            if record is None:
                raise HTTPException(404, "Controller run not found")
            if record.version != expected:
                raise HTTPException(409, "Controller revision conflict; reload before retry")
            state = copy.deepcopy(record.state)
            try:
                apply(state)
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from None
            saved = session.execute(
                update(ControllerRun)
                .where(ControllerRun.id == run_id, ControllerRun.version == expected)
                .values(state=state, version=expected + 1, updated_at=utcnow())
            )
            if saved.rowcount != 1:
                session.rollback()
                raise HTTPException(409, "Concurrent controller update; no overwrite")
            session.commit()
            return public(state, expected + 1)

    @app.get("/api/master-automation", dependencies=read)
    def overview():
        with Session(engine()) as session:
            row = session.scalars(
                select(ControllerRun).order_by(ControllerRun.updated_at.desc()).limit(1)
            ).first()
            return {
                "configured": True,
                "writesEnabled": os.getenv("PDUFA_MASTER_WRITES_ENABLED") == "1",
                "workflowExecutionEnabled": False,
                "latest": serialize(row) if row else None,
                "stages": [
                    {"id": x["id"], "label": x["label"], "workflow": x["workflow"],
                     "integration": x["kind"], "needs": list(x["needs"])}
                    for x in STAGES
                ],
                "fullEndToEndCertified": False,
                "tradingOrdersEnabled": False,
            }

    @app.get("/api/master-automation/runs/{run_id}", dependencies=read)
    def read_run(run_id: str):
        with Session(engine()) as session:
            row = session.get(ControllerRun, run_id)
            if row is None:
                raise HTTPException(404, "Controller run not found")
            return serialize(row)

    @app.post("/api/master-automation/runs", dependencies=write)
    def create_run(payload: NewRun):
        try:
            state = new_state(payload.runKey, payload.sourceSha)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        now = utcnow()
        with Session(engine()) as session:
            old = session.scalars(
                select(ControllerRun).where(ControllerRun.run_key == payload.runKey)
            ).first()
            if old:
                if old.source_sha != payload.sourceSha:
                    raise HTTPException(409, "Existing run key is pinned to a different SHA")
                return serialize(old)
            row = ControllerRun(id=state["runId"], run_key=payload.runKey,
                                source_sha=payload.sourceSha, state=state,
                                version=1, created_at=now, updated_at=now)
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(409, "Run key already created concurrently; reload")
            return serialize(row)

    @app.post("/api/master-automation/runs/{run_id}/claim", dependencies=write)
    def claim_stage(run_id: str, payload: Claim):
        return mutate(run_id, payload.version,
                      lambda state: claim(state, payload.stage, payload.worker))

    @app.post("/api/master-automation/runs/{run_id}/complete", dependencies=write)
    def complete_stage(run_id: str, payload: Complete):
        return mutate(run_id, payload.version,
                      lambda state: finish(
                          state, payload.stage, payload.worker, payload.conclusion,
                          payload.workflowRunId, payload.evidenceDigest,
                          payload.errorCode))

    @app.post("/api/master-automation/runs/{run_id}/resume", dependencies=write)
    def resume_failed(run_id: str, payload: Mutation):
        return mutate(run_id, payload.version,
                      lambda state: resume(state, payload.stage))
