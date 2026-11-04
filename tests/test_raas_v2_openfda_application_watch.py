"""Offline FDA public-API identity monitor regression tests: never a predictor."""
from copy import deepcopy
import unittest

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import raas_v2_openfda_application_watch as watch

ASOF = "2026-11-03T23:59:59Z"


def response(submissions=None):
    if submissions is None:
        submissions = [
            {"submission_type":"ORIG","submission_number":"1",
             "submission_status":"AP","submission_status_date":"20251219",
             "submission_class_code":"TYPE 1"},
            {"submission_type":"SUPPL","submission_number":"001",
             "submission_status":"AP","submission_status_date":"20260205",
             "submission_class_code":"REMS"},
        ]
    return {"meta":{"last_updated":"2026-09-11"},
            "results":[{"application_number":"NDA219083",
                         "sponsor_name":"CYTOKINETICS INC",
                         "submissions":submissions}]}


class FDAApplicationWatchTests(unittest.TestCase):
    def test_parent_and_already_approved_s001_are_not_pending_maple_or_november_outcome(self):
        result=watch.inspect_response(response(), ASOF)
        self.assertEqual(result["openFdaSourceStatus"],"AVAILABLE")
        self.assertEqual(result["cytk"]["fdaKnownParentNda"],"NDA219083")
        self.assertTrue(result["cytk"]["fdaParentRecordReturned"])
        self.assertEqual(len(result["cytk"]["observedSupplementSubmissionRows"]),1)
        self.assertTrue(result["cytk"]["observedSupplementSubmissionRows"][0][
            "isPreviouslyApprovedUnrelatedRemsS001"])
        self.assertFalse(result["cytk"]["fdaApprovedFebruaryRemsS001IsNovemberMapleHcm"])
        self.assertFalse(result["cytk"]["mapleHcmCurrentSupplementNumberIndependentlyVerified"])
        self.assertFalse(result["cytk"]["newFdaMapleHcmApprovalIndependentlyAdjudicated"])
        self.assertEqual(result["smmt"]["fdaCurrentBlaNumberIndependentlyVerified"],False)
        self.assertFalse(result["smmt"]["fdaPublicOpenFdaNoMatchingApprovedBlaProvesNoPendingBla"])
        self.assertFalse(result["canPromoteToFdaPredictionAccuracy"])
        self.assertEqual(result["newImmutableThreeWayPredictions"],0)
        self.assertEqual(result["approvedMetricCalibrations"],0)

    def test_ambiguous_efficacy_approval_candidate_is_not_maple_outcome(self):
        p=response()
        p["results"][0]["submissions"].append({
            "submission_type":"SUPPL","submission_number":"002",
            "submission_status":"AP","submission_status_date":"20261030",
            "submission_class_code":"EFFICACY","application_docs":[
                {"title":"FDA Supplement Approval Letter","url":"https://www.accessdata.fda.gov/"}
            ]})
        result=watch.inspect_response(p,ASOF)
        candidate=result["cytk"]["nonS001SupplementRowsRequireSeparateDocumentCycleMatching"]
        self.assertEqual(len(candidate),1)
        self.assertEqual(candidate[0]["submissionNumber"],"002")
        self.assertFalse(candidate[0]["isMapleHcmPendingSupplementIndependentlyIdentified"])
        self.assertFalse(candidate[0]["isApprovedMapleHcmOutcomeIndependentlyAdjudicated"])
        self.assertEqual(result["independentlyAdjudicatedNov14FdaActions"],0)

    def test_all_known_s001_number_formats_are_excluded(self):
        for number in ("001","S-001","S001","1","0001"):
            p=response([{"submission_type":"SUPPL","submission_number":number,
                         "submission_status":"AP","submission_status_date":"20260205"}])
            with self.subTest(number=number):
                r=watch.inspect_response(p,ASOF)
                self.assertTrue(r["cytk"]["observedSupplementSubmissionRows"][0][
                    "isPreviouslyApprovedUnrelatedRemsS001"])
                self.assertEqual(r["cytk"][
                    "nonS001SupplementRowsRequireSeparateDocumentCycleMatching"],[])

    def test_source_unavailable_or_404_is_unknown_not_negative_evidence(self):
        for status in ("SOURCE_UNAVAILABLE","HTTP_404_NO_PUBLIC_RECORD",
                       "MALFORMED_RESPONSE"):
            r=watch.inspect_response(None,ASOF,status,"simulated")
            self.assertFalse(r["cytk"]["fdaParentRecordReturned"])
            self.assertFalse(r["smmt"][
                "fdaPublicOpenFdaNoMatchingApprovedBlaProvesNoPendingBla"])
            self.assertFalse(r["canPromoteToFdaPredictionAccuracy"])
            self.assertEqual(r["independentlyCertifiedCurrentFdaReviewCycles"],0)

    def test_future_dated_fda_rows_not_retroactive_proof(self):
        p=response([{"submission_type":"SUPPL","submission_number":"005",
                     "submission_status":"AP","submission_status_date":"20261120"}])
        r=watch.inspect_response(p,ASOF)
        self.assertEqual(r["cytk"]["observedSupplementSubmissionRows"],[])

    def test_mismatched_parent_application_or_duplicate_results_fails_closed(self):
        for p in (
            {"results":[{"application_number":"NDA999999","submissions":[]}]},
            {"results":[]},
            {"results":[{"application_number":"NDA219083","submissions":[]},
                        {"application_number":"NDA219083","submissions":[]}]},
            {"results":[{"application_number":"NDA219083","submissions":None}]},
        ):
            with self.assertRaises(ValueError):
                watch.inspect_response(p,ASOF)
        with self.assertRaises(ValueError):
            watch.inspect_response(response(),ASOF,"SOURCE_UNAVAILABLE")

    def test_fda_dossier_cannot_promote_unknown_review_cycle_or_frozen_forecast(self):
        import json
        source=json.loads(watch.DOSSIER.read_text("utf-8"))
        for ticker,field,bad in (
            ("CYTK","currentSupplementSequenceNumber","S-002"),
            ("CYTK","fdaPreviouslyApprovedS001EstablishesNov14FDAOutcome",True),
            ("SMMT","currentBlaNumber","BLA761999"),
            ("SMMT","independentlyVerifiedThreeWayForecast",True),
        ):
            modified=deepcopy(source)
            next(x for x in modified["records"] if x["ticker"]==ticker)[field]=bad
            with self.subTest(ticker=ticker,field=field),self.assertRaises(ValueError):
                watch.inspect_response(response(),ASOF,dossier=modified)

    def test_asof_date_must_be_parseable(self):
        for bad in ("2026-11-03","2026-13-03T23:59:59Z","not a date",None):
            with self.assertRaises(ValueError):
                watch.inspect_response(response(),bad)


if __name__=="__main__":
    unittest.main()
