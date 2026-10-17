"""Lossless, resumable all-phase ClinicalTrials.gov download into the new DB.

No field or phase restriction is sent to the registry. Original Streamlit files,
scan schedules, checklist state and permanent program identities are not edited.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import hmac
import io
import json
import logging
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from . import main as db

LOG = logging.getLogger(__name__)
API = "https://clinicaltrials.gov/api/v2/studies"
NCT = re.compile(r"^NCT\d{8}$")
_START_LOCK = threading.Lock()
_EXPORT_LOCK = threading.Lock()
_EXPORT_PATH = Path(tempfile.gettempdir()) / "pdufa-full-trial-export.zip"
_EXPORT_STAMP = ""


def now():
    return datetime.now(timezone.utc)


def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def statistics(study):
    """One row per reported analysis; never choose a p-value across endpoints."""
    result = []
    outcomes = study.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    for outcome_index, outcome in enumerate(outcomes, start=1):
        groups = {str(group.get("id")): group for group in outcome.get("groups", [])}
        for analysis_index, analysis in enumerate(outcome.get("analyses", []), start=1):
            group_ids = analysis.get("groupIds", [])
            result.append({
                "outcome_index": outcome_index, "analysis_index": analysis_index,
                "endpoint_type": outcome.get("type", ""), "endpoint": outcome.get("title", ""),
                "time_frame": outcome.get("timeFrame", ""),
                "comparison_groups": [groups.get(str(key), {"id": key}) for key in group_ids],
                "p_value": analysis.get("pValue"),
                "p_value_reported": "pValue" in analysis and analysis["pValue"] not in (None, ""),
                "method": analysis.get("statisticalMethod", ""),
                "parameter": analysis.get("paramType", ""), "estimate": analysis.get("paramValue", ""),
                "confidence_level": analysis.get("ciPctValue", ""),
                "confidence_lower": analysis.get("ciLowerLimit", ""),
                "confidence_upper": analysis.get("ciUpperLimit", ""),
                # Unknown/new statistics fields and all qualifiers are retained.
                "analysis_json": analysis,
            })
    return result


def summarize(study, analyses):
    protocol = study.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    sponsors = protocol.get("sponsorCollaboratorsModule", {})
    nct = ident.get("nctId", "")
    result = {
        "nct_id": nct, "study_url": "https://clinicaltrials.gov/study/" + nct,
        "study_title": ident.get("briefTitle", ""), "official_title": ident.get("officialTitle", ""),
        "acronym": ident.get("acronym", ""), "other_identifiers": ident.get("secondaryIdInfos", []),
        "organization_study_id": ident.get("orgStudyIdInfo", {}),
        "sponsor": sponsors.get("leadSponsor", {}), "collaborators": sponsors.get("collaborators", []),
        "brief_summary": protocol.get("descriptionModule", {}).get("briefSummary", ""),
        "detailed_description": protocol.get("descriptionModule", {}).get("detailedDescription", ""),
        "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
        "interventions": protocol.get("armsInterventionsModule", {}).get("interventions", []),
        "treatment_groups": protocol.get("armsInterventionsModule", {}).get("armGroups", []),
        "phases": design.get("phases", []), "study_type": design.get("studyType", ""),
        "study_design": design, "status": status.get("overallStatus", ""),
        "enrollment": design.get("enrollmentInfo", {}),
        "eligibility": protocol.get("eligibilityModule", {}),
        "start_date": status.get("startDateStruct", {}),
        "primary_completion_date": status.get("primaryCompletionDateStruct", {}),
        "study_completion_date": status.get("completionDateStruct", {}),
        "first_posted": status.get("studyFirstPostDateStruct", {}),
        "results_first_posted": status.get("resultsFirstPostDateStruct", {}),
        "last_update_posted": status.get("lastUpdatePostDateStruct", {}),
        "primary_outcomes": protocol.get("outcomesModule", {}).get("primaryOutcomes", []),
        "secondary_outcomes": protocol.get("outcomesModule", {}).get("secondaryOutcomes", []),
        "other_outcomes": protocol.get("outcomesModule", {}).get("otherOutcomes", []),
        "locations_and_contacts": protocol.get("contactsLocationsModule", {}),
        "documents": study.get("documentSection", {}),
        "references": protocol.get("referencesModule", {}),
        "has_results": study.get("hasResults", "resultsSection" in study),
        "statistical_analyses": len(analyses),
        "reported_p_values": [
            {key: row[key] for key in ("outcome_index", "analysis_index", "endpoint_type", "endpoint", "p_value")}
            for row in analyses if row["p_value_reported"]
        ],
        "p_value_status": "REPORTED" if any(row["p_value_reported"] for row in analyses)
                          else "NOT_REPORTED" if study.get("hasResults") else "NO_POSTED_RESULTS",
    }
    return result


def archive_status():
    try:
        with Session(db.ENGINE) as session:
            job = session.get(db.FullTrialDownload, 1)
            if job is None:
                return {"status": "NOT_STARTED", "target": 0, "downloaded": 0, "complete": False}
            return {"status": job.status, "target": len(job.scope_ids),
                    "downloaded": len(job.completed_ids), "complete": job.status == "COMPLETE",
                    "statisticalAnalyses": job.statistics_count, "reportedPValues": job.p_value_count,
                    "missing": len(job.missing_ids), "updatedAt": job.updated_at.isoformat(),
                    "completedAt": job.completed_at.isoformat() if job.completed_at else None,
                    "exportReady": bool(_EXPORT_PATH.exists() and job.completed_at
                                        and _EXPORT_STAMP == job.completed_at.isoformat()),
                    "error": job.error}
    except Exception:
        return {"status": "STORAGE_NOT_READY", "target": 0, "downloaded": 0, "complete": False}


def _scope():
    from .source_workspace import workspace
    result = set()
    for row in workspace()["pipeline"]:
        key = str(row.get("id", ""))
        candidate = str(row.get("nctId") or (key.split("|")[1] if key.startswith("TRIAL|") else ""))
        if NCT.fullmatch(candidate):
            result.add(candidate)
    if not result:
        raise RuntimeError("Published Pipeline has no exact tracked trial IDs")
    return sorted(result)


def start_download(refresh=False, launch=True):
    with _START_LOCK:
        scope = _scope()
        clock = now()
        with Session(db.ENGINE) as session:
            job = session.get(db.FullTrialDownload, 1)
            if job is None:
                job = db.FullTrialDownload(id=1, status="PENDING", scope_ids=scope,
                                          started_at=clock, updated_at=clock)
                session.add(job)
            elif job.status == "COMPLETE":
                if not refresh and set(scope).issubset(job.completed_ids):
                    return archive_status()
                job.scope_ids = scope
                job.completed_ids = []
                job.missing_ids = []
                job.statistics_count = job.p_value_count = 0
                job.started_at = clock
                job.completed_at = None
                job.status = "PENDING"
            else:
                job.scope_ids = sorted(set(job.scope_ids) | set(scope))
            session.commit()
        if launch:
            threading.Thread(target=run_download, daemon=True).start()
    return archive_status()


def bootstrap():
    try:
        state = start_download()
        if state.get("complete"):
            ensure_cached_export()
    except Exception as exc:
        LOG.error("PDUFA_FULL_TRIAL_BOOTSTRAP error_type=%s", type(exc).__name__)


def fetch_batch(ids):
    """Fetch complete native records, with pagination and exact-ID validation."""
    found, token, visited = {}, None, set()
    while True:
        params = {"filter.ids": ",".join(ids), "pageSize": 100, "format": "json"}
        if token:
            params["pageToken"] = token
        request = Request(API + "?" + urlencode(params), headers={
            "Accept": "application/json", "User-Agent": "PDUFA-full-trial-download/1.0"})
        for attempt in range(4):
            try:
                with urlopen(request, timeout=45) as response:
                    payload = json.load(response)
                if not isinstance(payload.get("studies"), list):
                    raise ValueError("Registry response has no studies list")
                break
            except (HTTPError, URLError, OSError, ValueError):
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        for study in payload["studies"]:
            nct = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
            if nct not in ids or nct in found:
                raise ValueError("Unexpected or duplicate registry study identity")
            found[nct] = study
        token = payload.get("nextPageToken")
        if not token or len(found) == len(ids):
            return found
        if token in visited:
            raise ValueError("Registry pagination did not advance")
        visited.add(token)


def run_download(fetcher=fetch_batch):
    owner = secrets.token_hex(16)
    clock = now()
    with Session(db.ENGINE) as session:
        claimed = session.execute(update(db.FullTrialDownload).where(
            db.FullTrialDownload.id == 1,
            db.FullTrialDownload.status != "COMPLETE",
            or_(db.FullTrialDownload.lease_until.is_(None), db.FullTrialDownload.lease_until < clock),
        ).values(status="RUNNING", lease_owner=owner, lease_until=clock + timedelta(minutes=5),
                 updated_at=clock, error=""))
        session.commit()
        if claimed.rowcount != 1:
            return
        job = session.get(db.FullTrialDownload, 1)
        due = sorted(set(job.scope_ids) - set(job.completed_ids))
    failed, consecutive_errors = [], 0
    for offset in range(0, len(due), 50):
        batch = due[offset:offset + 50]
        try:
            studies = fetcher(batch)
            saved, analyses_count, p_count = [], 0, 0
            with Session(db.ENGINE) as session:
                job = session.get(db.FullTrialDownload, 1)
                if job.lease_owner != owner:
                    return
                existing = {row.nct_id: row for row in session.scalars(
                    select(db.FullTrialRecord).where(db.FullTrialRecord.nct_id.in_(batch))
                )}
                for nct, study in studies.items():
                    if nct not in batch or study.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nct:
                        raise ValueError("Downloaded trial identity mismatch")
                    raw = packed(study).encode("utf-8")
                    analyses = statistics(study)
                    record = existing.get(nct)
                    if record is None:
                        record = db.FullTrialRecord(nct_id=nct)
                        session.add(record)
                    record.payload_gzip = gzip.compress(raw, compresslevel=6, mtime=0)
                    record.sha256 = hashlib.sha256(raw).hexdigest()
                    record.summary = summarize(study, analyses)
                    record.statistics = analyses
                    record.fetched_at = now()
                    saved.append(nct)
                    analyses_count += len(analyses)
                    p_count += sum(row["p_value_reported"] for row in analyses)
                failed.extend(sorted(set(batch) - set(saved)))
                job.completed_ids = sorted(set(job.completed_ids) | set(saved))
                job.statistics_count += analyses_count
                job.p_value_count += p_count
                job.updated_at = now()
                job.lease_until = now() + timedelta(minutes=5)
                session.commit()
            consecutive_errors = 0
        except Exception as exc:
            failed.extend(batch)
            consecutive_errors += 1
            LOG.warning("PDUFA_FULL_TRIAL_BATCH offset=%d error_type=%s", offset, type(exc).__name__)
        current = archive_status()
        LOG.warning("PDUFA_FULL_TRIAL_PROGRESS downloaded=%d target=%d p_values=%d",
                    current["downloaded"], current["target"], current.get("reportedPValues", 0))
        if consecutive_errors >= 5:
            break
        time.sleep(0.2)
    with Session(db.ENGINE) as session:
        job = session.get(db.FullTrialDownload, 1)
        if job.lease_owner != owner:
            return
        missing = sorted(set(job.scope_ids) - set(job.completed_ids))
        job.missing_ids = missing
        job.status = "PARTIAL" if missing else "COMPLETE"
        job.error = "Some registry records could not be downloaded; retry resumes missing IDs." if missing else ""
        job.updated_at = now()
        job.completed_at = None if missing else now()
        job.lease_owner = ""
        job.lease_until = None
        session.commit()
    LOG.warning("PDUFA_FULL_TRIAL_FINISHED %s", packed(archive_status()))
    if not missing:
        try:
            ensure_cached_export()
        except Exception as exc:
            LOG.error("PDUFA_FULL_TRIAL_EXPORT error_type=%s", type(exc).__name__)


def make_export_ticket():
    if not archive_status().get("complete"):
        raise HTTPException(status_code=409, detail="Full all-phase download is not complete yet")
    key = os.getenv("PDUFA_INTERNAL_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="Export is not configured")
    payload = "v1." + str(int(time.time()) + 900)
    signature = hmac.new(key.encode(), ("full-trial-export:" + payload).encode(), hashlib.sha256).hexdigest()
    return "/downloads/pipeline-all-fields/" + payload + "." + signature


def _records(ids):
    for offset in range(0, len(ids), 50):
        with Session(db.ENGINE) as session:
            rows = list(session.scalars(select(db.FullTrialRecord).where(
                db.FullTrialRecord.nct_id.in_(ids[offset:offset + 50])
            ).order_by(db.FullTrialRecord.nct_id)))
        yield from rows


def _csv_cell(value):
    if isinstance(value, (dict, list)):
        return packed(value)
    # CSV is opened in Excel as well as code. Block formula interpretation.
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return "" if value is None else value


def _csv_member(archive, name, fields, rows):
    with archive.open(name, "w") as member:
        wrapper = io.TextIOWrapper(member, encoding="utf-8-sig", newline="", write_through=True)
        writer = csv.DictWriter(wrapper, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_cell(row.get(key)) for key in fields})
        wrapper.flush()
        wrapper.detach()


def build_archive(path):
    state = archive_status()
    if not state.get("complete"):
        raise HTTPException(status_code=409, detail="Download is still collecting full trial records")
    with Session(db.ENGINE) as session:
        job = session.get(db.FullTrialDownload, 1)
        ids = sorted(job.scope_ids)
    first = next(_records(ids), None)
    if first is None:
        raise HTTPException(status_code=409, detail="No full trial records available")
    with Session(db.ENGINE) as session:
        identities = [
            {"program_id": f"PDUFA-{row.id:06d}", "source_id": row.source_key,
             "ticker": row.ticker, "drug": row.drug,
             "nct_id": next(iter(re.findall(r"NCT\d{8}", row.source_key)), "")}
            for row in session.scalars(select(db.ProgramIdentity).order_by(db.ProgramIdentity.id))
        ]
    mapping = {}
    for identity in identities:
        if identity["nct_id"]:
            mapping.setdefault(identity["nct_id"], []).append(identity)
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        _csv_member(archive, "program_identity.csv", ["program_id", "source_id", "ticker", "drug", "nct_id"], identities)
        _csv_member(archive, "trials.csv", ["program_ids", "tickers", *first.summary],
                    ({"program_ids": [v["program_id"] for v in mapping.get(r.nct_id, [])],
                      "tickers": sorted({v["ticker"] for v in mapping.get(r.nct_id, [])}),
                      **r.summary} for r in _records(ids)))
        stat_fields = ["nct_id", "outcome_index", "analysis_index", "endpoint_type", "endpoint", "time_frame",
                       "comparison_groups", "p_value", "p_value_reported", "method", "parameter", "estimate",
                       "confidence_level", "confidence_lower", "confidence_upper", "analysis_json"]
        _csv_member(archive, "statistical_analyses.csv", stat_fields,
                    ({"nct_id": r.nct_id, **analysis} for r in _records(ids) for analysis in r.statistics))
        checksums = []
        with archive.open("full_studies.jsonl", "w") as full:
            for record in _records(ids):
                raw = gzip.decompress(record.payload_gzip)
                if hashlib.sha256(raw).hexdigest() != record.sha256:
                    raise ValueError("Stored full trial record checksum mismatch")
                full.write(raw + b"\n")
                checksums.append({"nct_id": record.nct_id, "sha256": record.sha256,
                                  "fetched_at": record.fetched_at.isoformat()})
        if [row["nct_id"] for row in checksums] != ids:
            raise ValueError("Full export does not cover every requested trial ID")
        _csv_member(archive, "record_checksums.csv", ["nct_id", "sha256", "fetched_at"], checksums)
        archive.writestr("manifest.json", packed({
            **state, "source": API, "scope": "All exact NCT trials currently tracked by PIPELINE, across every phase; no market-cap restriction",
            "field_filter": None, "phase_filter": None, "trial_ids": ids,
            "all_fields_file": "full_studies.jsonl", "reported_statistics_file": "statistical_analyses.csv",
            "missing_p_values": "NOT_REPORTED or NO_POSTED_RESULTS; never inferred from protocol thresholds",
            "documents": "All document metadata and URLs are retained; linked PDF contents are not registry fields.",
        }))


def ensure_cached_export():
    global _EXPORT_STAMP
    state = archive_status()
    if not state.get("complete"):
        raise HTTPException(status_code=409, detail="Complete trial data is still downloading")
    with _EXPORT_LOCK:
        if _EXPORT_PATH.exists() and _EXPORT_STAMP == state["completedAt"]:
            return _EXPORT_PATH
        partial = _EXPORT_PATH.with_suffix(".building")
        try:
            build_archive(partial)
            with ZipFile(partial) as zipped:
                manifest = json.loads(zipped.read("manifest.json"))
                if manifest["downloaded"] != manifest["target"]:
                    raise ValueError("Export archive coverage does not reconcile")
            partial.replace(_EXPORT_PATH)
            _EXPORT_STAMP = state["completedAt"]
            LOG.warning("PDUFA_FULL_TRIAL_EXPORT_READY records=%d bytes=%d",
                        state["downloaded"], _EXPORT_PATH.stat().st_size)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
    return _EXPORT_PATH


def export_response(ticket):
    parts = ticket.split(".")
    key = os.getenv("PDUFA_INTERNAL_API_KEY", "")
    if len(parts) != 3 or parts[0] != "v1" or not key:
        raise HTTPException(status_code=401, detail="Invalid export link")
    try:
        expiry = int(parts[1])
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid export link") from None
    payload = ".".join(parts[:2])
    expected = hmac.new(key.encode(), ("full-trial-export:" + payload).encode(), hashlib.sha256).hexdigest()
    if not int(time.time()) < expiry <= int(time.time()) + 900 or not hmac.compare_digest(parts[2], expected):
        raise HTTPException(status_code=401, detail="Export link expired or invalid")
    filename = ensure_cached_export()
    return FileResponse(filename, media_type="application/zip", filename="pipeline-all-phases-all-fields.zip",
                        headers={"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"})
