"""Read-only historical-parallel *candidate* retrieval for PDUFA review.

Input dictionaries, source URLs and reviewer flags cannot establish original-source
truth. This adapter never promotes candidates to independently verified parallels,
training observations, or FDA probabilities. Comparisons are descriptive/unscored.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

FIELDS = ("indication", "population", "line_of_therapy", "mechanism",
          "modality", "endpoint_family", "regulatory_pathway")
DECISIONS = {"approved", "crl", "withdrawn"}
DEVELOPMENT = {"terminated", "discontinued", "no_application"}
ACTION_REVISIONS = {
    "rescinded_crl", "rescind_complete_response", "corrected_complete_response",
    "corrected_crl", "corrected_provisional_determination", "rescinded_approval",
    "corrected_approval", "rescission", "correction",
}
FDA_HOSTS = {"fda.gov", "www.fda.gov", "accessdata.fda.gov",
             "www.accessdata.fda.gov", "download.open.fda.gov", "api.fda.gov"}


def _as_date(value: Any) -> date | None:
    """Reject invalid dates and timestamps rather than silently truncating them."""
    if type(value) is date:
        return value
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _application(value: Any) -> str | None:
    value = _text(value).upper()
    if not re.fullmatch(r"(?:NDA|BLA|ANDA)[ -]?[0-9]{6}", value):
        return None
    return value.replace("-", "").replace(" ", "")


def _source_url(value: Any, *, fda: bool = False) -> bool:
    if (not isinstance(value, str) or not value
            or any(c.isspace() or ord(c) < 32 for c in value)):
        return False
    try:
        parsed = urlsplit(value)
        return bool(parsed.scheme == "https" and parsed.hostname
                    and parsed.username is None and parsed.password is None
                    and parsed.port is None and not parsed.fragment
                    and (not fda or (parsed.hostname in FDA_HOSTS
                                      and parsed.path not in {"", "/"})))
    except ValueError:
        return False


def find_parallels(
    current: Mapping[str, Any],
    historical: Sequence[Mapping[str, Any]],
    *,
    as_of: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Retrieve candidates without treating caller claims as verification.

    FDA candidates require canonical application identity, explicit submission_id
    (original/supplement as documented), review_cycle, FDA source URL, decision
    date and two separate dates: public_features_as_of must precede that decision;
    evidence_as_of is when the outcome evidence became public, on/after the action
    and before this target cutoff. No later decision is relabeled as development.

    Multiple NCT/program rows for the same application/submission/cycle contribute
    one candidate. Conflicting dates/outcomes or pre-cutoff corrections/rescissions
    quarantine the entire cycle pending prior-action adjudication. Distinct
    cycles remain separate, with distinct application and cycle counts. Those
    counts do not establish an unbiased independent denominator or probabilities.
    """
    cutoff = _as_date(as_of)
    if cutoff is None:
        raise ValueError("as_of must be a valid YYYY-MM-DD date")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer 1..100")
    if not isinstance(current, Mapping) or not _text(current.get("program_id")):
        raise ValueError("current program_id required")
    current_application = _application(current.get("application_id"))
    if current.get("application_id") is not None and current_application is None:
        raise ValueError("invalid current application_id")

    rejected: Counter[str] = Counter()
    candidates = []
    cycle_claims: dict[tuple, set[tuple]] = defaultdict(set)
    revision_cycles = set()
    for h in historical:
        if not isinstance(h, Mapping):
            rejected["invalid_record"] += 1
            continue
        program_id = _text(h.get("program_id"))
        if not program_id or program_id == _text(current["program_id"]):
            rejected["missing_or_target_program"] += 1
            continue
        outcome = _text(h.get("fda_outcome")).lower()
        application_id, submission_id, cycle = None, None, None
        decision_date, outcome_date = None, None
        if outcome in DECISIONS | ACTION_REVISIONS:
            application_id = _application(h.get("application_id"))
            submission_id = _text(h.get("submission_id"))
            cycle = h.get("review_cycle")
            if (application_id is None or not submission_id
                    or len(submission_id) > 80
                    or any(ord(c) < 32 for c in submission_id)
                    or type(cycle) is not int or cycle < 1):
                rejected["missing_exact_application_submission_cycle"] += 1
                continue
            if application_id == current_application:
                rejected["target_application_excluded"] += 1
                continue
            decision_date = _as_date(h.get("fda_decision_date"))
            outcome_date = _as_date(h.get("evidence_as_of"))
            if (decision_date is None or outcome_date is None
                    or decision_date >= cutoff or outcome_date >= cutoff
                    or outcome_date < decision_date):
                rejected["invalid_or_leaking_decision_chronology"] += 1
                continue
            if not _source_url(h.get("outcome_source_url"), fda=True):
                rejected["official_fda_outcome_source_required"] += 1
                continue
            key = (application_id, submission_id, cycle)
            if outcome in ACTION_REVISIONS:
                # A revision changes whether the prior action can be used. It
                # must be reconciled even without clinical matching features.
                revision_cycles.add(key)
                rejected["action_revision_requires_prior_action_review"] += 1
                continue
            # Reconcile every well-formed cycle claim, even if one row has no
            # matching dimensions. Never hide an opposing claim by ranking it out.
            cycle_claims[key].add((outcome, decision_date))
            kind = "fda_decision_candidate"
        elif outcome in DEVELOPMENT:
            if h.get("application_id") is not None:
                rejected["development_application_requires_action_review"] += 1
                continue
            key = ("development", program_id)
            kind = "development_candidate"
        else:
            rejected["unknown_or_missing_outcome"] += 1
            continue

        sources = h.get("source_urls")
        if (not isinstance(sources, list) or not sources
                or not all(_source_url(url) for url in sources)):
            rejected["invalid_source_urls"] += 1
            continue
        features_date = _as_date(h.get("public_features_as_of"))
        if features_date is None or features_date >= cutoff:
            rejected["invalid_or_postcutoff_features"] += 1
            continue
        if decision_date is not None and features_date >= decision_date:
            rejected["invalid_or_leaking_decision_chronology"] += 1
            continue

        compared = [f for f in FIELDS if _text(current.get(f)) and _text(h.get(f))]
        equal = [f for f in compared
                 if _text(current[f]).casefold() == _text(h[f]).casefold()]
        if not equal:
            rejected["no_matching_dimensions"] += 1
            continue
        candidates.append({
            "program_id": program_id, "application_id": application_id,
            "submission_id": submission_id, "review_cycle": cycle,
            "matched_dimensions": equal, "compared_dimensions": compared,
            "match_status": "unscored", "group": kind,
            "public_features_as_of": features_date.isoformat(),
            "source_urls": sorted(set(sources)),
            "candidate_fda_outcome": outcome if decision_date else None,
            "candidate_fda_decision_date": decision_date.isoformat() if decision_date else None,
            "outcome_evidence_as_of": outcome_date.isoformat() if outcome_date else None,
            "outcome_source_url": h.get("outcome_source_url") if decision_date else None,
            "candidate_development_outcome": outcome if not decision_date else None,
            "fda_outcome": None,
            "source_content_verified": False,
            "independently_verified": False,
            "model_eligible": False,
            "_key": key,
        })

    conflicting = {key for key, claims in cycle_claims.items() if len(claims) != 1}
    candidates.sort(key=lambda m: (-len(m["matched_dimensions"]),
                                  -len(m["compared_dimensions"]), m["program_id"],
                                  str(m["_key"])))
    grouped: dict[tuple, dict] = {}
    for match in candidates:
        key = match.pop("_key")
        if key in revision_cycles:
            rejected["prior_action_adjudication_required"] += 1
            continue
        if key in conflicting:
            rejected["conflicting_review_cycle"] += 1
            continue
        if key not in grouped:
            match["associated_program_ids"] = [match["program_id"]]
            grouped[key] = match
        elif match["program_id"] not in grouped[key]["associated_program_ids"]:
            grouped[key]["associated_program_ids"].append(match["program_id"])
    all_candidates = list(grouped.values())
    result = all_candidates[:limit]
    return {
        "as_of": cutoff.isoformat(),
        "status": "unverified_candidates_available" if result else "no_verified_matches",
        "candidate_match_count": len(result),
        "total_candidate_count": len(all_candidates),
        "candidate_application_count": len({m["application_id"] for m in all_candidates
                                            if m["application_id"] is not None}),
        "candidate_review_cycle_count": sum(m["group"] == "fda_decision_candidate"
                                            for m in all_candidates),
        "conflicting_review_cycle_count": len(conflicting),
        "revision_dependent_review_cycle_count": len(revision_cycles & cycle_claims.keys()),
        "excluded_record_counts": dict(sorted(rejected.items())),
        "verified_match_count": 0,
        "source_content_verified": False,
        "match_count_is_limited": len(all_candidates) > limit,
        "historical_parallels_collapsed": True,
        "prediction_probability": None,
        "prediction_status": "not_calibrated",
        "model_validated": False,
        "matches": result,
    }
