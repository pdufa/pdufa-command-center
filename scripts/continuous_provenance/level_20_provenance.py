"""Research-only source metadata gate; never validates clinical findings."""
from datetime import date
import re
from urllib.parse import urlsplit

LEVEL = 20
LEVEL_NAME = 'Scientific Red-Team Adjudication'
REQUIRED_FIELDS = ('red_team_challenges', 'adjudication_record', 'unresolved_risks')
NCT = re.compile(r"NCT[0-9]{8}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def inspect_metadata(record: dict) -> dict:
    """Identify missing/invalid receipts; cannot certify a source or outcome."""
    if not isinstance(record, dict):
        raise ValueError("Metadata record must be an object")
    nct = record.get("nct")
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Exact NCT identifier is required")
    phase = record.get("trial_phase")
    if phase not in (1, 2, 3, 4) or type(phase) is not int:
        raise ValueError("Use the actually documented trial phase")
    cutoff = record.get("knowledge_cutoff")
    try:
        as_of = date.fromisoformat(cutoff) if isinstance(cutoff, str) else None
    except ValueError:
        as_of = None
    if as_of is None or as_of.isoformat() != cutoff:
        raise ValueError("An exact knowledge cutoff date is required")
    observed = record.get("source_metadata", {})
    if not isinstance(observed, dict):
        raise ValueError("Source metadata must be keyed by evidence field")
    missing, invalid = [], []
    for key in REQUIRED_FIELDS:
        receipt = observed.get(key)
        if receipt is None:
            missing.append(key)
            continue
        if not isinstance(receipt, dict):
            invalid.append(key)
            continue
        url = receipt.get("url")
        try:
            parsed = urlsplit(url) if isinstance(url, str) else None
            good_url = (parsed is not None and parsed.scheme == "https"
                        and bool(parsed.hostname) and not parsed.username
                        and not parsed.password and not parsed.fragment)
        except ValueError:
            good_url = False
        excerpt = receipt.get("excerpt")
        digest = receipt.get("sha256")
        date_str = receipt.get("published_on")
        try:
            published = date.fromisoformat(date_str) if isinstance(date_str, str) else None
        except ValueError:
            published = None
        if (not good_url or not isinstance(excerpt, str)
                or len(excerpt.strip()) < 20
                or not isinstance(digest, str) or not DIGEST.fullmatch(digest)
                or published is None or published.isoformat() != date_str
                or published > as_of):
            invalid.append(key)
    return {
        "nct": nct, "trial_phase": phase, "level": LEVEL,
        "status": "MANUAL_SOURCE_REVIEW_REQUIRED",
        "missing_receipts": missing, "invalid_receipts": invalid,
        "source_facts_independently_verified": False,
        "scientific_stage_complete": False,
        "approval_probability": None, "clinical_score": None,
        "fda_prediction": None,
    }
