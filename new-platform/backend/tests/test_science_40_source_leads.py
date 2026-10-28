"""PEAK source observations are leads, not independent clinical adjudications."""
from pathlib import Path
import json

from app.science_40_dossier import evaluate_science_40
from app.phase3_research_batch import evaluate_candidate_batch
from app.phase3_sheet_population_preview import build_sheet_population_preview

KEY = "APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130"
CUTOFF = "2026-10-27"
EXPECTED = {"S01", "S02", "S03", "S04", "S05", "S17", "S18", "S19", "S26", "S30"}


def test_real_peak_sources_are_discovery_leads_only():
    r = evaluate_science_40(exact_key=KEY, evidence={}, as_of=CUTOFF)
    assert r["sourceLeadsDiscovered"] == 10
    assert r["submittedSourceObservations"] == 0
    assert r["independentlyReviewedAssessments"] == 0
    assert r["readinessGrade"] == "RELUCTANT"
    assert r["approvalProbability"] is None
    assert r["independentScientificConclusion"] is None
    assert r["tradeAuthorized"] is False
    observed = {q["id"]: q["sourceLead"] for q in r["records"] if q["sourceLead"] is not None}
    assert set(observed) == EXPECTED
    assert len(r["records"]) == 40
    for id, lead in observed.items():
        assert lead["sourceStatus"] == "SOURCE_LEAD_AWAITING_ORIGINAL_DOCUMENT_REVIEW"
        assert lead["sourceType"] == "ISSUER_PRESS_RELEASE"
        assert lead["independentlyReviewed"] is False
        assert lead["originalSourceHashAvailable"] is False
        assert lead["sourceUrl"].startswith("https://investors.cogentbio.com/")
        assert lead["publishedAt"] in {"2026-05-28", "2026-05-30"}
        assert r["records"][int(id[1:])-1]["status"] == "NOT_SUBMITTED"


def test_as_of_date_does_not_backfill_leads_before_source_indexing():
    old = evaluate_science_40(exact_key=KEY, evidence={}, as_of="2026-05-30")
    assert old["sourceLeadsDiscovered"] == 0
    assert old["independentlyReviewedAssessments"] == 0
    assert old["readinessGrade"] == "RELUCTANT"


def test_unrelated_exact_trial_cannot_borrow_peak_leads():
    other = evaluate_science_40(exact_key="TRIAL|NCT00000001", evidence={}, as_of=CUTOFF)
    assert other["sourceLeadsDiscovered"] == 0
    assert other["independentlyReviewedAssessments"] == 0


def test_untrusted_verified_flags_cannot_certify_peaks_source_leads():
    forged = {id: {"review_status": "VERIFIED", "source_url": "https://example.org"}
              for id in EXPECTED}
    result = evaluate_science_40(exact_key=KEY, evidence=forged, as_of=CUTOFF)
    assert result["sourceLeadsDiscovered"] == 10
    assert result["independentlyReviewedAssessments"] == 0
    assert result["approvalProbability"] is None
    assert result["readinessGrade"] == "RELUCTANT"


def test_existing_real_peak_batch_exposes_leads_without_sheet_writes():
    fixture = json.loads((Path(__file__).parent / "fixtures" / "peak_real_trial_20261027.json").read_text())
    batch = evaluate_candidate_batch([fixture["candidate"]], as_of=fixture["as_of"])
    row = batch["rows"][0]
    assert row["analysis"]["science40"]["sourceLeadsDiscovered"] == 10
    assert row["analysis"]["science40"]["independentlyReviewedAssessments"] == 0
    assert row["analysis"]["approvalProbability"] is None
    preview = build_sheet_population_preview(batch)
    assert preview["mode"] == "PREVIEW_ONLY"
    assert preview["writtenToSheet"] is False
    assert preview["rows"][0]["approvalProbability"] is None
