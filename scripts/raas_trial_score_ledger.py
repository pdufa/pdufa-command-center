#!/usr/bin/env python3
"""Publish ALL exact-NCT RAAS assessment status and source-backed design grades.

This is a factual score ledger, NOT a completed 30-metric RAAS, FDA probability,
or clinical effect/safety opinion. Missing design evidence stays unscored; a
registered trial and a posted trial are not verified TOP/BOTTOM readout stages.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")


import csv
import io
import json
from pathlib import Path
import re

from raas_review_worklist import build_worklist

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
REVIEWS = ROOT / "new-platform/frontend/data/raas-reviewed-metric-assessments.json"
OUTPUT = ROOT / "new-platform/frontend/public/raas-trial-score-ledger.csv"
STATUS = ROOT / "new-platform/frontend/data/raas-trial-score-ledger-status.json"
ID = re.compile(r"NCT\d{8}\Z")
CONTROL = re.compile(r"(?:placebo|sham|active\s*(?:comparator|control)|standard\s*of\s*care|best\s*supportive\s*care)", re.I)
FIELDS = (
    "nctId", "ticker", "sourceUrl", "registryStatus", "registryResultsPosted",
    "registrySourceAsOf", "designDiagnosticScore", "designKnownFacetsOf4",
    "designMissingFacets", "designMissingDataLowerBound",
    "designMissingDataUpperBound", "topRegistryLeadWeightPct",
    "bottomRegistryLeadWeightPct", "topAiSourceCrosschecks",
    "bottomAiSourceCrosschecks", "topIndependentMetricReviewsOf30",
    "bottomIndependentMetricReviewsOf30", "fullValidatedRaasScore",
    "fullRaasScoreStatus", "sourceEvidenceReviewStatus"
)


def _norm(value: object) -> str:
    return value.strip().upper() if isinstance(value, str) else ""


def source_design_diagnostic(e: dict) -> dict:
    """Python mirror of TS rawRaasRegistryDesignDiagnostic, not an outcome grade."""
    design = e.get("registeredDesign") or {}
    definitions = e.get("primaryDefinitions") or []
    interventions = e.get("registeredInterventions") or []
    if definitions and any(isinstance(item, dict) and
                           str(item.get("measure") or "").strip() and
                           str(item.get("timeFrame") or "").strip()
                           for item in definitions):
        endpoint = True
    elif definitions:
        endpoint = False
    else:
        endpoint = None
    allocation = _norm(design.get("allocation"))
    randomized = (True if allocation == "RANDOMIZED" else
                  False if allocation in ("NON_RANDOMIZED", "NA") else None)
    masking = _norm(design.get("masking"))
    blinded = (True if masking in ("DOUBLE", "TRIPLE", "QUADRUPLE") else
               False if masking in ("NONE", "SINGLE") else None)
    controls = any(isinstance(name, str) and CONTROL.search(name)
                   for name in interventions)
    comparator = True if controls else (
        False if _norm(design.get("interventionModel")) == "SINGLE_GROUP" else None)
    facets = [endpoint, randomized, blinded, comparator]
    known = sum(value is not None for value in facets)
    favorable = sum(value is True for value in facets)
    unknown = 4 - known
    # Match JS Math.round(yes/known*4)*25, not Python's bankers rounding.
    score = (int((favorable / known * 4) + 0.5) * 25) if known >= 3 else None
    return {"score": score, "known": known, "unknown": unknown,
            "lowerBound": favorable * 25,
            "upperBound": (favorable + unknown) * 25}


def source_lead_weights(e: dict) -> tuple[int, int]:
    """Weights of PRIMARY SOURCE LEADS, not grades or evidence quality."""
    top = 5 if e.get("primaryDefinitions") else 0  # pre-1-2, 25% / five metrics
    bottom = 0
    if e.get("postedResults") and e.get("postedPrimaryOutcomeCount", 0) > 0:
        bottom += 5  # post-1-1
        if any(x.get("analysisCount", 0) > 0 for x in e.get("primaryResults") or []):
            bottom += 5  # post-1-3
    if e.get("postedResults") and e.get("seriousAdverseEventTermCount", 0) > 0:
        bottom += 5  # post-1-5
    return top, bottom


def build_ledger(index: dict, reviews: dict) -> tuple[list[dict], dict]:
    review_rows, worklist_status = build_worklist(index, reviews)
    by_review = {(x["nctId"], x["researchStage"]): x for x in review_rows}
    records = index["records"]
    source_as_of = index.get("sourceAsOf")
    if not isinstance(source_as_of, str) or not source_as_of:
        raise ValueError("RAAS_LEDGER_SOURCE_AS_OF_MISSING")
    rows = []
    for e in records:
        nct, ticker = e["nctId"], e["ticker"]
        if not ID.fullmatch(nct):
            raise ValueError("RAAS_LEDGER_INVALID_NCT")
        top = by_review.get((nct, "TOP_RESEARCH_ONLY"))
        bottom = by_review.get((nct, "BOTTOM_RESEARCH_ONLY"))
        if not top or not bottom or top["ticker"] != ticker or bottom["ticker"] != ticker:
            raise ValueError("RAAS_LEDGER_REVIEW_MISMATCH")
        design = source_design_diagnostic(e)
        top_lead, bottom_lead = source_lead_weights(e)
        if (top["independentMetricReviews"] == 30 or
            bottom["independentMetricReviews"] == 30):
            # A full score requires stage verification PLUS the standalone TS
            # adjudication engine; the registry-only ledger cannot grant it.
            full_state = "INDEPENDENT_REVIEWS_REQUIRE_STAGE_VALIDATION"
        else:
            full_state = "INCOMPLETE_30_METRIC_INDEPENDENT_REVIEW"
        status = ("REGISTRY_RESULTS_POSTED_REVIEW_REQUIRED"
                  if e["postedResults"] else "REGISTERED_PROTOCOL_REVIEW_REQUIRED")
        rows.append({
            "nctId": nct, "ticker": ticker, "sourceUrl": e["sourceUrl"],
            "registryStatus": e.get("registryStatus", ""),
            "registryResultsPosted": e["postedResults"],
            "registrySourceAsOf": source_as_of,
            "designDiagnosticScore": "" if design["score"] is None else design["score"],
            "designKnownFacetsOf4": design["known"],
            "designMissingFacets": design["unknown"],
            "designMissingDataLowerBound": design["lowerBound"],
            "designMissingDataUpperBound": design["upperBound"],
            "topRegistryLeadWeightPct": top_lead,
            "bottomRegistryLeadWeightPct": bottom_lead,
            "topAiSourceCrosschecks": top["aiSourceCrosscheckedGrades"],
            "bottomAiSourceCrosschecks": bottom["aiSourceCrosscheckedGrades"],
            "topIndependentMetricReviewsOf30": top["independentMetricReviews"],
            "bottomIndependentMetricReviewsOf30": bottom["independentMetricReviews"],
            "fullValidatedRaasScore": "",
            "fullRaasScoreStatus": full_state,
            "sourceEvidenceReviewStatus": status
        })
    if len(rows) != worklist_status["researchTrials"]:
        raise ValueError("RAAS_LEDGER_COHORT_INCOMPLETE")
    rows.sort(key=lambda r: (r["ticker"], r["nctId"]))
    numeric = [x["designDiagnosticScore"] for x in rows
               if isinstance(x["designDiagnosticScore"], int)]
    summary = {
        "schemaVersion": 1,
        "scope": "RAAS_ALL_TRIAL_SOURCE_SCORE_LEDGER_NOT_FULL_RATINGS",
        "sourceAsOf": source_as_of,
        "researchTrials": len(rows),
        "trialsWithNumericSourceDesignDiagnostic": len(numeric),
        "trialsWithoutSufficientSourceDesignFacets": len(rows) - len(numeric),
        "trialStageReviewRows": len(review_rows),
        "aiSourceCrosscheckedMetricReviews": worklist_status["aiSourceCrosscheckedGradeRecords"],
        "independentMetricReviews": worklist_status["independentMetricReviewRecords"],
        "fullyValidatedRaasScoresInLedger": 0,
        "warning": "Numeric design diagnostics are observational trial-design facts only. They are NOT complete RAAS 30/30 ratings, FDA approval probabilities, efficacy, benefit-risk or financial predictions. Missing metrics remain N/A. This ledger does not independently verify TOP/BOTTOM or current $300M-$10B PIPELINE eligibility."
    }
    return rows, summary


def generate(index: dict, reviews: dict) -> tuple[str, str]:
    rows, summary = build_ledger(index, reviews)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue(), json.dumps(summary, indent=2) + "\n"


def main() -> None:
    text, summary = generate(json.loads(INDEX.read_text(encoding="utf-8")),
                             json.loads(REVIEWS.read_text(encoding="utf-8")))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    STATUS.write_text(summary, encoding="utf-8")
    print(summary.strip())


if __name__ == "__main__":
    main()
