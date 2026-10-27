"""Offline, pinned GitHub artifact recovery into a NEW research-only SQLite file.

No downloads, environment database URLs, original-FDA certification, cycle
inference, or training labels. Default is a deterministic, read-only JSON audit.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
import csv
from datetime import date
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import zipfile

PINNED_ARTIFACTS = {
    "CRL_SNAPSHOT": {"artifact_id": 12610736354, "run_id": 40224038609,
        "sha256": "e2270f2ba87688c348429f1e37225eaa1aba0bb196ad6b96277342c866ff6b70",
        "source_run_head_sha": "3729db0e7c21dd71ccf569fbebf80afa2eebd87f",
        "created_at": "2026-10-25T19:01:47Z"},
    "DRUGSFDA_SNAPSHOT": {"artifact_id": 12611090768, "run_id": 40224730350,
        "sha256": "58f9197c4d040fbf21f2bbf4edf223318b46c4df354a2a1efc95a844cad502c0",
        "source_run_head_sha": "c27a6ca061356859408029a94bf71a6e02126249",
        "created_at": "2026-10-25T19:10:24Z"},
    "ACTION_REVIEW": {"artifact_id": 12615481622, "run_id": 40236833550,
        "sha256": "e3f90ebcc3aa96fbc70518e14b40d9705402e46851832802c34668bf23603a25",
        "source_run_head_sha": "3d3b74ba1420fffe3ab5387d5f9b07b96a5ebf8a",
        "created_at": "2026-10-25T21:45:12Z"},
}
CRL_MEMBER = "fda_crl_published_quarantined.json"
REGISTRY_MEMBER = "drugsfda_approved_registry_quarantined.json"
WORKLIST_MEMBER = "fda_all_published_action_review_worklist.json"
PDF_MEMBER = "fda_all_published_action_pdf_checks.json"
MEMBERS = {
    "CRL_SNAPSHOT": {CRL_MEMBER, "fda_crl_audit.json"},
    "DRUGSFDA_SNAPSHOT": {REGISTRY_MEMBER, "drugsfda_approved_registry_audit.json"},
    "ACTION_REVIEW": {WORKLIST_MEMBER, PDF_MEMBER,
        "fda_all_published_action_pdf_checks_audit.json", "fda_all_published_action_review_audit.json",
        "fda_shared_pdf_document_page_mapping_review.json", "fda_shared_pdf_document_reconciliation_audit.json",
        "fda_shared_pdf_provisional_page_candidates.json", "fda_shared_pdf_provisional_page_candidates_audit.json",
        "fda_shared_pdf_review_worksheet_audit.json", "fda_shared_pdf_independent_review_worksheet.csv"},
}
CRL_URL = "https://download.open.fda.gov/transparency/crl/transparency-crl-0001-of-0001.json.zip"
REGISTRY_URL = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"
CRL_SOURCE_SHA = "744de010761c9ba445c3756ff7e47d5715c3e9d5aef48f5b1fd663646b5d6732"
REGISTRY_SOURCE_SHA = "d218e3d6ced00a6d117612529faa1eafa223ee65668a69f8139b5cd35054b3de"
MAX_ZIP_BYTES = 10_000_000
MAX_MEMBER_BYTES = 90_000_000
MAX_TOTAL_BYTES = 100_000_000
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("malformed JSON") from exc


def _parent_fd(path):
    """Pin each directory component with openat; never traverse a symlink."""
    path = Path(path).absolute()
    if ".." in path.parts:
        raise ValueError("parent traversal is not accepted")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        return fd, path.name
    except OSError as exc:
        os.close(fd)
        raise ValueError("unsafe or unavailable directory (symlink paths forbidden)") from exc


def _read_regular(path, limit):
    """No symlink path components, special files, or unbounded reads."""
    parent, name = _parent_fd(path)
    try:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except OSError as exc:
            raise ValueError("unsafe or unavailable regular file (symlink paths forbidden)") from exc
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise ValueError("regular file within size limit required")
            with os.fdopen(fd, "rb", closefd=False) as f:
                data = f.read(limit + 1)
            after = os.fstat(fd)
            if len(data) > limit or (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError("file changed or exceeds size limit")
            return data
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def _publish_new(path, data):
    parent, name = _parent_fd(path)
    try:
        fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def _day(raw, pattern=r"[0-9]{4}-[0-9]{2}-[0-9]{2}"):
    if not isinstance(raw, str) or not re.fullmatch(pattern, raw):
        return None
    try:
        if pattern == r"[0-9]{2}/[0-9]{2}/[0-9]{4}":
            m, d, y = map(int, raw.split("/")); return date(y, m, d).isoformat()
        if pattern == r"[0-9]{8}":
            return date(int(raw[:4]), int(raw[4:6]), int(raw[6:])).isoformat()
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return None


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _false(row, fields):
    _require(isinstance(row, dict), "record must be object")
    _require(all(row.get(field) is False for field in fields), "source must remain explicitly quarantined")


def _no_promotions(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"model_eligible", "model_eligible_records", "independently_verified", "independent_review_complete"} or key.endswith("_verified"):
                _require(item is False or (type(item) is int and item == 0), "source metadata cannot self-promote verification")
            if key in {"prediction_probability", "probability"}:
                _require(item is None, "source metadata cannot provide predictions")
            _no_promotions(item)
    elif isinstance(value, list):
        for item in value: _no_promotions(item)


def _digest(value):
    _require(isinstance(value, str) and SHA.fullmatch(value), "invalid source record digest")
    return value


def _records(value, status):
    _require(isinstance(value, dict) and value.get("schema_version") == 1 and
             value.get("status") == status and isinstance(value.get("records"), list), "unexpected quarantined snapshot schema")
    return value["records"]


def _audit_count(audit, field, expected):
    _require(type(audit.get(field)) is int and audit[field] == expected, "audit count mismatch: " + field)


def _range(values):
    valid = [x for x in values if x is not None]
    return {"minimum": min(valid) if valid else None, "maximum": max(valid) if valid else None,
            "valid_dates": len(valid), "unknown_or_invalid_dates": len(values) - len(valid)}


def load_package(manifest_path):
    path = Path(manifest_path).absolute()
    manifest = _decode(_read_regular(path, 100_000))
    _require(isinstance(manifest, dict) and set(manifest) == {"schema_version", "record_type", "retrieved_on", "artifacts"}
             and type(manifest["schema_version"]) is int and manifest["schema_version"] == 1
             and manifest["record_type"] == "RECOVERED_HOP_ARTIFACT_PROVENANCE"
             and _day(manifest["retrieved_on"]) is not None, "invalid recovery manifest")
    rows = manifest["artifacts"]
    _require(isinstance(rows, list) and len(rows) == 3, "exactly three pinned artifacts required")
    artifacts = {}
    filenames = set()
    for receipt in rows:
        _require(isinstance(receipt, dict) and set(receipt) == {"role", "artifact_id", "run_id", "repository",
                 "relative_path", "sha256", "source_run_head_sha", "created_at"}, "invalid artifact receipt fields")
        role = receipt["role"]
        _require(isinstance(role, str) and role in PINNED_ARTIFACTS and role not in artifacts, "unknown or repeated artifact role")
        _require(receipt["repository"] == "pdufa/pdufa-command-center" and all(receipt[k] == v and type(receipt[k]) is type(v)
                 for k, v in PINNED_ARTIFACTS[role].items()), "artifact receipt does not match trusted GitHub metadata")
        filename = receipt["relative_path"]
        _require(isinstance(filename, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*[.]zip", filename)
                 and ".." not in filename and filename not in filenames, "unsafe or duplicate artifact filename")
        filenames.add(filename)
        _require(manifest["retrieved_on"] >= receipt["created_at"][:10], "recovery cannot predate artifact")
        raw = _read_regular(path.parent / filename, MAX_ZIP_BYTES)
        _require(hashlib.sha256(raw).hexdigest() == receipt["sha256"], "artifact ZIP digest mismatch")
        members, metadata = {}, {}
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                files = archive.infolist()
                names = [f.filename for f in files]
                _require(len(names) == len(set(names)) and set(names) == MEMBERS[role], "unexpected or duplicate ZIP members")
                _require(sum(f.file_size for f in files) <= MAX_TOTAL_BYTES, "ZIP expanded size exceeds limit")
                for f in files:
                    mode = f.external_attr >> 16
                    _require(not f.is_dir() and not (f.flag_bits & 1) and not stat.S_ISLNK(mode)
                             and (stat.S_IFMT(mode) in {0, stat.S_IFREG})
                             and 0 <= f.file_size <= MAX_MEMBER_BYTES, "unsafe ZIP member")
                    with archive.open(f) as stream:
                        data = stream.read(MAX_MEMBER_BYTES + 1)
                    _require(len(data) == f.file_size, "ZIP member size mismatch")
                    metadata[f.filename] = {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
                    members[f.filename] = _decode(data) if f.filename.endswith(".json") else data.decode("utf-8")
        except (zipfile.BadZipFile, RuntimeError, UnicodeError) as exc:
            raise ValueError("invalid ZIP artifact") from exc
        artifacts[role] = {"receipt": receipt, "members": members, "member_metadata": metadata}
    return manifest, artifacts


def validate_package(manifest, artifacts):
    crl_files = artifacts["CRL_SNAPSHOT"]["members"]
    reg_files = artifacts["DRUGSFDA_SNAPSHOT"]["members"]
    rev_files = artifacts["ACTION_REVIEW"]["members"]
    for artifact in artifacts.values():
        for value in artifact["members"].values(): _no_promotions(value)
    crl = crl_files[CRL_MEMBER]; reg = reg_files[REGISTRY_MEMBER]
    letters = _records(crl, "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT")
    applications = _records(reg, "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT")
    for snapshot in (crl, reg):
        _require(_day(snapshot.get("source_export_date")) is not None and _day(snapshot.get("retrieved_on")) is not None
                 and snapshot["source_export_date"] <= snapshot["retrieved_on"] <= manifest["retrieved_on"], "invalid source export/retrieval chronology")
    ca = crl_files["fda_crl_audit.json"]; ra = reg_files["drugsfda_approved_registry_audit.json"]
    _require(ca.get("archive_sha256_by_url") == {CRL_URL: CRL_SOURCE_SHA}
             and ra.get("source_archive_sha256") == {REGISTRY_URL: REGISTRY_SOURCE_SHA}, "claimed original archive fingerprints differ")
    _audit_count(ca, "published_letter_records", len(letters)); _audit_count(ca, "quarantined_records", len(letters))
    _audit_count(ra, "source_application_records", len(applications)); _audit_count(ra, "quarantined_application_records", len(applications))
    backend = str(Path(__file__).resolve().parents[1] / "new-platform" / "backend")
    if backend not in sys.path: sys.path.insert(0, backend)
    from app.hop_fda_application_crosswalk import canonical_application_id, crosswalk_public_fda_sources
    by_digest = {}; types = Counter(); letter_dates = []
    for index, row in enumerate(letters):
        _false(row, ("model_eligible", "independently_verified", "cohort_complete_verified"))
        sha = _digest(row.get("source_record_sha256"))
        _require(sha not in by_digest and type(row.get("source_record_index")) is int and row["source_record_index"] == index
                 and row.get("source_partition") == CRL_URL and row.get("review_cycle") is None
                 and row.get("predecision_evidence_as_of") is None
                 and row.get("status") == "QUARANTINED_PUBLICATION_SELECTED"
                 and isinstance(row.get("application_numbers"), list)
                 and all(isinstance(x, str) for x in row["application_numbers"])
                 and isinstance(row.get("letter_type_as_published"), str), "invalid or duplicate CRL observation")
        by_digest[sha] = row; types[row["letter_type_as_published"]] += 1
        letter_dates.append(_day(row.get("letter_date_as_published"), r"[0-9]{2}/[0-9]{2}/[0-9]{4}"))
    _require(dict(types) == ca.get("letter_types"), "CRL type counts differ")
    app_digests = set(); app_ids = set(); statuses = Counter(); sub_dates = []; missing_submissions = 0; prefixes = Counter()
    canonical_ids = Counter(); malformed_application_ids = 0; missing_status = 0
    for index, row in enumerate(applications):
        _false(row, ("model_eligible", "review_cycles_independently_adjudicated", "complete_application_denominator_verified", "point_in_time_features_verified"))
        sha = _digest(row.get("record_sha256")); app = row.get("application_number_as_published")
        _require(sha not in app_digests and isinstance(app, str) and bool(app)
                 and app not in app_ids and row.get("source_archive_url") == REGISTRY_URL
                 and type(row.get("source_record_index")) is int and row["source_record_index"] == index
                 and row.get("status") == "QUARANTINED_APPROVED_PRODUCT_REGISTRY"
                 and isinstance(row.get("submissions_as_published"), list), "invalid or duplicate registry application")
        app_digests.add(sha); app_ids.add(app)
        prefix = next((k for k in ("ANDA", "NDA", "BLA") if app.startswith(k)), "OTHER")
        prefixes[prefix] += 1
        canonical = canonical_application_id(app)
        if canonical is None: malformed_application_ids += 1
        else: canonical_ids[canonical] += 1
        missing_submissions += not row["submissions_as_published"]
        for sub in row["submissions_as_published"]:
            _require(isinstance(sub, dict) and set(sub) == {"review_priority_as_published", "submission_number_as_published",
                "submission_status_as_published", "submission_status_date_as_published", "submission_type_as_published"}
                and all(x is None or isinstance(x, str) for x in sub.values()), "invalid published submission metadata")
            status_value = sub["submission_status_as_published"]
            if status_value: statuses[status_value] += 1
            else: missing_status += 1
            sub_dates.append(_day(sub["submission_status_date_as_published"], r"[0-9]{8}"))
    _require(dict(prefixes) == ra.get("application_number_prefixes") and dict(statuses) == ra.get("published_submission_status_counts"), "registry counts differ")
    _audit_count(ra, "missing_or_invalid_submissions", missing_submissions)
    worklist = _records(rev_files[WORKLIST_MEMBER], "PUBLISHED_FDA_ACTION_REVIEW_ONLY_NO_VALIDATED_OUTCOMES")
    pdfs = _records(rev_files[PDF_MEMBER], "PDF_FETCH_CHECK_ONLY_NOT_HISTORICAL_OUTCOME_VERIFICATION")
    for records, fields in ((worklist, ("model_eligible", "identity_verified", "review_cycle_verified", "independent_review_complete",
            "complete_denominator_verified", "effective_fda_action_date_independently_verified", "original_fda_action_document_verified", "review_cycle_number_verified")),
            (pdfs, ("model_eligible", "document_identity_adjudicated", "effective_fda_action_date_verified", "review_cycle_verified"))):
        seen = set()
        for row in records:
            _false(row, fields); sha = _digest(row.get("source_record_sha256"))
            _require(sha in by_digest and sha not in seen, "unknown or duplicate review source digest")
            seen.add(sha); original = by_digest[sha]
            is_work = records is worklist
            names = (("application_ids_as_published", "application_numbers"), ("file_name_as_published", "file_name_as_published"),
                     ("letter_date_as_published", "letter_date_as_published"), ("letter_type_as_published", "letter_type_as_published")) if is_work else (
                    ("source_application_ids_as_published", "application_numbers"), ("source_file_name_as_published", "file_name_as_published"),
                    ("letter_date_as_published", "letter_date_as_published"), ("letter_type_as_published", "letter_type_as_published"))
            _require(all(row.get(a) == original.get(b) for a, b in names), "review metadata does not match original CRL observation")
            if is_work:
                _require(all(row.get(k) is None for k in ("fda_review_cycle_outcome", "effective_fda_action_date_candidate",
                         "public_features_as_of", "independent_reviewer_one", "independent_reviewer_two")), "review worklist cannot self-certify")
            elif row.get("document_fetch_status") == "OFFICIAL_PDF_BYTES_CONFIRMED":
                _digest(row.get("full_document_sha256_if_confirmed"))
            else:
                _require(row.get("full_document_sha256_if_confirmed") is None, "unconfirmed PDF cannot have confirmed hash")
        _require(seen == set(by_digest), "review observations do not cover CRL inventory exactly")
    for files in (crl_files, reg_files, rev_files):
        for value in files.values():
            if isinstance(value, dict):
                for field in ("model_eligible_records", "unique_application_review_cycles_verified", "independently_adjudicated_review_cycles",
                              "independently_adjudicated_review_cycle_outcomes", "independently_verified_review_cycles"):
                    if field in value: _audit_count(value, field, 0)
    # Reuse the project's application crosswalk; identity links are not outcomes.
    crosswalk, identity_audit = crosswalk_public_fda_sources(crl, reg)
    linked = {x["letter_record_sha256"]: x for x in crosswalk["records"]}
    worksheet = list(csv.DictReader(io.StringIO(rev_files["fda_shared_pdf_independent_review_worksheet.csv"])))
    _require(len({r.get("source_record_sha256") for r in worksheet}) == len(worksheet)
             and all(r.get("source_record_sha256") in by_digest and r.get("model_eligible") == "False"
             and r.get("independent_review_complete") == "False" and not r.get("first_reviewer")
             and not r.get("second_reviewer") for r in worksheet), "invalid unadjudicated worksheet")
    _audit_count(rev_files["fda_shared_pdf_review_worksheet_audit.json"], "published_letter_rows", len(worksheet))
    report = {"status": "RECOVERED_METADATA_QUARANTINED_NOT_VERIFIED_FDA_OUTCOMES", "recovered_on": manifest["retrieved_on"],
        "source_retrieved_on": {"crl": crl["retrieved_on"], "registry": reg["retrieved_on"]},
        "source_export_dates": {"crl": crl["source_export_date"], "registry": reg["source_export_date"]},
        "source_artifacts": [{**artifacts[k]["receipt"], "members": artifacts[k]["member_metadata"]} for k in sorted(artifacts)],
        "counts": {"recovered_artifacts": 3, "crl_source_observations": len(letters), "registry_applications": len(applications),
            "registry_submission_observations": len(sub_dates), "action_review_observations": len(worklist), "pdf_check_observations": len(pdfs),
            "review_worksheet_observations": len(worksheet), "identified_adjudicated_review_cycles": 0,
            "independently_verified_pass": 0, "independently_verified_fail": 0,
            "usable_predecision_scientific_evidence_decisions": 0, "backtesting_eligible_decisions": 0,
            "registry_applications_without_submissions": missing_submissions,
            "registry_submissions_without_status": missing_status,
            "registry_application_ids_unparseable": malformed_application_ids,
            "registry_canonical_application_id_collisions": sum(n > 1 for n in canonical_ids.values())},
        "published_letter_type_counts": dict(sorted(types.items())), "published_submission_status_counts": dict(sorted(statuses.items())),
        "application_identity_link_counts": identity_audit["identity_link_status_counts"],
        "published_letter_date_range": _range(letter_dates), "published_submission_status_date_range": _range(sub_dates),
        "independently_verified": False, "original_fda_bytes_retained": False, "complete_decision_denominator_verified": False,
        "prediction_model_validated": False, "prediction_probability": None,
        "limitations": ["Pinned GitHub ZIP receipts attest recovered artifact bytes, not original FDA document truth.",
            "Original FDA archives, manifests and PDFs were not retained by the historical collectors.",
            "CRL publication selection and approved-product registry selection do not establish an unbiased review-cycle denominator.",
            "AP/CR/TA source codes and published letter dates are not adjudicated cycle labels or effective action dates.",
            "Drug, indication, trial, PDUFA target, source publication and predecision features remain missing; no inference fills them."]}
    return report, linked


SCHEMA = """
CREATE TABLE source_artifacts(artifact_id INTEGER PRIMARY KEY, role TEXT UNIQUE NOT NULL, run_id INTEGER NOT NULL, zip_sha256 TEXT NOT NULL, source_created_at TEXT NOT NULL, recovered_on TEXT NOT NULL, source_snapshot_retrieved_on TEXT, source_export_date TEXT, receipt_json TEXT NOT NULL);
CREATE TABLE artifact_members(artifact_id INTEGER REFERENCES source_artifacts, name TEXT, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, PRIMARY KEY(artifact_id,name));
CREATE TABLE source_records(artifact_id INTEGER, member_name TEXT, record_index INTEGER, payload_json TEXT NOT NULL, recovered_row_sha256 TEXT NOT NULL, PRIMARY KEY(artifact_id,member_name,record_index), FOREIGN KEY(artifact_id,member_name) REFERENCES artifact_members);
CREATE TABLE crl_observations(claimed_original_source_record_sha256 TEXT PRIMARY KEY, artifact_id INTEGER REFERENCES source_artifacts, source_record_index INTEGER, application_ids_json TEXT NOT NULL, sponsor TEXT, published_letter_type TEXT, published_letter_date TEXT, published_letter_date_raw TEXT, canonical_candidates_json TEXT NOT NULL, identity_link_status TEXT NOT NULL, drug TEXT, indication TEXT, trial_id TEXT, pdufa_target_date TEXT, source_publication_date TEXT, review_cycle INTEGER, independently_verified INTEGER NOT NULL CHECK(independently_verified=0), model_eligible INTEGER NOT NULL CHECK(model_eligible=0));
CREATE TABLE registry_applications(claimed_original_source_record_sha256 TEXT PRIMARY KEY, artifact_id INTEGER REFERENCES source_artifacts, source_record_index INTEGER, application_id_candidate TEXT, application_id_as_published TEXT UNIQUE NOT NULL, sponsor TEXT, drug TEXT, indication TEXT, trial_id TEXT, pdufa_target_date TEXT, source_publication_date TEXT, independently_verified INTEGER NOT NULL CHECK(independently_verified=0), model_eligible INTEGER NOT NULL CHECK(model_eligible=0));
CREATE TABLE registry_submissions(claimed_original_source_record_sha256 TEXT REFERENCES registry_applications, observation_index INTEGER, submission_type TEXT, submission_number TEXT, published_status TEXT, published_status_date TEXT, published_status_date_raw TEXT, review_priority TEXT, model_eligible INTEGER NOT NULL CHECK(model_eligible=0), PRIMARY KEY(claimed_original_source_record_sha256,observation_index));
CREATE TABLE action_review_observations(claimed_original_source_record_sha256 TEXT PRIMARY KEY REFERENCES crl_observations, artifact_id INTEGER REFERENCES source_artifacts, payload_json TEXT NOT NULL, model_eligible INTEGER NOT NULL CHECK(model_eligible=0));
CREATE TABLE pdf_check_observations(claimed_original_source_record_sha256 TEXT PRIMARY KEY REFERENCES crl_observations, artifact_id INTEGER REFERENCES source_artifacts, payload_json TEXT NOT NULL, original_pdf_retained INTEGER NOT NULL CHECK(original_pdf_retained=0), model_eligible INTEGER NOT NULL CHECK(model_eligible=0));
CREATE TABLE review_cycles(application_id TEXT, submission_id TEXT, review_cycle INTEGER, outcome TEXT, CHECK(0));
"""


def write_database(path, manifest, artifacts, linked):
    """Explicit NEW file only. No existing database is opened or overwritten."""
    path = Path(path).absolute()
    _require(not any(p.is_symlink() for p in (path, *path.parents)), "database symlink paths forbidden")
    _require(path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}, "local SQLite filename required")
    # SQLite never opens a destination path: serialize a completed in-memory DB
    # and write bytes once through an exclusive descriptor in a pinned directory.
    with closing(sqlite3.connect(":memory:")) as db, db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(SCHEMA)
        for role in sorted(artifacts):
            artifact = artifacts[role]; receipt = artifact["receipt"]; aid = receipt["artifact_id"]
            db.execute("INSERT INTO source_artifacts VALUES(?,?,?,?,?,?,?,?,?)", (aid, role, receipt["run_id"], receipt["sha256"], receipt["created_at"], manifest["retrieved_on"], artifact["members"].get(CRL_MEMBER if role == "CRL_SNAPSHOT" else REGISTRY_MEMBER, {}).get("retrieved_on"), artifact["members"].get(CRL_MEMBER if role == "CRL_SNAPSHOT" else REGISTRY_MEMBER, {}).get("source_export_date"), _json(receipt)))
            for name, meta in sorted(artifact["member_metadata"].items()):
                db.execute("INSERT INTO artifact_members VALUES(?,?,?,?)", (aid, name, meta["sha256"], meta["size_bytes"]))
                value = artifact["members"][name]
                for i, row in enumerate(value.get("records", []) if isinstance(value, dict) else []):
                    payload = _json(row)
                    db.execute("INSERT INTO source_records VALUES(?,?,?,?,?)", (aid, name, i, payload, hashlib.sha256(payload.encode()).hexdigest()))
        aid = artifacts["CRL_SNAPSHOT"]["receipt"]["artifact_id"]
        for row in artifacts["CRL_SNAPSHOT"]["members"][CRL_MEMBER]["records"]:
            sha = row["source_record_sha256"]; link = linked[sha]
            db.execute("INSERT INTO crl_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (sha, aid, row["source_record_index"], _json(row["application_numbers"]), row.get("company_name_as_published"), row["letter_type_as_published"], _day(row.get("letter_date_as_published"), r"[0-9]{2}/[0-9]{2}/[0-9]{4}"), row.get("letter_date_as_published"), _json(link["canonical_application_candidates"]), link["identity_link_status"], None, None, None, None, None, None, 0, 0))
        from app.hop_fda_application_crosswalk import canonical_application_id
        aid = artifacts["DRUGSFDA_SNAPSHOT"]["receipt"]["artifact_id"]
        for row in artifacts["DRUGSFDA_SNAPSHOT"]["members"][REGISTRY_MEMBER]["records"]:
            sha = row["record_sha256"]
            db.execute("INSERT INTO registry_applications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (sha, aid, row["source_record_index"], canonical_application_id(row["application_number_as_published"]), row["application_number_as_published"], row.get("sponsor_name_as_published"), None, None, None, None, None, 0, 0))
            for i, sub in enumerate(row["submissions_as_published"]):
                db.execute("INSERT INTO registry_submissions VALUES(?,?,?,?,?,?,?,?,?)", (sha, i, sub["submission_type_as_published"], sub["submission_number_as_published"], sub["submission_status_as_published"], _day(sub["submission_status_date_as_published"], r"[0-9]{8}"), sub["submission_status_date_as_published"], sub["review_priority_as_published"], 0))
        aid = artifacts["ACTION_REVIEW"]["receipt"]["artifact_id"]
        for row in artifacts["ACTION_REVIEW"]["members"][WORKLIST_MEMBER]["records"]:
            db.execute("INSERT INTO action_review_observations VALUES(?,?,?,?)", (row["source_record_sha256"], aid, _json(row), 0))
        for row in artifacts["ACTION_REVIEW"]["members"][PDF_MEMBER]["records"]:
            db.execute("INSERT INTO pdf_check_observations VALUES(?,?,?,?,?)", (row["source_record_sha256"], aid, _json(row), 0, 0))
        _require(db.execute("PRAGMA foreign_key_check").fetchall() == [], "database foreign key check failed")
        db.commit()
        data = db.serialize()
    _publish_new(path, data)


def ingest(manifest_path, *, database=None):
    manifest, artifacts = load_package(manifest_path)
    report, linked = validate_package(manifest, artifacts)
    if database is not None:
        write_database(database, manifest, artifacts, linked)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--database", type=Path, help="Create a NEW local research SQLite file; existing paths are refused")
    args = p.parse_args()
    try:
        print(json.dumps(ingest(args.manifest, database=args.database), indent=2, sort_keys=True))
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"RECOVERY_REJECTED: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
