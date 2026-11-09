"""Offline tests for alternate public evidence; no grade or source absence claims."""
import importlib.util
from pathlib import Path
import json
from datetime import datetime,timezone
import unittest

script=Path(__file__).resolve().parents[1]/"scripts/medical/acacia_alternative_public_evidence.py"
spec=importlib.util.spec_from_file_location("acacia_alt",script)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
STAMP=datetime(2026,11,9,9,40,tzinfo=timezone.utc)

ARTICLE=b"""<html><head><title>Aficamten for Symptomatic Nonobstructive Hypertrophic Cardiomyopathy</title></head>
<body><h1>Aficamten for Symptomatic Nonobstructive Hypertrophic Cardiomyopathy</h1>
<a href="/doi/suppl/10.1056/NEJMoa2603021/suppl_file/nejmoa2603021_protocol.pdf">Protocol</a>
<a href="/doi/suppl/10.1056/NEJMoa2603021/suppl_file/nejmoa2603021_appendix.pdf">Appendix</a>
<a href="/doi/suppl/10.1056/NEJMoa2603021/suppl_file/nejmoa2603021_data-sharing.pdf">Data sharing</a>
</body></html>"""
RESPONDER=b"""<?xml version="1.0" encoding="utf-8"?>
<article><front><article-meta><title-group>
<article-title>Global Efficacy of Aficamten in Nonobstructive Hypertrophic Cardiomyopathy</article-title>
</title-group></article-meta></front><body><p>NCT06081894</p>
<p>This multidomain responder analysis was included as a secondary analysis in
the ACACIA-HCM statistical analysis plan, before database lock and unblinding.</p>
<p>For patients with missing data, the last available observation (week 8 to week 36)
was used. Patients with no available data on or after week 8 were classified
as nonresponders.</p><p>Requests: medicalaffairs@cytokinetics.com</p>
<p>heart failure events were 11 versus 1 in the two arms.</p></body></article>"""
ECHO=b"""<?xml version="1.0" encoding="utf-8"?>
<article><front><article-meta><title-group><article-title>
Effect of Aficamten on Cardiac Structure and Function in Patients With Symptomatic
Nonobstructive Hypertrophic Cardiomyopathy</article-title>
</title-group></article-meta></front>
<body><p>ACACIA-HCM NCT06081894</p></body></article>"""
def source_fetch(missing=(),corrupt=None):
    data={"NEJM_ARTICLE_LANDING":ARTICLE,
          "EUROPEPMC_RESPONDER_FULLTEXT":RESPONDER,
          "EUROPEPMC_ECHO_FULLTEXT":ECHO}
    if corrupt:
        data[corrupt[0]]=corrupt[1]
    def fetch(k):
        if k in missing:return None,"UNAVAILABLE","HTTPError"
        return data[k],"RETRIEVED",None
    return fetch

class AlternativeResearchTests(unittest.TestCase):
    def run_audit(self,**kwargs):
        return audit.audit(at=STAMP,commit="a"*40,run="1234",**kwargs)
    def test_fixed_https_allowlist(self):
        self.assertEqual(set(audit.SOURCES),{
            "NEJM_ARTICLE_LANDING","EUROPEPMC_RESPONDER_FULLTEXT",
            "EUROPEPMC_ECHO_FULLTEXT"})
        self.assertTrue(all(x.startswith("https://") for x in audit.SOURCES.values()))
        with self.assertRaisesRegex(ValueError,"NOT_AN_ALLOWLISTED"):
            audit.fetch_public("https://untrusted.example/fake")
    def test_publisher_lists_documents_but_does_not_authenticate_final_sap(self):
        parsed=audit.article_landing(ARTICLE)
        self.assertEqual(parsed["sourceIdentity"],"ORIGINAL_PRIMARY_ARTICLE")
        self.assertTrue(parsed["listedProtocol"])
        self.assertTrue(parsed["listedAppendix"])
        self.assertTrue(parsed["dataSharingStatementListed"])
        self.assertEqual(audit.article_landing(b"<html>other paper</html>")["sourceIdentity"],"UNVERIFIED")
        report=self.run_audit(fetcher=source_fetch())
        self.assertFalse(report["finalLockedPrimarySapAuthenticated"])
    def test_secondary_prespec_analysis_and_missingness_are_not_primary_sap(self):
        parsed=audit.europe_pmc_xml(RESPONDER,"RESPONDER")
        self.assertEqual(parsed["sourceIdentity"],"EXACT_TRIAL_SECONDARY_RESPONDER_ARTICLE")
        self.assertTrue(parsed["responderAnalysisDescribedAsPrespecified"])
        self.assertTrue(parsed["lastAvailableObservationDescribed"])
        self.assertTrue(parsed["zeroPostWeek8ClassifiedNonresponder"])
        self.assertTrue(parsed["sponsorDataRequestContactListed"])
        self.assertTrue(parsed["hfEvent11vs1Mentioned"])
        self.assertFalse(parsed["isFinalLockedPrimarySap"])
        self.assertFalse(parsed["isPrimarySensitivityReanalysis"])
    def test_echo_is_same_trial_but_cannot_grade_primary(self):
        parsed=audit.europe_pmc_xml(ECHO,"ECHO")
        self.assertEqual(parsed["sourceIdentity"],"EXACT_TRIAL_SECONDARY_ECHOCARDIOGRAPHY_ARTICLE")
        self.assertFalse(parsed["isFinalLockedPrimarySap"])
    def test_wrong_trial_or_paper_and_invalid_xml_fail_closed(self):
        self.assertEqual(audit.europe_pmc_xml(RESPONDER.replace(b"NCT06081894",b"NCT99999999"),"RESPONDER")["sourceIdentity"],"UNVERIFIED")
        self.assertEqual(audit.europe_pmc_xml(RESPONDER.replace(b"Global Efficacy",b"Other Research"),"RESPONDER")["sourceIdentity"],"UNVERIFIED")
        self.assertEqual(audit.europe_pmc_xml(b"<notxml", "RESPONDER")["sourceIdentity"],"INVALID_XML")
        self.assertEqual(audit.europe_pmc_xml(b"<foo/>","ECHO")["sourceIdentity"],"WRONG_ROOT")
    def test_valid_receipt_is_metadata_only_and_has_stable_self_hash(self):
        r=self.run_audit(fetcher=source_fetch())
        self.assertEqual(r["schema"],audit.SCHEMA)
        self.assertEqual(r["nct"],"NCT06081894")
        self.assertEqual(r["receiptSha256"],audit.hash_receipt(r))
        self.assertEqual(len(r["sources"]),3)
        self.assertTrue(all(v["retrieval"]=="RETRIEVED" for v in r["sources"]))
        self.assertTrue(all(len(v["responseSha256"])==64 for v in r["sources"]))
        self.assertFalse(r["finalLockedPrimarySapAuthenticated"])
        self.assertFalse(r["primaryEndpointSensitivityRecalculated"])
        self.assertFalse(r["hfSafety11vs1Vs12vs3Reconciled"])
        self.assertEqual(r["signedClinicalGrades"],0)
        self.assertEqual(r["fdaPrediction"],"ABSTAIN")
        self.assertIsNone(r["calibratedAccuracy"])
        self.assertNotIn("<article>",json.dumps(r))
        self.assertNotIn("<html>",json.dumps(r))
        self.assertNotIn("Authorization:",json.dumps(r))
    def test_unreachable_sources_do_not_claim_missing_or_authentication(self):
        r=self.run_audit(fetcher=source_fetch(missing=["NEJM_ARTICLE_LANDING","EUROPEPMC_RESPONDER_FULLTEXT"]))
        self.assertEqual(r["sources"][0]["retrieval"],"UNAVAILABLE")
        self.assertEqual(r["sources"][1]["retrieval"],"UNAVAILABLE")
        self.assertEqual(r["publisherSupplementListings"]["sourceIdentity"],"UNVERIFIED")
        self.assertEqual(r["supportiveSecondaryResponderMethods"]["sourceIdentity"],"UNVERIFIED")
        self.assertFalse(r["finalLockedPrimarySapAuthenticated"])
        self.assertEqual(r["signedClinicalGrades"],0)
    def test_source_change_and_safety_count_remain_not_reconciled(self):
        a=self.run_audit(fetcher=source_fetch())
        b=self.run_audit(fetcher=source_fetch(corrupt=("EUROPEPMC_RESPONDER_FULLTEXT",
            RESPONDER.replace(b"11 versus 1",b"9 versus 2"))))
        self.assertNotEqual(a["sources"][1]["responseSha256"],b["sources"][1]["responseSha256"])
        self.assertFalse(b["supportiveSecondaryResponderMethods"]["hfEvent11vs1Mentioned"])
        self.assertFalse(b["hfSafety11vs1Vs12vs3Reconciled"])
        self.assertEqual(b["signedClinicalGrades"],0)
    def test_time_must_have_timezone(self):
        with self.assertRaisesRegex(ValueError,"UTC_AWARE_TIME_REQUIRED"):
            audit.audit(fetcher=source_fetch(),at=datetime(2026,11,9))
if __name__=="__main__":unittest.main()
