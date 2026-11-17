"""Publisher link identity is distinct from scientific review or an FDA decision."""
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
RECORD = REPO / "research/source-links/MLYS-NCT06153693-PMID40587141-2026-11-17.json"


def test_exact_trial_publication_link_and_original_source_provenance():
    row = json.loads(RECORD.read_text(encoding="utf-8"))
    paper = row["publication"]
    assert row["schemaVersion"] == 1
    assert row["kind"] == "ORIGINAL_PUBLISHER_EXACT_NCT_LINK_AUDIT"
    assert row["studyNctId"] == "NCT06153693"
    assert row["focusTicker"] == "MLYS"
    assert paper["pmid"] == "40587141"
    assert paper["doi"] == "10.1001/jama.2025.9413"
    assert paper["publisherUrl"] == "https://jamanetwork.com/journals/jama/fullarticle/2835763"
    assert paper["exactNctIdPrintedInPublisherAbstract"] is True


def test_published_results_remain_unadjudicated_and_cannot_backfill_predictions():
    row = json.loads(RECORD.read_text(encoding="utf-8"))
    assert row["clinicalScientificReviewComplete"] is False
    assert row["clinicalFindingsIndependentlyValidated"] is False
    assert row["fdaApplicationIdentityVerified"] is False
    assert row["fdaReviewCycleVerified"] is False
    assert row["scientificScore"] is None
    assert row["fdaPrediction"] == "ABSTAIN"
    assert row["productionWritePermitted"] is False
    assert row["blindBacktestRule"].startswith("EXCLUDE_UNLESS_")


def test_publisher_reported_primary_endpoint_retains_original_units_and_safety():
    row = json.loads(RECORD.read_text(encoding="utf-8"))
    published = row["publication"]
    assert published["publishedOnline"] == "2025-06-30"
    outcome = published["publisherReportedPrimaryResults"]
    assert outcome["placeboAdjustedMeanDifferenceMmHg"] == -9.1
    assert outcome["confidenceInterval95MmHg"] == [-13.3, -4.9]
    assert outcome["reportedPValue"] == "<0.001"
    assert "Hyponatremia" in published["publisherReportedSafetyCaveat"]
