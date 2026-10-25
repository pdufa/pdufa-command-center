import json
from pathlib import Path

import pytest

from app.hop_fda_filing_benchmarks import audit_fda_filing_benchmarks

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "research_sources"
          / "hop_fda_pdufa_filing_benchmarks.json")


def baseline():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_official_fda_2024_revision_and_2025_filing_totals():
    result = audit_fda_filing_benchmarks(baseline())
    assert result["latest_original_applications_filed_by_fy"] == {
        "2024": 129, "2025": 157
    }
    changed = result["documented_revisions"]["2024"]
    assert changed["earlier_total"] == 128
    assert changed["later_total"] == 129
    assert changed["difference"] == 1
    assert result["applications_individually_enumerated"] is False
    assert result["complete_review_cycle_denominator_verified"] is False
    assert result["review_cycle_outcomes_verified"] == 0
    assert result["model_eligible_records"] == 0
    assert result["prediction_probability"] is None


@pytest.mark.parametrize("mutation,error", [
    (lambda x: x["report_versions"][0].update({"priority_ndas": 30}), "do not add up"),
    (lambda x: x["report_versions"][1].update({"chart_standard": 90}), "graph total"),
    (lambda x: x.update({"complete_application_denominator_verified": True}), "cannot authorize"),
    (lambda x: x.update({"model_eligible_records": 1}), "cannot authorize"),
    (lambda x: x["report_versions"][2].update({
        "source_document_url": "https://www.fda.gov.attacker.example/media/191112/download"}), "exact official host"),
    (lambda x: x["documented_revision"].update({"later_reported": 128}), "revision is inconsistent"),
    (lambda x: x["latest_reported_original_filings_by_fy"].update({"2025": 158}), "do not reconcile"),
])
def test_invalid_or_self_certified_filing_benchmarks_fail_closed(mutation, error):
    source = baseline()
    mutation(source)
    with pytest.raises(ValueError, match=error):
        audit_fda_filing_benchmarks(source)


def test_2025_report_subtype_and_figure_total_reconcile():
    source = baseline()
    rows = [r for r in source["report_versions"] if r["fiscal_year_of_filing"] == 2025]
    subtype = next(x for x in rows if x["source_section"] == "Appendix B Table B-1")
    figure = next(x for x in rows if x["source_section"] == "Figure 1")
    assert sum(subtype[x] for x in (
        "priority_ndas", "standard_ndas", "priority_blas",
        "standard_blas", "undesignated_originals")) == 157
    assert figure["chart_priority_including_undesignated"] == 66
    assert figure["chart_standard"] == 91
    assert sum((figure["chart_priority_including_undesignated"], figure["chart_standard"])) == 157
    assert audit_fda_filing_benchmarks(source)["model_eligible_records"] == 0
