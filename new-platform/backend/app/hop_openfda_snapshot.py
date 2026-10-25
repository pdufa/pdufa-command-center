"""Quarantined snapshot of the FDA's published CRL archive, not an outcome cohort.

The openFDA transparency corpus is selected for PUBLICATION. It cannot establish
the number of all NDA/BLA review cycles or a representative approval probability.
This module NEVER exports model-eligible outcomes.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import date
from urllib.parse import urlparse

MAX_UNCOMPRESSED_BYTES = 80_000_000
ALLOWED_DOWNLOAD_HOST = "download.open.fda.gov"


def build_crl_snapshot(download_manifest: dict, partitions: dict[str, bytes], as_of: date) -> tuple[dict, dict]:
    """Validate all advertised partitions; return quarantined rows and audit."""
    try:
        meta = download_manifest["results"]["transparency"]["crl"]
        planned = meta["partitions"]
        declared_total = meta["total_records"]
        export_date = date.fromisoformat(meta["export_date"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("missing or invalid official FDA download manifest") from exc
    if (not isinstance(planned, list) or not planned
            or type(declared_total) is not int or declared_total < 1
            or export_date > as_of):
        raise ValueError("invalid CRL export metadata")
    urls = [part.get("file") for part in planned if isinstance(part, dict)]
    if (len(urls) != len(planned) or len(urls) != len(set(urls))
            or set(partitions) != set(urls)):
        raise ValueError("CRL partitions must exactly match official manifest")
    quarantined = []
    archive_hashes = {}
    letter_types = Counter()
    missing_identifiers = 0
    for part in planned:
        url = part["file"]
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.hostname != ALLOWED_DOWNLOAD_HOST
                or not parsed.path.startswith("/transparency/crl/")
                or not parsed.path.endswith(".json.zip")
                or parsed.username or parsed.password or parsed.port):
            raise ValueError("invalid official CRL download location")
        data = partitions[url]
        archive_hashes[url] = hashlib.sha256(data).hexdigest()
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = [i for i in archive.infolist() if not i.is_dir()]
                if len(entries) != 1 or not entries[0].filename.endswith(".json"):
                    raise ValueError("CRL archive must contain exactly one JSON")
                if entries[0].file_size > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("CRL archive expanded size exceeds limit")
                content = archive.read(entries[0])
                if len(content) > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("CRL archive exceeds limit")
            payload = json.loads(content)
            rows = payload["results"]
        except (zipfile.BadZipFile, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid official CRL archive contents") from exc
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("CRL results must be an array of objects")
        if type(part.get("records")) is not int or len(rows) != part["records"]:
            raise ValueError("CRL archive does not match declared partition count")
        for index, row in enumerate(rows):
            applications = row.get("application_number")
            if not isinstance(applications, list) or not applications:
                missing_identifiers += 1
                applications = []
            letter_type = row.get("letter_type")
            if not isinstance(letter_type, str) or not letter_type:
                letter_type = "UNCLASSIFIED"
            letter_types[letter_type] += 1
            quarantined.append({
                "source_record_index": index,
                "source_partition": url,
                "source_record_sha256": hashlib.sha256(
                    json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "application_numbers": applications,
                "letter_date_as_published": row.get("letter_date"),
                "letter_type_as_published": letter_type,
                "company_name_as_published": row.get("company_name"),
                "file_name_as_published": row.get("file_name"),
                "review_cycle": None,
                "predecision_evidence_as_of": None,
                "independently_verified": False,
                "cohort_complete_verified": False,
                "model_eligible": False,
                "status": "QUARANTINED_PUBLICATION_SELECTED",
            })
    if len(quarantined) != declared_total:
        raise ValueError("CRL partition sum differs from FDA manifest total")
    snapshot = {
        "schema_version": 1,
        "status": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
        "source_manifest_url": "https://api.fda.gov/download.json",
        "source_export_date": export_date.isoformat(),
        "retrieved_on": as_of.isoformat(),
        "records": quarantined,
    }
    audit = {
        "status": "PUBLICATION_CORPUS_ONLY_NOT_MODEL_ELIGIBLE",
        "source_manifest_url": "https://api.fda.gov/download.json",
        "source_export_date": export_date.isoformat(),
        "published_letter_records": len(quarantined),
        "quarantined_records": len(quarantined),
        "unique_application_review_cycles_verified": 0,
        "model_eligible": 0,
        "full_decision_denominator_verified": False,
        "letter_types": dict(sorted(letter_types.items())),
        "records_missing_application_number": missing_identifiers,
        "archive_sha256_by_url": archive_hashes,
        "limitations": [
            "Only publicly released letters, not every NDA/BLA review outcome",
            "Letters may repeat applications or represent successive review cycles",
            "Publication and release policies introduce outcome and calendar-time selection bias",
            "Approval labels, review cycles, and predecision predictors are not independently adjudicated",
        ],
        "prediction_probability": None,
    }
    return snapshot, audit
