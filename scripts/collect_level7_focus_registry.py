"""Capture official FOCUS registry records into an explicit development SQLite database."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

from fetch_focus_registry_evidence import BASE, NCT_RE, retrieve_with_bytes
from level7_focus_report import SNAPSHOT
from level7_evidence import make_record
from level7_store import EvidenceStore
from level8_evidence_readiness import assess_evidence_readiness


def collect_trial(nct, retrieve=retrieve_with_bytes):
    current = datetime.now(timezone.utc)
    status, raw, posted = "inaccessible", None, None
    notes = "Official registry unavailable"
    stamp = current.isoformat()
    try:
        document, receipt, raw = retrieve(nct)
        stamp = receipt["retrieved_at_utc"]
        posted = document["protocolSection"].get("statusModule", {}).get("lastUpdatePostDateStruct", {}).get("date")
        if not posted or date.fromisoformat(posted) > datetime.fromisoformat(stamp).date():
            raise ValueError("Registry version date missing or inconsistent")
        status, notes = "verified", "Official registry origin and exact NCT verified; claims are sponsor-reported"
    except HTTPError as error:
        if error.code == 404:
            status, notes = "missing", "Official registry returned HTTP 404"
    except (URLError, TimeoutError):
        pass
    except (ValueError, KeyError, TypeError, AttributeError):
        status, notes = "conflicting", "Official registry response failed format, chronology, or identity validation"
        posted = None
    record = make_record(
        trial_id=nct, source_id="CLINICALTRIALS_GOV_REGISTRY",
        source_url=BASE + nct, publisher="ClinicalTrials.gov",
        source_version=stamp, retrieved_at=stamp,
        status=status, content=raw, document_date=posted, notes=notes,
    )
    return record, raw


def capture(store, snapshot_path=SNAPSHOT, collect=collect_trial):
    trials = json.loads(snapshot_path.read_text(encoding="utf-8"))["records"]
    identifiers = [row.get("nct") for row in trials]
    if len(identifiers) != 32 or any(not isinstance(nct, str) or not NCT_RE.fullmatch(nct)
                                      for nct in identifiers) or len(set(identifiers)) != 32:
        raise ValueError("Expected exactly 32 distinct FOCUS NCTs")
    with ThreadPoolExecutor(max_workers=4) as executor:
        captures = list(executor.map(collect, identifiers))
    records = [record for record, _ in captures]
    store.initialize()
    store.add_many(records, source_bytes={
        record.sha256_digest: raw for record, raw in captures if raw is not None
    })
    read_only = EvidenceStore(store.path, read_only=True)
    verified = 0
    for record in records:
        if record.status != "verified":
            continue
        raw = read_only.document(record.sha256_digest)
        if raw is None or json.loads(raw)["protocolSection"]["identificationModule"]["nctId"] != record.trial_id:
            raise ValueError("Saved registry evidence failed exact-NCT readback")
        verified += 1
    return {"total": len(identifiers), "verifiedRegistryDocuments": verified,
            "readiness": {nct: assess_evidence_readiness(nct, read_only.history(nct)).status
                          for nct in identifiers}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-db", type=Path, required=True,
                        help="Writable SQLite evidence path outside the repository")
    args = parser.parse_args()
    path = args.development_db.resolve()
    if path.is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("Keep the development SQLite database outside the repository")
    path.parent.mkdir(parents=True, exist_ok=True)
    result = capture(EvidenceStore(path))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["total"] == result["verifiedRegistryDocuments"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
