"""Explicit, bounded ClinicalTrials.gov archive import for isolated review only.

Run from the backend working directory with:
    python -m app.scientific_import NCT01234567

No scheduled scanning; no production or trading writes.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from .main import DATABASE_URL, ENGINE, FullTrialRecord

NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")


def fetch_trial(nct_id: str) -> tuple[dict, bytes]:
    if not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    url = "https://clinicaltrials.gov/api/v2/studies/" + nct_id
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "PDUFA-Scientific-Review/1.0"})
    with urlopen(request, timeout=25) as response:
        raw = response.read(10_000_001)
    if len(raw) > 10_000_000:
        raise ValueError("Registry response exceeds size limit")
    record = json.loads(raw)
    actual = (record.get("protocolSection", {}).get("identificationModule", {}).get("nctId"))
    if actual != nct_id:
        raise ValueError("Registry identity mismatch")
    return record, raw


def import_one(nct_id: str) -> str:
    if not DATABASE_URL.startswith("postgresql+psycopg://"):
        raise RuntimeError("Persistent PostgreSQL required; refusing SQLite import")
    if not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    # Idempotent existing archive: avoid a redundant remote request, which also
    # permits a controlled end-to-end smoke test with zero registry mutations.
    with Session(ENGINE) as session:
        if session.get(FullTrialRecord, nct_id) is not None:
            return "already_exists"
    record, raw = fetch_trial(nct_id)
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    checksum = hashlib.sha256(canonical).hexdigest()
    from .scientific_registry_evidence import extract_trial_evidence
    extract_trial_evidence(nct_id, record)  # Validate identity before persisting
    with Session(ENGINE) as session:
        existing = session.get(FullTrialRecord, nct_id)
        if existing is not None:
            return "already_exists"
        session.add(FullTrialRecord(
            nct_id=nct_id,
            payload_gzip=gzip.compress(canonical),
            sha256=checksum,
            summary={"nctId": nct_id, "source": "ClinicalTrials.gov API v2", "sourceUrl": "https://clinicaltrials.gov/study/" + nct_id},
            statistics=[],
            fetched_at=datetime.now(timezone.utc),
        ))
        session.commit()
    return "imported"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.scientific_import NCT########")
    print("SCIENTIFIC_IMPORT nct_id=" + sys.argv[1] + " status=" + import_one(sys.argv[1]))
