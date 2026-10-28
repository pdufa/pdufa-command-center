"""Original FDA action-letter research packet; no training or probability authority.

This module validates two independently located FDA-hosted *action documents*
as dated research observations. It never equates letter signature date with
first public availability, a filename with an adjudicated review cycle, or
source inspection with a verified historical evaluation cohort.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .hop_outcomes_import import normalize_application_id

_SAMPLE_FILE = Path(__file__).parent / "research_sources" / "hop_fda_primary_action_letter_samples.json"
_SCHEMA = "hop-fda-primary-action-letter-samples-v1"
_HOSTS = frozenset({"www.accessdata.fda.gov", "accessdata.fda.gov",
                    "download.open.fda.gov"})
_ACTIONS = {"APPROVED": "NDA APPROVAL", "COMPLETE_RESPONSE": "COMPLETE RESPONSE"}
_REFERENCE = re.compile(r"[1-9][0-9]{5,9}\Z")
_UNIT = re.compile(r"ORIGINAL_[1-9][0-9]*\Z")
_REQUIRED = frozenset((
    "record_id", "application_id", "submission_unit",
    "submission_unit_basis", "review_cycle", "drug", "sponsor", "indication",
    "action", "fda_action_date", "fda_document_date", "original_document_url",
    "document_reference_id", "inspected_pages", "document_action_heading",
    "signature_date_observed", "source_observation",
    "source_document_bytes_sha256", "source_document_bytes_retained",
    "original_publication_date_verified", "first_known_label_public_as_of",
    "frozen_predecision_features_as_of", "pdufa_target_history_verified",
    "application_cycle_independently_adjudicated",
    "original_action_independently_adjudicated",
    "eligible_for_training", "limitation",
))


def _date(raw):
    if not isinstance(raw, str) or len(raw) != 10:
        return None
    try:
        d = date.fromisoformat(raw)
        return d if d.isoformat() == raw else None
    except ValueError:
        return None


def _url_ok(value):
    if not isinstance(value, str) or any(x.isspace() for x in value):
        return False
    try:
        p = urlsplit(value)
        return (p.scheme == "https" and p.hostname in _HOSTS
                and p.username is None and p.password is None
                and p.port in (None, 443) and p.fragment == ""
                and p.path.endswith(".pdf") and p.query == "")
    except ValueError:
        return False


def _check_letter(letter, cutoff):
    if not isinstance(letter, dict) or set(letter) != _REQUIRED:
        raise ValueError("Action letter metadata must use the complete v1 contract")
    app = normalize_application_id(letter["application_id"])
    unit = letter["submission_unit"]
    if not app or app != letter["application_id"]:
        raise ValueError("Canonical FDA application identity required")
    if not isinstance(unit, str) or not _UNIT.fullmatch(unit):
        raise ValueError("Exact original/submission unit required")
    if letter["submission_unit_basis"] not in ("FDA_LETTER_TEXT", "FDA_PDF_FILENAME_ONLY"):
        raise ValueError("Unsupported unit provenance")
    if not isinstance(letter["record_id"], str) or not letter["record_id"].startswith(app + "_"):
        raise ValueError("Record and exact application identity mismatch")
    action = letter["action"]
    if action not in _ACTIONS or letter["document_action_heading"] != _ACTIONS[action]:
        raise ValueError("FDA action and inspected action heading disagree")
    if letter["record_id"] != (
        f"{app}_{unit}_{letter['fda_action_date'].replace('-', '')}_"
        f"{'CRL' if action == 'COMPLETE_RESPONSE' else 'APPROVED'}"
    ):
        raise ValueError("Action record identity/date/disposition mismatch")
    action_date = _date(letter["fda_action_date"])
    signed_date = _date(letter["signature_date_observed"])
    document_date = _date(letter["fda_document_date"])
    if not action_date or action_date != signed_date or action_date != document_date or action_date > cutoff:
        raise ValueError("Signed FDA action date not verified or after research cutoff")
    if not _url_ok(letter["original_document_url"]):
        raise ValueError("Official FDA-hosted PDF URL required")
    if not isinstance(letter["document_reference_id"], str) or not _REFERENCE.fullmatch(letter["document_reference_id"]):
        raise ValueError("FDA PDF reference ID required")
    pages = letter["inspected_pages"]
    if (not isinstance(pages, list) or not pages or any(type(p) is not int or p < 0 or p > 5000 for p in pages)
            or len(set(pages)) != len(pages) or 0 not in pages):
        raise ValueError("Original PDF source page observations required")
    for key in ("drug", "sponsor", "indication", "source_observation", "limitation"):
        if not isinstance(letter[key], str) or not letter[key].strip() or len(letter[key]) > 1200:
            raise ValueError(f"Invalid nonempty source context: {key}")
    # A model cannot be unlocked by attacker-supplied clearance flags or hashes.
    if (letter["review_cycle"] is not None or letter["source_document_bytes_sha256"] is not None
            or letter["source_document_bytes_retained"] is not False
            or letter["original_publication_date_verified"] is not None
            or letter["first_known_label_public_as_of"] is not None
            or letter["frozen_predecision_features_as_of"] is not None
            or letter["pdufa_target_history_verified"] is not False
            or letter["application_cycle_independently_adjudicated"] is not False
            or letter["original_action_independently_adjudicated"] is not False
            or letter["eligible_for_training"] is not False):
        raise ValueError("Unreviewed original bytes, date clocks or adjudication must remain unset")
    if action == "COMPLETE_RESPONSE" and "Original" not in letter["indication"] and "original" not in letter["limitation"].lower():
        # The chosen CRL has a distinct Original 2; never collapse indications.
        raise ValueError("Original-level CRL differentiation required")
    return app, unit, action, letter["document_reference_id"]


def audit_primary_letter_samples(source, *, as_of: date):
    """Research-only roster; fail completely on conflicts, without any model fit."""
    if type(as_of) is not date:
        raise ValueError("Exact research audit date required")
    if not isinstance(source, dict) or source.get("schema_version") != _SCHEMA:
        raise ValueError("Unsupported source-register schema")
    captured = _date(source.get("compiled_on"))
    if not captured:
        raise ValueError("Source register needs a valid compiled date")
    if as_of < captured:
        return {
            "status": "NOT_AVAILABLE_AT_AS_OF",
            "asOf": as_of.isoformat(),
            "compiledOn": captured.isoformat(),
            "sourceLettersInspected": 0,
            "outcomeObservations": {},
            "independentlyAdjudicatedModelCycles": 0,
            "independentlyBacktestedCases": 0,
            "approvalProbability": None,
            "trainingAuthorized": False,
            "blockedReasons": ["SOURCE_REGISTER_NOT_YET_COMPILED"],
            "records": [],
        }
    if (source.get("collection_policy") !=
            "TWO_PURPOSIVELY_SELECTED_REAL_FDA_ACTION_EXAMPLES_NOT_A_COMPLETE_COHORT"
            or not isinstance(source.get("provenance_caveat"), str)
            or not source["provenance_caveat"].strip()):
        raise ValueError("Representative-cohort warning required")
    letters = source.get("letters")
    if not isinstance(letters, list) or len(letters) != 2:
        raise ValueError("The source pilot must contain exactly two inspected action letters")
    refs = set()
    identities = set()
    ids = set()
    observations = []
    for letter in letters:
        app, unit, action, ref = _check_letter(letter, as_of)
        key = (app, unit, letter["fda_action_date"])
        if ref in refs or key in identities or letter["record_id"] in ids:
            raise ValueError("Duplicated PDF reference or application/submission/action identity")
        refs.add(ref)
        identities.add(key)
        ids.add(letter["record_id"])
        observations.append({
            "recordId": letter["record_id"],
            "applicationId": app,
            "submissionUnit": unit,
            "submissionUnitEvidence": letter["submission_unit_basis"],
            "actionObservedInFDAHostedLetter": action,
            "fdaActionDateInSignedLetter": letter["fda_action_date"],
            "documentReferenceId": ref,
            "officialDocumentUrl": letter["original_document_url"],
            "inspectedPdfPagesZeroIndexed": list(letter["inspected_pages"]),
            "pdfBytesRetained": False,
            "originalDocumentSha256": None,
            "outcomePublicAsOf": None,
            "reviewCycle": None,
            "verifiedPredecisionFeatures": False,
            "sourceStatus": "SIGNED_FDA_LETTER_INSPECTED_RESEARCH_ONLY",
            "modelEligible": False,
        })
    counts = Counter(r["actionObservedInFDAHostedLetter"] for r in observations)
    return {
        "status": "REAL_FDA_LETTER_SAMPLES_RESEARCH_ONLY",
        "asOf": as_of.isoformat(),
        "compiledOn": captured.isoformat(),
        "sourceLettersInspected": len(observations),
        "outcomeObservations": {k: counts.get(k, 0) for k in _ACTIONS},
        "selectionBasis": "PURPOSIVE_NONREPRESENTATIVE",
        "independentlyAdjudicatedModelCycles": 0,
        "independentlyBacktestedCases": 0,
        "approvalProbability": None,
        "trainingAuthorized": False,
        "blockedReasons": [
            "ORIGINAL_PDF_BYTES_NOT_RETAINED_OR_HASHED",
            "FIRST_OUTCOME_PUBLICATION_CLOCK_UNKNOWN",
            "REVIEW_CYCLE_NOT_INDEPENDENTLY_ADJUDICATED",
            "PDUFA_REVISION_HISTORY_UNKNOWN",
            "PREDECISION_FEATURE_SNAPSHOT_MISSING",
            "POPULATION_DENOMINATOR_NOT_VERIFIED",
            "INDEPENDENT_SECOND_SOURCE_REVIEW_MISSING",
        ],
        "records": observations,
    }


def load_primary_letter_samples(*, as_of: date):
    return audit_primary_letter_samples(
        json.loads(_SAMPLE_FILE.read_text(encoding="utf-8")), as_of=as_of
    )
