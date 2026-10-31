"""Read-only, fail-closed NCT identity preservation across DB and published POOL.

A dated manifest may be smaller than the current downloaded scope: extra later
NCT records are retained, not treated as missing historical records. Counts do
not certify source-family completeness, FDA labels, qualification or restore.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.orm import Session

NCT = re.compile(r"^NCT[0-9]{8}$")


def checked_set(ids, label):
    if not isinstance(ids, list) or any(not isinstance(x, str) or not NCT.fullmatch(x) for x in ids):
        raise ValueError(f"{label}: invalid exact trial identities")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label}: duplicate trial identities")
    return set(ids)


def nct_digest(ids):
    return hashlib.sha256(",".join(sorted(ids)).encode("utf-8")).hexdigest()


def evidence(scope_ids, completed_ids, physical_ids, catalog_ids, published_ids,
             manifest_ids, download_status, published_state):
    scope = checked_set(scope_ids, "download scope")
    completed = checked_set(completed_ids, "completed download")
    physical = checked_set(physical_ids, "physical archive")
    catalog = checked_set(catalog_ids, "research catalog")
    published = checked_set(published_ids, "published trial POOL")
    manifest = checked_set(manifest_ids, "dated manifest")
    missing_archive = len(scope - physical)
    missing_pool = len(scope - published)
    missing_manifest = len(manifest - physical)
    status = ("VERIFIED" if download_status == "COMPLETE"
              and published_state not in ("STALE", "UNKNOWN", "")
              and completed == scope and physical == scope
              and missing_pool == 0 and missing_manifest == 0
              else "REVIEW_REQUIRED")
    return {
        "status": status,
        "scopeType": "SAVED_EXACT_NCT_IDENTITY_PRESERVATION_NOT_FULL_UNIVERSE",
        "originalScopeRecords": len(scope),
        "archivePhysicalRecords": len(physical),
        "catalogDistinctTrials": len(catalog),
        "publishedDistinctTrials": len(published),
        "unionDistinctTrials": len(scope | physical | catalog | published),
        "missingExpectedArchiveRecords": missing_archive,
        "archiveOutsideOriginalScope": len(physical - scope),
        "catalogOutsideArchive": len(catalog - physical),
        "publishedOutsideArchive": len(published - physical),
        "missingPoolTrials": missing_pool,
        "datedManifestRecords": len(manifest),
        "missingDatedManifestRecords": missing_manifest,
        "laterArchiveRecordsOutsideDatedManifest": len(physical - manifest),
        "completedDownloadRecords": len(completed),
        "currentScopeSha256": nct_digest(scope),
        "physicalArchiveSha256": nct_digest(physical),
        "publishedPoolSha256": nct_digest(published),
        "downloadStatus": download_status,
        "publishedSourceState": published_state,
        "caveat": "Exact NCT identity preservation only; not FDA/SEC/source completeness, 300M-10B eligibility, clinical validation or disaster recovery."
    }


def report():
    from . import main as db
    from .source_workspace import workspace
    with Session(db.ENGINE) as session:
        job = session.get(db.FullTrialDownload, 1)
        if not job:
            raise ValueError("No persisted download scope")
        physical = list(session.scalars(select(db.FullTrialRecord.nct_id)))
        catalog = list(session.execute(text("SELECT nct_id FROM phase3_trials")).scalars())
        saved = session.execute(text(
            "SELECT document FROM archive_manifests ORDER BY created_at DESC LIMIT 1"
        )).scalar_one_or_none()
        if not saved:
            raise ValueError("Dated immutable archive manifest missing")
    manifest = json.loads(saved)
    snapshot = workspace()
    rows = snapshot.get("pipeline")
    health = snapshot.get("sourceHealth") or {}
    if not isinstance(rows, list):
        raise ValueError("Published POOL is unavailable")
    parity = health.get("pipelineSourceParity") or health.get("streamlitPipelineParity") or {}
    if parity.get("exactPrograms") != len(rows):
        raise ValueError("Published source parity is invalid")
    published = []
    for row in rows:
        key = row.get("id") if isinstance(row, dict) else None
        if not isinstance(key, str):
            raise ValueError("Published source identity invalid")
        if key.startswith("TRIAL|") and NCT.fullmatch(key[6:]):
            published.append(key[6:])
    # Include only canonical clinical trial IDs; never count regulatory rows as trials.
    # Retain duplicates as a warning if source integrity regresses.
    result = evidence(
        job.scope_ids, job.completed_ids, physical, catalog, published,
        manifest.get("expected_nct_ids"), job.status, health.get("state") or "UNKNOWN")
    result["checkedAtUtc"] = datetime.now(timezone.utc).isoformat()
    return result
