"""Fail-closed provenance checks for proposed historical FDA outcome cohorts.

A declaration of completeness is never itself proof of completeness.
This audit produces review blockers only; it cannot authorize model fitting.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import date
from urllib.parse import urlparse


def audit_cohort_manifest(manifest: Mapping) -> dict:
    """Inspect declared cohort coverage without asserting independent verification."""
    blockers = []
    required = ("cohort_id", "population_definition", "start_date", "end_date",
                "source_url", "expected_review_cycles", "observed_review_cycles",
                "independent_reviewer", "source_retrieved_on")
    if not isinstance(manifest, Mapping):
        return {"status": "BLOCKED", "blockers": ["manifest_not_object"],
                "independently_verified": False, "model_eligible": False}
    for field in required:
        if field not in manifest or manifest[field] is None or (
                isinstance(manifest[field], str) and not manifest[field].strip()):
            blockers.append("missing_" + field)
    if blockers:
        return {"status": "BLOCKED", "blockers": sorted(blockers),
                "independently_verified": False, "model_eligible": False}
    parsed = urlparse(str(manifest["source_url"]))
    if parsed.scheme != "https" or parsed.hostname not in (
            "fda.gov", "www.fda.gov", "accessdata.fda.gov"):
        blockers.append("source_not_official_fda")
    try:
        start = date.fromisoformat(manifest["start_date"])
        end = date.fromisoformat(manifest["end_date"])
        retrieved = date.fromisoformat(manifest["source_retrieved_on"])
        if not start <= end <= retrieved <= date.today():
            blockers.append("invalid_coverage_dates")
    except (ValueError, TypeError):
        blockers.append("invalid_coverage_dates")
    expected = manifest["expected_review_cycles"]
    observed = manifest["observed_review_cycles"]
    if (type(expected) is not int or type(observed) is not int
            or expected <= 0 or observed < 0 or observed != expected):
        blockers.append("denominator_not_reconciled")
    if manifest.get("independent_review_complete") is not True:
        blockers.append("independent_review_not_confirmed")
    if manifest.get("approval_and_crl_ascertainment_complete") is not True:
        blockers.append("outcome_ascertainment_not_confirmed")
    # Even a fully populated self-declared manifest is insufficient proof.
    blockers.append("external_source_verification_required")
    return {"status": "BLOCKED", "blockers": sorted(set(blockers)),
            "independently_verified": False, "model_eligible": False}
