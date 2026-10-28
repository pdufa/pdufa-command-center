"""FDA published approved-application historical cycle trajectories: survivor biased.

Appendix A of the FY2023 PDUFA Performance Report describes *applications
ultimately approved during FY2023*, including previous nonapproval cycles.
Those prior CR entries do not create a consecutive/unbiased CRL denominator,
or prove exact dates/identity. Research notes only, never model labels.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import json
import re
from urllib.parse import urlsplit

_PATH = Path(__file__).parent / "research_sources" / "hop_fda_approval_survivor_sequences.json"
_SCHEMA = "hop-fda-approval-survivor-sequence-examples-v1"
_OFFICIAL_URL = "https://www.govinfo.gov/content/pkg/CMR-HE20_4000-00195429/pdf/CMR-HE20_4000-00195429.pdf"
_EXPECTED_NAMES = frozenset({"NGENLA", "LANTIDRA", "RYKINDO", "YCANTH"})
_PRODUCT_ID = re.compile(r"FDA_FY2023_APPROVAL_[A-Z0-9_]+\Z")


def _day(value: object) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _months(value: object) -> Decimal:
    if type(value) not in (int, float):
        raise ValueError("Cycle durations must be finite nonnegative numbers")
    months = Decimal(str(value))
    if not months.is_finite() or months <= 0 or months > 180:
        raise ValueError("Cycle duration outside supported FDA report range")
    return months


def audit_approved_survivor_sequences(data: dict, *, as_of: date) -> dict:
    """Preserve sequence, approval-only sampling, and regulatory abstention."""
    if type(as_of) is not date:
        raise ValueError("Exact as_of date required")
    if not isinstance(data, dict) or data.get("schema_version") != _SCHEMA:
        raise ValueError("Unknown FDA approval sequence research schema")
    captured = _day(data.get("as_of_research"))
    cover = _day(data.get("source_cover_letter_dated"))
    if captured is None or cover is None or captured < cover:
        raise ValueError("Invalid FDA source/report/capture dates")
    if as_of < captured:
        return {
            "status": "RESEARCH_SOURCE_NOT_AVAILABLE_AT_AS_OF",
            "asOf": as_of.isoformat(), "reportedSequenceCases": 0,
            "observedReviewCycleRows": 0, "approvedSurvivorSampling": True,
            "modelEligibleHistoricalCycles": 0,
            "independentlyBacktestedCases": 0,
            "approvalProbability": None,
            "trainingAuthorized": False, "cases": [],
        }
    if (data.get("source_report") != "FY 2023 PDUFA Performance Report to Congress"
            or data.get("source_report_url") != _OFFICIAL_URL
            or data.get("source_first_publication_verified") is not None
            or data.get("source_table") !=
            "Appendix A, FY 2023 approved NDA/BLA application cycle histories"
            or data.get("denominator") !=
            "ONLY_APPS_EVENTUALLY_APPROVED_IN_FY2023_NOT_ALL_FILINGS"
            or any(type(data.get(name)) is not int or data[name] != 0 for name in (
                "model_eligible_cycles", "adjudicated_fda_action_dates",
                "verified_application_ids", "independent_real_backtests"))
            or data.get("approval_probability") is not None):
        raise ValueError("FDA approval-only sampling frame cannot authorize model labels")
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) != 4:
        raise ValueError("Four researched approved-survivor trajectories required")
    ids = set()
    products = set()
    output = []
    num_cr = num_ap = 0
    for case in cases:
        required = {
            "case_id", "product", "established_name", "applicant",
            "source_pdf_zero_indexed_page", "source_appendix_page",
            "filing_fiscal_year", "review_cycles", "sponsor_intervals_months",
            "total_approval_time_months",
        }
        if not isinstance(case, dict) or set(case) != required:
            raise ValueError("FDA Appendix A row contract does not allow unsupported fields")
        ident = case["case_id"]
        product = case["product"]
        if (not isinstance(ident, str) or not _PRODUCT_ID.fullmatch(ident)
                or not isinstance(product, str) or product not in _EXPECTED_NAMES
                or product not in ident
                or ident in ids or product in products):
            raise ValueError("Duplicate or unrecognized source case identity")
        ids.add(ident)
        products.add(product)
        if (not isinstance(case.get("established_name"), str)
                or not case["established_name"].strip()
                or not isinstance(case.get("applicant"), str)
                or not case["applicant"].strip()
                or type(case["source_pdf_zero_indexed_page"]) is not int
                or case["source_pdf_zero_indexed_page"] not in (82, 83)
                or case["source_appendix_page"] not in ("A-72", "A-73")
                or case["source_pdf_zero_indexed_page"] !=
                    (82 if case["source_appendix_page"] == "A-72" else 83)
                or (case["filing_fiscal_year"] is not None
                    and (type(case["filing_fiscal_year"]) is not int or
                         not 2010 <= case["filing_fiscal_year"] <= 2023))):
            raise ValueError("FDA Appendix A provenance or scope malformed")
        cycles = case["review_cycles"]
        intervals = case["sponsor_intervals_months"]
        if (not isinstance(cycles, list) or not 2 <= len(cycles) <= 8
                or not isinstance(intervals, list) or len(intervals) != len(cycles)-1):
            raise ValueError("FDA historical cycle count or sponsor gap mismatch")
        previous_nonapprovals = 0
        cycle_total = Decimal("0")
        for i, row in enumerate(cycles):
            if not isinstance(row, dict) or set(row) != {
                "cycle_ordinal", "action_code", "review_time_months"
            }:
                raise ValueError("Noncanonical FDA cycle")
            if type(row["cycle_ordinal"]) is not int or row["cycle_ordinal"] != i+1:
                raise ValueError("Out-of-order or duplicate FDA cycle")
            action = row["action_code"]
            if action != ("AP" if i == len(cycles)-1 else "CR"):
                raise ValueError("Research-approved survivor must end with AP and prior cycles CR")
            previous_nonapprovals += action == "CR"
            cycle_total += _months(row["review_time_months"])
        for value in intervals:
            cycle_total += _months(value)
        reported_total = _months(case["total_approval_time_months"])
        # FDA explicitly rounds individual months, so sums may differ slightly.
        if abs(cycle_total - reported_total) > Decimal("0.1") * len(cycles):
            raise ValueError("FDA report total-time reconciliation exceeds rounded-month tolerance")
        num_cr += previous_nonapprovals
        num_ap += 1
        output.append({
            "caseId": ident,
            "product": product,
            "establishedName": case["established_name"],
            "sourceUrl": _OFFICIAL_URL,
            "sourcePdfPageZeroIndexed": case["source_pdf_zero_indexed_page"],
            "sourceAppendixPage": case["source_appendix_page"],
            "reportedFDAReviewCycles": [
                {"ordinal": x["cycle_ordinal"], "actionCode": x["action_code"],
                 "reviewMonths": x["review_time_months"]} for x in cycles],
            "priorCRLsReported": previous_nonapprovals,
            "eventuallyApprovedInFY2023": True,
            "applicationNumberVerified": False,
            "eachActionDateVerified": False,
            "firstPublicSourcePublicationDateVerified": False,
            "cycleMatchedToExactNdaBlaIdentity": False,
            "eligibleForTraining": False,
            "sourceCoverageClass": "APPROVED_IN_FY2023_ONLY_SURVIVOR_BIASED",
        })
    if products != _EXPECTED_NAMES:
        raise ValueError("FDA source sample identifiers changed")
    return {
        "status": "FDA_APPROVED_SURVIVOR_SEQUENCES_RESEARCH_ONLY",
        "asOf": as_of.isoformat(),
        "sourceReportedCoverDate": cover.isoformat(),
        "reportedSequenceCases": len(output),
        "observedReviewCycleRows": num_cr + num_ap,
        "priorCRLActionsInEventuallyApprovedCases": num_cr,
        "finalApprovalsInEventuallyApprovedCases": num_ap,
        "approvedSurvivorSampling": True,
        "completeNdaBlaFilingDenominatorKnown": False,
        "historicalNonapprovalDenominatorKnown": False,
        "independentlyVerifiedActionDates": 0,
        "verifiedExactApplicationReviewCycles": 0,
        "modelEligibleHistoricalCycles": 0,
        "independentlyBacktestedCases": 0,
        "approvalProbability": None,
        "trainingAuthorized": False,
        "selectionWarning": (
            "All selected cases were ultimately approved in FY2023; prior CRLs "
            "are not unbiased nonapproval samples, and source-cycle months "
            "do not establish original action dates or predecision features."
        ),
        "cases": sorted(output, key=lambda row: row["caseId"]),
    }


def load_approved_survivor_sequences(*, as_of: date) -> dict:
    return audit_approved_survivor_sequences(
        json.loads(_PATH.read_text(encoding="utf-8")), as_of=as_of
    )
