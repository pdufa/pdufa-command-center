#!/usr/bin/env python3
"""Auditable, prospective-source TOP RAAS metric evidence pilot.

Readout dates come solely from dated sponsor filings captured *before* the
readout, not registry completion dates. The ordinal 0-100 source-crosschecked
metric ratings are never full 30/30 RAAS, FDA PASS/CRL/extension probabilities
or current active PDUFA candidate eligibility.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from raas_all_trial_partial_metric_ratings import build as build_all
from raas_all_trial_partial_metric_ratings import metric_weights

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "new-platform/frontend/data/raas-prospective-source-baselines.json"
REGISTRY = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
REVIEWS = ROOT / "new-platform/frontend/data/raas-reviewed-metric-assessments.json"
CATALOG = ROOT / "new-platform/frontend/lib/raas-metric-specs.ts"
CSV = ROOT / "new-platform/frontend/public/raas-prospective-top-metric-pilot.csv"
STATUS = ROOT / "new-platform/frontend/data/raas-prospective-top-metric-pilot-status.json"
FINDING_SCORES = {
    "MATERIAL_ADVERSE": 0, "BELOW_BENCHMARK": 25, "MIXED_EVIDENCE": 50,
    "ABOVE_BENCHMARK": 75, "EXCEPTIONAL_EVIDENCE": 100,
}
FIELDS = (
    "nctId", "ticker", "drug", "indication", "registeredTrialUrl",
    "prospectiveCaptureDate", "lastReviewDate",
    "marketCapVendorUsdMillions", "marketCapVendorAsOf",
    "marketCapCurrentValidation", "sourceStage",
    "readoutWindowAsReported", "readoutSourceUrl",
    "stageAndPdufaIndependentlyVerified",
    "metricId", "provisionalMetricScore", "reviewClass",
    "metricEvidenceSourceUrl", "metricSourceDate", "benchmarkSourceUrl",
    "observedEvidence", "uncertainty", "criticalRisks",
    "weightedCoverageAcross30Pct", "observedMeanOnReviewedMetricsOnly",
    "missingMetricIds", "full30MetricRaasScore", "fdaPassCrlExtensionProbability",
    "interpretation",
)


def _safe(x: object) -> str:
    v = str(x) if x is not None else ""
    return "'" + v if v.startswith(("=", "+", "-", "@")) else v


def generate(
    baselines: dict, index: dict, reviews: dict, catalog: str
) -> tuple[str, str]:
    if (baselines.get("scope") != "RAAS_PROSPECTIVE_SOURCE_BASELINES" or
        baselines.get("schemaVersion") != 1 or
        not isinstance(baselines.get("records"), list) or
        not baselines["records"]):
        raise ValueError("RAAS_PROSPECTIVE_PILOT_BASELINE_SCOPE")
    all_rows, full_status = build_all(index, reviews, catalog)
    source_rows = {(row["nctId"], row["stage"]): row for row in all_rows}
    specs = metric_weights(catalog)["pre"]
    review_lookup = {}
    for r in reviews["records"]:
        if r.get("stage") != "pre":
            continue
        key = (r.get("nctId"), r.get("metricId"))
        if key in review_lookup:
            raise ValueError("RAAS_PROSPECTIVE_PILOT_DUPLICATE_REVIEW")
        review_lookup[key] = r
    records = []
    seen_ncts = set()
    ncts_with_grades = set()
    for b in baselines["records"]:
        nct, ticker = b.get("nctId"), b.get("ticker")
        if (not isinstance(nct, str) or nct in seen_ncts or
            not isinstance(ticker, str) or not ticker or
            b.get("stage") != "pre" or
            b.get("readoutAtCapture") != "NOT_YET_REPORTED" or
            b.get("archivedRaasPrediction") is not False or
            b.get("predictedRaas") is not None or
            not isinstance(b.get("capturedOn"), str) or
            b["capturedOn"] > reviews["sourceAsOf"]):
            raise ValueError("RAAS_PROSPECTIVE_PILOT_INVALID_CAPTURE")
        seen_ncts.add(nct)
        roster = source_rows.get((nct, "PRE_RESEARCH_ONLY"))
        if not roster or ticker != roster["ticker"]:
            raise ValueError("RAAS_PROSPECTIVE_PILOT_CROSS_NCT")
        cap = b.get("marketCap") or {}
        if (cap.get("verification") != "VENDOR_REPORTED_NOT_INDEPENDENTLY_AUDITED" or
            not isinstance(cap.get("usdMillions"), (float, int)) or
            cap["usdMillions"] <= 0 or
            not isinstance(cap.get("observedAsOf"), str) or
            cap["observedAsOf"] > b["capturedOn"]):
            raise ValueError("RAAS_PROSPECTIVE_PILOT_INVALID_VENDOR_CAP")
        observations = b.get("observations")
        if not isinstance(observations, list):
            raise ValueError("RAAS_PROSPECTIVE_PILOT_MISSING_OBSERVATIONS")
        for o in observations:
            if (not isinstance(o.get("sourcePublishedAt"), str) or
                o["sourcePublishedAt"] > b["capturedOn"] or
                not str(o.get("sourceUrl") or "").startswith("https://")):
                raise ValueError("RAAS_PROSPECTIVE_PILOT_FUTURE_SOURCE")
        # Use the most recent *issuer guidance for this trial* rather than
        # borrowing another asset's or companion trial's topline horizon.
        timing = [o for o in observations if "pre-4-1" in o.get("metricIds", [])
                  and ("topline" in (o.get("valueText") or "").lower() or
                       "topline" in (o.get("id") or "").lower())]
        if not timing:
            raise ValueError("RAAS_PROSPECTIVE_PILOT_MISSING_READOUT_GUIDANCE")
        latest = max(timing, key=lambda x: x["sourcePublishedAt"])
        names = (str(b.get("drug") or "").strip().casefold(),
                 str(b.get("indication") or "").strip().casefold())
        if not all(names):
            raise ValueError("RAAS_PROSPECTIVE_PILOT_MISSING_PROGRAM")
        for metric in specs:
            r = review_lookup.get((nct, metric))
            if r and (
                r.get("ticker") != ticker or
                str(r.get("drug") or "").strip().casefold() != names[0] or
                str(r.get("indication") or "").strip().casefold() != names[1] or
                r.get("sourceDate", "") > b["capturedOn"] or
                r.get("independentReview") not in ("PASSED", "AI_SOURCE_CROSSCHECKED") or
                r.get("finding") not in FINDING_SCORES
            ):
                raise ValueError("RAAS_PROSPECTIVE_PILOT_REVIEW_IDENTITY")
            if r:
                ncts_with_grades.add(nct)
            records.append({
                "nctId": nct, "ticker": ticker, "drug": b["drug"],
                "indication": b["indication"], "registeredTrialUrl": roster["sourceUrl"],
                "prospectiveCaptureDate": b["capturedOn"],
                "lastReviewDate": reviews["sourceAsOf"],
                "marketCapVendorUsdMillions": cap["usdMillions"],
                "marketCapVendorAsOf": cap["observedAsOf"],
                "marketCapCurrentValidation": "VENDOR_ONLY_NOT_INDEPENDENTLY_VERIFIED",
                "sourceStage": "PRE_READOUT_SOURCE_BASELINE_NOT_INDEPENDENTLY_VERIFIED",
                "readoutWindowAsReported": latest.get("valueText") or "",
                "readoutSourceUrl": latest["sourceUrl"],
                "stageAndPdufaIndependentlyVerified": False,
                "metricId": metric,
                "provisionalMetricScore": FINDING_SCORES[r["finding"]] if r else "",
                "reviewClass": (
                    "HUMAN_INDEPENDENT" if r and r["independentReview"] == "PASSED"
                    else "AI_SOURCE_CROSSCHECKED" if r else "N_A_MISSING_REVIEW"),
                "metricEvidenceSourceUrl": r["sourceUrl"] if r else "",
                "metricSourceDate": r["sourceDate"] if r else "",
                "benchmarkSourceUrl": r["benchmarkSourceUrl"] if r else "",
                "observedEvidence": r["observedResult"] if r else "",
                "uncertainty": r["uncertaintyReview"] if r else "",
                "criticalRisks": r["criticalRiskReview"] if r else "",
                "weightedCoverageAcross30Pct": roster["weightedMetricCoveragePct"],
                "observedMeanOnReviewedMetricsOnly": roster[
                    "observedMeanOnlyOnReviewedMetrics"],
                "missingMetricIds": roster["missingMetricIds"],
                "full30MetricRaasScore": "",
                "fdaPassCrlExtensionProbability": "",
                "interpretation": "PROSPECTIVE_TOP_PARTIAL_RESEARCH_NOT_AN_FDA_FORECAST"
            })
        if (roster["metricReviewsOf30"] !=
            sum(1 for x in records if x["nctId"] == nct and
                x["provisionalMetricScore"] != "")):
            raise ValueError("RAAS_PROSPECTIVE_PILOT_PARITY")
    total = len(records)
    scored = sum(r["provisionalMetricScore"] != "" for r in records)
    if total != len(seen_ncts) * 30 or (
        scored != sum(r["metricReviewsOf30"] for r in all_rows if
                      r["nctId"] in seen_ncts and r["stage"] == "PRE_RESEARCH_ONLY")):
        raise ValueError("RAAS_PROSPECTIVE_PILOT_SCORE_COUNT")
    summary = {
        "schemaVersion": 1,
        "scope": "RAAS_PROSPECTIVE_TOP_SOURCE_CROSSCHECKED_30_METRIC_PILOT",
        "sourceAsOf": reviews["sourceAsOf"],
        "baselineCapturedAsOf": baselines.get("sourceAsOf"),
        "researchTrialUniverse": full_status["researchTrials"],
        "prospectiveTrials": len(seen_ncts),
        "trialNcts": sorted(seen_ncts),
        "metricSlots": total,
        "provisionalScoredMetricSlots": scored,
        "unscoredMetricSlots": total - scored,
        "trialNctsWithProvisionalScores": len(ncts_with_grades),
        "fullValidatedRaasScores": 0,
        "calibratedFdaPredictions": 0,
        "warning": (
            "Source captured before clinical results for two prospective study IDs. "
            "Ordinal metric bands added during later review; not backdated predictions. "
            "Source-only pre-readout stage and vendor market cap not independently "
            "verified. No confirmed PDUFA dates, FDA outcomes or validated probability. "
            "Observed mean over reviewed metrics is NOT complete RAAS; missing are N/A."
        ),
    }
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for r in records:
        writer.writerow({k: _safe(r[k]) for k in FIELDS})
    return buf.getvalue(), json.dumps(summary, indent=2) + "\n"


def main() -> None:
    csv_text, status = generate(
        json.loads(BASELINES.read_text(encoding="utf8")),
        json.loads(REGISTRY.read_text(encoding="utf8")),
        json.loads(REVIEWS.read_text(encoding="utf8")),
        CATALOG.read_text(encoding="utf8"))
    CSV.write_text(csv_text, encoding="utf8")
    STATUS.write_text(status, encoding="utf8")
    print(status.strip())


if __name__ == "__main__":
    main()
