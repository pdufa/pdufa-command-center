"""Two-clock FDA historical outcome research, without model-label certification.

The FDA *action* date and a publisher's *reported public announcement* date
are independent facts. A release announcing a drug/indication outcome is not
proof that the exact BLA/NDA Original submission/review cycle was publicly
identifiable on that day. No reported date may become a model label directly.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from urllib.parse import urlsplit

_REGISTRY = Path(__file__).parent / "research_sources" / "hop_fda_public_outcome_disclosure_leads.json"
_SCHEMA = "hop-public-outcome-disclosure-leads-v1"
_LETTER_SCHEMA = "hop-fda-primary-action-letter-samples-v1"
_PUBLISHERS = {
    "U.S. FOOD AND DRUG ADMINISTRATION":
        ("FDA_PRESS_RELEASE_SYNDICATED_VIA_PRNEWSWIRE", "www.prnewswire.com"),
    "DECIPHERA PHARMACEUTICALS":
        ("ISSUER_OWN_SITE", "www.deciphera.com"),
    "REGENERON PHARMACEUTICALS":
        ("ISSUER_OWN_SITE", "investor.regeneron.com"),
}
_REQUIRED_EVENT_FIELDS = frozenset({
    "event_id", "related_letter_record_id", "publisher_origin", "channel",
    "source_url", "source_reported_publication_time", "source_observed_on",
    "source_reported_outcome", "drug", "indication_scope", "source_claim",
    "exact_application_id_named_in_release", "exact_original_unit_named_in_release",
    "release_original_bytes_sha256", "independently_adjudicated_as_cycle_label",
})


def _day(value: object) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        day = date.fromisoformat(value)
        return day if day.isoformat() == value else None
    except ValueError:
        return None


def _reported_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if (parsed.tzinfo is None or parsed.utcoffset() is None
                or parsed.utcoffset() != timedelta(hours=-4)
                or parsed.isoformat(timespec="seconds") != value
                or parsed.second != 0):
            return None
        return parsed
    except ValueError:
        return None


def _source_url(url: object, expected_host: str) -> bool:
    if not isinstance(url, str) or any(char.isspace() for char in url):
        return False
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and parsed.hostname == expected_host
                and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443) and parsed.path not in ("", "/")
                and not parsed.query and not parsed.fragment)
    except ValueError:
        return False


def _no_duplicate_json_fields(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"Duplicate public disclosure JSON field: {key}")
        obj[key] = value
    return obj


def _blocked_snapshot(cutoff: date, compiled: date) -> dict:
    return {
        "status": "SOURCE_REGISTER_NOT_AVAILABLE_AT_AS_OF",
        "asOf": cutoff.isoformat(),
        "researchCompiledOn": compiled.isoformat(),
        "totalPublicReleaseLeads": 0,
        "publicReleaseLeadsByLetter": {},
        "exactUnitPublicMappingVerified": False,
        "fdaLetterOriginalPublicationDateVerified": False,
        "independentlyVerifiedModelLabels": 0,
        "independentHistoricalBacktests": 0,
        "approvalProbability": None,
        "trainingAuthorized": False,
        "blockers": ["PUBLIC_DISCLOSURE_RESEARCH_REGISTER_NOT_YET_COMPILED"],
    }


def audit_public_outcome_disclosure_leads(
    registry: dict, letter_manifest: dict, *, as_of: date,
) -> dict:
    """Validate source-publication leads paired to exact FDA letter metadata.

    The register is captured retrospectively; dates are *source-reported* page
    timestamps and never imply an independently verified first-publication
    time, exact original-submission association, or authorizing training label.
    """
    if type(as_of) is not date:
        raise ValueError("Exact research cutoff date required")
    if not isinstance(registry, dict) or registry.get("schema_version") != _SCHEMA:
        raise ValueError("Unsupported public disclosure source schema")
    compiled = _day(registry.get("research_compiled_on"))
    if compiled is None:
        raise ValueError("Public disclosure source register has no valid compiled date")
    if as_of < compiled:
        return _blocked_snapshot(as_of, compiled)
    if (registry.get("research_status") !=
            "PUBLIC_DISCLOSURE_SOURCE_LEADS_ONLY_NOT_MODEL_LABELS"
            or registry.get("collection_policy") !=
            "PURPOSIVELY_SELECTED_TWO_ACTION_LETTER_SAMPLES_NOT_COMPLETE_DENOMINATOR"
            or not isinstance(registry.get("notes"), str)
            or not registry["notes"].strip()):
        raise ValueError("Nonrepresentative source/clock warning required")
    if not isinstance(letter_manifest, dict) or letter_manifest.get("schema_version") != _LETTER_SCHEMA:
        raise ValueError("Matching original FDA action-letter manifest required")
    letters = letter_manifest.get("letters")
    if not isinstance(letters, list) or len(letters) != 2:
        raise ValueError("Expected two original FDA letter source records")
    letter_index = {}
    for letter in letters:
        if not isinstance(letter, dict) or not isinstance(letter.get("record_id"), str):
            raise ValueError("Invalid FDA letter source identity")
        key = letter["record_id"]
        if key in letter_index:
            raise ValueError("Duplicate FDA letter exact identity")
        letter_index[key] = letter
    events = registry.get("events")
    if not isinstance(events, list) or len(events) != 3:
        raise ValueError("Expected three publisher source observations")
    by_case: dict[str, list[dict]] = defaultdict(list)
    seen = set()
    seen_url = set()
    for event in events:
        if not isinstance(event, dict) or set(event) != _REQUIRED_EVENT_FIELDS:
            raise ValueError("Unexpected public disclosure event schema")
        ident = event["event_id"]
        if not isinstance(ident, str) or not ident or ident in seen:
            raise ValueError("Duplicate/invalid source event ID")
        seen.add(ident)
        link = event["related_letter_record_id"]
        if link not in letter_index:
            raise ValueError("Source event cannot transfer an outcome to an unrecognized FDA letter")
        original = letter_index[link]
        publisher = event["publisher_origin"]
        if publisher not in _PUBLISHERS:
            raise ValueError("Unrecognized publisher origin")
        if event["source_url"] in seen_url:
            raise ValueError("Duplicate URL cannot inflate independent source count")
        channel, host = _PUBLISHERS[publisher]
        if event["channel"] != channel or not _source_url(event["source_url"], host):
            raise ValueError("Publisher channel/official URL mismatch")
        seen_url.add(event["source_url"])
        announced = _reported_at(event["source_reported_publication_time"])
        observed = _day(event["source_observed_on"])
        signed = _day(original.get("fda_action_date"))
        if (announced is None or observed is None or signed is None
                or announced.date() < signed or announced.date() > observed
                or observed > as_of or observed < compiled):
            raise ValueError("Public source time/capture chronologies conflict with FDA action")
        if (event["source_reported_outcome"] != original.get("action")
                or event["drug"].casefold() != original.get("drug", "").casefold()
                or not isinstance(event["source_claim"], str)
                or not 15 <= len(event["source_claim"].strip()) <= 800
                or not isinstance(event["indication_scope"], str)
                or not 12 <= len(event["indication_scope"].strip()) <= 800):
            raise ValueError("Source outcome, drug identity, or evidence claim mismatch")
        # The source does NOT name an exact FDA review cycle. A caller may not
        # self-certify that retrospectively inferred identification.
        if (event["exact_application_id_named_in_release"] is not False
                or event["exact_original_unit_named_in_release"] is not False
                or event["release_original_bytes_sha256"] is not None
                or event["independently_adjudicated_as_cycle_label"] is not False):
            raise ValueError("Source-level publicity must not promote an exact cycle label")
        by_case[link].append({
            "eventId": ident,
            "publisherOrigin": publisher,
            "publicationChannel": channel,
            "sourceUrl": event["source_url"],
            "reportedPublishedAt": announced.isoformat(timespec="seconds"),
            "reportedPublicationDate": announced.date().isoformat(),
            "retrievedAndInspectedOn": observed.isoformat(),
            "outcomeReport": event["source_reported_outcome"],
            "disclosedIndicationScope": event["indication_scope"],
            "sourceClaim": event["source_claim"],
            "exactApplicationAndOriginalUnitNamed": False,
            "originalReleaseBytesRetained": False,
            "eligibleAsExactReviewCycleLabel": False,
        })
    if set(by_case) != set(letter_index):
        raise ValueError("Both FDA source letters require public-disclosure source leads")
    return {
        "status": "PUBLISHER_REPORTED_PUBLIC_OUTCOME_LEADS_RESEARCH_ONLY",
        "asOf": as_of.isoformat(),
        "researchCompiledOn": compiled.isoformat(),
        "totalPublicReleaseLeads": len(events),
        "publicReleaseLeadsByLetter": {
            key: {
                "signedFdaActionDate": letter_index[key]["fda_action_date"],
                "earliestDateAmongSelectedReleasePages": min(
                    row["reportedPublicationDate"] for row in matches),
                "earliestActualPublicOutcomeDateIndependentlyVerified": None,
                "distinctPublishingOrigins": len({
                    row["publisherOrigin"] for row in matches}),
                "releaseObservations": sorted(
                    matches, key=lambda row: row["reportedPublishedAt"]),
                "FDAoriginalLetterPublicationDate": None,
                "exactFDAapplicationOriginalUnitPubliclyMapped": False,
                "eligibleAsVerifiedHistoricalLabel": False,
            } for key, matches in sorted(by_case.items())
        },
        "exactUnitPublicMappingVerified": False,
        "fdaLetterOriginalPublicationDateVerified": False,
        "independentlyVerifiedModelLabels": 0,
        "independentHistoricalBacktests": 0,
        "approvalProbability": None,
        "trainingAuthorized": False,
        "blockers": [
            "EARLIEST_PUBLIC_LABEL_DATE_NOT_INDEPENDENTLY_CERTIFIED",
            "FDA_EXACT_ORIGINAL_UNIT_NOT_NAMED_IN_RELEASES",
            "SIGNED_FDA_LETTER_PUBLICATION_DATE_UNKNOWN",
            "NO_INDEPENDENT_REVIEW_CYCLE_ADJUDICATION",
            "NO_CONSECUTIVE_HISTORICAL_DENOMINATOR",
            "NO_FROZEN_PREDECISION_FEATURES",
            "ORIGINAL_WEB_RELEASE_BYTES_NOT_ARCHIVED",
        ],
    }


def load_public_outcome_disclosure_leads(letter_manifest: dict, *, as_of: date) -> dict:
    source = json.loads(
        _REGISTRY.read_text(encoding="utf-8"),
        object_pairs_hook=_no_duplicate_json_fields,
    )
    return audit_public_outcome_disclosure_leads(source, letter_manifest, as_of=as_of)


def load_historical_fda_public_outcome_packet(*, as_of: date) -> dict:
    """Combine distinct regulator action and publisher-disclosure clocks safely."""
    from .hop_primary_action_letter_samples import (
        _SAMPLE_FILE, audit_primary_letter_samples,
    )
    original_letters = json.loads(
        _SAMPLE_FILE.read_text(encoding="utf-8"),
        object_pairs_hook=_no_duplicate_json_fields,
    )
    action_audit = audit_primary_letter_samples(original_letters, as_of=as_of)
    disclosure = load_public_outcome_disclosure_leads(
        original_letters, as_of=as_of,
    )
    from .hop_fda_original_capture_receipts import load_real_fda_capture_receipts
    pdf_receipts = load_real_fda_capture_receipts(as_of=as_of)
    from .hop_fda_approval_survivor_sequences import load_approved_survivor_sequences
    historical_sequences = load_approved_survivor_sequences(as_of=as_of)
    return {
        "mode": "READ_ONLY_HISTORICAL_FDA_ACTION_AND_DISCLOSURE_RESEARCH",
        "asOf": as_of.isoformat(),
        "actionLetterResearch": action_audit,
        "publicDisclosureResearch": disclosure,
        "originalPdfCaptureResearch": pdf_receipts,
        "approvedSurvivorSequenceResearch": historical_sequences,
        "independentModelEligibleCycles": 0,
        "independentHistoricalBacktests": 0,
        "accuracy": None,
        "approvalProbability": None,
        "predictionStatus": "INSUFFICIENT_EVIDENCE",
        "trainingAuthorized": False,
        "databaseWritten": False,
        "spreadsheetWritten": False,
        "tradeAuthorized": False,
    }
