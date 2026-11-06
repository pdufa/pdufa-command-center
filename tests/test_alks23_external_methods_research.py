"""Source-joined external methods reviews do not imply full sponsor protocol/SAP availability."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "new-platform/frontend/data"

def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_every_external_methods_row_matches_one_of_original_23_attachment_gaps():
    audit = read("alks34ProtocolSafetyApplicabilityAudit20261106.json")
    external = read("alks23ExternalMethodsResearch20261106.json")
    ids = [r["nctId"] for r in external["records"]]
    original_gaps = {r["nctId"] for r in audit["records"]
                     if not r["sourceDocuments"]["registryProtocolAttached"]
                     and not r["sourceDocuments"]["registrySapAttached"]}
    assert len(ids) == len(set(ids)) == 23
    assert set(ids) == original_gaps
    assert all(re.fullmatch(r"NCT\d{8}", nct) for nct in ids)
    assert external["summary"]["registryProtocolAndSapAttachmentGaps"] == 23
    assert all(r["registryUrl"] == "https://clinicaltrials.gov/study/"+r["nctId"]
               for r in external["records"])


def test_literature_source_coverage_keeps_missing_attached_documents_missing():
    external = read("alks23ExternalMethodsResearch20261106.json")
    rows = external["records"]
    reviewed = [r for r in rows if r["sourceType"] != "PRIOR_AUDIT_SOURCE_CROSSCHECK_REUSED"]
    carried = [r for r in rows if r["sourceType"] == "PRIOR_AUDIT_SOURCE_CROSSCHECK_REUSED"]
    assert len(reviewed) == external["summary"]["originalPeerReviewedOrFdaOrRegistryMethodsReviewed"] == 15
    assert len(carried) == external["summary"]["sourceCrosschecksAlreadyInUpstreamAudit"] == 8
    assert len(rows) == external["summary"]["sourceLinkedTrialDesignOrMethods"] == 23
    assert external["summary"]["notYetIndividuallyResearchedOutsideStoredRegistry"] == 0
    assert all(r["sourceUrl"] for r in rows)
    assert external["summary"]["fullOriginalProtocolsNewlyLocated"] == 0
    assert external["summary"]["fullOriginalSapsNewlyLocated"] == 0
    assert external["summary"]["completedProductionThirtyQuestionRescores"] == 0
    assert all(not r["fullProtocolRegistryAttachment"] and not r["fullSapRegistryAttachment"]
               for r in rows)
    assert all(not r["fullProtocolLocatedViaThisExternalResearch"] and
               not r["fullSapLocatedViaThisExternalResearch"] and
               not r["productionQuestionStatusesUpdated"] for r in rows)


def test_exact_nct_fda_review_and_peer_reviewed_program_boundaries():
    external = read("alks23ExternalMethodsResearch20261106.json")
    by_id = {r["nctId"]: r for r in external["records"]}
    fda = by_id["NCT01469039"]
    assert fda["sourceType"] == "INDEPENDENT_FDA_STATISTICAL_REVIEW"
    assert fda["sourceDate"] == "2015-06-08"
    assert fda["sourceUrl"].startswith("https://www.accessdata.fda.gov/")
    assert "Q14" in fda["sourceQuestionLeads"] and "Q15" in fda["sourceQuestionLeads"]
    assert external["summary"]["independentFdaStatisticalReviews"] == 1
    forward4 = by_id["NCT02158533"]
    forward5 = by_id["NCT02218008"]
    forward3 = by_id["NCT02158546"]
    assert "-1.8" in " ".join(forward4["findings"]) and "0.109" in " ".join(forward4["findings"])
    assert "0.018" in " ".join(forward5["findings"])
    assert "0.782" in " ".join(forward3["findings"])
    assert by_id["NCT01218958"]["sourceType"] == "PROGRAM_CROSSWALKED_PEER_REVIEWED_METHODS"
    assert "NCT01626456" in " ".join(by_id["NCT01895452"]["findings"])
    assert "NCT01218958" in " ".join(by_id["NCT01218971"]["findings"])
    assert "NCT01218997" in by_id and by_id["NCT01218997"]["sourceUrl"]
    assert "NCT00834080" in by_id and "38 participants" in " ".join(by_id["NCT00834080"]["findings"])
    assert "0.336" in " ".join(by_id["NCT00501631"]["findings"])


def test_web_site_shows_23_gap_ledger_with_source_urls_and_caveats():
    page = (ROOT / "new-platform/frontend/app/alkermes-scores/page.tsx").read_text(encoding="utf-8")
    assert 'alks23ExternalMethodsResearch20261106.json' in page
    assert "data-alks-external-methods-backfill" in page
    assert "data-alks-external-methods-trial" in page
    assert "data-alks-external-methods-expand" in page
    assert "This is not a substitute for the original full protocol/SAP" in page
