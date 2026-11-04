#!/usr/bin/env python3
"""Publish source-only quantitative RAAS clinical evidence components for all NCTs.

A numeric 0-100 reporting-completeness grade is objective evidence DOCUMENTATION,
not scientific merit, treatment efficacy, risk/benefit, FDA approval, valuation,
investment signals, or a component eligible for a full 30/30 RAAS composite.

Never identify a treatment arm from an opaque registry group ID. Never infer
between-treatment effects from a p-value or a single-group response. No missing
factual source data becomes a zero efficacy or safety score.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
SUMMARY = ROOT / "new-platform/frontend/data/raas-clinical-evidence-components-status.json"
COMPONENTS = ROOT / "new-platform/frontend/public/raas-clinical-evidence-components.csv"
COMPARISONS = ROOT / "new-platform/frontend/public/raas-primary-comparisons.csv"
SAFETY = ROOT / "new-platform/frontend/public/raas-serious-event-rates.csv"
NCT = re.compile(r"NCT\d{8}\Z")

COMPONENT_FIELDS = (
    "nctId", "ticker", "sourceUrl", "registryResultsPosted", "registrySourceAsOf",
    "reportingCompletenessDiagnosticScore", "documentedFeaturesOf5",
    "missingFeaturesOf5", "primaryMeasurementsDocumented",
    "groupComparisonDocumented", "confidenceIntervalDocumented",
    "statisticalResultDocumented", "safetyRateDenominatorsDocumented",
    "primaryComparisonRows", "seriousEventRateRows", "overallRaasScore",
    "interpretation"
)
COMPARE_FIELDS = (
    "nctId", "ticker", "sourceUrl", "registrySourceAsOf", "outcomeIndex",
    "outcomeTitle", "outcomeTimeFrame", "outcomeUnit", "analysisIndex",
    "groupIdsAsReported", "analysisMethod", "parameterType", "parameterValueAsReported",
    "pValueAsReported", "confidenceLevelAsReported", "confidenceLowerAsReported",
    "confidenceUpperAsReported", "interpretation"
)
SAFETY_FIELDS = (
    "nctId", "ticker", "sourceUrl", "registrySourceAsOf", "term",
    "groupIdAsReported", "numAffected", "numAtRisk",
    "numEventsAsReported", "observedAffectedRatePercent",
    "interpretation"
)
SOURCE_ONLY = ("OBSERVED_REGISTRY_DOCUMENTATION_NOT_CLINICAL_OR_FDA_RAAS")
NO_INFERENCE = ("GROUP_IDENTITIES_AND_ENDPOINT_DIRECTION_NOT_ADJUDICATED")


def _csv(rows: list[dict], fields: tuple[str, ...]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _numeric_string(raw: object) -> bool:
    return isinstance(raw, str) and bool(re.fullmatch(
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?", raw.strip(), re.I))


def _safe_interval(analysis: dict) -> bool:
    lo = analysis.get("ciLowerLimit")
    hi = analysis.get("ciUpperLimit")
    return _numeric_string(lo) and _numeric_string(hi)


def _valid_sae_group(group: dict) -> bool:
    a, risk = group.get("numAffected"), group.get("numAtRisk")
    return (isinstance(a, int) and not isinstance(a, bool) and
            isinstance(risk, int) and not isinstance(risk, bool) and
            0 < risk <= 1000000 and 0 <= a <= risk)


def build_components(index: dict) -> tuple[list[dict], list[dict], list[dict], dict]:
    if (index.get("schemaVersion") != 1 or
        index.get("scope") != "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX" or
        not isinstance(index.get("records"), list) or
        index.get("summary", {}).get("researchNcts") != len(index["records"])):
        raise ValueError("RAAS_CLINICAL_COMPONENT_INVALID_INDEX")
    snapshot = index.get("sourceAsOf")
    if not isinstance(snapshot, str) or not snapshot:
        raise ValueError("RAAS_CLINICAL_COMPONENT_SOURCE_DATE_MISSING")
    components, comparisons, safety = [], [], []
    ids = set()
    for e in sorted(index["records"], key=lambda r: (r.get("ticker", ""), r.get("nctId", ""))):
        nct, ticker = e.get("nctId"), e.get("ticker")
        if (not isinstance(nct, str) or not NCT.fullmatch(nct) or
            nct in ids or not isinstance(ticker, str) or not ticker.strip() or
            e.get("sourceUrl") != f"https://clinicaltrials.gov/study/{nct}" or
            not isinstance(e.get("postedResults"), bool)):
            raise ValueError("RAAS_CLINICAL_COMPONENT_TRIAL_IDENTITY")
        ids.add(nct)
        posted = e["postedResults"]
        primary = e.get("primaryResults") or []
        events = e.get("seriousEventDetails") or []
        if not posted and (primary or events or e.get("postedPrimaryOutcomeCount", 0)):
            raise ValueError("RAAS_CLINICAL_COMPONENT_UNPUBLISHED_CLAIM")
        measured = contrasted = intervals = statistics = rates = False
        count_comparison = count_safety = 0
        if posted:
            for oi, outcome in enumerate(primary, 1):
                if not isinstance(outcome, dict):
                    raise ValueError("RAAS_CLINICAL_COMPONENT_BAD_OUTCOME")
                measured |= bool(outcome.get("measurements"))
                for ai, a in enumerate(outcome.get("comparisons") or [], 1):
                    gids = a.get("groupIds") or []
                    # Without two explicitly identified groups, a numeric
                    # parameter is NOT an interpretable group comparison.
                    if not isinstance(gids, list) or len(gids) < 2 or not all(
                        isinstance(g, str) and g.strip() for g in gids
                    ):
                        continue
                    contrasted = True
                    intervals |= _safe_interval(a)
                    statistics |= bool(str(a.get("pValue") or "").strip() or
                                       _numeric_string(a.get("paramValue")))
                    comparisons.append({
                        "nctId": nct, "ticker": ticker, "sourceUrl": e["sourceUrl"],
                        "registrySourceAsOf": snapshot, "outcomeIndex": oi,
                        "outcomeTitle": outcome.get("title", ""),
                        "outcomeTimeFrame": outcome.get("timeFrame", ""),
                        "outcomeUnit": outcome.get("unit", ""),
                        "analysisIndex": ai, "groupIdsAsReported": ";".join(gids),
                        "analysisMethod": a.get("method") or "",
                        "parameterType": a.get("paramType") or "",
                        "parameterValueAsReported": a.get("paramValue") or "",
                        "pValueAsReported": a.get("pValue") or "",
                        "confidenceLevelAsReported": a.get("ciPctValue") or "",
                        "confidenceLowerAsReported": a.get("ciLowerLimit") or "",
                        "confidenceUpperAsReported": a.get("ciUpperLimit") or "",
                        "interpretation": NO_INFERENCE
                    })
                    count_comparison += 1
            for event in events:
                for group in event.get("groups") or []:
                    if not _valid_sae_group(group):
                        continue
                    # Group IDs are copied exactly; no invented treatment
                    # assignment or treatment-relative risk is calculated.
                    affected, denominator = group["numAffected"], group["numAtRisk"]
                    rates = True
                    safety.append({
                        "nctId": nct, "ticker": ticker, "sourceUrl": e["sourceUrl"],
                        "registrySourceAsOf": snapshot,
                        "term": event.get("term") or "",
                        "groupIdAsReported": group.get("groupId") or "",
                        "numAffected": affected, "numAtRisk": denominator,
                        "numEventsAsReported": (
                            group.get("numEvents") if isinstance(group.get("numEvents"), int)
                            and not isinstance(group["numEvents"], bool) else ""),
                        "observedAffectedRatePercent": round(100 * affected / denominator, 2),
                        "interpretation": NO_INFERENCE
                    })
                    count_safety += 1
        features = (measured, contrasted, intervals, statistics, rates)
        documented = sum(features)
        components.append({
            "nctId": nct, "ticker": ticker, "sourceUrl": e["sourceUrl"],
            "registryResultsPosted": posted, "registrySourceAsOf": snapshot,
            "reportingCompletenessDiagnosticScore": documented * 20 if posted else "",
            "documentedFeaturesOf5": documented if posted else "",
            "missingFeaturesOf5": 5 - documented if posted else "",
            "primaryMeasurementsDocumented": measured,
            "groupComparisonDocumented": contrasted,
            "confidenceIntervalDocumented": intervals,
            "statisticalResultDocumented": statistics,
            "safetyRateDenominatorsDocumented": rates,
            "primaryComparisonRows": count_comparison,
            "seriousEventRateRows": count_safety,
            "overallRaasScore": "",
            "interpretation": SOURCE_ONLY if posted else
                "PROTOCOL_ONLY_NOT_ELIGIBLE_FOR_POSTED_RESULTS_GRADE"
        })
    status = {
        "schemaVersion": 1,
        "scope": "RAAS_SOURCE_DOCUMENTATION_AND_QUANTITATIVE_FACTS_NOT_OVERALL_RATINGS",
        "sourceAsOf": snapshot,
        "researchTrials": len(components),
        "trialsWithPostedResults": sum(bool(r["registryResultsPosted"]) for r in components),
        "trialsWithExperimentalReportingDiagnostic": sum(
            isinstance(r["reportingCompletenessDiagnosticScore"], int) for r in components),
        "trialsWithPrimaryGroupComparisons": sum(
            bool(r["groupComparisonDocumented"]) for r in components),
        "trialsWithConfidenceIntervalData": sum(
            bool(r["confidenceIntervalDocumented"]) for r in components),
        "trialsWithObservedSafetyGroupRates": sum(
            bool(r["safetyRateDenominatorsDocumented"]) for r in components),
        "primaryGroupComparisonRows": len(comparisons),
        "observedSeriousEventGroupRateRows": len(safety),
        "fullValidatedRaasScores": 0,
        "warning": "Five-feature completeness grade rates SOURCE REPORTING, not benefit or risk. The arm contrasts and serious-event rates are raw per-group facts, not drug-versus-placebo effects. No cohort entry gains a validated FDA, safety, clinical success or full 30/30 RAAS score."
    }
    return components, comparisons, safety, status


def generate(index: dict) -> tuple[str, str, str, str]:
    components, comparisons, safety, status = build_components(index)
    return (_csv(components, COMPONENT_FIELDS), _csv(comparisons, COMPARE_FIELDS),
            _csv(safety, SAFETY_FIELDS), json.dumps(status, indent=2) + "\n")


def main() -> None:
    components, comparisons, safety, status = generate(
        json.loads(INDEX.read_text(encoding="utf-8")))
    for path, value in ((COMPONENTS, components), (COMPARISONS, comparisons),
                        (SAFETY, safety), (SUMMARY, status)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    print(status.strip())


if __name__ == "__main__":
    main()
