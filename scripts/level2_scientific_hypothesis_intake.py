#!/usr/bin/env python3
"""Level 2 scientific-hypothesis intake: source-bound, research-only.

This is an *input readiness* contract, not an AI assessment, hypothesis
validation, clinical efficacy verdict, or FDA prediction. It does not require
Phase 3 evidence for early-phase trials. It makes no network calls or writes.
"""
from __future__ import annotations

from datetime import date
import re
from urllib.parse import urlsplit

NCT = re.compile(r"NCT[0-9]{8}\Z")
FIELDS = (
    "mechanism_claim",
    "biological_rationale",
    "expected_observation",
    "alternative_explanation",
    "potential_refutation",
)
MAX_SOURCES = 25


def _date(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("A dated original-source record must use YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Impossible document or as-of date") from exc
    if parsed.isoformat() != value:
        raise ValueError("Noncanonical evidence date")
    return parsed


def _url(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("https://") or any(x.isspace() for x in value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        return (
            parsed.scheme == "https" and "." in host and not host.endswith(".local")
            and host.lower() != "localhost" and not parsed.username
            and not parsed.password and not parsed.fragment
            and parsed.port in (None, 443)
        )
    except ValueError:
        return False


def prepare_hypothesis_review(record: object, as_of: str) -> dict:
    """Validate source metadata, preserve uncertainty and require human review.

    Input claim text is *untrusted* and copied as a proposal, not endorsed.
    """
    cutoff = _date(as_of)
    if not isinstance(record, dict):
        raise ValueError("Expected one exact-trial hypothesis record")
    nct = record.get("nct")
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Exact eight-digit ASCII NCT identity required")
    for field in ("scientifically_verified", "approval_probability", "fda_prediction", "adjudication"):
        if record.get(field) is not None:
            raise ValueError("Unreviewed Level 2 intake cannot contain verdicts")
    claims: dict[str, str] = {}
    missing: list[str] = []
    for field in FIELDS:
        value = record.get(field)
        if value is None or value == "":
            missing.append(field)
            continue
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 2500:
            raise ValueError("Malformed hypothesis text: " + field)
        claims[field] = value.strip()

    sources = record.get("sources", [])
    if not isinstance(sources, list) or len(sources) > MAX_SOURCES:
        raise ValueError("Hypothesis sources must be a bounded list")
    seen = set()
    observations = []
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("Invalid source observation")
        address = item.get("url")
        if not _url(address):
            raise ValueError("Invalid primary-source URL")
        published, retrieved = _date(item.get("published_at")), _date(item.get("retrieved_at"))
        if not published <= retrieved <= cutoff:
            raise ValueError("Future, after-cutoff or contradictory source timing")
        excerpt = item.get("excerpt")
        if not isinstance(excerpt, str) or not 1 <= len(excerpt.strip()) <= 2500:
            raise ValueError("Missing source excerpt")
        identity = (address, published.isoformat())
        if identity in seen:
            raise ValueError("Duplicate source receipt")
        seen.add(identity)
        observations.append({
            "url": address,
            "published_at": published.isoformat(),
            "retrieved_at": retrieved.isoformat(),
            "excerpt": excerpt.strip(),
            "status": "SOURCE_REPORTED_UNADJUDICATED",
        })

    if not observations:
        missing.append("source_documentation")
    ready_for_review = not missing
    return {
        "level": 2,
        "nct": nct,
        "as_of": cutoff.isoformat(),
        "hypothesis": claims,
        "sources": observations,
        "missing_for_review": missing,
        "status": (
            "DOCUMENTED_HYPOTHESIS_AWAITING_REVIEW"
            if ready_for_review else "INCOMPLETE_HYPOTHESIS_AWAITING_EVIDENCE"
        ),
        "source_documentation_complete": bool(observations),
        "scientifically_verified": False,
        "clinical_efficacy_established": False,
        "fda_prediction": None,
        "approval_probability": None,
        "score": None,
        "requires_independent_scientific_review": True,
        "assessment_complete": False,
        "production_modified": False,
    }
