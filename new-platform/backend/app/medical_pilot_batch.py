"""One-time, exact-NCT, PostgreSQL-only medical source research batch.

The isolated preview may execute this on startup only when the three-key
campaign gate is explicitly enabled. This never releases an FDA probability,
does not run on production by default, and cannot start more than three
additional FOCUS NCTs per explicitly named campaign. Durable idempotency prevents replay on restart.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
import uuid

from sqlalchemy import text

LOG = logging.getLogger(__name__)
CAMPAIGN = re.compile(r"[A-Za-z0-9_-]{8,72}\Z")
YES = ("true", "1", "yes")


def requested():
    """Validate before creating any tables, research requests or threads."""
    from . import medical_continuous as core
    if os.getenv("PDUFA_MEDICAL_BATCH_AUTORUN", "").lower() not in YES:
        return None
    campaign = os.getenv("PDUFA_MEDICAL_BATCH_CAMPAIGN", "")
    raw = os.getenv("PDUFA_MEDICAL_BATCH_NCTS", "")
    studies = [x.strip() for x in raw.split(",")]
    if (not CAMPAIGN.fullmatch(campaign) or not (1 <= len(studies) <= 3)
            or len(set(studies)) != 3 or
            any(not core.NCT.fullmatch(x) for x in studies)):
        raise ValueError("Batch gate requires one named campaign and one to three unique NCTs")
    if os.getenv("PDUFA_ANALYZE_NOW_ALL_ENABLED", "").lower() in YES:
        raise ValueError("Global all-trial rollout must remain disabled")
    canary = os.getenv("PDUFA_ANALYZE_NOW_CANARY_NCT", "NCT06081894")
    if canary in studies:
        raise ValueError("The original canary cannot be rerun by the batch")
    roster = core.roster()
    if not all(x in roster for x in studies):
        raise ValueError("Requested batch includes a non-FOCUS trial")
    return campaign, tuple(studies)


def allowed_ncts():
    """Use the same exact allowlist for manual/change triggers and batch jobs."""
    config = requested()
    return frozenset(config[1]) if config else frozenset()


def _idempotency(campaign, nct):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "pdufa-medical-batch:" + campaign + ":" + nct))


def initialize(engine):
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Controlled batch requires durable PostgreSQL")
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_batch_campaigns (
            campaign_key TEXT PRIMARY KEY, first_nct TEXT NOT NULL,
            stop_resume_verified BOOLEAN NOT NULL DEFAULT FALSE,
            verified_at TEXT, details TEXT NOT NULL DEFAULT 'PENDING')"""))


def _proof(engine, campaign, nct):
    with engine.connect() as c:
        row = c.execute(text("""SELECT first_nct,stop_resume_verified
            FROM medical_batch_campaigns WHERE campaign_key=:campaign"""),
            {"campaign":campaign}).first()
    if row is None:
        return False
    if row[0] != nct:
        raise RuntimeError("Campaign name belongs to a different trial")
    return bool(row[1])


def _mark_proof(engine, campaign, nct):
    from . import medical_continuous as core
    from . import medical_on_demand as saved
    latest = saved.latest(engine, nct)
    history = saved.history(engine, nct)
    key = _idempotency(campaign, nct)
    with engine.connect() as c:
        origin = c.execute(text("SELECT request_key FROM medical_continuous_runs WHERE run_id=:run"),
                           {"run":latest["runId"]}).scalar()
        first_count = c.execute(text("""SELECT COUNT(*) FROM medical_continuous_stages
            WHERE run_id=:run AND stage_index=0"""),
            {"run":latest["runId"]}).scalar_one()
        total = c.execute(text("""SELECT COUNT(*) FROM medical_continuous_stages
            WHERE run_id=:run"""), {"run":latest["runId"]}).scalar_one()
    verified = (origin == key and latest["status"] == "COMPLETE"
                and latest["completedStages"] == len(core.STAGES) == 12
                and first_count == 1 and total == 12
                and isinstance(latest.get("revision"), int)
                and any(h.get("runId") == latest["runId"] and
                        h.get("revision") == latest["revision"]
                        for h in history.get("records", [])))
    if not verified:
        return False
    with engine.begin() as c:
        c.execute(text("""UPDATE medical_batch_campaigns SET
            stop_resume_verified=TRUE,verified_at=:now,
            details='ONE_STAGE_STOP_RESUME_PERSISTED'
            WHERE campaign_key=:campaign AND first_nct=:nct"""),
            {"now":core.now(),"campaign":campaign,"nct":nct})
    return True


def _wait(engine, nct, run_id, seconds=240):
    from . import medical_on_demand as saved
    limit = time.monotonic() + seconds
    while time.monotonic() < limit:
        snapshot = saved.get_run(engine, nct, run_id)
        if snapshot["status"] in ("COMPLETE", "FAILED", "STOPPED"):
            return snapshot
        time.sleep(2)
    return saved.get_run(engine, nct, run_id)


def _one(engine, campaign, nct, *, stop_after_first):
    from . import medical_continuous as core
    from . import medical_on_demand as saved
    key = _idempotency(campaign, nct)
    snap = saved.start_now(engine, nct, key, submit=False, trigger="CONTROLLED_SOURCE_BATCH")
    with engine.connect() as c:
        origin = c.execute(text("SELECT request_key FROM medical_continuous_runs WHERE run_id=:id"),
                           {"id":snap["runId"]}).scalar()
    if origin != key:
        raise RuntimeError("Existing independently triggered run blocks controlled batch")
    if stop_after_first and snap["status"] == "PENDING" and snap["completedStages"] == 0:
        # Run the official trial identity/source stage, requesting stop before
        # its result is committed. The same worker persists that stage then
        # sees stop_requested and transitions to STOPPED on its next iteration.
        called = []
        def first_stage(index, exact_nct):
            if index != 0 or exact_nct != nct:
                raise RuntimeError("Stop/resume phase can run only source stage one")
            result = core.process_stage(index, exact_nct)
            if result[0] == "SOURCE_RECORDED":
                core.stop(engine, nct, snap["runId"])
                called.append(True)
            return result
        core.worker(engine, snap["runId"], step=first_stage)
        stopped = saved.get_run(engine, nct, snap["runId"])
        if (not called or stopped["status"] != "STOPPED"
                or stopped["completedStages"] != 1
                or stopped["stages"][0]["number"] != 1):
            raise RuntimeError("Live stage-one source stop did not pass; later NCTs remain blocked")
        LOG.warning("PDUFA_MEDICAL_BATCH_STOP status=PASS nct=%s stages=1", nct)
        core.resume(engine, nct, snap["runId"])
        snap = _wait(engine, nct, snap["runId"])
        if snap["status"] != "COMPLETE":
            raise RuntimeError("Source stage resume did not reach a persisted 12-stage result")
        if not _mark_proof(engine, campaign, nct):
            raise RuntimeError("Stop/resume immutable history verification failed")
        LOG.warning("PDUFA_MEDICAL_BATCH_RESUME status=PASS nct=%s stages=%d revision=%s",
                    nct, snap["completedStages"], snap["revision"])
        return snap

    if snap["status"] == "STOPPED":
        if not stop_after_first:
            raise RuntimeError("Unexpected stopped trial; no further batch runs launched")
        if snap["completedStages"] != 1:
            raise RuntimeError("Resumed canary must contain exactly the first stage")
        core.resume(engine,nct,snap["runId"])
    elif snap["status"] == "PENDING":
        core._POOL.submit(core.worker, engine, snap["runId"])
    elif snap["status"] not in ("RUNNING", "COMPLETE"):
        raise RuntimeError("Existing batch run is in a non-resumable state")

    snap = _wait(engine, nct, snap["runId"])
    if snap["status"] != "COMPLETE" or snap["completedStages"] != 12:
        raise RuntimeError("A batch source research run did not complete twelve recorded stages")
    if stop_after_first and not _proof(engine, campaign, nct):
        # A fresh run completed without the required live stop/resume proof.
        raise RuntimeError("No persisted live stop/resume proof; later trials remain blocked")
    from .medical_on_demand import history
    h = history(engine, nct)
    if not any(x.get("runId") == snap["runId"] and
               x.get("revision") == snap.get("revision") for x in h.get("records", [])):
        raise RuntimeError("Batch result missing from immutable history")
    LOG.warning("PDUFA_MEDICAL_BATCH_TRIAL status=PASS nct=%s stages=12 revision=%s",
                nct,snap["revision"])
    return snap


def launch(engine):
    """One bounded daemon runner; every new record uses a fixed campaign UUID."""
    config = requested()
    if not config:
        return
    campaign, studies = config
    initialize(engine)
    from . import medical_on_demand as saved
    pilot = os.getenv("PDUFA_ANALYZE_NOW_CANARY_NCT","NCT06081894")
    canary = saved.latest(engine,pilot)
    ledger = saved.history(engine,pilot)
    if (canary["status"]!="COMPLETE" or canary["completedStages"]!=12
            or not isinstance(canary.get("revision"),int)
            or not any(r.get("runId")==canary["runId"] and r.get("revision")==canary["revision"]
                       for r in ledger.get("records", []))):
        raise RuntimeError("Existing canary not independently saved and verified")
    with engine.begin() as c:
        c.execute(text("""INSERT INTO medical_batch_campaigns
            (campaign_key,first_nct,stop_resume_verified,details)
            VALUES(:campaign,:nct,FALSE,'PENDING')
            ON CONFLICT(campaign_key) DO NOTHING"""),
            {"campaign":campaign,"nct":studies[0]})
    if _proof(engine,campaign,studies[0]):
        LOG.warning("PDUFA_MEDICAL_BATCH_RESTART status=PREVIOUS_STOP_RESUME_VERIFIED campaign=%s",campaign)
    for pos,nct in enumerate(studies):
        try:
            _one(engine,campaign,nct,stop_after_first=pos==0)
        except Exception as exc:
            LOG.error("PDUFA_MEDICAL_BATCH status=HALTED index=%d nct=%s error_type=%s",
                      pos+1,nct,type(exc).__name__)
            return
    LOG.warning("PDUFA_MEDICAL_BATCH status=COMPLETE completed=%d target=%d "
                "scientificSignoff=False prediction=ABSTAIN certainty=NOT_VALIDATED",
                len(studies), len(studies))


def start(engine):
    config = requested()
    if not config:
        return
    LOG.warning("PDUFA_MEDICAL_BATCH status=STARTING target=%d sourceResearchOnly=True",
                len(config[1]))
    def run():
        try:
            launch(engine)
        except Exception as exc:
            LOG.error("PDUFA_MEDICAL_BATCH status=ABORTED error_type=%s",
                      type(exc).__name__)
    threading.Thread(target=run,name="medical-controlled-three",daemon=True).start()
