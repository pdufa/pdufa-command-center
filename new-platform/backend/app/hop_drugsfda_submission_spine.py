"""Offline Drugs@FDA original NDA/BLA *submission inventory*, not outcome labels.

Reads the official tab-delimited Applications/ Submissions extracts. The
approval-centric Drugs@FDA export does NOT contain a complete universe of
unapproved NDA/BLA submissions; the raw submission-status code does not encode
a validated review cycle or an adjudicated approval/nonapproval decision.

No network access, database mutation, model eligibility or scoring.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

APPLICATION_COLUMNS = ("ApplNo", "ApplType")
SUBMISSION_COLUMNS = (
    "ApplNo", "SubmissionType", "SubmissionNo",
    "SubmissionStatus", "SubmissionStatusDate",
)
FDA_APPLICATION_TYPES = frozenset({"NDA", "BLA"})
ORIGINAL_TYPES = frozenset({"ORIG"})
STATUS_PATTERN = re.compile(r"[A-Za-z0-9._ /-]{1,24}\Z")
NUMBER_PATTERN = re.compile(r"[0-9]{1,4}\Z")
FDA_DATA_SOURCE = "https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files"


def _read_tsv(
    path: Path, required: tuple[str, ...],
) -> tuple[list[dict[str, str]], str]:
    """Decode official tabular text: UTF-8 first, explicit CP-1252 fallback.

    FDA download snapshots contain legacy Windows smart punctuation in free
    text. Never use errors="ignore"/replacement or silently drop bytes.
    """
    raw = path.read_bytes()
    if b"\x00" in raw:
        raise ValueError("FDA source table contains NUL bytes")
    try:
        body = raw.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        body = raw.decode("cp1252", errors="strict")
        encoding = "cp1252"
    with io.StringIO(body, newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        fields = reader.fieldnames or []
        if (len(fields) != len(set(fields))
                or any(not field for field in fields)
                or not set(required).issubset(fields)):
            raise ValueError("Drugs@FDA TSV schema missing or duplicate required columns")
        rows = list(reader)
    for row in rows:
        if None in row or any(not isinstance(value, str) for value in row.values()):
            raise ValueError("Malformed Drugs@FDA tab-delimited row")
    return rows, encoding


def _digest(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def _source_date(value: str) -> date | None:
    stripped = value.strip()
    if not stripped:
        return None
    candidates = (stripped, stripped[:10])
    for item in candidates:
        for pattern in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(item, pattern).date()
            except ValueError:
                pass
    return None


def audit_original_submissions(
    applications_tsv: str | Path,
    submissions_tsv: str | Path,
    *, as_of: date,
) -> dict:
    """Audit visible original submissions without inferring FDA review cycles."""
    if not isinstance(as_of, date):
        raise ValueError("Explicit cutoff date is required")
    apps_path = Path(applications_tsv)
    subs_path = Path(submissions_tsv)
    apps, app_encoding = _read_tsv(apps_path, APPLICATION_COLUMNS)
    subs, sub_encoding = _read_tsv(subs_path, SUBMISSION_COLUMNS)
    application_types: dict[str, str] = {}
    types = Counter()
    for app in apps:
        number, category = app["ApplNo"].strip(), app["ApplType"].strip().upper()
        if (not re.fullmatch(r"[0-9]{6}", number)
                or not re.fullmatch(r"[A-Z]{2,8}", category)):
            raise ValueError("Malformed Drugs@FDA application identity")
        if number in application_types:
            raise ValueError("Duplicate Drugs@FDA application identity")
        application_types[number] = category
        types[category] += 1

    seen_keys: set[tuple[str, str, str]] = set()
    skipped = Counter()
    flags = Counter()
    entries = []
    for submission in subs:
        app = submission["ApplNo"].strip()
        kind = submission["SubmissionType"].strip().upper()
        serial = submission["SubmissionNo"].strip()
        if (not re.fullmatch(r"[0-9]{6}", app)
                or not re.fullmatch(r"[A-Z]{2,12}", kind)
                or not NUMBER_PATTERN.fullmatch(serial)):
            raise ValueError("Invalid Drugs@FDA submission identity")
        key = (app, kind, str(int(serial)))
        if key in seen_keys:
            # May indicate a duplicated action, not a new FDA decision.
            flags["DUPLICATE_SUBMISSION_KEY_REQUIRES_RECONCILIATION"] += 1
            continue
        seen_keys.add(key)
        if app not in application_types:
            skipped["NO_MATCHING_APPLICATION_ROW"] += 1
            continue
        if application_types[app] not in FDA_APPLICATION_TYPES:
            skipped["NON_NDA_BLA_APPLICATION"] += 1
            continue
        if kind not in ORIGINAL_TYPES:
            skipped["NOT_AN_ORIGINAL_SUBMISSION"] += 1
            continue
        raw_status = submission["SubmissionStatus"].strip()
        raw_day = submission["SubmissionStatusDate"].strip()
        problems = []
        if not raw_status:
            problems.append("RAW_SUBMISSION_STATUS_MISSING")
        elif not STATUS_PATTERN.fullmatch(raw_status):
            problems.append("RAW_SUBMISSION_STATUS_UNPARSEABLE")
            raw_status = ""  # Never export unsafe spreadsheet cells.
        parsed = _source_date(raw_day)
        if parsed is None:
            problems.append(
                "RAW_SUBMISSION_DATE_MISSING" if not raw_day
                else "RAW_SUBMISSION_DATE_UNPARSEABLE"
            )
        elif parsed > as_of:
            problems.append("RAW_SUBMISSION_DATE_AFTER_RESEARCH_CUTOFF")
        flags.update(problems)
        entries.append({
            "application_id": application_types[app] + app,
            "application_type": application_types[app],
            "submission_kind": kind,
            "original_submission_number": int(serial),
            "raw_submission_status_code": raw_status,
            "raw_submission_status_date": parsed.isoformat() if parsed else None,
            "status_date_within_cutoff": bool(parsed and parsed <= as_of),
            "source_data_quality_flags": problems,
            "review_cycle": None,
            "fda_action_outcome": None,
            "independently_verified": False,
            "model_eligible": False,
        })
    entries.sort(key=lambda r: (r["application_id"], r["original_submission_number"]))
    return {
        "status": "DRUGSFDA_ORIGINAL_SUBMISSION_SPINE_RESEARCH_ONLY",
        "source_family": "FDA_DRUGS_AT_FDA_TAB_DELIMITED_APPROVAL_CENTRIC_EXPORT",
        "source_documentation_url": FDA_DATA_SOURCE,
        "research_cutoff": as_of.isoformat(),
        "source_application_tsv_sha256": _digest(apps_path),
        "source_submission_tsv_sha256": _digest(subs_path),
        "source_applications_tsv_encoding": app_encoding,
        "source_submissions_tsv_encoding": sub_encoding,
        "application_rows_in_extract": len(apps),
        "application_type_counts": dict(sorted(types.items())),
        "submission_rows_in_extract": len(subs),
        "original_nda_bla_submission_rows": len(entries),
        "distinct_nda_bla_applications_in_original_submission_inventory":
            len({r["application_id"] for r in entries}),
        "excluded_submission_row_reason_counts": dict(sorted(skipped.items())),
        "source_data_quality_flag_counts": dict(sorted(flags.items())),
        "candidate_original_submissions": entries,
        "independently_verified_fda_review_cycles": 0,
        "complete_original_nda_bla_application_denominator_verified": False,
        "unapproved_applications_absent_from_export_possible": True,
        "submission_number_is_not_review_cycle": True,
        "raw_status_not_a_verified_decision_label": True,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "readiness": "REVIEW_REQUIRED",
        "note": (
            "All rows are unverified submission-history observations from an "
            "approval-centric registry. Submissions are not decision cycles. "
            "Original CRLs and never-approved applications must be reconstructed "
            "from independent contemporaneous FDA and sponsor sources."
        ),
    }
