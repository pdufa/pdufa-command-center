"""Audit FDA PDUFA annual filing totals without converting them to outcomes.

Official filing *aggregates* help check historical population coverage, but do
not identify individual NDA/BLA applications, decision dates, or review cycles.
Later FDA reports may revise previously published fiscal-year totals.
"""
from __future__ import annotations

from collections import defaultdict
import re
from urllib.parse import urlparse


CATEGORIES = (
    "priority_ndas", "standard_ndas", "priority_blas",
    "standard_blas", "undesignated_originals",
)


def audit_fda_filing_benchmarks(raw: dict) -> dict:
    if not isinstance(raw, dict) or raw.get("status") != (
            "OFFICIAL_FDA_ANNUAL_FILING_AGGREGATES_NOT_DECISION_COHORT"):
        raise ValueError("not a quarantined FDA annual filing reference")
    if (raw.get("application_level_membership_known") is not False
            or raw.get("complete_application_denominator_verified") is not False
            or raw.get("source_for_training_labels") is not False
            or type(raw.get("model_eligible_records")) is not int
            or raw["model_eligible_records"] != 0
            or type(raw.get("review_cycle_outcomes_verified")) is not int
            or raw["review_cycle_outcomes_verified"] != 0
            or type(raw.get("individual_fda_action_dates_verified")) is not int
            or raw["individual_fda_action_dates_verified"] != 0
            or raw.get("prediction_probability") is not None):
        raise ValueError("aggregate FDA filings cannot authorize a model cohort")
    rows = raw.get("report_versions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("missing published FDA annual filing versions")
    seen = set()
    totals_by_fy = defaultdict(list)
    source_details = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("malformed FDA aggregate source row")
        fiscal = row.get("fiscal_year_of_filing")
        report = row.get("source_report_fy")
        source_section = row.get("source_section")
        if (type(fiscal) is not int or type(report) is not int
                or not 2010 <= fiscal <= report <= 2100
                or source_section not in ("Appendix B Table B-1", "Figure 1")):
            raise ValueError("invalid year or FDA report table type")
        source_url = row.get("source_document_url")
        parsed = urlparse(source_url) if isinstance(source_url, str) else None
        if (parsed is None or parsed.scheme != "https"
                or parsed.hostname != "www.fda.gov"
                or not re.fullmatch(r"/media/[0-9]+/download", parsed.path)
                or parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError("FDA report provenance must be on exact official host")
        page = row.get("source_pdf_page_zero_indexed")
        total = row.get("source_originals_filed_total")
        if type(page) is not int or page < 0 or type(total) is not int or total <= 0:
            raise ValueError("invalid source PDF location or filing total")
        if source_section == "Appendix B Table B-1":
            values = [row.get(category) for category in CATEGORIES]
            if any(type(n) is not int or n < 0 for n in values) or sum(values) != total:
                raise ValueError("original application category counts do not add up")
        else:
            priority = row.get("chart_priority_including_undesignated")
            standard = row.get("chart_standard")
            if (type(priority) is not int or type(standard) is not int
                    or priority < 0 or standard < 0 or priority + standard != total):
                raise ValueError("FDA annual graph total is inconsistent")
        key = (fiscal, report, source_section)
        if key in seen:
            raise ValueError("duplicate FDA report version and table")
        seen.add(key)
        totals_by_fy[fiscal].append((report, source_section, total))
        source_details.append({
            "fiscal_year_of_filing": fiscal,
            "report_fiscal_year": report,
            "source_page": row.get("source_page"),
            "source_section": source_section,
            "source_document_url": source_url,
            "original_applications_filed": total,
        })
    latest = {}
    revisions = {}
    for fiscal, data in totals_by_fy.items():
        most_recent = max(x[0] for x in data)
        source_values = {total for report, _, total in data if report == most_recent}
        if len(source_values) != 1:
            raise ValueError("inconsistent totals in the latest FDA report version")
        latest[str(fiscal)] = source_values.pop()
        older = sorted((report, total) for report, _, total in data if report < most_recent)
        if older:
            unique_older = sorted(set(older))
            revisions[str(fiscal)] = {
                "earliest_source_report_fy": unique_older[0][0],
                "earlier_total": unique_older[0][1],
                "latest_source_report_fy": most_recent,
                "later_total": latest[str(fiscal)],
                "difference": latest[str(fiscal)] - unique_older[0][1],
            }
    if raw.get("latest_reported_original_filings_by_fy") != latest:
        raise ValueError("latest FDA filing totals do not reconcile")
    revision = raw.get("documented_revision")
    if (not isinstance(revision, dict) or str(revision.get("fiscal_year_of_filing")) not in revisions):
        raise ValueError("missing versioned FDA source revision")
    recorded = revisions[str(revision["fiscal_year_of_filing"])]
    if any(revision.get(key) != value for key, value in (
            ("earlier_reported", recorded["earlier_total"]),
            ("later_reported", recorded["later_total"]),
            ("change_in_reported_count", recorded["difference"]))):
        raise ValueError("FDA historical filing revision is inconsistent")
    return {
        "status": "FDA_FILING_AGGREGATE_REFERENCE_NOT_MODEL_COHORT",
        "latest_original_applications_filed_by_fy": dict(sorted(latest.items())),
        "documented_revisions": revisions,
        "source_versions": sorted(source_details, key=lambda x: (
            x["fiscal_year_of_filing"], x["report_fiscal_year"], x["source_section"])),
        "applications_individually_enumerated": False,
        "complete_review_cycle_denominator_verified": False,
        "effective_fda_action_dates_verified": 0,
        "review_cycle_outcomes_verified": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
    }
