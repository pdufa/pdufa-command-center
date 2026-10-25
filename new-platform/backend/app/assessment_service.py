"""Whole-universe score index plus exact-program evidence and durable history."""
from __future__ import annotations
from datetime import date, datetime, timezone
import hashlib
import json
import logging
import os
import threading
import time
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from . import main as db
from .candidate_assessments import MODEL, compact, fingerprint, nct_id, packed, score_candidate

LOG = logging.getLogger(__name__)
_LOCK = threading.RLock()
_STATE = {"key": "", "building": False, "index": None, "error": "", "snapshot": None, "reviews": {}, "token": ""}
_REVIEW_CACHE = {"at": 0, "value": {}, "status": "NOT_LOADED"}
FIELDS = ("nct_id", "study_title", "study_design", "treatment_groups", "primary_outcomes", "secondary_outcomes", "enrollment", "status", "last_update_posted", "primary_completion_date", "has_results")


def _reclaim_transient_memory():
    """Release completed scoring temporaries on the 512 MiB staging instance.

    No persistent evidence, index rows, or scores are changed. Python's GC
    clears unreachable objects; glibc then returns free malloc pages to Linux.
    Both steps are best-effort and do not gate the scoring result.
    """
    import gc
    gc.collect()
    try:
        import ctypes
        import sys
        if sys.platform.startswith("linux"):
            libc = ctypes.CDLL("libc.so.6")
            trim = libc.malloc_trim
            trim.argtypes = [ctypes.c_size_t]
            trim.restype = ctypes.c_int
            trim(0)
    except (AttributeError, OSError, ValueError):
        pass


def _build_index_with_reclamation(*args):
    """Reclaim only after build_index's large local variables have gone away."""
    try:
        return build_index(*args)
    finally:
        _reclaim_transient_memory()



def review_evidence():
    if time.monotonic() - _REVIEW_CACHE["at"] < 300: return _REVIEW_CACHE["value"], _REVIEW_CACHE["status"]
    from .source_workspace import fetch
    try:
        value = json.loads(fetch("candidate_assessment_reviews.json"))
        if value.get("schemaVersion") != 1 or not isinstance(value.get("programs"), dict): raise ValueError("Invalid reviews")
        _REVIEW_CACHE.update(at=time.monotonic(), value=value["programs"], status="AVAILABLE")
    except Exception:
        _REVIEW_CACHE.update(at=time.monotonic(), value={}, status="UNAVAILABLE")
    return _REVIEW_CACHE["value"], _REVIEW_CACHE["status"]


def rows_for(snapshot):
    rows = {r["id"]: r for r in snapshot["pipeline"]}
    if len(rows) != len(snapshot["pipeline"]): raise ValueError("Duplicate exact program IDs")
    for group in snapshot.get("members", {}).values():
        for member in group.get("rows", []):
            if member.get("id") in rows and member.get("ticker") == rows[member["id"]].get("ticker"):
                rows[member["id"]] = {**rows[member["id"]], **member}
    return rows


def tuple_summary(result):
    return [[m["score"], m["observedPoints"], m["coverage"],
             *[round(c["observedPoints"], 2) for c in m["categories"]],
             *[round(c["coverage"], 2) for c in m["categories"]]]
            for m in (result["models"][k] for k in ("PIPELINE", "GEM_JR", "GEM"))]


def registry_rows(ids=None):
    # Read only scoring inputs, never the lossless gzip archive or narrative modules.
    query = select(db.FullTrialRecord.nct_id, *[db.FullTrialRecord.summary[k] for k in FIELDS], db.FullTrialRecord.statistics, db.FullTrialRecord.fetched_at)
    if ids is not None: query = query.where(db.FullTrialRecord.nct_id.in_(ids))
    with Session(db.ENGINE) as session:
        for item in session.execute(query.execution_options(yield_per=100)):
            yield item[0], dict(zip(FIELDS, item[1:1 + len(FIELDS)])), item[-2] or [], item[-1].isoformat()


def build_index(snapshot, reviews, review_status, key, token):
    try:
        rows = rows_for(snapshot)
        by_nct = {}
        for row in rows.values():
            nct = nct_id(row)
            if nct: by_nct.setdefault(nct, []).append(row["id"])
        records, updates, covered = {}, [], set()
        writable = os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() not in {"1", "true", "yes"}
        with Session(db.ENGINE) as session:
            latest = select(func.max(db.CandidateAssessmentHistory.id)).group_by(db.CandidateAssessmentHistory.exact_id)
            prior = dict(session.execute(select(db.CandidateAssessmentHistory.exact_id, db.CandidateAssessmentHistory.evidence_hash)
                                         .where(db.CandidateAssessmentHistory.id.in_(latest))).all())
        clock = datetime.now(timezone.utc)
        def accept(row, registry=None, analyses=None, checked=""):
            result = score_candidate(row, registry, analyses, reviews.get(row["id"], {}), today=date.fromisoformat(snapshot["assessmentDate"]), registry_checked=checked)
            values = tuple_summary(result)
            evidence_hash = fingerprint(result)
            records[row["id"]] = [row["id"], *values, result["riskFlags"]]
            if writable and prior.get(row["id"]) != evidence_hash:
                updates.append({"exact_id": row["id"], "program_id": row.get("programId") or "", "model_version": MODEL,
                                "evidence_hash": evidence_hash, "summary": {"models": values, "riskFlags": result["riskFlags"]}, "assessed_at": clock})
        for nct, registry, analyses, checked in registry_rows():
            for identity in by_nct.get(nct, []):
                accept(rows[identity], registry, analyses, checked)
                covered.add(identity)
        for identity, row in rows.items():
            if identity not in records: accept(row)
        if set(records) != set(rows): raise ValueError("Scoring universe mismatch")
        if updates:
            from sqlalchemy import insert
            # Atomic append: a failed commit never publishes a completed run.
            with Session(db.ENGINE) as session:
                for offset in range(0, len(updates), 250): session.execute(insert(db.CandidateAssessmentHistory), updates[offset:offset + 250])
                session.commit()
        ordered = [records[row["id"]] for row in snapshot["pipeline"]]
        totals = {stage: {"complete": sum(record[i + 1][0] is not None for record in ordered),
                          "partial": sum(0 < record[i + 1][2] < 100 for record in ordered),
                          "missing": sum(record[i + 1][2] == 0 for record in ordered)} for i, stage in enumerate(("PIPELINE", "GEM_JR", "GEM"))}
        result = {"modelVersion": MODEL, "status": "COMPLETE", "version": key, "asOf": snapshot["assessmentDate"],
                  "computedAt": clock.isoformat(), "workspaceVersion": snapshot.get("workspaceVersion"),
                  "total": len(rows), "registryLinked": len(covered), "registryMissing": len(rows) - len(covered),
                  "reviewSource": review_status, "historyStatus": "SAVED" if writable else "READ_ONLY", "totals": totals,
                  "columns": ["id", "PIPELINE", "GEM_JR", "GEM", "riskFlags"],
                  "scoreColumns": ["score", "observedPoints", "coverage", "categoryPoints1to7", "categoryCoverage1to7"],
                  "records": ordered}
        # Keep the whole-universe payload safely under Vercel's response limit.
        if len(packed(result).encode()) > 4_000_000: raise ValueError("Score index exceeds response budget")
        with _LOCK:
            if _STATE["token"] == token: _STATE.update(key=key, building=False, index=result, snapshot=snapshot, reviews=reviews, error="")
        LOG.warning("CANDIDATE_ASSESSMENTS complete=%d registry=%d history_changes=%d", len(rows), len(covered), len(updates))
    except Exception as exc:
        LOG.error("CANDIDATE_ASSESSMENTS_FAILED error_type=%s", type(exc).__name__)
        with _LOCK:
            if _STATE["token"] == token: _STATE.update(building=False, error="Candidate assessments could not be verified. Retry the scoring index.")


def get_index(*, synchronous=False):
    from .source_workspace import workspace
    from .workspace_response import prepared
    from zoneinfo import ZoneInfo
    snapshot = prepared(workspace())
    if not snapshot.get("workspaceVersion") or snapshot.get("sourceHealth", {}).get("state") == "STALE":
        raise HTTPException(status_code=503, detail="Fresh versioned candidate source unavailable")
    reviews, review_status = review_evidence()
    with Session(db.ENGINE) as session:
        revision = session.execute(select(func.count(db.FullTrialRecord.nct_id), func.max(db.FullTrialRecord.fetched_at))).one()
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    key = hashlib.sha256(packed([MODEL, snapshot["workspaceVersion"], today, str(revision), reviews, review_status]).encode()).hexdigest()
    with _LOCK:
        if _STATE["key"] == key and _STATE["index"] is not None: return _STATE["index"]
        if _STATE["building"]: return {"modelVersion": MODEL, "status": "BUILDING", "total": len(snapshot["pipeline"])}
        token = hashlib.sha256((key + str(time.monotonic())).encode()).hexdigest()
        _STATE.update(building=True, token=token, error="")
    selected = {**snapshot, "assessmentDate": today}
    if synchronous:
        _build_index_with_reclamation(selected, reviews, review_status, key, token)
        if _STATE["error"]: raise HTTPException(status_code=503, detail=_STATE["error"])
        return _STATE["index"]
    threading.Thread(target=_build_index_with_reclamation, args=(selected, reviews, review_status, key, token), daemon=True).start()
    return {"modelVersion": MODEL, "status": "BUILDING", "total": len(snapshot["pipeline"])}


def exact_detail(identity):
    index = get_index()
    if index["status"] != "COMPLETE": raise HTTPException(status_code=409, detail="Scoring index is rebuilding; retry shortly")
    with _LOCK:
        snapshot, reviews = _STATE["snapshot"], _STATE["reviews"]
    row = rows_for(snapshot).get(identity)
    if row is None: raise HTTPException(status_code=404, detail="Exact program is not in the current Pipeline universe")
    nct = nct_id(row)
    saved = next(registry_rows([nct]), None) if nct else None
    result = score_candidate(row, saved[1] if saved else None, saved[2] if saved else None, reviews.get(identity, {}),
                             today=date.fromisoformat(snapshot["assessmentDate"]), registry_checked=saved[3] if saved else "")
    indexed = next((record for record in index["records"] if record[0] == identity), None)
    if indexed is None or tuple_summary(result) != indexed[1:4]:
        raise HTTPException(status_code=409, detail="Candidate evidence changed during scoring; refresh shortly")
    if nct:
        import gzip
        with Session(db.ENGINE) as session:
            payload = session.scalar(select(db.FullTrialRecord.payload_gzip).where(db.FullTrialRecord.nct_id == nct))
        if payload:
            try:
                full = json.loads(gzip.decompress(payload))
                raw = full.get("resultsSection", {})
                safety = {k: raw.get(k) for k in ("adverseEventsModule", "participantFlowModule", "baselineCharacteristicsModule") if k in raw}
                result["data"]["savedSafetyAndExposure"] = safety
                for metric in result["models"]["PIPELINE"]["categories"][3]["metrics"]:
                    metric["observations"] = safety
            except (ValueError, OSError):
                result["data"]["savedSafetyAndExposure"] = {"status": "Saved safety fields unavailable"}
    result["version"] = index["version"]
    result["computedAt"] = index["computedAt"]
    result["historyStatus"] = index["historyStatus"]
    with Session(db.ENGINE) as session:
        history = list(session.scalars(select(db.CandidateAssessmentHistory).where(db.CandidateAssessmentHistory.exact_id == identity)
                                       .order_by(db.CandidateAssessmentHistory.id.desc()).limit(25)))
        result["history"] = [{"assessedAt": h.assessed_at.isoformat(), "modelVersion": h.model_version, "evidenceHash": h.evidence_hash, **h.summary} for h in history]
    previous = history[1].summary.get("models", []) if len(history) > 1 else []
    result["changes"] = {stage: {"observedPoints": round(result["models"][stage]["observedPoints"] - previous[i][1], 2),
                                "coverage": round(result["models"][stage]["coverage"] - previous[i][2], 2)}
                         for i, stage in enumerate(("PIPELINE", "GEM_JR", "GEM"))} if previous else {}
    return result


def public_status():
    """Aggregate health only. Never expose candidate evidence on a public route."""
    with _LOCK:
        index = _STATE["index"]
        if _STATE["building"]: return {"status": "BUILDING", "modelVersion": MODEL}
        if _STATE["error"]: return {"status": "ERROR", "modelVersion": MODEL}
        if not index: return {"status": "PENDING", "modelVersion": MODEL}
        return {key: index[key] for key in ("status", "modelVersion", "total", "registryLinked", "registryMissing", "totals", "computedAt", "historyStatus", "reviewSource")}
