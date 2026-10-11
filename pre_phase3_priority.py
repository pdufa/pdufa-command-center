"""Deterministic review-order scores, separate from clinical assessments.

Input rows come from step7_live's exact-ticker/NCT, source-dated snapshot.
Weights are research workflow choices, not a calibrated clinical model.
Missing inputs earn no readiness points; they never imply clinical failure.
"""
from __future__ import annotations

import calendar
import math
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from phase3_issuer_readouts import ANNOUNCED

RUBRIC_VERSION = "REVIEW-PRIORITY-V1"
ACTIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION",
          "NOT_YET_RECRUITING"}
STAGE_POINTS = {"Phase 3": 30, "Phase 2/3": 25, "Phase 2": 15, "Phase 1": 5}
POINT_COLUMNS = (
    "Priority stage /30", "Priority identity /15", "Priority registry /10",
    "Priority protocol /15", "Priority Phase 2 evidence /15",
    "Priority timing /10", "Priority market cap /5",
)
RUBRIC_ROWS = (
    ("Trial stage", 30, "Phase 3: 30; Phase 2/3: 25; Phase 2: 15; Phase 1: 5"),
    ("Program identity", 15, "Saved VERIFIED identity with named drug and indication"),
    ("Registry freshness", 10, "Exact-NCT source and check within 48 hours"),
    ("Protocol coverage", 15, "Fresh exact-NCT protocol: floor(15 × recorded fields / 6); coverage, not design quality"),
    ("Linked Phase 2 evidence", 15, "Presence of a source-dated linked PRIMARY analysis; p-value magnitude and analysis count add no points"),
    ("Completion timing", 10, "Within 90/180/365 days: 10/7/4; later: 2; current month: 7; elapsed within 90 days: 5; older/missing: 0"),
    ("Market-cap fit", 5, "Recent sourced $300M–$10B quote; other companies remain visible"),
)


def _text(value):
    return str(value or "").strip()


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def _recent(value, now, hours):
    checked = _timestamp(value)
    return bool(checked and timedelta(0) <= now - checked <= timedelta(hours=hours))


def _integer(value):
    try:
        return int(value)
    except (ValueError, TypeError, OverflowError):
        return 0


def _timing(raw, today):
    """Use a full month interval rather than inventing a completion day."""
    value = _text(raw)
    try:
        if re.fullmatch(r"\d{4}-\d{2}", value):
            year, month = map(int, value.split("-"))
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
            precision = "month interval"
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            start = end = date.fromisoformat(value)
            precision = "registry day"
        else:
            raise ValueError
    except (ValueError, OverflowError):
        return 0, "missing/invalid registry completion", "Confirm registry completion timing"
    if end < today:
        points = 5 if (today - end).days <= 90 else 0
        return points, f"{value} ({precision}) elapsed; issuer readout recheck needed", "Recheck elapsed completion and issuer disclosures"
    if start < today <= end:
        return 7, f"{value} (current month; exact day unknown)", "Confirm completion day and issuer disclosures"
    days = (end - today).days
    points = 10 if days <= 90 else 7 if days <= 180 else 4 if days <= 365 else 2
    return points, f"{value} ({precision}); registry milestone, not issuer guidance", ""


def _exclusion(row):
    ticker, nct = _text(row.get("Ticker")).upper(), _text(row.get("NCT ID")).upper()
    if (not re.fullmatch(r"[A-Z0-9.-]{1,15}", ticker)
            or not re.fullmatch(r"NCT\d{8}", nct)
            or _text(row.get("NCT source")) != f"https://clinicaltrials.gov/study/{nct}"):
        return "INVALID EXACT-TRIAL PROVENANCE"
    if (row.get("Issuer Phase 3 readout") == ANNOUNCED
            or _text(row.get("Phase 3 trial type")).startswith("ISSUER RESULT ANNOUNCED")
            or _text(row.get("Score status")).startswith("NOT PRE-READOUT — ISSUER TOPLINE ANNOUNCED")):
        return "ISSUER READOUT ANNOUNCED"
    if _text(row.get("Registry results posted")):
        return "REGISTRY RESULTS POSTED"
    if (_text(row.get("Market cap state")).startswith("NOT LISTED")
            or _text(row.get("Listing status")).startswith(("SUSPENDED", "DELISTED", "NOT LISTED"))):
        return "LISTING INACTIVE"
    if _text(row.get("Registry status")).upper() not in ACTIVE:
        return "REGISTRY INACTIVE OR STATUS UNKNOWN"
    if row.get("Trial phase") not in STAGE_POINTS:
        return "STAGE OUTSIDE RESEARCH SCOPE"
    if row.get("Phase 3 trial type") == "NON-PIVOTAL EFFICACY — SAFETY / OPEN LABEL":
        return "NON-PIVOTAL SAFETY / OPEN LABEL"
    if _text(row.get("Drug")).casefold() == "placebo":
        return "COMPARATOR ONLY — PROGRAM REVIEW NEEDED"
    return ""


def _linked_evidence(row, now):
    observed = _timestamp(row.get("Phase 2 PRIMARY first observed UTC"))
    sources = [_text(s) for s in _text(row.get("Phase 2 PRIMARY registry sources")).split("|")]
    sources = [s for s in sources if s]
    summary = _text(row.get("Linked Phase 2 PRIMARY p"))
    return bool(
        _integer(row.get("Phase 2 PRIMARY evidence count")) > 0
        and observed and observed <= now and sources
        and all(re.fullmatch(r"https://clinicaltrials\.gov/study/NCT\d{8}", s) for s in sources)
        and all(s.rsplit("/", 1)[-1] in summary for s in sources)
        and "NOT VERIFIED" not in summary
    )


def attach_review_priorities(trials, now):
    """Score every row, rank active review candidates, preserve clinical fields.

    Exact trial identities must already be deduplicated by the snapshot builder.
    Ranks are global ordinal ranks; filtering must not renumber them. Excluded
    rows get a scope score of zero and no rank, not a clinical score of zero.
    """
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("now must be a timezone-aware datetime")
    now = now.astimezone(timezone.utc)
    today = now.astimezone(ZoneInfo("America/Los_Angeles")).date()
    out = []
    for original in trials or []:
        row = dict(original)
        nct = _text(row.get("NCT ID")).upper()
        points = dict.fromkeys(POINT_COLUMNS, 0)
        excluded = _exclusion(row)
        gaps = []
        details = []
        reviewed = row.get("Score status") == "100-POINT RESEARCH SCORE — UNCALIBRATED"
        next_action = "Monitor issuer disclosures and refresh time-bound sources" if reviewed else "Check exact-program issuer topline disclosures before clinical scoring"
        if excluded:
            status = f"EXCLUDED — {excluded}"
            details = [f"Scope exclusion: {excluded}; zero is not a clinical result"]
            next_action = "Review released results separately" if "RESULTS" in excluded or "ANNOUNCED" in excluded else "Resolve scope/provenance before adding to active review queue"
        else:
            points[POINT_COLUMNS[0]] = STAGE_POINTS[row["Trial phase"]]
            verified = (_text(row.get("Company/program identity")).upper() == "VERIFIED"
                        and bool(_text(row.get("Drug"))) and bool(_text(row.get("Indication"))))
            points[POINT_COLUMNS[1]] = 15 if verified else 0
            if not verified:
                gaps.append("Verify exact company/drug/indication identity")
                next_action = "Verify exact company/drug/indication identity, then check issuer disclosures"
            fresh_registry = row.get("Registry check") == "RECENT" and _recent(row.get("Last trial check UTC"), now, 48)
            points[POINT_COLUMNS[2]] = 10 if fresh_registry else 0
            if not fresh_registry:
                gaps.append("Refresh exact-NCT registry snapshot; stale/missing/future timestamp earns no points")
            fresh_protocol = (row.get("Protocol check") == "RECENT"
                              and _recent(row.get("Protocol as of UTC"), now, 72)
                              and _text(row.get("Protocol source")) == f"https://clinicaltrials.gov/study/{nct}")
            coverage = max(0, min(6, _integer(row.get("Design inputs present /6"))))
            points[POINT_COLUMNS[3]] = 15 * coverage // 6 if fresh_protocol else 0
            if not fresh_protocol or coverage < 6:
                gaps.append("Retrieve/complete fresh exact-NCT protocol fields; coverage is not quality")
            linked = _linked_evidence(row, now)
            points[POINT_COLUMNS[4]] = 15 if linked else 0
            if not linked:
                gaps.append("Locate source-dated linked Phase 2 PRIMARY analysis or document unavailable")
            timing_points, timing_detail, timing_gap = _timing(row.get("Registry primary completion"), today)
            points[POINT_COLUMNS[5]] = timing_points
            if timing_gap:
                gaps.append(timing_gap)
            try:
                cap = float(row.get("Market cap USD"))
            except (ValueError, TypeError, OverflowError):
                cap = float("nan")
            cap_fit = (row.get("Market cap state") == "VERIFIED RECENT"
                       and math.isfinite(cap) and 300_000_000 <= cap <= 10_000_000_000
                       and _recent(row.get("Market cap as of UTC"), now, 72)
                       and _text(row.get("Market source")).startswith("https://"))
            points[POINT_COLUMNS[6]] = 5 if cap_fit else 0
            if not cap_fit:
                gaps.append("Current sourced $300M–$10B market-cap fit not established")
            if row.get("Trial phase") in ("Phase 3", "Phase 2/3") and row.get("Phase 3 trial type") != "PIVOTAL EFFICACY DESIGN — SOURCE CHECKED":
                gaps.append("Confirm pivotal efficacy design before clinical scoring")
            if not reviewed:
                gaps.append("Issuer unreleased status and clinical efficacy/safety require independent review")
            status = ("REVIEW CANDIDATE — IDENTITY REVIEW FIRST" if not verified else
                      "REVIEW CANDIDATE — DATED CLINICAL REVIEW AVAILABLE" if reviewed else
                      "REVIEW CANDIDATE — ISSUER STATUS UNCHECKED")
            details = [f"{label}: {points[col]}/{maximum}" for col, (label, maximum, _) in zip(POINT_COLUMNS, RUBRIC_ROWS)]
            details.append(timing_detail)
        row.update(points)
        row.update({
            "Review priority /100": sum(points.values()),
            "Review priority rank": None,
            "Review priority status": status,
            "Review priority factors": "; ".join(details),
            "Review priority gaps": "; ".join(gaps),
            "Review priority next action": next_action,
            "Review priority as of": now.isoformat(timespec="seconds"),
            "Review priority rubric": RUBRIC_VERSION,
        })
        out.append(row)
    ranked = sorted((r for r in out if not r["Review priority status"].startswith("EXCLUDED")),
                    key=lambda r: (-r["Review priority /100"], _text(r.get("Ticker")).upper(),
                                   _text(r.get("NCT ID")).upper()))
    for rank, row in enumerate(ranked, 1):
        row["Review priority rank"] = rank
    return out
