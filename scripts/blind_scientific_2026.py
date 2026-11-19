#!/usr/bin/env python3
"""Offline historical execution of the installed scientific assessment levels."""

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit

from blind_six_levels_2026 import canonical_digest, load_csv, write_new_lock

BACKEND = Path(__file__).resolve().parents[1] / "new-platform" / "backend"
sys.path.insert(0, str(BACKEND))
from app.phase_first_intake import phase_first_intake
from app.scientific_levels_two_to_six import LEVELS as CONTRACTS
from app.scientific_levels_two_to_six import assess_levels_two_to_six

PROTOCOL = "CANONICAL_HISTORICAL_FDA_DIRECTION_V1"
RULE_SET = "SCIENTIFIC_L01_L06_HISTORICAL_DIRECTION_V1"
LEVELS = tuple(f"L{number:02d}" for number in range(1, 7))
EVENT_FIELDS = {
    "event_id", "application_number", "review_cycle", "drug", "indication", "decision_date",
}
OPTIONAL_EVENT_FIELDS = {"ticker"}
PACKAGE_FIELDS = {
    "event_id", "application_number", "review_cycle", "outcome_exposure",
    "trial_set_rationale", "trials",
}
TRIAL_FIELDS = {"nct_id", "linkage", "registry", "reviews"}
RECEIPT_FIELDS = {
    "source", "sourceDate", "sourceVersionUrl", "sourceVersionDate",
    "sourceRetrievedAt", "sourceVerifiedAt", "sourceVerifiedBy", "reviewedAt",
    "reviewerId", "rationale",
}
REGISTRY_FIELDS = {"document", "documentSha256", "sourceVersionUrl",
                   "sourceVersionDate", "sourceRetrievedAt"}
UNKNOWN_FIELDS = {"status", "reviewedAt", "reviewerId", "rationale"}
REVIEW_FIELDS = RECEIPT_FIELDS | {
    "status", "judgment", "documentType", "evidenceExcerpt", "sourceVerificationMethod",
    "material_blocker",
}
CRITERIA = {
    f"{number}.{criterion}" for number, (_, criteria) in CONTRACTS.items()
    for criterion in criteria
}
BLOCKER_CRITERIA = {
    2: {"randomizationAndControl", "blindingAndBias"},
    3: {"primaryEndpointResults", "statisticalAnalysisPlan", "multiplicityAdjustment"},
    4: {"benefitRiskInterpretation"},
    5: {"clinicalMeaningfulness", "subgroupGeneralizability"},
    6: {"agencyInteractions", "manufacturingReadiness", "labelingAndRiskMitigation"},
}
DIRECTIONS = {"APPROVE", "CRL", "ABSTAIN"}
OUTCOME_LABELS = {
    "actualoutcome", "fdaoutcome", "fdaaction", "decisionoutcome", "actualdecision",
    "actualaction", "outcome", "outcomelabel", "prediction", "correct", "crl",
}


def strict_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"Expected YYYY-MM-DD, got {value!r}")
    return date.fromisoformat(value)


def require_fields(record, fields, optional=()):
    if not isinstance(record, dict) or fields - record.keys() or record.keys() - fields - set(optional):
        raise ValueError(f"Expected fields {', '.join(sorted(fields))}")


def require_text(record, fields):
    if any(not isinstance(record[k], str) or not record[k].strip() for k in fields):
        raise ValueError(f"Missing required text among {', '.join(sorted(fields))}")


def dated_review(record):
    require_text(record, ("reviewerId", "rationale"))
    reviewed = strict_day(record["reviewedAt"])
    if reviewed > date.today():
        raise ValueError("Evidence review date is in the future")
    return reviewed


def secure_url(value):
    url = urlsplit(value)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or any(char.isspace() for char in value)):
        raise ValueError("Evidence requires a secure source URL")
    return url


def validate_receipt(record, cutoff):
    require_text(record, RECEIPT_FIELDS)
    secure_url(record["source"])
    secure_url(record["sourceVersionUrl"])
    initial, version, retrieved, verified = (
        strict_day(record[key]) for key in (
            "sourceDate", "sourceVersionDate", "sourceRetrievedAt", "sourceVerifiedAt",
        )
    )
    reviewed = dated_review(record)
    if not initial <= version <= cutoff or not version <= retrieved <= verified <= reviewed:
        raise ValueError("Evidence version/retrieval/verification/review chronology failed")
    if retrieved > cutoff and record["source"] == record["sourceVersionUrl"]:
        # A DOI, numbered docket document or dated issuer release can itself be
        # the immutable locator. Require an explicit original-document check.
        if record.get("sourceVerificationMethod") == "REGISTRY_RECORD_REVIEW":
            raise ValueError("Mutable post-cutoff registry review requires a frozen version locator")


def validate_registry(record, nct, cutoff):
    require_fields(record, REGISTRY_FIELDS)
    locator = secure_url(record["sourceVersionUrl"])
    api = f"/api/v2/studies/{nct}"
    history = f"/study/{nct}"
    query = parse_qs(locator.query)
    pinned_revision = (
        locator.path == history and query.get("tab") == ["history"]
        and len(query.get("a", [])) == 1 and query["a"][0].isascii()
        and query["a"][0].isdigit()
    )
    if (locator.hostname not in {"clinicaltrials.gov", "www.clinicaltrials.gov"}
            or not (locator.path == api or pinned_revision)):
        raise ValueError("Registry locator is not an exact official trial version")
    document = record["document"]
    if canonical_digest(document) != record["documentSha256"]:
        raise ValueError("Registry document hash mismatch")
    protocol = document["protocolSection"]
    if protocol["identificationModule"]["nctId"] != nct:
        raise ValueError("Registry document does not match the pivotal NCT")
    status = protocol["statusModule"]
    metadata_date = strict_day(status["lastUpdatePostDateStruct"]["date"])
    version_date = strict_day(record["sourceVersionDate"])
    retrieval_date = strict_day(record["sourceRetrievedAt"])
    if (metadata_date != version_date or not version_date <= cutoff
            or not version_date <= retrieval_date <= date.today()):
        raise ValueError("Registry version is not eligible at the historical cutoff")
    if retrieval_date > cutoff and not pinned_revision:
        raise ValueError("Post-cutoff retrieval requires a pinned registry revision")
    return {
        "nct_id": nct,
        "last_update_posted": {"date": version_date.isoformat()},
        "phases": protocol["designModule"].get("phases"),
        "status": status["overallStatus"],
        "study_design": protocol["designModule"],
        "primary_outcomes": protocol["outcomesModule"].get("primaryOutcomes"),
    }


def reject_outcome_fields(value):
    """Reject structural outcome-label fields in evidence before assessment."""
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized in OUTCOME_LABELS:
                raise ValueError(f"Outcome-bearing evidence field prohibited: {key}")
            reject_outcome_fields(item)
    elif isinstance(value, list):
        for item in value:
            reject_outcome_fields(item)


def execute_trial(trial, cutoff):
    require_fields(trial, TRIAL_FIELDS)
    nct = trial["nct_id"]
    if not isinstance(nct, str) or not re.fullmatch(r"NCT[0-9]{8}", nct):
        raise ValueError("Historical clinical execution requires an exact pivotal NCT")
    linkage = trial["linkage"]
    require_fields(linkage, RECEIPT_FIELDS)
    validate_receipt(linkage, cutoff)
    registry = validate_registry(trial["registry"], nct, cutoff)
    # The date parameter is source availability for an immutable version.
    # Preserve the real later retrieval date independently in the recorded rating.
    intake = phase_first_intake(
        registry, cutoff=cutoff.isoformat(), registry_checked=trial["registry"]["sourceVersionDate"]
    )
    intake["registryVersionAvailableAt"] = intake.pop("registryCheckedAt")
    intake["registryRetrievedAt"] = trial["registry"]["sourceRetrievedAt"]

    reviews = trial["reviews"]
    require_fields(reviews, CRITERIA)
    eligible = {}
    for key, review in reviews.items():
        if review.get("status") == "UNKNOWN":
            require_fields(review, UNKNOWN_FIELDS)
            dated_review(review)
            continue
        require_fields(review, REVIEW_FIELDS)
        if review["status"] != "REVIEWED" or type(review["material_blocker"]) is not bool:
            raise ValueError(f"{nct} {key}: invalid documented review status")
        if (review["judgment"] not in {"SUPPORTS", "CONCERNS", "INCONCLUSIVE"}
                or review["material_blocker"] and review["judgment"] != "CONCERNS"):
            raise ValueError(f"{nct} {key}: invalid review judgment or material blocker")
        validate_receipt(review, cutoff)
        eligible[key] = {**review, "nctId": nct, "sourceVerified": True}

    rating = assess_levels_two_to_six(
        intake, trial_id=nct, evidence=eligible, historical_versions=True
    )
    for number, level in rating.items():
        if level["rejectedCriteria"]:
            reasons = level["rejectionReasons"]
            raise ValueError(f"{nct} L{number.zfill(2)} evidence rejected: {reasons}")
    return {"nct_id": nct, "L01": intake, **{
        f"L{int(k):02d}": v for k, v in rating.items()
    }}


def decide_direction(number, assessments, trials):
    """Produce a research direction from accepted scientific judgments only."""
    level = LEVELS[number - 1]
    if any(item["L01"]["executionStatus"] != "INTAKE_ONLY" for item in assessments):
        return "ABSTAIN", "unverified_trial_phase_or_status", []
    if number == 1:
        return "ABSTAIN", "trial_identity_alone_is_not_directional_evidence", []

    _, criteria = CONTRACTS[number]
    accepted = {}
    missing = []
    for criterion in criteria:
        entries = []
        for rating, trial in zip(assessments, trials, strict=True):
            state = rating[level]["criteria"][criterion]
            key = f"{number}.{criterion}"
            if state not in {"SUPPORTS", "CONCERNS"}:
                missing.append(f"{trial['nct_id']}:{criterion}:{state}")
                continue
            source = trial["reviews"][key]
            entries.append((state, source["material_blocker"], trial["nct_id"]))
        accepted[criterion] = entries
    if missing:
        return "ABSTAIN", "incomplete_or_inconclusive_level_evidence", missing

    # A signal contradicted by a linked pivotal trial does not establish the
    # application's direction. Missing/inconclusive was handled above.
    conflicted = [
        criterion for criterion, entries in accepted.items()
        if len({entry[0] for entry in entries}) > 1
    ]
    if conflicted:
        return "ABSTAIN", "mixed_pivotal_trial_findings", conflicted
    blockers = [
        f"{nct}:{criterion}" for criterion, entries in accepted.items()
        if criterion in BLOCKER_CRITERIA[number]
        for state, material, nct in entries if state == "CONCERNS" and material
    ]
    if blockers:
        return "CRL", "documented_material_concern_in_decisive_criterion", blockers
    concerns = [
        f"{nct}:{criterion}" for criterion, entries in accepted.items()
        for state, _, nct in entries if state == "CONCERNS"
    ]
    if concerns:
        return "ABSTAIN", "concerns_without_a_prespecified_material_blocker", concerns
    if number == 2:
        return "ABSTAIN", "trial_design_alone_is_not_supportive_of_approval", []
    return "APPROVE", "all_level_criteria_supportive_across_pivotal_trials", list(criteria)


def make_lock(events, packages, cutoff_days):
    if not 1 <= cutoff_days or not events:
        raise ValueError("A nonempty reconciled manifest and a positive cutoff lead time are required")
    if not isinstance(packages, list):
        raise ValueError("Expected a list of outcome-unexposed case evidence packages")
    reject_outcome_fields(packages)
    index = {}
    for package in packages:
        require_fields(package, PACKAGE_FIELDS)
        event_id = package["event_id"]
        if event_id in index:
            raise ValueError(f"Duplicate reviewed evidence package: {event_id}")
        index[event_id] = package

    if len(events) != len({row["event_id"] for row in events}):
        raise ValueError("Duplicate event IDs in reconciled manifest")
    if set(index) != {row["event_id"] for row in events}:
        raise ValueError("Reviewed evidence package IDs differ from the reconciled manifest")
    predictions = []
    snapshots = []
    for event in sorted(events, key=lambda row: row["event_id"]):
        require_fields(event, EVENT_FIELDS, OPTIONAL_EVENT_FIELDS)
        require_text(event, EVENT_FIELDS)
        event_id = event["event_id"]
        package = index[event_id]
        require_text(package, ("trial_set_rationale",))
        if (package["outcome_exposure"] != "OUTCOME_UNEXPOSED"
                or package["application_number"] != event["application_number"]
                or package["review_cycle"] != event["review_cycle"]):
            raise ValueError(f"{event_id}: outcome exposure or unverified application/cycle match")
        decision = strict_day(event["decision_date"])
        if decision > date.today():
            raise ValueError(f"{event_id}: decision date must be historical")
        cutoff = decision - timedelta(days=cutoff_days)
        trials = package["trials"]
        if not isinstance(trials, list) or not trials or len(trials) != len({t["nct_id"] for t in trials}):
            raise ValueError(f"{event_id}: requires an explicitly reviewed nonduplicate pivotal trial set")
        trials = sorted(trials, key=lambda trial: trial["nct_id"])
        try:
            assessments = [execute_trial(trial, cutoff) for trial in trials]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{event_id}: {error}") from error
        snapshots.append({
            "event": event,
            "evidence": {**package, "trials": trials},
            "scientific_ratings": assessments,
        })
        for number, level in enumerate(LEVELS, 1):
            direction, reason, findings = decide_direction(number, assessments, trials)
            predictions.append({
                **event, "level": level, "cutoff_date": cutoff.isoformat(),
                "prediction": direction, "reason": reason, "criterion_references": findings,
                "protocol": PROTOCOL,
            })
    lock = {
        "protocol": PROTOCOL, "rule_set": RULE_SET, "expected_events": len(events),
        "cutoff_days": cutoff_days, "feature_snapshots": snapshots, "predictions": predictions,
        "feature_snapshots_sha256": canonical_digest(snapshots),
        "predictions_sha256": canonical_digest(predictions),
    }
    return {**lock, "lock_sha256": canonical_digest(lock)}


def verify_canonical_lock(locked, frozen_digest):
    if not isinstance(frozen_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", frozen_digest):
        raise ValueError("Supply the independently recorded canonical lock SHA-256")
    if (locked["protocol"], locked["rule_set"]) != (PROTOCOL, RULE_SET):
        raise ValueError("Canonical historical lock protocol or rule set mismatch")
    payload = {key: value for key, value in locked.items() if key != "lock_sha256"}
    if locked["lock_sha256"] != frozen_digest or canonical_digest(payload) != frozen_digest:
        raise ValueError("Canonical historical lock integrity failure")
    snapshots = locked["feature_snapshots"]
    predictions = locked["predictions"]
    if (canonical_digest(snapshots) != locked["feature_snapshots_sha256"]
            or canonical_digest(predictions) != locked["predictions_sha256"]):
        raise ValueError("Canonical evidence or prediction digest mismatch")
    events = {snapshot["event"]["event_id"]: snapshot["event"] for snapshot in snapshots}
    expected = {(eid, level) for eid in events for level in LEVELS}
    actual = {(row["event_id"], row["level"]) for row in predictions}
    if (not events or len(snapshots) != len(events) or len(events) != locked["expected_events"]
            or len(predictions) != len(expected) or actual != expected):
        raise ValueError("Incomplete or duplicate canonical prediction grid")
    for row in predictions:
        event = events[row["event_id"]]
        if (row["protocol"] != PROTOCOL or row["prediction"] not in DIRECTIONS
                or any(row.get(key) != value for key, value in event.items())):
            raise ValueError("Canonical prediction does not match its event or rule set")
    return predictions


def unique_json_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate key in evidence JSON")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True, help="Outcome-free reconciled case CSV")
    parser.add_argument("--evidence", required=True, help="Reviewed and outcome-unexposed JSON")
    parser.add_argument("--expected-events", type=int, required=True)
    parser.add_argument("--cutoff-days", type=int, default=30)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    events = load_csv(args.events)
    if len(events) != args.expected_events:
        raise ValueError(f"Expected {args.expected_events} reconciled events, got {len(events)}")
    packages = json.loads(
        Path(args.evidence).read_text(encoding="utf-8"), object_pairs_hook=unique_json_object
    )
    lock = make_lock(events, packages, args.cutoff_days)
    write_new_lock(args.output, lock)
    print(f"Locked {len(lock['predictions'])} directions. SHA-256 {lock['lock_sha256']}")


if __name__ == "__main__":
    main()
