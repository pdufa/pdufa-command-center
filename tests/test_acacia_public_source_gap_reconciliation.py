"""Offline integrity tests: original source discovery cannot become a clinical grade."""
from __future__ import annotations

from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts/medical/acacia_public_source_gap_reconciliation.py"
spec = spec_from_file_location("acacia_gap_audit",path)
gap = module_from_spec(spec)
spec.loader.exec_module(gap)
TIME = datetime(2026, 11, 9, 7, 17, tzinfo=timezone.utc)


def registry(with_sap=False):
    result = {
        "protocolSection":{
            "identificationModule":{"nctId":"NCT06081894"},
            "designModule":{"phases":["PHASE3"]}
        },
        "documentSection":{"largeDocumentModule":{"largeDocs":[
            {"title":"Statistical Analysis Plan (SAP)"} if with_sap else
            {"type":"Study Protocol","title":"Protocol Amendment 04"}
        ]}}
    }
    return result


def sponsor(complete=True):
    n = "Ten" if complete else "Nine"
    return ("""
    <html><head><title>Cytokinetics Announces Additional Data from ACACIA-HCM
    Presented at the HFSA Annual Scientific Meeting 2026</title></head>
    <body><h1>Cytokinetics Announces Additional Data from ACACIA-HCM</h1>
    <span>October 12, 2026</span>
    <p>Results in non-obstructive HCM: As previously reported, two participants
    on aficamten experienced a serious adverse event (SAE) of heart failure
    associated with LVEF &lt;50%.</p>
    <p>""" + n + """ additional patients on aficamten had SAEs of heart failure
    not associated with LVEF &lt;50%, for a total of 12 patients (4.7%)
    compared to three patients (1.2%) on placebo.</p></body></html>
    """).encode()


def fake_fetch(reg=None, safety=None, pdf=True):
    source={
        "REGISTRY":json.dumps(reg or registry()).encode(),
        "SPONSOR_HF_OCT12":safety if safety is not None else sponsor(),
        "NEJM_PROTOCOL_SUPPLEMENT":b"%PDF-1.7\n" if pdf else None,
        "NEJM_APPENDIX_SUPPLEMENT":b"%PDF-1.7\n" if pdf else None,
    }
    def fetch(source_id):
        if source[source_id] is None:
            return None,"HTTP_OR_NETWORK_UNAVAILABLE","HTTPError"
        return source[source_id],"RETRIEVED",None
    return fetch


class SourceGapAuditTests(unittest.TestCase):
    def checkpoint(self,**kwargs):
        return gap.audit(timestamp=TIME,commit="a"*40,run="123456",**kwargs)

    def test_exact_allowlisted_sources_and_no_user_urls(self):
        self.assertEqual(set(gap.SOURCES),{
            "REGISTRY","SPONSOR_HF_OCT12","NEJM_PROTOCOL_SUPPLEMENT",
            "NEJM_APPENDIX_SUPPLEMENT"})
        self.assertTrue(all(x.startswith("https://") for x in gap.SOURCES.values()))
        with self.assertRaisesRegex(ValueError,"SOURCE_NOT_ALLOWLISTED"):
            gap.observe("https://attacker.example/override")

    def test_source_discovery_reports_doc_titles_not_authentication(self):
        p=gap.check_registry(registry(with_sap=True))
        self.assertEqual(p["identity"],"MATCH_PHASE3")
        self.assertEqual(p["sapDocumentListed"],"CANDIDATE_TITLE_ONLY")
        self.assertEqual(p["largeDocuments"],1)
        self.assertEqual(p["resultsPosted"],False)
        self.assertEqual(gap.check_registry(registry())["sapDocumentListed"],
                         "NOT_LISTED_IN_THIS_RESPONSE")
        wrong=registry();wrong["protocolSection"]["identificationModule"]["nctId"]="NCT99999999"
        self.assertEqual(gap.check_registry(wrong)["identity"],"MISMATCH")
        wrong=registry();wrong["protocolSection"]["designModule"]["phases"]=["PHASE2"]
        self.assertEqual(gap.check_registry(wrong)["identity"],"MISMATCH")

    def test_sponsor_breakdown_is_precise_and_not_independent_reconciliation(self):
        p=gap.check_sponsor(sponsor())
        self.assertEqual(p["documentIdentity"],"MATCH")
        self.assertEqual(p["hfBreakdown"],
          "PUBLIC_SPONSOR_COMPONENTS_MATCH_2_PLUS_10_EQUALS_12_VS_3")
        self.assertEqual((p["lvefAssociatedTreated"],p["otherTreated"],
                          p["treatedReportedTotal"],p["placeboReportedTotal"]),(2,10,12,3))
        mismatch=gap.check_sponsor(sponsor(complete=False))
        self.assertEqual(mismatch["hfBreakdown"],"NOT_VERIFIED")
        self.assertEqual(gap.check_sponsor(b"<h1>Not Cytokinetics</h1>")["documentIdentity"],
                         "UNVERIFIED")

    def test_report_has_hashes_and_review_gaps_not_clinical_outputs(self):
        r=self.checkpoint(fetcher=fake_fetch())
        self.assertEqual(r["schema"],gap.SCHEMA)
        self.assertEqual(r["nct"],"NCT06081894")
        self.assertEqual(len(r["sources"]),4)
        self.assertTrue(all(x["status"]=="RETRIEVED" for x in r["sources"]))
        self.assertTrue(all(len(x["sha256"])==64 for x in r["sources"]))
        self.assertEqual(r["receiptSha256"],gap.receipt_sha(r))
        self.assertEqual(r["sponsor"]["treatedReportedTotal"],12)
        self.assertEqual(r["sponsor"]["placeboReportedTotal"],3)
        self.assertFalse(r["finalLockedSapAuthenticated"])
        self.assertFalse(r["originalPrimarySensitivityReviewed"])
        self.assertFalse(r["hfSeriousEvent11vs1Versus12vs3Reconciled"])
        self.assertFalse(r["safetyLineListingAdjudicated"])
        self.assertFalse(r["independentPhaseReviewerSigned"])
        self.assertEqual(r["independentClinicalGradesWritten"],0)
        self.assertEqual(r["fdaPrediction"],"ABSTAIN")
        self.assertIsNone(r["calibratedAccuracy"])
        self.assertNotIn("<html>",json.dumps(r))
        self.assertNotIn("%PDF",json.dumps(r))

    def test_downloadable_suppl_not_equal_final_locked_sap(self):
        r=self.checkpoint(fetcher=fake_fetch(reg=registry(with_sap=True)))
        self.assertEqual(r["registry"]["sapDocumentListed"],"CANDIDATE_TITLE_ONLY")
        self.assertFalse(r["finalLockedSapAuthenticated"])
        self.assertEqual(r["independentClinicalGradesWritten"],0)

    def test_source_block_does_not_masquerade_as_missing_original_document(self):
        r=self.checkpoint(fetcher=fake_fetch(pdf=False))
        self.assertEqual(r["sources"][2]["status"],"HTTP_OR_NETWORK_UNAVAILABLE")
        self.assertIsNone(r["sources"][2]["sha256"])
        self.assertEqual(r["sources"][3]["status"],"HTTP_OR_NETWORK_UNAVAILABLE")
        self.assertFalse(r["finalLockedSapAuthenticated"])
        self.assertEqual(r["fdaPrediction"],"ABSTAIN")

    def test_sponsor_mismatch_does_not_autofill_12_vs_3(self):
        r=self.checkpoint(fetcher=fake_fetch(safety=sponsor(complete=False)))
        self.assertEqual(r["sponsor"]["hfBreakdown"],"NOT_VERIFIED")
        self.assertIsNone(r["sponsor"]["treatedReportedTotal"])
        self.assertFalse(r["hfSeriousEvent11vs1Versus12vs3Reconciled"])

    def test_untrusted_registry_identity_never_authenticates_phase(self):
        wrong=registry();wrong["protocolSection"]["identificationModule"]["nctId"]="NCT00000000"
        r=self.checkpoint(fetcher=fake_fetch(reg=wrong))
        self.assertEqual(r["registry"]["identity"],"MISMATCH")
        self.assertFalse(r["independentPhaseReviewerSigned"])

    def test_timestamp_must_be_timezone_aware(self):
        with self.assertRaisesRegex(ValueError,"Timezone-aware"):
            gap.audit(fetcher=fake_fetch(),timestamp=datetime(2026,11,9))

    def test_provenance_hash_changes_when_evidence_changes(self):
        a=self.checkpoint(fetcher=fake_fetch())
        b=self.checkpoint(fetcher=fake_fetch(safety=sponsor(complete=False)))
        self.assertNotEqual(a["receiptSha256"],b["receiptSha256"])
        self.assertNotEqual(a["sources"][1]["sha256"],b["sources"][1]["sha256"])
        self.assertEqual(b["independentClinicalGradesWritten"],0)


if __name__ == "__main__":
    unittest.main()
