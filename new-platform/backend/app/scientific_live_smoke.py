"""Single opt-in live HTTP smoke test for the isolated Scientific Assessment service.

Set PDUFA_SCIENTIFIC_SMOKE_NCT to ONE ALREADY ARCHIVED exact NCT identifier
for a temporary deployment, then clear the flag and redeploy. Runs inside
the isolated service and reads the existing API key only from its environment.

No API key, connection URL, registry content or HTTP response body is logged.
Never schedules scans, touches trading, or automatically retries a failed job.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import main

_LOG = logging.getLogger(__name__)
_ISOLATED_SERVICE_ID = "srv-dbehn9fb9u1s739ok5vg"
_NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")
_TERMINAL = {"completed", "completed_with_errors", "interrupted"}
_BASE_URL = "http://127.0.0.1:8000"


def _request(method: str, path: str, key: str | None, payload: dict | None = None) -> tuple[int, dict]:
    """Use real loopback HTTP, never a public URL or untrusted destination."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if key is not None:
        headers["x-pdufa-internal-key"] = key
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(_BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=12) as response:
            raw = response.read(100_001)
            if len(raw) > 100_000:
                raise ValueError("Oversized smoke response")
            return response.status, json.loads(raw)
    except HTTPError as error:
        # Never print the response or sensitive exception text.
        return error.code, {}


def _preflight(nct_id: str) -> tuple[bool, str]:
    if not _NCT_PATTERN.fullmatch(nct_id):
        return False, "invalid_id"
    if os.getenv("RENDER_SERVICE_ID") != _ISOLATED_SERVICE_ID:
        return False, "wrong_service"
    if os.getenv("PDUFA_SCIENTIFIC_BATCH_WRITE_ENABLED") != "1":
        return False, "write_disabled"
    if not os.getenv("PDUFA_INTERNAL_API_KEY"):
        return False, "missing_internal_key"
    if not main.DATABASE_URL.startswith("postgresql+psycopg://"):
        return False, "not_postgresql"
    if not main._DB_STATE.get("available"):
        return False, "storage_not_ready"
    with Session(main.ENGINE) as session:
        if session.get(main.FullTrialRecord, nct_id) is None:
            return False, "source_not_archived"
        active = session.scalar(
            select(main.ScientificBatchJob.id)
            .where(main.ScientificBatchJob.active_slot.is_not(None))
            .limit(1)
        )
        if active:
            return False, "unfinished_batch_present"
        # Durable replay guard: a previous single-ID batch means the smoke
        # cannot safely re-run on a restart without operator review.
        previous = session.scalars(
            select(main.ScientificBatchJob).order_by(
                main.ScientificBatchJob.created_at.desc()
            ).limit(100)
        ).all()
        if any(job.nct_ids == [nct_id] for job in previous):
            return False, "single_id_batch_already_recorded"
    return True, "ready"


def _claim_once(nct_id: str) -> bool:
    """Atomic PostgreSQL primary-key claim; only one concurrent smoke may submit."""
    with Session(main.ENGINE) as session:
        session.add(main.ScientificSmokeClaim(
            nct_id=nct_id, status="claimed", claimed_at=datetime.now(timezone.utc),
            finished_at=None,
        ))
        try:
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            return False


def _finish_claim(nct_id: str, passed: bool) -> None:
    with Session(main.ENGINE) as session:
        claim = session.get(main.ScientificSmokeClaim, nct_id)
        if claim is None:
            raise RuntimeError("Scientific smoke claim lost")
        claim.status = "passed" if passed else "failed"
        claim.finished_at = datetime.now(timezone.utc)
        session.commit()


def run_smoke(nct_id: str, *, delay_before_start: float = 5.0,
              poll_interval: float = 1.0, max_polls: int = 100) -> bool:
    """Check 401/200/202 and durable completion through deployed HTTP routes."""
    claimed = False
    passed = False
    try:
        ready, reason = _preflight(nct_id)
        if not ready:
            _LOG.warning("SCIENTIFIC_E2E_SMOKE status=SKIPPED reason=%s", reason)
            return False
        if not _claim_once(nct_id):
            _LOG.warning("SCIENTIFIC_E2E_SMOKE status=SKIPPED reason=atomic_claim_already_exists")
            return False
        claimed = True
        time.sleep(delay_before_start)
        key = os.environ["PDUFA_INTERNAL_API_KEY"]
        status, _ = _request("GET", "/api/scientific-assessment/batches", None)
        if status != 401:
            _LOG.error("SCIENTIFIC_E2E_SMOKE status=FAIL stage=unauthorized_rejection code=%s", status)
            return False
        status, records = _request("GET", "/api/scientific-assessment/batches", key)
        if status != 200 or not isinstance(records.get("jobs"), list):
            _LOG.error("SCIENTIFIC_E2E_SMOKE status=FAIL stage=authenticated_read code=%s", status)
            return False
        status, submitted = _request(
            "POST", "/api/scientific-assessment/batches", key, {"nct_ids": [nct_id]}
        )
        if status != 202 or not re.fullmatch(r"[0-9a-f]{32}", str(submitted.get("id", ""))):
            _LOG.error("SCIENTIFIC_E2E_SMOKE status=FAIL stage=authenticated_submit code=%s", status)
            return False
        job_id = submitted["id"]
        for _ in range(max_polls):
            time.sleep(poll_interval)
            status, job = _request("GET", "/api/scientific-assessment/batches/" + job_id, key)
            if status != 200:
                _LOG.error("SCIENTIFIC_E2E_SMOKE status=FAIL stage=job_read code=%s", status)
                return False
            if job.get("status") in _TERMINAL:
                valid = (job.get("status") == "completed" and job.get("processed") == 1
                         and job.get("already_exists") == 1 and job.get("imported") == 0
                         and job.get("failed") == 0
                         and len(job.get("events", [])) == 1
                         and job["events"][0].get("status") == "already_exists")
                _LOG.warning("SCIENTIFIC_E2E_SMOKE status=%s stage=completed "
                             "archived_record_unchanged=%s processed=%s",
                             "PASS" if valid else "FAIL",
                             valid, job.get("processed"))
                passed = valid
                return valid
        _LOG.error("SCIENTIFIC_E2E_SMOKE status=FAIL stage=timeout job_left_untouched=True")
        return False
    except Exception as exc:
        _LOG.error("SCIENTIFIC_E2E_SMOKE status=FAIL stage=unexpected error_type=%s",
                   type(exc).__name__)
        return False
    finally:
        if claimed:
            try:
                _finish_claim(nct_id, passed)
            except Exception as exc:
                _LOG.error("SCIENTIFIC_E2E_SMOKE status=FAIL stage=claim_finalization error_type=%s",
                           type(exc).__name__)


def launch_once_if_requested() -> None:
    nct_id = os.getenv("PDUFA_SCIENTIFIC_SMOKE_NCT", "")
    if not nct_id or "PYTEST_CURRENT_TEST" in os.environ:
        return
    # This thread is not a recurring scanner, and never automatically retries.
    threading.Thread(target=run_smoke, args=(nct_id,),
                     name="scientific-review-e2e-smoke", daemon=True).start()
