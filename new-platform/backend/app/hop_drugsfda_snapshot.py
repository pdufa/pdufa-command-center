"""Research-only staging of the approved-product Drugs@FDA registry.

The registry contains many FDA-approved products and their submission records;
it is NOT a census of every NDA/BLA filing, complete response or review cycle.
Nothing produced by this module is eligible for model training.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import io
import json
from urllib.parse import urlparse
import zipfile


def stage_drugsfda_manifest(manifest: dict, archives: dict[str, bytes], as_of: date) -> tuple[dict, dict]:
    try:
        source = manifest["results"]["drug"]["drugsfda"]
        export_date = date.fromisoformat(source["export_date"])
        parts = source["partitions"]
        expected = source["total_records"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("missing Drugs@FDA source manifest") from exc
    if (export_date > as_of or not isinstance(parts, list) or not parts
            or type(expected) is not int or expected < 1):
        raise ValueError("invalid Drugs@FDA source manifest")
    links = [p.get("file") if isinstance(p, dict) else None for p in parts]
    if len(links) != len(set(links)) or set(archives) != set(links):
        raise ValueError("Drugs@FDA partitions must match manifest exactly")
    staged = []
    app_types = Counter()
    statuses = Counter()
    missing_app = 0
    missing_submissions = 0
    duplicate_apps = 0
    seen = set()
    sha_by_archive = {}
    for part in parts:
        url = part["file"]
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.hostname != "download.open.fda.gov"
                or not parsed.path.startswith("/drug/drugsfda/")
                or not parsed.path.endswith(".json.zip")
                or parsed.username or parsed.password):
            raise ValueError("unapproved Drugs@FDA archive host or path")
        sha_by_archive[url] = hashlib.sha256(archives[url]).hexdigest()
        try:
            with zipfile.ZipFile(io.BytesIO(archives[url])) as z:
                files = [f for f in z.infolist() if not f.is_dir()]
                if len(files) != 1 or not files[0].filename.endswith(".json"):
                    raise ValueError("Drugs@FDA ZIP must contain one JSON file")
                if files[0].file_size > 300_000_000:
                    raise ValueError("Drugs@FDA ZIP expands past safety limit")
                payload = json.loads(z.read(files[0]))
                rows = payload["results"]
        except (zipfile.BadZipFile, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid Drugs@FDA source archive") from exc
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Drugs@FDA rows must be an array of objects")
        if type(part.get("records")) is not int or len(rows) != part["records"]:
            raise ValueError("Drugs@FDA partition count mismatch")
        for index, row in enumerate(rows):
            appl = row.get("application_number")
            if not isinstance(appl, str) or not appl.strip():
                missing_app += 1
                appl = None
            elif appl in seen:
                duplicate_apps += 1
            else:
                seen.add(appl)
            prefix = "UNKNOWN"
            if appl:
                prefix = next((name for name in ("ANDA", "NDA", "BLA") if appl.startswith(name)), "OTHER")
            app_types[prefix] += 1
            submission_rows = row.get("submissions", [])
            if not isinstance(submission_rows, list):
                submission_rows = []
            if not submission_rows:
                missing_submissions += 1
            actions = []
            for sub in submission_rows:
                if not isinstance(sub, dict):
                    continue
                kind = sub.get("submission_type")
                status = sub.get("submission_status")
                if isinstance(status, str) and status:
                    statuses[status] += 1
                actions.append({
                    "submission_type_as_published": kind,
                    "submission_number_as_published": sub.get("submission_number"),
                    "submission_status_as_published": status,
                    "submission_status_date_as_published": sub.get("submission_status_date"),
                    "review_priority_as_published": sub.get("review_priority"),
                })
            staged.append({
                "source_record_index": index,
                "source_archive_url": url,
                "record_sha256": hashlib.sha256(
                    json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "application_number_as_published": appl,
                "sponsor_name_as_published": row.get("sponsor_name"),
                "submissions_as_published": actions,
                "review_cycles_independently_adjudicated": False,
                "complete_application_denominator_verified": False,
                "point_in_time_features_verified": False,
                "model_eligible": False,
                "status": "QUARANTINED_APPROVED_PRODUCT_REGISTRY",
            })
    if len(staged) != expected:
        raise ValueError("Drugs@FDA total does not match official manifest")
    snapshot = {
        "schema_version": 1,
        "status": "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
        "source_export_date": export_date.isoformat(),
        "source_manifest_url": "https://api.fda.gov/download.json",
        "retrieved_on": as_of.isoformat(),
        "records": staged,
    }
    audit = {
        "status": "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
        "source_manifest_url": "https://api.fda.gov/download.json",
        "source_export_date": export_date.isoformat(),
        "source_application_records": expected,
        "quarantined_application_records": len(staged),
        "application_number_prefixes": dict(sorted(app_types.items())),
        "published_submission_status_counts": dict(sorted(statuses.items())),
        "missing_application_identifiers": missing_app,
        "missing_or_invalid_submissions": missing_submissions,
        "duplicate_application_identifiers": duplicate_apps,
        "source_archive_sha256": sha_by_archive,
        "complete_original_nda_bla_denominator_verified": False,
        "independently_adjudicated_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "Approved-product-centric source cannot independently enumerate all rejected and unresolved NDAs/BLAs",
            "Includes generic ANDA and supplemental applications; not all correspond to pivotal Phase 3 programs",
            "Submission action codes are preserved as published and not inferred as trial outcomes",
            "Public availability dates of predecision predictor features have not been independently established",
        ],
    }
    return snapshot, audit
