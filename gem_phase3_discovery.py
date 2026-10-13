"""GEM broad Phase-3 discovery and ranking-quality audit.

Read-only candidate discovery from the actual ClinicalTrials.gov / issuer
collector ledger. A posted result, registry primary p-value, or a press
release does NOT establish verified successful Phase 3, clinical benefit,
safety clearance, identity to an FDA application, or financing completion.
Only the strict exact-event gate in gem_scans may promote to GEM tracking.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from post_phase3_unified import read_rows

NCT_RE = re.compile(r"^NCT\d{8}$")
TICKER_RE = re.compile(r"^[A-Z0-9.-]{1,15}$")
RESULT_TYPES = {"CLINICALTRIALS_RESULTS", "ISSUER_TOPLINE_RELEASE"}
DISCOVERY_COLUMNS = (
    "Ticker", "NCT ID", "Drug", "Indication", "Result posted (source)",
    "Discovery category", "Verification status", "Review priority",
    "What is missing", "First seen UTC", "Last checked UTC",
    "Results source", "Registry source",
)


def _text(obj):
    return str(obj or "").strip()


def _utc_date(value):
    raw = _text(value)
    if not raw:
        return None
    try:
        if len(raw) == 10:
            return date.fromisoformat(raw)
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return timestamp.astimezone(timezone.utc).date() if timestamp.tzinfo else None
    except (ValueError, TypeError):
        return None


def _https(value):
    try:
        u = urlsplit(_text(value))
        return u.scheme == "https" and bool(u.hostname) and not u.username and not u.password
    except ValueError:
        return False


def discover_phase3_results(root="data", as_of=None, *, limit=20000):
    """Collect bounded, distinct Phase 3 result-review leads from saved sources.

    The independent announcement ledger is already populated by the nightly
    scan #4 collector, where available. It cannot substitute for explicit
    verified-success evidence: every result remains REVIEW. Ambiguous exact
    trial identities and future/invalid sources are retained as separate
    audit counts but are NOT silently promoted.
    """
    today = as_of or date.today()
    if not isinstance(today, date) or isinstance(today, datetime):
        raise ValueError("as_of must be a date")
    source = Path(root) / "phase3_announcements.csv"
    raw = read_rows(source)
    if not isinstance(limit, int) or not 1 <= limit <= 100000:
        raise ValueError("invalid ledger row limit")
    counts = Counter()
    by_program = {}
    for item in raw:
        counts["source_rows"] += 1
        if counts["source_rows"] > limit:
            counts["unprocessed_due_to_limit"] += 1
            continue
        source_type = _text(item.get("source_type"))
        if source_type not in RESULT_TYPES:
            counts["unsupported_types"] += 1
            continue
        ticker = _text(item.get("ticker")).upper()
        nct = _text(item.get("nct_id")).upper()
        published = _utc_date(item.get("phase3_results_posted_at"))
        first_seen = _utc_date(item.get("first_seen_at"))
        checked = _utc_date(item.get("last_checked_at"))
        url = _text(item.get("phase3_results_source"))
        if not TICKER_RE.fullmatch(ticker) or not NCT_RE.fullmatch(nct):
            counts["ambiguous_ticker_or_trial"] += 1
            continue
        if (published is None or published > today or first_seen is None
                or first_seen > today or checked is None or checked > today
                or first_seen > checked or not _https(url)):
            counts["missing_or_future_source_evidence"] += 1
            continue
        # One issuer and one registry item may legitimately identify the
        # same trial. We retain them separately: neither proves efficacy.
        key = (ticker, nct, source_type)
        row = {
            "Ticker": ticker, "NCT ID": nct,
            "Drug": _text(item.get("drug")), "Indication": _text(item.get("indication")),
            "Result posted (source)": published.isoformat(),
            "Discovery category": ("ISSUER READOUT — NEEDS ENDPOINT REVIEW"
                                   if source_type == "ISSUER_TOPLINE_RELEASE"
                                   else "REGISTRY RESULTS — NEEDS ENDPOINT REVIEW"),
            "Verification status": _text(item.get("verification_status")) or "NOT VERIFIED",
            "Review priority": "HIGH — VERIFY CLINICAL SUCCESS" if source_type == "ISSUER_TOPLINE_RELEASE" else "REVIEW — VALIDATE PRIMARY ENDPOINT",
            "What is missing": ("Independent endpoint, effect size, safety and exact-program review. "
                                "Finance #2 and entry gates remain independent."),
            "First seen UTC": _text(item.get("first_seen_at")),
            "Last checked UTC": _text(item.get("last_checked_at")),
            "Results source": url,
            "Registry source": "https://clinicaltrials.gov/study/" + nct,
        }
        previous = by_program.get(key)
        if previous:
            # Conflicting source dates, drugs or indications cannot be
            # silently resolved by last-writer-wins.
            if any(previous[k] != row[k] for k in (
                "Result posted (source)", "Drug", "Indication", "Results source"
            )):
                counts["ambiguous_duplicate_program"] += 1
                by_program[key] = None
            else:
                counts["duplicate_identical"] += 1
        else:
            # Dict None is also used for ambiguous identity; never revive it.
            if key in by_program:
                counts["ambiguous_duplicate_program"] += 1
            else:
                by_program[key] = row
    out = [row for row in by_program.values() if row is not None]
    out.sort(key=lambda r: (r["Review priority"].startswith("REVIEW"),
                            r["Result posted (source)"], r["Ticker"]), reverse=False)
    # Within the same priority, show the newest actual source first.
    out.sort(key=lambda r: r["Result posted (source)"], reverse=True)
    out.sort(key=lambda r: r["Review priority"].startswith("REVIEW"))
    state = {
        "source_file": str(source.name), "review_candidates": len(out),
        "source_rows": counts["source_rows"],
        "rejected_ambiguous_identity": counts["ambiguous_ticker_or_trial"],
        "rejected_missing_or_future_evidence": counts["missing_or_future_source_evidence"],
        "ambiguous_duplicates": counts["ambiguous_duplicate_program"],
        "unprocessed_due_to_limit": counts["unprocessed_due_to_limit"],
        "last_saved_check": max((_text(item.get("Last checked UTC"))
                                 for item in out), default=""),
        "status": ("REVIEW_SOURCE_LEDGER_EMPTY" if not raw else
                   "REVIEW_PARTIAL_INPUT_TRUNCATED" if counts["unprocessed_due_to_limit"] else
                   "REVIEW_EVIDENCE_NOT_ADJUDICATED"),
        "caveat": "Readout posted or announced is not a successful clinical result. "
                  "Source ledger is saved state; no live issuer website check ran here.",
    }
    return out, state


def gem_discrimination_audit(items, stages):
    """Describe how much the existing 100-point score actually separates ranks."""
    report = {}
    for stage in stages:
        scores = [row[stage + " score"] for row in items
                  if row.get(stage + " score") is not None]
        freq = Counter(scores)
        qualified = len(scores)
        report[stage] = {
            "qualified": qualified,
            "unique_scores": len(freq),
            "tied_candidates": sum(n for n in freq.values() if n > 1),
            "largest_tied_group": max(freq.values(), default=0),
            "status": ("NO_RANKED_CANDIDATES" if not qualified else
                       "NO_DISCRIMINATION_ALL_TIED" if len(freq) == 1 and qualified > 1 else
                       "LIMITED_DISCRIMINATION" if sum(n for n in freq.values() if n > 1) / qualified >= 0.5 else
                       "SCORE_SPREAD_EXISTS_NOT_RETURN_VALIDATED"),
        }
    return report
