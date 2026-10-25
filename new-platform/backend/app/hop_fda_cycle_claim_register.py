"""Offline FDA action/cycle *claim* register, strictly quarantined.

The review worklist is published-letter selected, not a representative FDA
decision denominator. Filling an adjudicator field is only a *claim*; this
module cannot verify identity, original letters, an action, or model eligibility.
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from .hop_fda_review_triage import TRIAGE_FIELDS, REVIEW_STATES
from .hop_fda_reviewer_reconciliation import APPLICATION_ID, SHA256
from .hop_outcomes_import import OFFICIAL_FDA_HOSTS

WORKLIST_FIELDS = (
    "review_queue_priority", "triage_status", "source_record_sha256",
    "fda_pdf_sha256", "fda_pdf_url", "provisional_page_link",
    "disputed_fields", "source_metadata_warning_flags",
)
CLAIM_FIELDS = (
    "claimed_adjudicator_token", "claimed_original_letter_pages",
    "claimed_application_id", "claimed_review_cycle",
    "claimed_fda_action_date", "claimed_fda_action_type",
    "claimed_indication", "claimed_independent_fda_url",
    "claimed_resolution_notes",
)
FIELDS = (*WORKLIST_FIELDS, "register_status", *CLAIM_FIELDS, "model_eligible")
STATUS = "UNADJUDICATED_SOURCE_CLAIM_REQUIRES_HUMAN_REVIEW"
ACTIONS = frozenset({
    "APPROVED", "COMPLETE_RESPONSE", "WITHDRAWN", "OTHER_NONAPPROVAL",
    "NOT_AN_FDA_DECISION",
})
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_PAGES = re.compile(r"[1-9][0-9]{0,5}(?:-[1-9][0-9]{0,5})?\Z")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]{2,79}\Z")


def _official_fda_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https"
            and parsed.hostname in OFFICIAL_FDA_HOSTS
            and parsed.username is None and parsed.password is None
            and parsed.port is None and bool(parsed.path and parsed.path != "/")
            and not parsed.query and not parsed.fragment
        )
    except ValueError:
        return False


def _safe_text(value: str, limit: int) -> bool:
    return (
        isinstance(value, str) and len(value) <= limit
        and "\x00" not in value and "\r" not in value
        and not value.lstrip().startswith(("=", "+", "-", "@", "\t", "\n"))
    )


def _verify_worklist(worklist: list[dict]) -> dict[str, dict]:
    if not isinstance(worklist, list) or not worklist:
        raise ValueError("Missing FDA source-review worklist")
    by_source = {}
    for row in worklist:
        if (not isinstance(row, dict) or set(row) != set(TRIAGE_FIELDS)
                or row.get("triage_status") not in REVIEW_STATES
                or row.get("review_queue_priority") !=
                   str(REVIEW_STATES.index(row["triage_status"]) + 1)):
            raise ValueError("Invalid quarantined FDA source worklist")
        sid, pdf_sha = row["source_record_sha256"], row["fda_pdf_sha256"]
        pdf_url = row["fda_pdf_url"]
        if not isinstance(pdf_url, str):
            raise ValueError("Invalid FDA source PDF URL")
        try:
            parsed = urlparse(pdf_url)
            official_pdf = (
                parsed.scheme == "https"
                and parsed.hostname == "download.open.fda.gov"
                and parsed.path.startswith("/crl/")
                and parsed.path.endswith(".pdf")
                and parsed.username is None and parsed.password is None
                and parsed.port is None and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            official_pdf = False
        if (not isinstance(sid, str) or not SHA256.fullmatch(sid)
                or sid in by_source or not isinstance(pdf_sha, str)
                or not SHA256.fullmatch(pdf_sha) or not official_pdf):
            raise ValueError("Invalid, repeated or modified FDA source reference")
        anchor = row["provisional_page_link"]
        if (anchor and (not isinstance(anchor, str)
                        or not re.fullmatch(
                            re.escape(row["fda_pdf_url"]) + r"#page=[1-9][0-9]*",
                            anchor))):
            raise ValueError("Provisional page link points away from source")
        if (not isinstance(row["disputed_fields"], str)
                or not isinstance(row["source_metadata_warning_flags"], str)):
            raise ValueError("Invalid source-review discrepancy fields")
        if any(not _safe_text(row.get(k), 2000) for k in TRIAGE_FIELDS):
            raise ValueError("Unsafe source-review worklist field")
        by_source[sid] = row
    return by_source


def prepare_claim_register(worklist: list[dict]) -> list[dict[str, str]]:
    """Produce blank candidate claims, never inferred action or review cycle."""
    _verify_worklist(worklist)
    return [{
        **{k: row[k] for k in WORKLIST_FIELDS},
        "register_status": STATUS,
        **{k: "" for k in CLAIM_FIELDS},
        "model_eligible": "false",
    } for row in worklist]


def read_csv(path: str | Path, headers: tuple[str, ...]) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(headers):
            raise ValueError("Adjudication register CSV has invalid columns")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed CSV row or extra cells")
    return rows


def render_csv(rows: list[dict[str, str]], headers: tuple[str, ...]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="raise",
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return stream.getvalue()


def _claim_state(row: dict[str, str], as_of: date) -> str:
    filled = [field for field in CLAIM_FIELDS if row[field].strip()]
    if not filled:
        return "NO_ADJUDICATION_CLAIM"
    for key in CLAIM_FIELDS:
        if not _safe_text(row[key], 5000 if key == "claimed_resolution_notes" else 500):
            raise ValueError("Unsafe or excessive adjudication claim field")
    if len(filled) < len(CLAIM_FIELDS):
        return "INCOMPLETE_ADJUDICATION_CLAIM"
    if not _TOKEN.fullmatch(row["claimed_adjudicator_token"]):
        raise ValueError("Claimed adjudicator identity token invalid")
    page_range = row["claimed_original_letter_pages"]
    if not _PAGES.fullmatch(page_range):
        raise ValueError("Claimed FDA page range invalid")
    pages = [int(n) for n in page_range.split("-")]
    if len(pages) == 2 and pages[0] > pages[1]:
        raise ValueError("Claimed FDA page range reversed")
    if not APPLICATION_ID.fullmatch(row["claimed_application_id"]):
        raise ValueError("Claimed FDA application identity invalid")
    if not re.fullmatch(r"[1-9][0-9]{0,2}", row["claimed_review_cycle"]):
        raise ValueError("Claimed FDA review cycle invalid")
    claimed_date = row["claimed_fda_action_date"]
    if not _DATE.fullmatch(claimed_date):
        raise ValueError("Claimed FDA action date invalid")
    try:
        action_day = date.fromisoformat(claimed_date)
    except ValueError:
        raise ValueError("Claimed FDA action date invalid") from None
    if action_day > as_of:
        raise ValueError("Claimed FDA action date in the future")
    if row["claimed_fda_action_type"] not in ACTIONS:
        raise ValueError("Unsupported FDA action claim")
    if not _official_fda_url(row["claimed_independent_fda_url"]):
        raise ValueError("Claimed external FDA corroboration must be official HTTPS")
    if row["claimed_fda_action_type"] == "NOT_AN_FDA_DECISION":
        return "NONDECISION_CLAIM_NEEDS_EXCLUSION_REVIEW"
    return "COMPLETE_UNVERIFIED_CLAIM_NEEDS_SIGNOFF"


def screen_claim_register(
    worklist: list[dict], submissions: list[dict], *, as_of: date,
) -> dict:
    """Screen candidate cycle claims and collisions, never verify any outcome."""
    if not isinstance(as_of, date):
        raise ValueError("Controlled date cutoff required")
    expected = {r["source_record_sha256"]: r for r in prepare_claim_register(worklist)}
    if not isinstance(submissions, list) or len(submissions) != len(expected):
        raise ValueError("Missing adjudication register source references")
    seen = set()
    by_cycle: dict[tuple[str, int], list[tuple[str, str, str]]] = defaultdict(list)
    per_source = {}
    for row in submissions:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError("Adjudication register columns altered")
        sid = row["source_record_sha256"]
        if sid not in expected or sid in seen:
            raise ValueError("Unknown or duplicate original FDA source reference")
        seen.add(sid)
        baseline = expected[sid]
        if (any(row[k] != baseline[k] for k in WORKLIST_FIELDS)
                or row.get("register_status") != STATUS
                or row.get("model_eligible") != "false"):
            raise ValueError("Original FDA source, status or model gate modified")
        status = _claim_state(row, as_of)
        per_source[sid] = status
        if status == "COMPLETE_UNVERIFIED_CLAIM_NEEDS_SIGNOFF":
            app = row["claimed_application_id"].replace("-", "")
            key = (app, int(row["claimed_review_cycle"]))
            by_cycle[key].append((
                sid, row["claimed_fda_action_type"],
                row["claimed_fda_action_date"]
            ))
    if seen != set(expected):
        raise ValueError("Register missing original FDA source rows")

    collided = set()
    contradictory = set()
    for claims in by_cycle.values():
        if len(claims) > 1:
            collided.update(source_id for source_id, _, _ in claims)
            if len({(action, day) for _, action, day in claims}) > 1:
                contradictory.update(source_id for source_id, _, _ in claims)
    counts = Counter(per_source.values())
    for sid in collided:
        counts[per_source[sid]] -= 1
        counts["MULTIPLE_LETTERS_SAME_CYCLE_NEEDS_RECONCILIATION"] += 1
    return {
        "status": "UNVERIFIED_FDA_CYCLE_CLAIMS_QUARANTINED",
        "published_source_references": len(expected),
        "source_review_status_counts": dict(sorted(counts.items())),
        "source_refs_with_duplicate_application_cycles": sorted(collided),
        "source_refs_with_conflicting_cycle_action_claims": sorted(contradictory),
        "original_source_documents_independently_verified": 0,
        "reviewer_identities_authenticated": False,
        "adjudication_signatures_authenticated": False,
        "complete_application_denominator_verified": False,
        "chronological_calibration_validated": False,
        "independently_verified_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "approval_rate": None,
        "readiness": "REVIEW_REQUIRED",
        "note": (
            "This is a source-selected published-letter claim worklist, not a "
            "complete FDA cohort. All signed/un-signed text remains "
            "unverified without independent original-source checks."
        ),
    }
