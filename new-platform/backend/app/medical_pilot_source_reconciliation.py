"""Research-only source-count reconciliation for the ACACIA-HCM pilot.

This module checks arithmetic and disagreement among ORIGINAL REPORTS, not
clinical event adjudication, source completeness, independent reviewer grades,
causal safety inference or FDA prediction. Do not feed these flags to a
clinical score or FDA probability model.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

PILOT = "NCT06081894"


@dataclass(frozen=True)
class CountCitation:
    source_url: str
    outcome_definition: str
    treated: int
    treated_denominator: int
    control: int
    control_denominator: int
    published_treated_percent: Decimal | None
    published_control_percent: Decimal | None
    source_context: str


def _percent(n: int, d: int) -> Decimal:
    return (Decimal(n) * Decimal(100) / Decimal(d)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _validate(report: CountCitation) -> None:
    if not isinstance(report, CountCitation):
        raise ValueError("An explicitly attributed source record is required")
    if not isinstance(report.source_url, str) or not report.source_url.startswith("https://"):
        raise ValueError("An original HTTPS source locator is required")
    if not isinstance(report.outcome_definition, str) or len(report.outcome_definition.strip()) < 10:
        raise ValueError("Exact reported outcome-definition context is required")
    if not isinstance(report.source_context, str) or len(report.source_context.strip()) < 15:
        raise ValueError("The source observation window and population caveat must be recorded")
    for num, denominator in ((report.treated, report.treated_denominator),
                             (report.control, report.control_denominator)):
        if type(num) is not int or type(denominator) is not int or not 0 <= num <= denominator or denominator <= 0:
            raise ValueError("Counts must be whole, bounded by nonzero stated arm denominators")
    for pct in (report.published_treated_percent, report.published_control_percent):
        if pct is not None and (type(pct) is not Decimal or not Decimal(0) <= pct <= Decimal(100)):
            raise ValueError("Printed percentages must be Decimal 0–100 or explicitly unknown")


def arithmetic_audit(report: CountCitation) -> dict:
    _validate(report)
    computed = (_percent(report.treated, report.treated_denominator),
                _percent(report.control, report.control_denominator))
    printed = (report.published_treated_percent, report.published_control_percent)
    mismatch = [
        name for name, value, expected in zip(("TREATED", "PLACEBO"), computed, printed)
        if expected is not None and abs(value - expected) > Decimal("0.1")
    ]
    status = ("PERCENT_DENOMINATOR_RECHECK" if mismatch else
              "PRINTED_PERCENTAGES_PARTIALLY_UNAVAILABLE" if None in printed else
              "ARITHMETIC_CONSISTENT_NOT_CLINICALLY_ADJUDICATED")
    return {"sourceUrl":report.source_url, "outcomeDefinition":report.outcome_definition,
            "populationWindowCaveat":report.source_context,
            "recordedCounts":[report.treated,report.control],
            "providedDenominators":[report.treated_denominator,report.control_denominator],
            "reportedPercentages":[str(v) if v is not None else None for v in printed],
            "arithmeticFromProvidedDenominators":[str(v) for v in computed],
            "needsOriginalDenominatorReview":mismatch,
            "status":status}


def cross_source_counts(first: CountCitation, second: CountCitation) -> dict:
    a, b = arithmetic_audit(first), arithmetic_audit(second)
    if first.outcome_definition != second.outcome_definition:
        raise ValueError("Different event definitions cannot be compared as identical endpoints")
    discrepancy = [label for label, n, m in zip(("TREATED", "PLACEBO"),
                     a["recordedCounts"], b["recordedCounts"]) if n != m]
    return {"exactNct":PILOT,
            "sources":[first.source_url,second.source_url],
            "reportCountDifferences":discrepancy,
            "clinicalDefinitionAndWindowAgreement":"NOT_VERIFIED",
            "status":"NEEDS_ORIGINAL_EVENT_DEFINITION_WINDOW_RECONCILIATION" if discrepancy else
                     "COUNTS_MATCH_DEFINITIONS_AND_WINDOWS_STILL_UNVERIFIED",
            "scientificGrade":None, "phaseReviewerSignoff":False,
            "fdaOutcomes":{"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"},
            "predictionAccuracy":"NOT_CALIBRATED"}


def pilot_research_docket() -> dict:
    """Fixed publicly reported examples, with explicit unknown analysis windows."""
    journal="https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/"
    issuer="https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm"
    first=CountCitation(journal,"Serious adverse events of heart failure",11,258,1,259,
                        Decimal("4.3"),Decimal("0.4"),
                        "Secondary publication; exact safety-set cutoff and coding need review")
    second=CountCitation(issuer,"Serious adverse events of heart failure",12,258,3,259,
                         Decimal("4.7"),Decimal("1.2"),
                         "Later issuer reporting; exact safety-set cutoff and coding need review")
    interrupted=CountCitation(journal,"Per-protocol interruptions after LVEF decline",14,258,1,259,
                              Decimal("2.7"),Decimal("0.8"),
                              "Printed percentages; safety denominators may differ from randomized arms")
    return {
        "schema":"ACACIA_SOURCE_COUNT_RESEARCH_QA_V1",
        "nct":PILOT, "reconciliation":cross_source_counts(first,second),
        "secondaryInterruptionArithmetic":arithmetic_audit(interrupted),
        "sourceVerification":"SOURCE_REPORTED_NOT_INDEPENDENTLY_CLINICALLY_ADJUDICATED",
        "methodAssignments":["5.3","8.2"], "officialMethodGradesWritten":0,
        "fdaPrediction":"ABSTAIN",
    }
