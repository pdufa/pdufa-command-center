#!/usr/bin/env python3
"""Produce the 762-trial, two-stage RAAS evidence REVIEW worklist.

Source readiness and submitted reviews are NOT validated numeric RAAS scores,
confirmed TOP/BOTTOM readouts, or proof of Pipeline/PDUFA eligibility.
Never infer a readout stage from ClinicalTrials.gov results-posting status.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")


import csv
import io
import json
from collections import defaultdict
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
REVIEWS = ROOT / "new-platform/frontend/data/raas-reviewed-metric-assessments.json"
WORKLIST = ROOT / "new-platform/frontend/public/raas-source-review-worklist.csv"
STATUS = ROOT / "new-platform/frontend/data/raas-source-review-worklist-status.json"
ID = re.compile(r"NCT\d{8}\Z")
STAGES = ("pre", "post")
METRICS = {s: tuple(f"{s}-{cat}-{i}" for cat in range(1, 7)
                    for i in range(1, 6)) for s in STAGES}
FIELDS = ("nctId", "ticker", "researchStage", "stageIndependentlyVerified",
          "registryEvidenceState", "sourceUrl", "hasPrimaryDefinitions",
          "hasPostedResults", "hasPrimaryMeasurements", "hasGroupComparisons",
          "hasConfidenceIntervals", "hasSafetyDenominators",
          "submittedMetricReviews", "aiSourceCrosscheckedGrades",
          "independentMetricReviews", "missingMetricReviewCount",
          "missingMetricIds", "reviewIdentityState", "sourceReviewPriority",
          "nextReviewAction")


def build_worklist(index: dict, reviews: dict) -> tuple[list[dict], dict]:
    if (index.get("schemaVersion") != 1 or
        index.get("scope") != "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX"):
        raise ValueError("RAAS_WORKLIST_INDEX_SCOPE")
    if (reviews.get("schemaVersion") != 1 or
        reviews.get("scope") != "RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY"):
        raise ValueError("RAAS_WORKLIST_REVIEW_SCOPE")
    source = index.get("records")
    entries = reviews.get("records")
    if not isinstance(source, list) or not isinstance(entries, list):
        raise ValueError("RAAS_WORKLIST_SOURCE_SHAPE")
    if len(source) != index.get("summary", {}).get("researchNcts"):
        raise ValueError("RAAS_WORKLIST_SOURCE_COUNT")
    roster = {}
    for e in source:
        nct, ticker = e.get("nctId"), e.get("ticker")
        if (not isinstance(nct, str) or not ID.fullmatch(nct) or
            not isinstance(ticker, str) or not ticker.strip() or
            nct in roster or
            e.get("sourceUrl") != "https://clinicaltrials.gov/study/" + nct or
            not isinstance(e.get("postedResults"), bool)):
            raise ValueError("RAAS_WORKLIST_TRIAL_IDENTITY")
        roster[nct] = e

    # Submitted reviews are an INPUT COUNT, not independent validation. Only
    # one unambiguous drug+indication identity may contribute to a row count.
    grouped = defaultdict(lambda: defaultdict(set))
    ai_grouped = defaultdict(lambda: defaultdict(set))
    independent_grouped = defaultdict(lambda: defaultdict(set))
    for review in entries:
        nct = review.get("nctId")
        stage = review.get("stage")
        metric = review.get("metricId")
        ticker = review.get("ticker")
        if (nct not in roster or ticker != roster[nct]["ticker"] or
            review.get("independentReview") not in ("PASSED", "AI_SOURCE_CROSSCHECKED") or
            stage not in STAGES or metric not in METRICS[stage] or
            not str(review.get("drug") or "").strip() or
            not str(review.get("indication") or "").strip()):
            raise ValueError("RAAS_WORKLIST_REVIEW_CROSS_TRIAL")
        program = (review["drug"].strip().casefold(),
                   review["indication"].strip().casefold())
        if metric in grouped[(nct, stage)][program]:
            raise ValueError("RAAS_WORKLIST_DUPLICATE_REVIEW")
        grouped[(nct, stage)][program].add(metric)
        target = (independent_grouped if review["independentReview"] == "PASSED"
                  else ai_grouped)
        target[(nct, stage)][program].add(metric)

    rows = []
    for nct in sorted(roster):
        e = roster[nct]
        outcomes = e.get("primaryResults") or []
        measured = any(o.get("measurements") for o in outcomes)
        contrasted = any(any(len(a.get("groupIds") or []) >= 2
                             for a in o.get("comparisons") or [])
                         for o in outcomes)
        intervals = any(any(a.get("ciLowerLimit") not in ("", None) and
                                a.get("ciUpperLimit") not in ("", None)
                                for a in o.get("comparisons") or [])
                        for o in outcomes)
        safety = any(any(isinstance(g.get("numAffected"), int) and
                              not isinstance(g.get("numAffected"), bool) and
                              isinstance(g.get("numAtRisk"), int) and
                              not isinstance(g.get("numAtRisk"), bool) and
                              0 < g["numAtRisk"] >= g["numAffected"] >= 0
                              for g in event.get("groups") or [])
                         for event in e.get("seriousEventDetails") or [])
        for stage in STAGES:
            programs = grouped.get((nct, stage), {})
            ambiguous = len(programs) > 1
            submitted = next(iter(programs.values())) if len(programs) == 1 else set()
            program = next(iter(programs)) if len(programs) == 1 else None
            ai = ai_grouped.get((nct, stage), {}).get(program, set())
            independent = independent_grouped.get((nct, stage), {}).get(program, set())
            missing = [m for m in METRICS[stage] if m not in submitted]
            if stage == "post" and e["postedResults"] and contrasted and safety:
                priority = "1_POSTED_COMPARISON_AND_SAFETY_REVIEW"
            elif stage == "post" and e["postedResults"]:
                priority = "2_POSTED_RESULTS_REVIEW"
            elif stage == "pre":
                priority = "3_PROTOCOL_AND_PRE_READOUT_REVIEW"
            else:
                priority = "4_PUBLIC_RESULTS_NOT_POSTED"
            action = ("Resolve conflicting drug/indication review identities"
                      if ambiguous else
                      "Verify issuer readout timing and independently review each missing "
                      "metric against primary sources, disease-specific benchmarks, "
                      "uncertainty and critical risks")
            rows.append({
                "nctId": nct,
                "ticker": e["ticker"],
                "researchStage": "TOP_RESEARCH_ONLY" if stage == "pre" else "BOTTOM_RESEARCH_ONLY",
                "stageIndependentlyVerified": "NOT_ASSESSED_IN_REGISTRY",
                "registryEvidenceState": e.get("evidenceState", ""),
                "sourceUrl": e["sourceUrl"],
                "hasPrimaryDefinitions": bool(e.get("primaryDefinitions")),
                "hasPostedResults": e["postedResults"],
                "hasPrimaryMeasurements": bool(measured),
                "hasGroupComparisons": bool(contrasted),
                "hasConfidenceIntervals": bool(intervals),
                "hasSafetyDenominators": bool(safety),
                "submittedMetricReviews": len(submitted),
                "aiSourceCrosscheckedGrades": len(ai),
                "independentMetricReviews": len(independent),
                "missingMetricReviewCount": len(missing),
                "missingMetricIds": ";".join(missing),
                "reviewIdentityState": ("AMBIGUOUS_PROGRAM" if ambiguous else
                                        "ONE_SUBMITTED_PROGRAM" if programs else
                                        "NONE_SUBMITTED"),
                "sourceReviewPriority": priority,
                "nextReviewAction": action,
            })
    rows.sort(key=lambda r: (r["sourceReviewPriority"], r["nctId"],
                             r["researchStage"]))
    summary = {
        "schemaVersion": 1,
        "scope": "RAAS_TRIAL_STAGE_SOURCE_REVIEW_WORKLIST_NOT_SCORES",
        "sourceAsOf": index.get("sourceAsOf"),
        "researchTrials": len(roster),
        "trialStageReviewRows": len(rows),
        "submittedMetricReviewRecords": len(entries),
        "aiSourceCrosscheckedGradeRecords": sum(
            r["aiSourceCrosscheckedGrades"] for r in rows),
        "independentMetricReviewRecords": sum(
            r["independentMetricReviews"] for r in rows),
        "stageRowsWithThirtyIndependentReviews": sum(
            r["independentMetricReviews"] == 30 for r in rows),
        "stageRowsWithThirtySubmittedReviews": sum(
            r["submittedMetricReviews"] == 30 for r in rows),
        "sourceReviewPriorityOneRows": sum(
            r["sourceReviewPriority"].startswith("1_") for r in rows),
        "unambiguousProgramReviewRows": sum(
            r["reviewIdentityState"] == "ONE_SUBMITTED_PROGRAM" for r in rows),
        "caution": "Priorities identify collected evidence for review. No row asserts independently verified TOP/BOTTOM stage or validated numeric RAAS/PDUFA probability.",
    }
    if len(rows) != 2 * len(roster):
        raise ValueError("RAAS_WORKLIST_STAGE_COVERAGE")
    return rows, summary


def generate(index: dict, reviews: dict) -> tuple[str, str]:
    rows, status = build_worklist(index, reviews)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue(), json.dumps(status, indent=2) + "\n"


def main() -> None:
    csv_text, summary_text = generate(json.loads(INDEX.read_text(encoding="utf-8")),
                                      json.loads(REVIEWS.read_text(encoding="utf-8")))
    WORKLIST.parent.mkdir(parents=True, exist_ok=True)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    WORKLIST.write_text(csv_text, encoding="utf-8")
    STATUS.write_text(summary_text, encoding="utf-8")
    print(summary_text.strip())


if __name__ == "__main__":
    main()
