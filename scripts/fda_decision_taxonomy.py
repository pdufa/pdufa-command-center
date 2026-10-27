"""Quarantined FDA action observations, never source-certified training labels.

A caller's source URL, downloaded-file hash, or reviewer flags cannot establish
independent verification. Binary candidate actions are reconciled by exact
application/submission/review cycle; all observations remain model-ineligible.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

APPROVAL_ACTIONS = {"approval", "accelerated_approval", "traditional_approval"}
NONAPPROVAL_ACTIONS = {"complete_response_letter", "complete_response", "crl"}
CENSORED_ACTIONS = {
    "withdrawn", "withdrawal", "delayed", "pending", "resubmitted", "unresolved",
    "refuse_to_file", "refusal_to_file", "rtf", "tentative_approval",
    "administrative_extension", "provisional_determination", "rescinded_crl",
    "rescind_complete_response", "corrected_provisional_determination",
}
FDA_HOSTS = frozenset({"fda.gov", "www.fda.gov", "accessdata.fda.gov",
                       "www.accessdata.fda.gov", "download.open.fda.gov",
                       "open.fda.gov", "api.fda.gov"})


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _date(value: Any) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _application(value: Any) -> str | None:
    value = _text(value).upper()
    if not re.fullmatch(r"(?:NDA|BLA|ANDA)[ -]?[0-9]{6}", value):
        return None
    return value.replace("-", "").replace(" ", "")


def _official_url(value: Any) -> bool:
    if (not isinstance(value, str) or not value
            or any(c.isspace() or ord(c) < 32 for c in value)):
        return False
    try:
        u = urlsplit(value)
        return bool(u.scheme == "https" and u.hostname in FDA_HOSTS
                    and u.username is None and u.password is None
                    and u.port is None and not u.fragment and u.path not in {"", "/"})
    except ValueError:
        return False


def classify_decision(event: Mapping[str, Any], *, as_of: str) -> dict[str, Any]:
    """Validate an action *claim* and chronology, never attest its source truth.

    `evidence_as_of` is outcome-source publication availability, distinct from the
    action date and `retrieved_on`. Unknown publication dates cannot be invented
    from retrieval dates. Review cycles are explicit supplied identities; this
    module does not infer an FDA cycle ordinal from chronological action rows.
    """
    cutoff = _date(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a valid YYYY-MM-DD date")
    base = {"application_id": None, "submission_id": None, "review_cycle": None,
            "action": None, "decision_date": None, "evidence_as_of": None,
            "retrieved_on": None, "source_url": None, "candidate_label": None,
            "label": None, "eligible_for_binary_training": False,
            "model_eligible": False, "independently_verified": False,
            "source_content_verified": False}
    if not isinstance(event, Mapping):
        return {**base, "status": "invalid_event", "issues": ["invalid_event"]}
    app = _application(event.get("application_id"))
    submission = _text(event.get("submission_id"))
    raw_cycle = event.get("review_cycle")
    # CSV strings are permitted, booleans and float ordinals are not.
    cycle = (int(raw_cycle) if isinstance(raw_cycle, str)
             and re.fullmatch(r"[1-9][0-9]{0,8}", raw_cycle) else raw_cycle)
    action = _text(event.get("action")).lower().replace(" ", "_")
    action_date = _date(event.get("decision_date"))
    evidence_date = _date(event.get("evidence_as_of"))
    retrieved = _date(event.get("retrieved_on"))
    issues = []
    exact_cycle = (app is not None and bool(submission) and len(submission) <= 80
                   and not any(ord(c) < 32 for c in submission)
                   and type(cycle) is int and 1 <= cycle <= 999999999)
    if not exact_cycle:
        issues.append("missing_exact_application_submission_cycle")
    if not _official_url(event.get("source_url")):
        issues.append("official_fda_source_required")
    if action_date is None:
        issues.append("invalid_decision_date")
    elif action_date > cutoff:
        issues.append("future_event_excluded")
    if evidence_date is None or retrieved is None:
        issues.append("unknown_or_invalid_source_chronology")
    elif (evidence_date > cutoff or retrieved > cutoff
          or retrieved < evidence_date
          or (action_date is not None and evidence_date < action_date)):
        issues.append("invalid_or_postcutoff_source_chronology")
    base.update(application_id=app, submission_id=submission or None,
                review_cycle=cycle if exact_cycle else None,
                action=action or None,
                decision_date=action_date.isoformat() if action_date else None,
                evidence_as_of=evidence_date.isoformat() if evidence_date else None,
                retrieved_on=retrieved.isoformat() if retrieved else None,
                source_url=event.get("source_url") if _official_url(event.get("source_url")) else None)
    if issues:
        return {**base, "status": issues[0], "issues": issues}
    if action in APPROVAL_ACTIONS:
        return {**base, "status": "binary_candidate_requires_independent_review",
                "candidate_label": "PASS", "issues": []}
    if action in NONAPPROVAL_ACTIONS:
        return {**base, "status": "binary_candidate_requires_independent_review",
                "candidate_label": "FAIL", "issues": []}
    if action in CENSORED_ACTIONS:
        return {**base, "status": "censored_or_out_of_scope", "issues": []}
    return {**base, "status": "unknown_action_requires_review", "issues": []}


def deduplicate_applications(events: list[Mapping[str, Any]], *, as_of: str) -> dict[str, Any]:
    """Reconcile candidate cycles without conflating an earlier CRL and approval.

    Repeated trials/documents for one application/submission/cycle count once.
    Conflicting action dates or binary labels quarantine that entire cycle.
    No quantity returned here is an independently verified PASS/FAIL count.
    """
    if _date(as_of) is None:
        raise ValueError("as_of must be a valid YYYY-MM-DD date")
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    excluded = []
    for event in events:
        result = classify_decision(event, as_of=as_of)
        if result["status"] != "binary_candidate_requires_independent_review":
            excluded.append(result)
            continue
        key = (result["application_id"], result["submission_id"], result["review_cycle"])
        grouped.setdefault(key, []).append(result)
    candidates, conflicts = [], []
    for key, rows in sorted(grouped.items()):
        claims = {(row["candidate_label"], row["decision_date"]) for row in rows}
        if len(claims) != 1:
            conflicts.append({"application_id": key[0], "submission_id": key[1],
                              "review_cycle": key[2], "status": "conflicting_review_cycle",
                              "claims": [{"candidate_label": label, "decision_date": day}
                                         for label, day in sorted(claims)]})
        else:
            candidates.append({**rows[0], "source_observation_count": len(rows),
                               "source_urls": sorted({row["source_url"] for row in rows})})
    conflict_apps = sorted({row["application_id"] for row in conflicts})
    return {"accepted": [], "candidates": candidates,
            "conflicting_applications": conflict_apps,
            "conflicting_review_cycles": conflicts, "excluded": excluded,
            "counts": {"verified_applications": 0, "verified_review_cycles": 0,
                       "verified_pass": 0, "verified_fail": 0,
                       "model_eligible_records": 0,
                       "candidate_applications": len({r["application_id"] for r in candidates}),
                       "candidate_review_cycles": len(candidates),
                       "candidate_pass": sum(r["candidate_label"] == "PASS" for r in candidates),
                       "candidate_fail": sum(r["candidate_label"] == "FAIL" for r in candidates),
                       "conflicting_applications": len(conflict_apps),
                       "conflicting_review_cycles": len(conflicts),
                       "excluded_events": len(excluded)}}
