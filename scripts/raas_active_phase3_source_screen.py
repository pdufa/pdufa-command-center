#!/usr/bin/env python3
"""Prioritize live Phase 3 RAAS source reviews without fabricating FDA eligibility.

Requires independently stored exact-NCT ClinicalTrials.gov registry receipts,
dated source-provided market capitalization from Nasdaq, and the full 762-trial
research roster. A Phase 3 + cap candidate is NOT an NDA/BLA, a PDUFA target,
a validated clinical outcome, or a completed 30/30 RAAS score.
"""
from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
from raas_review_worklist import build_worklist

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
CAPS = ROOT / "data/phase_pipeline_market_caps.csv"
ROSTER = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
REVIEWS = ROOT / "new-platform/frontend/data/raas-reviewed-metric-assessments.json"
CSV = ROOT / "new-platform/frontend/public/raas-active-phase3-source-screen.csv"
STATUS = ROOT / "new-platform/frontend/data/raas-active-phase3-source-screen-status.json"

MIN_CAP = 300_000_000
MAX_CAP = 10_000_000_000
MAX_CAP_AGE = timedelta(days=7)
ACTIVE_STATUSES = frozenset({
    "RECRUITING", "ACTIVE_NOT_RECRUITING",
    "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION",
})
NCT = re.compile(r"NCT\d{8}\Z")
TICKER = re.compile(r"[A-Z]{1,7}(?:[.-][A-Z]{1,3})?\Z")
FIELDS = (
    "nctId", "ticker", "company", "registrySourceUrl",
    "registryResearchStatus", "registryResearchPhase",
    "registrySnapshotAsOf", "registryCurrentActive",
    "sourceRegisteredPhase3", "marketCapSourceStatus",
    "marketCapSourceUrl", "marketCapCheckedAt",
    "marketCapUsd", "marketCapSnapshotFresh",
    "marketCapIn300mTo10bRange", "sourceActivePhase3CapScreen",
    "sourceRegisteredInterventions", "sourceRegisteredConditions",
    "topAiReviewedMetricsOf30", "bottomAiReviewedMetricsOf30",
    "topHumanIndependentReviewsOf30", "bottomHumanIndependentReviewsOf30",
    "fdaUsPathwayIndependentVerification", "drugIndicationProgramCrosswalk",
    "applicationAcceptedForReview", "confirmedPdufaDate",
    "fullRaasOverallRating", "fdaPassCrlExtensionProbability",
    "eligibilityAuditStatus", "missingSourceChecks",
    "priorityForMetricReview", "interpretation",
)


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("RAAS_ACTIVE_SOURCE_DATE_MISSING")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("RAAS_ACTIVE_SOURCE_DATE_INVALID") from error
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("RAAS_ACTIVE_SOURCE_DATE_NO_TIMEZONE")
    return dt.astimezone(timezone.utc)


def roster_records(text: str) -> dict[str, dict]:
    result = {}
    rows = csv.DictReader(io.StringIO(text))
    if not rows.fieldnames or not {"nct_id", "ticker", "company", "status", "source_url"}.issubset(
        rows.fieldnames):
        raise ValueError("RAAS_ACTIVE_ROSTER_HEADERS")
    for row in rows:
        nct, ticker = row["nct_id"], row["ticker"]
        if (not NCT.fullmatch(nct) or not TICKER.fullmatch(ticker) or
            nct in result or not row["company"] or
            row["source_url"] != f"https://clinicaltrials.gov/study/{nct}"):
            raise ValueError("RAAS_ACTIVE_ROSTER_IDENTITY")
        result[nct] = row
    if not result:
        raise ValueError("RAAS_ACTIVE_ROSTER_EMPTY")
    return result


def market_caps(text: str) -> dict[str, dict]:
    rows = csv.DictReader(io.StringIO(text))
    required = {"ticker", "market_cap", "market_cap_source",
                "market_cap_checked_at", "market_cap_status"}
    if not rows.fieldnames or not required.issubset(rows.fieldnames):
        raise ValueError("RAAS_ACTIVE_MARKET_CAP_HEADERS")
    out = {}
    for r in rows:
        ticker = r["ticker"]
        if not TICKER.fullmatch(ticker) or ticker in out:
            raise ValueError("RAAS_ACTIVE_MARKET_CAP_DUPLICATE_OR_TICKER")
        if r["market_cap_status"] != "VERIFIED":
            # Preserve recorded no-source states. They are not false market caps.
            out[ticker] = {"value": None, "status": r["market_cap_status"],
                           "date": None, "source": r["market_cap_source"]}
            continue
        try:
            val = float(r["market_cap"])
            date = utc(r["market_cap_checked_at"])
        except (TypeError, ValueError) as error:
            raise ValueError("RAAS_ACTIVE_MARKET_CAP_INVALID") from error
        if (not math.isfinite(val) or val <= 0 or
            not r["market_cap_source"].startswith(
                "https://api.nasdaq.com/api/quote/")):
            raise ValueError("RAAS_ACTIVE_MARKET_CAP_UNTRUSTED_SOURCE")
        out[ticker] = {"value": val, "status": "VERIFIED", "date": date,
                       "source": r["market_cap_source"]}
    return out


def build(
    index: dict, roster_csv: str, caps_csv: str, reviews: dict
) -> tuple[list[dict], dict]:
    source_date = utc(index.get("sourceAsOf"))
    if (index.get("schemaVersion") != 1 or
        index.get("scope") != "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX" or
        not isinstance(index.get("records"), list)):
        raise ValueError("RAAS_ACTIVE_INDEX_SCOPE")
    roster = roster_records(roster_csv)
    caps = market_caps(caps_csv)
    work, review_status = build_worklist(index, reviews)
    if (len(index["records"]) != len(roster) or
        review_status["researchTrials"] != len(roster) or
        len(work) != 2 * len(roster)):
        raise ValueError("RAAS_ACTIVE_ROSTER_COUNT_MISMATCH")
    by_review = {(x["nctId"], x["researchStage"]): x for x in work}
    records = []
    ids = set()
    for e in index["records"]:
        nct, ticker = e["nctId"], e["ticker"]
        if nct in ids or roster[nct]["ticker"] != ticker:
            raise ValueError("RAAS_ACTIVE_CROSS_NCT_SOURCE")
        ids.add(nct)
        c = caps.get(ticker)
        status = (e.get("registryStatus") or "").strip().upper()
        if status and roster[nct]["status"] != status:
            # Registry index is refreshed nightly; do not silently substitute
            # the older roster's status, even when classifications differ.
            research_status = status
        else:
            research_status = roster[nct]["status"]
        phase3 = "PHASE3" in (e.get("registeredPhases") or [])
        active = research_status in ACTIVE_STATUSES
        cap_status = c["status"] if c else "NO_VERIFIED_MARKET_CAP"
        cap_val = c["value"] if c else None
        checked = c["date"] if c else None
        fresh = (c is not None and cap_status == "VERIFIED" and
                 checked is not None and
                 timedelta(0) <= source_date - checked <= MAX_CAP_AGE)
        in_range = bool(fresh and MIN_CAP <= cap_val <= MAX_CAP)
        screen = bool(active and phase3 and in_range)
        interventions = [name.strip() for name in e.get("registeredInterventions") or []
                         if isinstance(name, str) and name.strip()]
        conditions = [name.strip() for name in e.get("registeredConditions") or []
                      if isinstance(name, str) and name.strip()]
        if screen:
            missing = [
                "FDA_US_PATHWAY_NOT_INDEPENDENTLY_VERIFIED",
                "EXACT_DRUG_INDICATION_TO_APPLICATION_NOT_VERIFIED",
                "NDA_BLA_ACCEPTANCE_AND_PDUFA_DATE_NOT_VERIFIED",
                "INDEPENDENT_30_OF_30_RAAS_EVIDENCE_REVIEWS_REQUIRED",
            ]
            if not interventions or not conditions:
                missing.append("REGISTRY_DRUG_OR_INDICATION_UNIDENTIFIED")
            stage = "SOURCE_ACTIVE_PHASE3_CAP_SCREENED_NOT_FDA_ELIGIBLE"
            priority = "1_SOURCE_CONFIRMED_PHASE3_CAP_PENDING_FDA_AND_SCIENCE"
        else:
            missing = []
            if not active:
                missing.append("REGISTRY_TRIAL_NOT_IN_ACTIVE_STAGE")
            if not phase3:
                missing.append("EXACT_REGISTRY_PHASE3_NOT_VERIFIED")
            if not fresh:
                missing.append("CURRENT_SEVEN_DAY_MARKET_CAP_NOT_VERIFIED")
            elif not in_range:
                missing.append("MARKET_CAP_OUTSIDE_300M_TO_10B")
            stage = "NOT_IN_ACTIVE_PHASE3_CAP_RESEARCH_SCREEN"
            priority = "2_NOT_READY_FOR_CURRENT_PIPELINE_METRIC_REVIEW"
        top = by_review.get((nct, "TOP_RESEARCH_ONLY"))
        bottom = by_review.get((nct, "BOTTOM_RESEARCH_ONLY"))
        if not top or not bottom:
            raise ValueError("RAAS_ACTIVE_MISSING_STAGE_REVIEW")
        records.append({
            "nctId": nct, "ticker": ticker, "company": roster[nct]["company"],
            "registrySourceUrl": e["sourceUrl"],
            "registryResearchStatus": research_status,
            "registryResearchPhase": ";".join(e.get("registeredPhases") or []),
            "registrySnapshotAsOf": index["sourceAsOf"],
            "registryCurrentActive": active,
            "sourceRegisteredPhase3": phase3,
            "marketCapSourceStatus": cap_status,
            "marketCapSourceUrl": c["source"] if c else "",
            "marketCapCheckedAt": checked.isoformat() if checked else "",
            "marketCapUsd": cap_val if cap_val is not None else "",
            "marketCapSnapshotFresh": bool(fresh),
            "marketCapIn300mTo10bRange": bool(in_range),
            "sourceActivePhase3CapScreen": screen,
            "sourceRegisteredInterventions": ";".join(interventions),
            "sourceRegisteredConditions": ";".join(conditions),
            "topAiReviewedMetricsOf30": top["aiSourceCrosscheckedGrades"],
            "bottomAiReviewedMetricsOf30": bottom["aiSourceCrosscheckedGrades"],
            "topHumanIndependentReviewsOf30": top["independentMetricReviews"],
            "bottomHumanIndependentReviewsOf30": bottom["independentMetricReviews"],
            "fdaUsPathwayIndependentVerification": "NOT_VERIFIED",
            "drugIndicationProgramCrosswalk": "NOT_VERIFIED",
            "applicationAcceptedForReview": "NOT_VERIFIED",
            "confirmedPdufaDate": "",
            "fullRaasOverallRating": "",
            "fdaPassCrlExtensionProbability": "",
            "eligibilityAuditStatus": stage,
            "missingSourceChecks": ";".join(missing),
            "priorityForMetricReview": priority,
            "interpretation": "DATE_GATED_RESEARCH_CANDIDATE_NOT_PDUFA_APPROVAL_PROBABILITY",
        })
    if set(roster) != ids:
        raise ValueError("RAAS_ACTIVE_ROSTER_INCOMPLETE")
    records.sort(key=lambda r: (not r["sourceActivePhase3CapScreen"],
                                r["ticker"], r["nctId"]))
    qualified = [r for r in records if r["sourceActivePhase3CapScreen"]]
    summary = {
        "schemaVersion": 1,
        "scope": "RAAS_ALL_762_ACTIVE_PHASE3_MARKET_CAP_SOURCE_PRE_SCREEN_NOT_FDA_PIPELINE",
        "registrySourceAsOf": index["sourceAsOf"],
        "marketCapMaxAgeDays": 7,
        "minMarketCapUsd": MIN_CAP, "maxMarketCapUsd": MAX_CAP,
        "researchTrials": len(records),
        "registryActiveTrials": sum(r["registryCurrentActive"] for r in records),
        "sourcePhase3Trials": sum(r["sourceRegisteredPhase3"] for r in records),
        "freshVerifiedCapInRangeTrials": sum(r["marketCapIn300mTo10bRange"] for r in records),
        "sourceActivePhase3CapResearchCandidates": len(qualified),
        "sourceActivePhase3CapIssuers": len({r["ticker"] for r in qualified}),
        "candidatesWithNonemptyTrialInterventionsAndConditions": sum(
            bool(r["sourceRegisteredInterventions"] and r["sourceRegisteredConditions"])
            for r in qualified),
        "candidatesWithSourceReviewedTopMetrics": sum(
            r["topAiReviewedMetricsOf30"] > 0 for r in qualified),
        "candidatesWithSourceReviewedBottomMetrics": sum(
            r["bottomAiReviewedMetricsOf30"] > 0 for r in qualified),
        "fullyIndependentlyReviewedOverallRaasRatings": 0,
        "confirmedFdaPdufaCandidatesFromThisScreen": 0,
        "calibratedFdaPredictions": 0,
        "warning": (
            "Phase 3, active trial status and Nasdaq-reported market cap are "
            "necessary research screening observations, not sufficient FDA "
            "pathway, exact drug-indication/application identity, live PDUFA "
            "or 30/30 RAAS validation. Unknown or stale cap is N/A, not an "
            "exclusion based on clinical merit. The full historical universe "
            "is preserved including inactive and out-of-scope NCTs."
        ),
    }
    return records, summary


def _safe(x: object) -> str:
    text = str(x) if x is not None else ""
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def generate(index: dict, roster: str, caps: str, reviews: dict) -> tuple[str, str]:
    rows, status = build(index, roster, caps, reviews)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: _safe(r[k]) for k in FIELDS})
    return stream.getvalue(), json.dumps(status, indent=2) + "\n"


def main() -> None:
    csv_text, stats = generate(
        json.loads(INDEX.read_text(encoding="utf8")),
        ROSTER.read_text(encoding="utf8"),
        CAPS.read_text(encoding="utf8"),
        json.loads(REVIEWS.read_text(encoding="utf8")),
    )
    CSV.write_text(csv_text, encoding="utf8")
    STATUS.write_text(stats, encoding="utf8")
    print(stats.strip())


if __name__ == "__main__":
    main()
