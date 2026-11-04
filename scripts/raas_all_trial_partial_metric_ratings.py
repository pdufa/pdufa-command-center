#!/usr/bin/env python3
"""Publish partial *reviewed-metric* RAAS grades for all exact-NCT research trials.

Unlike registry study-design and documentation diagnostics, these are numerical
provisional findings against individually cited clinical/financial benchmarks
from the explicit RAAS review feed. A 30-metric score is NEVER extrapolated
from a smaller number of reviewed inputs. No PDUFA, FDA or market forecast is
computed. Protocol/results state is not independently verified TOP/BOTTOM.
"""
from __future__ import annotations

from collections import defaultdict
import csv
import io
import json
from pathlib import Path
import re

from raas_review_worklist import build_worklist

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
REVIEWS = ROOT / "new-platform/frontend/data/raas-reviewed-metric-assessments.json"
CATALOG = ROOT / "new-platform/frontend/lib/raas-metric-specs.ts"
OUTPUT = ROOT / "new-platform/frontend/public/raas-all-trials-partial-metric-ratings.csv"
STATUS = ROOT / "new-platform/frontend/data/raas-all-trials-partial-metric-ratings-status.json"

# Provisional findings are ordinal research bands and require exact source
# review. An unreviewed metric is null, not scored as zero or neutral.
SCORE = {
    "MATERIAL_ADVERSE": 0,
    "BELOW_BENCHMARK": 25,
    "MIXED_EVIDENCE": 50,
    "ABOVE_BENCHMARK": 75,
    "EXCEPTIONAL_EVIDENCE": 100,
}
STAGES = ("pre", "post")
FIELDS = (
    "nctId", "ticker", "sourceUrl", "registryStatus",
    "registryResultsPosted", "stage", "readoutStageVerification",
    "metricReviewsOf30", "aiCrosscheckedMetricsOf30",
    "independentlyReviewedMetricsOf30", "weightedMetricCoveragePct",
    "observedMeanOnlyOnReviewedMetrics", "reviewedMetricContributionOf100",
    "missingMetricIds", "gradedMetricIdAndScorePairs",
    "unscoredMetricCountOf30", "full30MetricRaasScore",
    "fdaPassCrlExtensionProbability", "eligibleActive300mTo10bPipeline",
    "interpretation",
)


def metric_weights(catalog: str) -> dict[str, dict[str, float]]:
    """Parse 6 category weights per stage from the versioned TS metric catalog.

    Fail closed when the catalog drifts rather than silently producing
    incorrect financial/clinical weighting.
    """
    stages = {}
    for stage in STAGES:
        start = catalog.find(f'  "{stage}": [')
        if start < 0:
            raise ValueError("RAAS_PARTIAL_MISSING_STAGE_CATALOG")
        end = catalog.find('  "post": [', start + 1) if stage == "pre" else -1
        segment = catalog[start:end if end > 0 else None]
        weights = [int(n) for n in re.findall(r'"weight":\s*(\d+)', segment)]
        if len(weights) != 6 or sum(weights) != 100 or any(
            not 0 < w < 100 for w in weights
        ):
            raise ValueError("RAAS_PARTIAL_CATEGORY_WEIGHTS_INVALID")
        stages[stage] = {
            f"{stage}-{cat}-{item}": weights[cat - 1] / 5
            for cat in range(1, 7) for item in range(1, 6)
        }
    return stages


def _as_review(record: dict, roster: dict[str, dict],
               weights: dict[str, dict[str, float]],
               review_date: str) -> tuple[tuple[str, str], tuple[str, str], dict]:
    nct = record.get("nctId")
    stage = record.get("stage")
    if (nct not in roster or stage not in STAGES or
        record.get("ticker") != roster[nct]["ticker"] or
        record.get("metricId") not in weights[stage] or
        record.get("independentReview") not in ("PASSED", "AI_SOURCE_CROSSCHECKED") or
        record.get("finding") not in SCORE or
        not str(record.get("drug") or "").strip() or
        not str(record.get("indication") or "").strip() or
        not isinstance(record.get("assessedAt"), str) or
        record["assessedAt"] > review_date or
        not isinstance(record.get("sourceDate"), str) or
        record["sourceDate"] > record["assessedAt"] or
        not str(record.get("sourceUrl") or "").startswith("https://") or
        not str(record.get("benchmarkSourceUrl") or "").startswith("https://") or
        record["sourceUrl"] == record["benchmarkSourceUrl"] or
        not str(record.get("observedResult") or "").strip() or
        not str(record.get("uncertaintyReview") or "").strip() or
        not str(record.get("criticalRiskReview") or "").strip()):
        raise ValueError("RAAS_PARTIAL_REVIEW_EVIDENCE_INVALID")
    return (nct, stage), (record["drug"].strip().casefold(),
                          record["indication"].strip().casefold()), record


def build(index: dict, reviews: dict, catalog: str) -> tuple[list[dict], dict]:
    # Reuses rigorous exact-NCT source identity and review checks of the
    # full research review worklist. No trial can be silently dropped.
    worklist, status = build_worklist(index, reviews)
    if len(worklist) != 2 * status["researchTrials"]:
        raise ValueError("RAAS_PARTIAL_WORKLIST_COUNT_MISMATCH")
    weights = metric_weights(catalog)
    roster = {e["nctId"]: e for e in index["records"]}
    if len(roster) != status["researchTrials"]:
        raise ValueError("RAAS_PARTIAL_DUPLICATE_TRIAL")
    if not isinstance(reviews.get("sourceAsOf"), str):
        raise ValueError("RAAS_PARTIAL_REVIEW_SOURCE_DATE")
    submitted: dict[tuple[str, str], dict[tuple[str, str], list[dict]]] = \
        defaultdict(lambda: defaultdict(list))
    for r in reviews["records"]:
        trial_stage, program, review = _as_review(
            r, roster, weights, reviews["sourceAsOf"])
        submitted[trial_stage][program].append(review)
    out = []
    for e in sorted(index["records"], key=lambda x: (x["ticker"], x["nctId"])):
        nct = e["nctId"]
        for stage in STAGES:
            programs = submitted.get((nct, stage), {})
            # Never combine two drugs/indications associated with one NCT.
            ambiguity = len(programs) > 1
            candidates = next(iter(programs.values())) if len(programs) == 1 else []
            chosen = {}
            for r in candidates:
                mid = r["metricId"]
                if mid in chosen:
                    raise ValueError("RAAS_PARTIAL_DUPLICATE_REVIEW")
                chosen[mid] = r
            metric_ids = sorted(weights[stage])
            missing = [metric for metric in metric_ids if metric not in chosen]
            covered = sum(weights[stage][metric] for metric in chosen)
            contribution = sum(
                weights[stage][metric] * SCORE[record["finding"]] / 100
                for metric, record in chosen.items()
            )
            if not 0 <= covered <= 100 or not 0 <= contribution <= covered:
                raise ValueError("RAAS_PARTIAL_WEIGHT_BOUNDS")
            ai = sum(r["independentReview"] == "AI_SOURCE_CROSSCHECKED"
                     for r in chosen.values())
            independent = len(chosen) - ai
            observed_mean = round(100 * contribution / covered, 1) if covered else ""
            out.append({
                "nctId": nct,
                "ticker": e["ticker"],
                "sourceUrl": e["sourceUrl"],
                "registryStatus": e.get("registryStatus") or "",
                "registryResultsPosted": e["postedResults"],
                "stage": stage.upper() + "_RESEARCH_ONLY",
                "readoutStageVerification": "NOT_VERIFIED_FROM_REGISTRY",
                "metricReviewsOf30": len(chosen),
                "aiCrosscheckedMetricsOf30": ai,
                "independentlyReviewedMetricsOf30": independent,
                "weightedMetricCoveragePct": round(covered, 2),
                # This is a *conditional mean only over reviewed metrics*,
                # NOT a full RAAS rating, prediction or probability.
                "observedMeanOnlyOnReviewedMetrics": observed_mean,
                "reviewedMetricContributionOf100": round(contribution, 2),
                "missingMetricIds": ";".join(missing),
                "gradedMetricIdAndScorePairs": ";".join(
                    f"{mid}:{SCORE[chosen[mid]['finding']]}"
                    for mid in metric_ids if mid in chosen),
                "unscoredMetricCountOf30": len(missing),
                "full30MetricRaasScore": "",
                "fdaPassCrlExtensionProbability": "",
                "eligibleActive300mTo10bPipeline": "NOT_VERIFIED",
                "interpretation": (
                    "CONFLICTING_PROGRAM_IDENTITIES_NOT_SCORED" if ambiguity
                    else "PARTIAL_REVIEWED_METRIC_MEAN_NOT_FULL_RAAS_OR_FDA" if covered
                    else "NO_PROVISIONALLY_REVIEWED_METRICS")
            })
    total = len(out)
    numeric = [r for r in out if r["metricReviewsOf30"]]
    summary = {
        "schemaVersion": 1,
        "scope": "RAAS_ALL_NCTS_PARTIAL_BENCHMARK_REVIEWED_METRICS_NOT_FDA_PREDICTIONS",
        "registrySourceAsOf": index.get("sourceAsOf"),
        "reviewSourceAsOf": reviews["sourceAsOf"],
        "researchTrials": status["researchTrials"],
        "trialStageRows": total,
        "reviewedMetricRecords": sum(r["metricReviewsOf30"] for r in out),
        "trialStageRowsWithActualProvisionalMetricScores": len(numeric),
        "uniqueNctsWithActualProvisionalMetricScores": len(
            {r["nctId"] for r in numeric}),
        "totalAiCrosscheckedMetricReviews": sum(
            r["aiCrosscheckedMetricsOf30"] for r in out),
        "totalIndependentMetricReviews": sum(
            r["independentlyReviewedMetricsOf30"] for r in out),
        "fullValidatedRaasScores": 0,
        "calibratedFdaPredictions": 0,
        "warning": (
            "Observed mean is calculated only over the 1-30 individually reviewed "
            "ordinal metric findings. Weighted coverage is the fraction of the "
            "30-metric specification covered by these reviews, not probability. "
            "A mean of 75 with 5% covered is NOT an overall RAAS of 75. "
            "No missing metrics imputed as zero, neutral or favorable. "
            "All registry stages and $300M-$10B current PDUFA Pipeline eligibility "
            "remain separately unverified. No FDA PASS/CRL/extension forecast."
        )
    }
    if total != 2 * status["researchTrials"] or (
        summary["reviewedMetricRecords"] !=
        status["submittedMetricReviewRecords"]):
        raise ValueError("RAAS_PARTIAL_REVIEW_OR_COHORT_PARITY")
    return out, summary


def _excel_safe(value: object) -> str:
    text = str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def generate(index: dict, reviews: dict, catalog: str) -> tuple[str, str]:
    rows, status = build(index, reviews, catalog)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _excel_safe(row[key]) for key in FIELDS})
    return buf.getvalue(), json.dumps(status, indent=2) + "\n"


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf8"))
    assessments = json.loads(REVIEWS.read_text(encoding="utf8"))
    catalog = CATALOG.read_text(encoding="utf8")
    csv_file, status = generate(data, assessments, catalog)
    OUTPUT.write_text(csv_file, encoding="utf8")
    STATUS.write_text(status, encoding="utf8")
    print(status.strip())


if __name__ == "__main__":
    main()
