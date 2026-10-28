"""Build a research-only FY2024/FY2025 FDA action-candidate review queue.

Two different FDA publication-selected sources are available: Drugs@FDA
ultimately-approved registry, and openFDA selectively released action
letters. This is a *candidate source union*, NOT a consecutive filing cohort
and NOT an unbiased binary decision denominator. Every candidate and count
stays nontraining until a separate full filing roster and original action
review independently establish what happened at each actual review cycle.

The year here is the *reported action-year fiscal period* (October-September),
not the year an original NDA/BLA was FILED. Never subtract it from the FDA
original-filing totals or infer an approval rate.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
import re
from typing import Any

from .hop_fda_filing_benchmarks import audit_fda_filing_benchmarks

_APPROVED_STATUS = "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT"
_LETTERS_STATUS = "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT"
_ALLOWED_FYS = (2024, 2025)
_APP = re.compile(r"(NDA|BLA)([0-9]{6})\Z")
_PARENT = re.compile(r"(NDA|BLA)\s+([0-9]{6})\Z", re.IGNORECASE)
_ORIGINAL = re.compile(r"(NDA|BLA)\s+([0-9]{6})/Original\s+([1-9][0-9]*)\Z", re.IGNORECASE)
_SUPPLEMENT = re.compile(r"(NDA|BLA)\s+([0-9]{6})/S-([0-9]{3})\Z", re.IGNORECASE)
_SHA = re.compile(r"[a-f0-9]{64}\Z")


def _parsed_date(value: object, fmt: str) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        d = datetime.strptime(value, fmt).date()
        if d.strftime(fmt) != value:
            return None
        return d
    except ValueError:
        return None


def _fiscal_year(d: date) -> int:
    return d.year + (1 if d.month >= 10 else 0)


def _letter_identity(application_numbers: object) -> tuple[str, str | None, str | None]:
    """Separate parent-only, exact Original, supplement, legacy and ambiguity."""
    if not isinstance(application_numbers, list) or len(application_numbers) != 1:
        return "MULTIPLE_OR_MISSING_IDENTIFIERS", None, None
    raw = application_numbers[0]
    if not isinstance(raw, str):
        return "UNRESOLVED_IDENTIFIER", None, None
    raw = raw.strip()
    match = _ORIGINAL.fullmatch(raw)
    if match:
        return "EXPLICIT_ORIGINAL", match.group(1).upper()+match.group(2), match.group(3)
    match = _SUPPLEMENT.fullmatch(raw)
    if match:
        return "SUPPLEMENT_NOT_ORIGINAL", match.group(1).upper()+match.group(2), "S-"+match.group(3)
    match = _PARENT.fullmatch(raw)
    if match:
        return "PARENT_APPLICATION_ONLY", match.group(1).upper()+match.group(2), None
    return "LEGACY_OR_UNRESOLVED_IDENTIFIER", None, None


def _source_metadata_ok(source: dict, expected: str, observed_as_of: date) -> None:
    if not isinstance(source, dict) or source.get("status") != expected:
        raise ValueError("Source is not the previously quarantined FDA publication archive")
    exported = _parsed_date(source.get("source_export_date"), "%Y-%m-%d")
    retrieved = _parsed_date(source.get("retrieved_on"), "%Y-%m-%d")
    if exported is None or retrieved is None or not exported <= retrieved <= observed_as_of:
        raise ValueError("FDA source export/retrieval chronology invalid")
    if not isinstance(source.get("records"), list):
        raise ValueError("Source record list missing")


def build_fda_action_candidate_queue(
    drugsfda_source: dict, crl_source: dict, filing_benchmarks: dict,
    *, as_of: date, fiscal_years: tuple[int, ...] = _ALLOWED_FYS,
) -> dict:
    """Enumerate exact-source research leads; never grant FDA model clearance.

    Source snapshots must already have been obtained from the original FDA
    export, with ZIP SHA and extraction verified by the independent collector.
    An untrusted caller could fabricate any source dictionary, so this
    projection does not and cannot certify FDA historical truth.
    """
    if type(as_of) is not date or not isinstance(fiscal_years, tuple) or not fiscal_years:
        raise ValueError("Exact research date and supported fiscal-year tuple required")
    if any(type(fy) is not int or fy not in _ALLOWED_FYS for fy in fiscal_years):
        raise ValueError("Only preregistered FY2024/2025 research action years supported")
    if len(fiscal_years) != len(set(fiscal_years)) or tuple(sorted(fiscal_years)) != fiscal_years:
        raise ValueError("Fiscal years must be unique and ascending")
    _source_metadata_ok(drugsfda_source, _APPROVED_STATUS, as_of)
    _source_metadata_ok(crl_source, _LETTERS_STATUS, as_of)
    benchmark = audit_fda_filing_benchmarks(filing_benchmarks)
    official_filing = benchmark["latest_original_applications_filed_by_fy"]
    registry_rows = drugsfda_source["records"]
    published_rows = crl_source["records"]
    if not registry_rows or not published_rows:
        raise ValueError("A complete downloaded source snapshot is required")
    if len(registry_rows) > 100_000 or len(published_rows) > 25_000:
        raise ValueError("Unbounded source input not permitted")

    selected_years = set(fiscal_years)
    seen_registry = set()
    registry_candidate_keys = set()
    output = []
    fy_counts: dict[int, Counter] = defaultdict(Counter)
    source_rejected = Counter()
    seen_crl_records = set()
    for row in registry_rows:
        if not isinstance(row, dict):
            raise ValueError("Nonobject approved-product registry row")
        app = row.get("application_number_as_published")
        hash_value = row.get("record_sha256")
        if (row.get("model_eligible") is not False
                or row.get("complete_application_denominator_verified") is not False
                or row.get("review_cycles_independently_adjudicated") is not False
                or row.get("point_in_time_features_verified") is not False
                or not isinstance(hash_value, str) or not _SHA.fullmatch(hash_value)):
            raise ValueError("Unreviewed approved-product row must remain quarantined")
        if app in seen_registry:
            raise ValueError("Duplicate approved registry application identifier")
        seen_registry.add(app)
        if not isinstance(app, str) or not _APP.fullmatch(app):
            continue  # ANDA and other products are out of target NDA/BLA scope
        submissions = row.get("submissions_as_published")
        if not isinstance(submissions, list):
            raise ValueError("NDA/BLA registry submission list is invalid")
        for sub in submissions:
            if not isinstance(sub, dict):
                raise ValueError("NDA/BLA submission is invalid")
            d = _parsed_date(sub.get("submission_status_date_as_published"), "%Y%m%d")
            if d is None or _fiscal_year(d) not in selected_years:
                continue
            if sub.get("submission_type_as_published") != "ORIG":
                continue
            fy = _fiscal_year(d)
            status = sub.get("submission_status_as_published")
            if status not in ("AP", "TA"):
                fy_counts[fy]["other_original_status_rows"] += 1
                continue
            submission_no = sub.get("submission_number_as_published")
            if not isinstance(submission_no, str) or not submission_no.isdigit() or int(submission_no) < 1:
                fy_counts[fy]["original_submission_number_unresolved"] += 1
                continue
            unique = (app, submission_no, d.isoformat(), status)
            if unique in registry_candidate_keys:
                fy_counts[fy]["duplicate_original_action_rows"] += 1
                continue
            registry_candidate_keys.add(unique)
            category = "AP_SOURCE_REGISTRY" if status == "AP" else "TA_NONBINARY_SOURCE_REGISTRY"
            fy_counts[fy][category] += 1
            output.append({
                "source": "DRUGSFDA_APPROVED_PRODUCT_REGISTRY",
                "sourceRecordSha256": hash_value,
                "applicationId": app,
                "sourceOriginalSubmissionNo": submission_no,
                "reportedActionDate": d.isoformat(),
                "fiscalActionYear": fy,
                "sourceAction": status,
                "researchClass": category,
                "exactReviewCycleIndependentlyVerified": False,
                "publicOutcomeLabelDateIndependentlyVerified": False,
                "predecisionEvidenceVerified": False,
                "modelEligible": False,
            })
    for row in published_rows:
        if not isinstance(row, dict):
            raise ValueError("Nonobject public letter row")
        h = row.get("source_record_sha256")
        if (row.get("model_eligible") is not False
                or row.get("cohort_complete_verified") is not False
                or row.get("independently_verified") is not False
                or not isinstance(h, str) or not _SHA.fullmatch(h)):
            raise ValueError("Published letters cannot be promoted to verified FDA outcomes")
        if h in seen_crl_records:
            raise ValueError("Duplicate published CRL source identity")
        seen_crl_records.add(h)
        when = _parsed_date(row.get("letter_date_as_published"), "%m/%d/%Y")
        if when is None or _fiscal_year(when) not in selected_years:
            continue
        fy = _fiscal_year(when)
        if row.get("letter_type_as_published") != "COMPLETE RESPONSE":
            fy_counts[fy]["other_published_letter_actions"] += 1
            continue
        category, application, submission = _letter_identity(row.get("application_numbers"))
        fy_counts[fy]["CRL_" + category] += 1
        output.append({
            "source": "OPENFDA_SELECTED_PUBLIC_CRL_LETTERS",
            "sourceRecordSha256": h,
            "applicationId": application,
            "sourceApplicationReferences": list(row.get("application_numbers") or []),
            "sourceOriginalOrSupplementUnit": submission,
            "reportedActionDate": when.isoformat(),
            "fiscalActionYear": fy,
            "sourceAction": "COMPLETE RESPONSE",
            "researchClass": "CRL_" + category,
            "exactReviewCycleIndependentlyVerified": False,
            "publicOutcomeLabelDateIndependentlyVerified": False,
            "predecisionEvidenceVerified": False,
            "modelEligible": False,
        })
    output.sort(key=lambda x: (x["fiscalActionYear"], x["reportedActionDate"], x["source"], x["sourceRecordSha256"]))
    years = []
    for fy in fiscal_years:
        counts = fy_counts[fy]
        a = {row["applicationId"] for row in output if row["fiscalActionYear"] == fy and row["source"] == "DRUGSFDA_APPROVED_PRODUCT_REGISTRY" and row["sourceAction"] == "AP"}
        c = {row["applicationId"] for row in output if row["fiscalActionYear"] == fy and row["source"] == "OPENFDA_SELECTED_PUBLIC_CRL_LETTERS" and row["applicationId"]}
        years.append({
            "fiscalActionYear": fy,
            "reportedOriginalApplicationFilingsInFY": official_filing[str(fy)],
            "sourceRegistryOriginalAPActionCandidates": counts["AP_SOURCE_REGISTRY"],
            "sourceRegistryUniqueApplicationsWithOriginalAP": len(a),
            "sourceRegistryTentativeApprovalNonbinaryCandidates": counts["TA_NONBINARY_SOURCE_REGISTRY"],
            "selectedPublishedCRLParentOnly": counts["CRL_PARENT_APPLICATION_ONLY"],
            "selectedPublishedCRLExplicitOriginal": counts["CRL_EXPLICIT_ORIGINAL"],
            "selectedPublishedCRLSupplementExcluded": counts["CRL_SUPPLEMENT_NOT_ORIGINAL"],
            "selectedPublishedCRLLegacyOrUnresolved": counts["CRL_LEGACY_OR_UNRESOLVED_IDENTIFIER"],
            "selectedPublishedCRLMultipleOrMissing": counts["CRL_MULTIPLE_OR_MISSING_IDENTIFIERS"],
            "distinctParentApplicationsInSelectedCRLs": len(c),
            "applicationsRepresentedInBothArchivesSameFiscalActionYear": len(a & c),
            "sourceScopeMismatch": "FDA_FILING_FISCAL_YEAR_VS_ACTION_FISCAL_YEAR_DIFFERENT_POPULATIONS",
            "uniqueFiledApplicationsEnumerated": None,
            "filingDenominatorCoverage": None,
            "actionOutcomeApprovalFraction": None,
            "modelEligibleCycles": 0,
        })
    return {
        "status": "FDA_ACTION_CANDIDATE_UNION_FROM_SELECTED_PUBLISHED_SOURCES_NOT_A_COMPLETE_COHORT",
        "asOf": as_of.isoformat(),
        "sourceExports": {
            "drugsfda": drugsfda_source["source_export_date"],
            "openfdaCrl": crl_source["source_export_date"],
        },
        "sourceRecordsInspected": {
            "approvedProductRegistry": len(registry_rows),
            "selectedPublishedLetters": len(published_rows),
        },
        "selectedFiscalActionYears": years,
        "researchCandidateRows": len(output),
        "researchCandidates": output,
        "sourceUniverse": "APPROVED_PRODUCT_AND_PUBLISHED_CRL_SELECTION_BIASED",
        "applicationLevelFilingDenominatorIndependentlyVerified": False,
        "allPendingWithdrawnAndUnapprovedCasesRepresented": False,
        "allPdufaReviewCyclesIndependentlyEnumerated": False,
        "independentlyVerifiedModelEligibleCycles": 0,
        "independentRealBacktests": 0,
        "predictionAccuracy": None,
        "approvalProbability": None,
        "trainingAuthorized": False,
        "tradeAuthorized": False,
        "blockers": [
            "APPROVED_PRODUCT_SOURCE_EXCLUDES_NEVER_APPROVED_FILINGS",
            "PUBLIC_CRL_ARCHIVE_IS_SELECTION_BIASED",
            "REPORT_YEAR_FILING_COUNTS_CANNOT_BE_COMPARED_TO_ACTION_YEAR_CANDIDATES",
            "EXACT_ORIGINAL_VS_SUPPLEMENT_AND_REVIEW_CYCLE_NOT_ALL_VERIFIED",
            "FDA_DECISION_LABEL_PUBLICATION_DATE_NOT_VERIFIED",
            "NO_EXHAUSTIVE_NDA_BLA_ORIGINAL_FILING_ROSTER",
            "NO_FROZEN_PREDECISION_FEATURES",
            "INDEPENDENT_ACTION_ADJUDICATION_INCOMPLETE",
        ],
    }
