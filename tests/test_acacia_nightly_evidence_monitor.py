"""Offline regression for exact-NCT, hash-linked public-only pilot evidence receipts."""
import datetime
import importlib.util
import json
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parent.parent / "scripts/medical/acacia_nightly_evidence_monitor.py"
spec = importlib.util.spec_from_file_location("acacia_evidence", FILE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

DATE = datetime.datetime(2026, 11, 9, 3, 17, tzinfo=datetime.timezone.utc)


def registry(*, nct="NCT06081894", phase="PHASE3", date="2026-09-22",
             documents=None, results=False):
    result = {"protocolSection": {
        "identificationModule": {"nctId": nct,
            "briefTitle": "ACACIA-HCM in Non-Obstructive Hypertrophic Cardiomyopathy"},
        "designModule": {"phases": [phase]},
        "statusModule": {"studyLastUpdatePostDateStruct": {"date": date}},
    }}
    if documents is not None:
        result["documentSection"] = {"largeDocumentModule":{"largeDocs":documents}}
    if results:
        result["resultsSection"] = {"baselineCharacteristicsModule":{"groups":[]}}
    return result


def publication():
    return {"resultList":{"result":[{
        "pmid":"42663312","id":"42663312",
        "title":"Aficamten for Nonobstructive Hypertrophic Cardiomyopathy"}]}}


def fake_fetch(reg=None, pub=None, unavailable=()):
    data = {"REGISTRY": reg if reg is not None else registry(),
            "NEJM_PIVOTAL_INDEX": pub if pub is not None else publication()}
    def fetch(source_id):
        if source_id in unavailable:
            raise audit.SourceUnavailable("UPSTREAM_UNAVAILABLE")
        blob = audit.canonical(data[source_id]).encode("utf-8")
        return data[source_id], blob
    return fetch


class PilotMonitorTests(unittest.TestCase):
    def checkpoint(self, **kwargs):
        return audit.make_checkpoint(now=DATE, git_sha="a"*40,
            run_id="123456", **kwargs)

    def test_exact_identity_and_source_scope(self):
        self.assertTrue(audit.is_registry(registry()))
        self.assertFalse(audit.is_registry(registry(nct="NCT00000000")))
        self.assertFalse(audit.is_registry(registry(phase="PHASE2")))
        self.assertFalse(audit.is_registry({}))
        self.assertTrue(audit.is_publication(publication()))
        bad = publication()
        bad["resultList"]["result"][0]["pmid"] = "1234"
        self.assertFalse(audit.is_publication(bad))
        self.assertEqual(set(audit.SOURCES), {"REGISTRY","NEJM_PIVOTAL_INDEX"})
        with self.assertRaises(ValueError):
            audit.fetch_public("OTHER")

    def test_first_check_has_pinned_documentary_scores_and_no_clinical_writes(self):
        a = self.checkpoint(fetcher=fake_fetch())
        self.assertEqual(a["nct"],"NCT06081894")
        self.assertEqual(a["status"],"SOURCE_IDENTITIES_MATCH")
        self.assertEqual(a["historyStatus"],"NONE_PROVIDED")
        self.assertEqual([row["points"] for row in a["provisionalDocumentaryScores"]],[3,3,2])
        self.assertTrue(all(x["outOf"]==5 for x in a["provisionalDocumentaryScores"]))
        self.assertEqual(a["officialClinicalGradeEventsWritten"],0)
        self.assertEqual(a["independentPhaseSignoffsWritten"],0)
        self.assertEqual(a["fdaPrediction"],"ABSTAIN")
        self.assertEqual(a["accuracy"],"NOT_CALIBRATED")
        self.assertFalse(a["newDocumentsAutomaticallyGraded"])
        self.assertEqual(a["receiptSha256"],audit.receipt_hash(a))
        self.assertTrue(all(len(x["responseSha256"])==64 for x in a["sources"]))

    def test_prior_checkpoint_hash_chain_and_detect_changed_source(self):
        first = self.checkpoint(fetcher=fake_fetch())
        second = self.checkpoint(fetcher=fake_fetch(),prior=first)
        self.assertEqual(second["historyStatus"],"PREVIOUS_VALID")
        self.assertEqual(second["previousReceiptSha256"],first["receiptSha256"])
        self.assertEqual(second["sourceChangesSincePrevious"],[])
        changed = self.checkpoint(
            fetcher=fake_fetch(reg=registry(date="2026-11-09")),prior=first)
        self.assertEqual(changed["status"],"REVIEW_REQUIRED")
        self.assertEqual(changed["sourceChangesSincePrevious"],["REGISTRY"])
        self.assertIn("REGISTRY_RECORD_UPDATED_SINCE_BASELINE",
                      changed["newResearchCandidates"])
        self.assertEqual(changed["provisionalDocumentaryScores"],first["provisionalDocumentaryScores"])
        self.assertEqual(changed["officialClinicalGradeEventsWritten"],0)

    def test_hash_mismatch_does_not_silently_claim_no_change(self):
        original=self.checkpoint(fetcher=fake_fetch())
        original["sources"][0]["responseSha256"]="f"*64
        next_run=self.checkpoint(fetcher=fake_fetch(),prior=original)
        self.assertEqual(next_run["historyStatus"],"PREVIOUS_INVALID")
        self.assertIsNone(next_run["previousReceiptSha256"])
        self.assertTrue(all(x["changedSincePrevious"] is None for x in next_run["sources"]))

    def test_source_unavailable_is_not_false_success_or_clinical_failure(self):
        result=self.checkpoint(fetcher=fake_fetch(unavailable=("REGISTRY",)))
        self.assertEqual(result["status"],"PARTIAL_UNAVAILABLE")
        self.assertEqual(result["sources"][0]["status"],"UNAVAILABLE")
        self.assertIsNone(result["sources"][0]["responseSha256"])
        self.assertEqual(result["sources"][0]["errorCategory"],"UPSTREAM_UNAVAILABLE")
        self.assertEqual(result["officialClinicalGradeEventsWritten"],0)

    def test_changed_identity_withholds_research_status_but_not_new_scores(self):
        result=self.checkpoint(fetcher=fake_fetch(reg=registry(nct="NCT99999999")))
        self.assertEqual(result["status"],"REVIEW_REQUIRED")
        self.assertEqual(result["sources"][0]["status"],"CHANGED")
        self.assertEqual(result["newResearchCandidates"],[])
        self.assertEqual(result["fdaPrediction"],"ABSTAIN")

    def test_new_results_and_sap_document_are_research_candidates_only(self):
        reg=registry(date="2026-11-09",results=True,
            documents=[{"title":"Statistical Analysis Plan"}])
        result=self.checkpoint(fetcher=fake_fetch(reg=reg))
        self.assertEqual(result["status"],"REVIEW_REQUIRED")
        self.assertIn("NEW_REGISTRY_RESULTS_CANDIDATE",result["newResearchCandidates"])
        self.assertIn("PUBLIC_SAP_TITLE_CANDIDATE_UNREVIEWED",result["newResearchCandidates"])
        self.assertFalse(result["newDocumentsAutomaticallyGraded"])
        self.assertEqual(result["officialClinicalGradeEventsWritten"],0)

    def test_no_timezone_naive_receipt(self):
        with self.assertRaisesRegex(ValueError,"Timezone-aware"):
            audit.make_checkpoint(fetcher=fake_fetch(),
                now=datetime.datetime(2026,11,9))

    def test_receipts_include_only_public_metadata_and_no_source_html(self):
        result=self.checkpoint(fetcher=fake_fetch())
        stored=json.dumps(result)
        self.assertNotIn("DASHBOARD_PASSWORD",stored)
        self.assertNotIn("authorization",stored.lower())
        self.assertNotIn("medical_review_api_key",stored.lower())
        self.assertNotIn("<html>",stored.lower())
        self.assertEqual(result["productionWrites"],0)
        self.assertEqual(result["rosterMutations"],0)


if __name__=="__main__":
    unittest.main()
