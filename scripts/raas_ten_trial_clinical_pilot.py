#!/usr/bin/env python3
"""Publish exact-NCT 10-trial *historical* research grade pilot.

There are 30 named metric slots in the post-readout research rubric per trial.
An AI-assisted published evidence review fills its specific slot. Every other
slot remains N/A. The clinical pilot is not current eligible Pipeline, a
pre-outcome prediction, calibration, full RAAS composite or investment signal.
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
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
REVIEWS = ROOT / "new-platform/frontend/data/raas-reviewed-metric-assessments.json"
OUTPUT = ROOT / "new-platform/frontend/public/raas-ten-trial-metric-pilot.csv"
STATUS = ROOT / "new-platform/frontend/data/raas-ten-trial-metric-pilot-status.json"
TRIALS = (
    "NCT06445023", "NCT06455202",  # CLDX paired Phase 3 sponsor readouts
    "NCT04576949", "NCT05206370",  # ACHV ORCA-2, ORCA-3
    "NCT03687372", "NCT03691831",  # ACRS THWART-1, THWART-2
    "NCT04770753", "NCT04770779",  # AGIO ENERGIZE and ENERGIZE-T
    "NCT04181723", "NCT03325556",  # ACAD trofinetide and pimavanserin
)
METRICS = tuple(f"post-{cat}-{item}" for cat in range(1, 7)
                for item in range(1, 6))
SCORE = {"MATERIAL_ADVERSE": 0, "BELOW_BENCHMARK": 25,
         "MIXED_EVIDENCE": 50, "ABOVE_BENCHMARK": 75,
         "EXCEPTIONAL_EVIDENCE": 100}
FIELDS = (
    "nctId", "ticker", "drug", "indication", "registryUrl", "registryPostedResults",
    "metricId", "metricReviewStatus", "provisionalMetricScore", "observedFinding",
    "sourceUrl", "sourceDate", "benchmarkSourceUrl", "benchmarkContext",
    "observedResult", "uncertaintyReview", "criticalRiskReview", "assessedAt",
    "humanIndependentReview", "full30of30Score", "fdaPassCrlExtensionProbability",
    "currentPipelineAndPdufaEligibility", "purpose"
)


def safe(cell: object) -> str:
    """Excel-safe untrusted source text; no spreadsheet-formula injection."""
    val = str(cell) if cell is not None else ""
    return "'" + val if val[:1] in ("=", "+", "-", "@") else val


def build(index: dict, reviews: dict) -> tuple[list[dict], dict]:
    if (index.get("scope") != "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX" or
        not isinstance(index.get("records"), list) or
        reviews.get("scope") != "RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY" or
        not isinstance(reviews.get("records"), list)):
        raise ValueError("RAAS_PILOT_SOURCE_SCOPE")
    registry = {}
    for trial in index["records"]:
        nct = trial.get("nctId")
        if nct in registry:
            raise ValueError("RAAS_PILOT_DUPLICATE_REGISTRY")
        registry[nct] = trial
    if not set(TRIALS).issubset(registry):
        raise ValueError("RAAS_PILOT_MISSING_NCT")
    grades = {}
    id_names = {}
    for r in reviews["records"]:
        nct = r.get("nctId")
        if nct not in TRIALS:
            continue
        if (r.get("stage") != "post" or r.get("metricId") not in METRICS or
            r.get("ticker") != registry[nct].get("ticker") or
            not str(r.get("drug") or "").strip() or
            not str(r.get("indication") or "").strip() or
            r.get("independentReview") not in
                ("AI_SOURCE_CROSSCHECKED", "PASSED") or
            r.get("finding") not in SCORE or
            r.get("sourceUrl", "").startswith("https://") is not True or
            r.get("benchmarkSourceUrl", "").startswith("https://") is not True or
            r.get("sourceUrl") == r.get("benchmarkSourceUrl") or
            not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.get("sourceDate"))) or
            not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.get("assessedAt"))) or
            r["sourceDate"] > r["assessedAt"] or
            r["assessedAt"] > str(reviews.get("sourceAsOf"))):
            raise ValueError("RAAS_PILOT_INVALID_REVIEW")
        key = nct, r["metricId"]
        if key in grades:
            raise ValueError("RAAS_PILOT_DUPLICATE_METRIC")
        identity = (r["drug"].strip().casefold(), r["indication"].strip().casefold())
        if nct in id_names and id_names[nct] != identity:
            raise ValueError("RAAS_PILOT_MULTIPLE_DRUGS_IN_SAME_NCT")
        grades[key] = r
        id_names[nct] = identity
    if set(id_names) != set(TRIALS):
        raise ValueError("RAAS_PILOT_INCOMPLETE_TEN_TRIAL_REVIEW")
    out = []
    for nct in TRIALS:
        e = registry[nct]
        identity = next(grades[(nct, metric)] for metric in METRICS
                        if (nct, metric) in grades)
        for metric in METRICS:
            r = grades.get((nct, metric))
            out.append({
                "nctId": nct, "ticker": e["ticker"],
                "drug": identity["drug"], "indication": identity["indication"],
                "registryUrl": e["sourceUrl"],
                "registryPostedResults": e["postedResults"],
                "metricId": metric,
                "metricReviewStatus": (
                    "HUMAN_INDEPENDENT_REVIEW" if r and
                    r["independentReview"] == "PASSED" else
                    "AI_SOURCE_CROSSCHECKED_RESEARCH_ONLY" if r else
                    "UNSCORED_MISSING_INDEPENDENT_EVIDENCE"),
                "provisionalMetricScore": SCORE[r["finding"]] if r else "",
                "observedFinding": r["finding"] if r else "",
                "sourceUrl": r["sourceUrl"] if r else "",
                "sourceDate": r["sourceDate"] if r else "",
                "benchmarkSourceUrl": r["benchmarkSourceUrl"] if r else "",
                "benchmarkContext": r["benchmarkContext"] if r else "",
                "observedResult": r["observedResult"] if r else "",
                "uncertaintyReview": r["uncertaintyReview"] if r else "",
                "criticalRiskReview": r["criticalRiskReview"] if r else "",
                "assessedAt": r["assessedAt"] if r else "",
                "humanIndependentReview": r["independentReview"] == "PASSED" if r else False,
                "full30of30Score": "",
                "fdaPassCrlExtensionProbability": "",
                "currentPipelineAndPdufaEligibility": "NOT_INDEPENDENTLY_VERIFIED",
                "purpose": "RETROSPECTIVE_PILOT_NOT_PREDICTIVE_VALIDATION"
            })
    count = Counter(row["metricReviewStatus"] for row in out)
    status = {
        "schemaVersion": 1,
        "scope": "RAAS_TEN_HISTORICAL_TRIAL_30_METRIC_PARTIAL_SCORES_NOT_PREDICTIONS",
        "reviewSourceAsOf": reviews["sourceAsOf"],
        "registrySourceAsOf": index.get("sourceAsOf"),
        "pilotNctCount": len(TRIALS),
        "metricSlots": len(out),
        "aiSourceReviewedMetricSlots":
            count["AI_SOURCE_CROSSCHECKED_RESEARCH_ONLY"],
        "humanIndependentReviewedMetricSlots":
            count["HUMAN_INDEPENDENT_REVIEW"],
        "unscoredMetricSlots":
            count["UNSCORED_MISSING_INDEPENDENT_EVIDENCE"],
        "complete30MetricTrials": 0,
        "calibratedFdaPredictions": 0,
        "pilotTrialNcts": list(TRIALS),
        "warning": "Historical purposively chosen clinical studies, not the current capital-screened Pipeline. No holdout validation. Some historical FDA outcomes are already known. Provisional metric numbers cannot be averaged to produce 30/30 RAAS, probability of FDA approval, CRL/extension, or financial return. All missing inputs are N/A, not 0."
    }
    return out, status


def generate(index: dict, reviews: dict) -> tuple[str, str]:
    rows, status = build(index, reviews)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k:safe(v) for k,v in row.items()})
    return buffer.getvalue(), json.dumps(status, indent=2)+"\n"


def main() -> None:
    csv_out, status_out = generate(
        json.loads(INDEX.read_text(encoding="utf8")),
        json.loads(REVIEWS.read_text(encoding="utf8")))
    OUTPUT.write_text(csv_out, encoding="utf8")
    STATUS.write_text(status_out, encoding="utf8")
    print(status_out.strip())


if __name__ == "__main__":
    main()
