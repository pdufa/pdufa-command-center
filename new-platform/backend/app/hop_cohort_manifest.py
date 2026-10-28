"""Fail-closed provenance checks for proposed historical FDA outcome cohorts.

A declaration of completeness is never itself proof of completeness.
This audit produces review blockers only; it cannot authorize model fitting.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date

from .hop_outcomes_import import APPLICATION_PATTERN, _date, _fda_url

DISPOSITIONS = (
    "APPROVED", "COMPLETE_RESPONSE", "WITHDRAWN", "DELAYED",
    "REFUSE_TO_FILE", "UNRESOLVED", "OUT_OF_SCOPE",
)


def _identity(member):
    if not isinstance(member, Mapping):
        return None, ["member_not_object"]
    issues = []
    app = member.get("application_id")
    if not isinstance(app, str) or not APPLICATION_PATTERN.fullmatch(app.strip().upper()):
        issues.append("invalid_application_id")
    cycle = member.get("review_cycle")
    if type(cycle) is not int or cycle < 1:
        issues.append("invalid_review_cycle")
    if issues:
        return None, issues
    return (app.strip().upper().replace("-", ""), cycle), []


def _members(value):
    """Reconcile identity claims before considering observed dispositions."""
    if value is None:
        return None, Counter(), Counter(), 0
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None, Counter(), Counter({"members_not_sequence": 1}), 0
    identities = Counter()
    issues = Counter()
    invalid = 0
    for row in value:
        key, errors = _identity(row)
        if errors:
            invalid += 1
            issues.update(errors)
        else:
            identities[key] += 1
    return list(value), identities, issues, invalid


def _keys(keys):
    return [{"application_id": key[0], "review_cycle": key[1]} for key in sorted(keys)]


def _duplicates(counts):
    return [dict(identity, count=counts[(identity["application_id"], identity["review_cycle"])])
            for identity in _keys(key for key, count in counts.items() if count > 1)]


def _audit_roster(expected_members, observed_members):
    expected, expected_keys, expected_issues, invalid_expected = _members(expected_members)
    observed, observed_keys, observed_issues, invalid_observed = _members(observed_members)
    blockers = []
    if expected_members is None or observed_members is None:
        blockers.append("exact_roster_required")
    if expected is not None and not expected:
        blockers.append("empty_expected_roster")
    if expected_issues:
        blockers.append("invalid_expected_roster")
    if observed_issues:
        blockers.append("invalid_observed_roster")
    missing = expected_keys.keys() - observed_keys.keys()
    extra = observed_keys.keys() - expected_keys.keys()
    if missing:
        blockers.append("missing_roster_members")
    if extra:
        blockers.append("unexpected_roster_members")
    if any(count > 1 for count in expected_keys.values()):
        blockers.append("duplicate_expected_roster_identity")
    if any(count > 1 for count in observed_keys.values()):
        blockers.append("duplicate_observed_roster_identity")
    dispositions = Counter()
    # Row-level counts retain even invalid/duplicate claims. Cycle counts below
    # never turn these claims into additional binary observations.
    disposition_rows = Counter()
    for member in observed or []:
        key, _ = _identity(member)
        if not isinstance(member, Mapping):
            continue
        disposition = member.get("disposition")
        if disposition is None or disposition == "":
            observed_issues["missing_disposition"] += 1
            continue
        if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
            observed_issues["invalid_disposition"] += 1
            continue
        disposition_rows[disposition] += 1
        if disposition == "OUT_OF_SCOPE":
            reason = member.get("exclusion_reason")
            if not isinstance(reason, str) or not reason.strip():
                observed_issues["missing_exclusion_reason"] += 1
                continue
        # Only a unique claim matched to one unique expected member contributes
        # a cohort disposition. Extra or repeated identities stay visible above.
        if key is not None and observed_keys[key] == 1 and expected_keys[key] == 1:
            dispositions[disposition] += 1
    if observed_issues:
        blockers.append("invalid_observed_roster")
    if disposition_rows["UNRESOLVED"]:
        blockers.append("unresolved_roster_members")
    return {
        "status": "BLOCKED" if blockers else "RECONCILED_METADATA_ONLY",
        "expected_member_rows": len(expected) if expected is not None else None,
        "observed_member_rows": len(observed) if observed is not None else None,
        "expected_unique_identities": len(expected_keys),
        "observed_unique_identities": len(observed_keys),
        "missing_identities": _keys(missing),
        "extra_identities": _keys(extra),
        "duplicate_expected_identities": _duplicates(expected_keys),
        "duplicate_observed_identities": _duplicates(observed_keys),
        "invalid_expected_identity_rows": invalid_expected,
        "invalid_observed_identity_rows": invalid_observed,
        "invalid_observed_disposition_rows": sum(observed_issues[key] for key in (
            "missing_disposition", "invalid_disposition", "missing_exclusion_reason")),
        "expected_issue_counts": dict(sorted(expected_issues.items())),
        "observed_issue_counts": dict(sorted(observed_issues.items())),
        "disposition_row_counts": {key: disposition_rows[key] for key in DISPOSITIONS},
        "disposition_counts": {key: dispositions[key] for key in DISPOSITIONS},
        "disposition_count_basis": "UNIQUE_IDENTITIES_MATCHED_TO_EXPECTED_ROSTER",
        "binary_disposition_cycles": dispositions["APPROVED"] + dispositions["COMPLETE_RESPONSE"],
        "metadata_only": True,
        "model_eligible_records": 0,
        "probability": None,
    }, blockers


def audit_cohort_manifest(manifest: Mapping, *, expected_members=None,
                          observed_members=None, as_of: date | None = None) -> dict:
    """Inspect declared cohort coverage without asserting independent verification."""
    cutoff = date.today() if as_of is None else as_of
    if type(cutoff) is not date:
        raise ValueError("as_of must be a date")
    roster, blockers = _audit_roster(expected_members, observed_members)
    # A roster reconciles declarations only, never the original source truth.
    blockers.append("external_source_verification_required")
    required = ("cohort_id", "population_definition", "start_date", "end_date",
                "source_url", "expected_review_cycles", "observed_review_cycles",
                "independent_reviewer", "source_retrieved_on")
    if not isinstance(manifest, Mapping):
        manifest = {}
        blockers.append("manifest_not_object")
    for field in required:
        if field not in manifest or manifest[field] is None or (
                isinstance(manifest[field], str) and not manifest[field].strip()):
            blockers.append("missing_" + field)
    for field in ("cohort_id", "population_definition", "independent_reviewer"):
        if field in manifest and not isinstance(manifest[field], str):
            blockers.append("invalid_" + field)
    if not isinstance(manifest.get("source_url"), str) or not _fda_url(manifest["source_url"]):
        blockers.append("source_not_official_fda")
    try:
        start = _date(manifest.get("start_date"))
        end = _date(manifest.get("end_date"))
        retrieved = _date(manifest.get("source_retrieved_on"))
        if not start <= end <= retrieved <= cutoff:
            blockers.append("invalid_coverage_dates")
    except (ValueError, TypeError):
        blockers.append("invalid_coverage_dates")
    expected = manifest.get("expected_review_cycles")
    observed = manifest.get("observed_review_cycles")
    if (type(expected) is not int or type(observed) is not int
            or expected <= 0 or observed < 0 or observed != expected):
        blockers.append("denominator_not_reconciled")
    if roster["expected_member_rows"] is not None and (
            type(expected) is not int or expected != roster["expected_member_rows"]
            or expected != roster["expected_unique_identities"]):
        blockers.append("expected_roster_count_mismatch")
    if roster["observed_member_rows"] is not None and (
            type(observed) is not int or observed != roster["observed_member_rows"]
            or observed != roster["observed_unique_identities"]):
        blockers.append("observed_roster_count_mismatch")
    if any(reason in blockers for reason in (
            "expected_roster_count_mismatch", "observed_roster_count_mismatch")):
        roster["status"] = "BLOCKED"
    if manifest.get("independent_review_complete") is not True:
        blockers.append("independent_review_not_confirmed")
    if manifest.get("approval_and_crl_ascertainment_complete") is not True:
        blockers.append("outcome_ascertainment_not_confirmed")
    return {"status": "BLOCKED", "blockers": sorted(set(blockers)),
            "roster_audit": roster, "as_of": cutoff.isoformat(),
            "independently_verified": False, "model_eligible": False}
