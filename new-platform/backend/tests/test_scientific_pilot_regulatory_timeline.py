"""Historical DMC/PDUFA chronology: distinct documented events, no forecast."""
import copy
import unittest

from app.scientific_pilot_regulatory_timeline import (
    NCT, MERCK_DMC, MERCK_REVIEW, NEJM, NCI_APPROVAL, FDA_2016_APPROVAL,
    keynote024_historical_pdufa_timeline,
)
from app.scientific_pilot_keynote024_results import keynote024_published_results
from app.scientific_protocol_readiness import keynote024_protocol_readiness
from app.scientific_pilot_interim_design import published_keynote024_interim_design
from app.scientific_pilot_eu_plan_crosscheck import keynote024_eu_protocol_crosscheck


def sources():
    published = keynote024_published_results()
    dossier = {"nct_id": NCT, "source_sha256": "a" * 64,
               "read_only": True, "overall_score": None,
               "fda_approval_probability": None}
    readiness = keynote024_protocol_readiness(dossier, published)
    interim = published_keynote024_interim_design(published, readiness)
    european = keynote024_eu_protocol_crosscheck(interim, published, readiness)
    return published, readiness, interim, european


class HistoricalRegulatoryTimelineTests(unittest.TestCase):
    def test_dmc_review_dates_and_public_disclosure_are_different_events(self):
        result = keynote024_historical_pdufa_timeline(*sources())
        keyed = {e["key"]: e for e in result["events"]}
        self.assertEqual(result["eventCount"], 10)
        self.assertEqual(keyed["original_interim_data_cutoff"]["eventDate"], "2016-05-09")
        self.assertEqual(keyed["dmc_review_first"]["eventDate"], "2016-06-08")
        self.assertEqual(keyed["dmc_review_second"]["eventDate"], "2016-06-14")
        self.assertEqual(keyed["sponsor_public_stopping_notice"]["eventDate"], "2016-06-16")
        self.assertEqual(keyed["dmc_review_second"]["sourceUrl"], NEJM)
        self.assertEqual(keyed["dmc_review_second"]["sourceTemporalStatus"],
                         "event_reported_retrospectively")
        self.assertEqual(keyed["dmc_review_second"]["sourcePublicationOrEntryDate"],
                         "2016-10-08")
        self.assertEqual(keyed["sponsor_public_stopping_notice"]["sourceUrl"], MERCK_DMC)
        self.assertEqual(keyed["sponsor_public_stopping_notice"]["sourceTemporalStatus"],
                         "contemporaneous_sponsor_news")
        self.assertEqual(keyed["sponsor_public_stopping_notice"]["sourcePublicationOrEntryDate"],
                         "2016-06-16")
        self.assertEqual(result["interim"]["independentCommitteeReviewDatesReportedByJournal"],
                         ["2016-06-08", "2016-06-14"])
        self.assertFalse(result["interim"]["dmcMinutesAndSignedRecommendationReviewed"])
        self.assertFalse(result["interim"]["dmcExactRecommendationDecisionDateProven"])
        self.assertFalse(result["interim"]["prospectiveStoppingBoundaryRecalculated"])

    def test_first_line_pdufa_goal_is_after_real_approval_not_a_second_action(self):
        result = keynote024_historical_pdufa_timeline(*sources())
        keyed = {e["key"]: e for e in result["events"]}
        app = result["application"]
        self.assertEqual(app["biologicsLicense"], "125514/S-12")
        self.assertEqual(app["targetAnnouncedDate"], "2016-09-07")
        self.assertEqual(app["targetPdufaDate"], "2016-12-24")
        self.assertEqual(app["actualFdaActionDate"], "2016-10-24")
        self.assertEqual(app["actualAction"], "approved_first_line_pembrolizumab")
        self.assertEqual(app["firstLineSupportedBy"], NCT)
        self.assertEqual(app["sameDaySecondLineConversionDifferentTrial"], "KEYNOTE-010")
        self.assertTrue(app["actualActionKnownOnlyInHindsight"])
        self.assertTrue(app["neverTreatTargetAsObservedDecision"])
        self.assertEqual(keyed["first_line_priority_review_notice"]["sourceUrl"], MERCK_REVIEW)
        self.assertEqual(keyed["announced_pdufa_goal"]["sourceTemporalStatus"],
                         "historical_target_not_decision")
        self.assertEqual(keyed["fda_first_line_approval"]["sourceUrl"], FDA_2016_APPROVAL)
        self.assertEqual(keyed["fda_first_line_approval"]["sourcePublicationOrEntryDate"],
                         "2016-10-24")
        self.assertEqual(keyed["announced_pdufa_goal"]["eventDate"], "2016-12-24")
        self.assertEqual(keyed["fda_first_line_approval"]["eventDate"], "2016-10-24")

    def test_original_fda_letter_separates_s8_s12_and_future_commitment(self):
        report = keynote024_historical_pdufa_timeline(*sources())
        original = report["primaryFdaActionLetter"]
        self.assertEqual(original["sourceUrl"], FDA_2016_APPROVAL)
        self.assertEqual(original["referenceId"], "4003165")
        self.assertEqual(original["pdfPagesObserved"], 6)
        self.assertEqual(original["regulatoryActionDate"], "2016-10-24")
        self.assertEqual(original["signedDatePrintedInPdf"], "2016-10-24")
        self.assertEqual(original["sourceLocators"]["electronicSignature"], "PDF page 6")
        self.assertTrue(original["sameDocumentContainsDistinctS8AndS12Actions"])

        s8, s12 = original["s8"], original["s12"]
        self.assertEqual(s8["supplement"], "125514/S-8")
        self.assertEqual(s8["pdl1TpsMinimumPercent"], 1)
        self.assertFalse(s8["isFirstLineApproval"])
        self.assertEqual(s8["previousAcceleratedApprovalDate"], "2015-10-02")
        self.assertEqual(s12["supplement"], "125514/S-12")
        self.assertEqual(s12["pdl1TpsMinimumPercent"], 50)
        self.assertTrue(s12["egfrAndAlkGenomicAberrationsExcluded"])
        self.assertEqual(s12["trialReportedAsSupport"], "NCT02142738")
        self.assertEqual(original["secondaryNciReportUrl"], NCI_APPROVAL)

        commitment = original["keynote024PostmarketingCommitment"]
        self.assertEqual(commitment["commitmentId"], "3127-1")
        self.assertEqual(commitment["originalTargetFinalReportMonth"], "2018-06")
        self.assertTrue(commitment["letterDoesNotEstablishActualFinalReportSubmission"])
        self.assertFalse(commitment["originalReportSubmissionIndependentlyVerified"])
        self.assertFalse(original["fdaDocumentSha256VerifiedByThisReview"])
        self.assertFalse(original["fullSignedClinicalSapVerified"])
        self.assertTrue(original["sourceCitationNotIndependentClinicalAdjudication"])
        self.assertFalse(original["modelEligibleForProspectiveOutcomeCalibration"])
        self.assertIsNone(report["scientificScore"])
        self.assertIsNone(report["fdaApprovalProbability"])

    def test_fda_letter_event_is_primary_regulator_document_not_later_news(self):
        report = keynote024_historical_pdufa_timeline(*sources())
        event = next(event for event in report["events"]
                     if event["key"] == "fda_first_line_approval")
        self.assertEqual(event["eventDate"], "2016-10-24")
        self.assertEqual(event["sourceUrl"], FDA_2016_APPROVAL)
        self.assertEqual(event["sourceTemporalStatus"],
                         "primary_fda_regulatory_action_letter")
        self.assertIn("p. 1", event["sourceLocator"])
        self.assertIn("S-8", event["caveat"])
        self.assertIn("S-12", event["caveat"])
        self.assertNotEqual(event["sourceUrl"], NCI_APPROVAL)

    def test_historical_success_does_not_raise_science_grades(self):
        result = keynote024_historical_pdufa_timeline(*sources())
        self.assertEqual(result["status"],
                         "historical_source_timeline_not_outcome_forecast")
        decision = result["conclusions"]
        self.assertTrue(decision["publicStoppingChronologyCorroborated"])
        self.assertTrue(decision["regulatoryTargetAndActualActionIdentified"])
        self.assertTrue(decision["retrospectiveDataNotProspectivePrediction"])
        self.assertFalse(decision["independentDmcMinutesReviewed"])
        self.assertFalse(decision["originalProtocolSapAuthenticated"])
        self.assertFalse(decision["originalSignedAlphaSpendingReconstructed"])
        self.assertFalse(decision["fullIndependentScientificAdjudicationDone"])
        self.assertFalse(decision["inputReadinessGradeChanged"])
        self.assertFalse(decision["reluctanceGradeChanged"])
        self.assertTrue(result["readOnly"])
        self.assertFalse(result["fsFaModified"])
        self.assertFalse(result["tradingActionsEnabled"])
        self.assertIsNone(result["scientificScore"])
        self.assertIsNone(result["fdaApprovalProbability"])

    def test_2014_registry_entry_is_not_original_endpoint_amendment_proof(self):
        result = keynote024_historical_pdufa_timeline(*sources())
        record = result["events"][0]
        self.assertEqual(record["eventDate"], "2014-06-19")
        self.assertEqual(record["sourceTemporalStatus"],
                         "registry_source_version_unverified")
        self.assertIn("no individual", record["caveat"])
        self.assertEqual(result["events"][1]["eventDate"], "2015-05-20")
        for milestone in result["events"]:
            self.assertFalse(milestone["originalDmcMinutesVerified"])
            self.assertFalse(milestone["originalSignedSapVerified"])
            self.assertTrue(milestone["sourceUrl"].startswith("https://"))
            self.assertTrue(milestone["sourceLocator"])

    def test_stale_identity_grade_fake_signed_sap_or_edited_events_fail(self):
        fixture = sources()
        attacks = [
            lambda a,b,c,d: a.__setitem__("nct_id", "NCT99999999"),
            lambda a,b,c,d: a.__setitem__("overall_score", 85),
            lambda a,b,c,d: b["inputReadiness"].__setitem__("grade", "PASS"),
            lambda a,b,c,d: b["reluctance"].__setitem__("grade", "LOW"),
            lambda a,b,c,d: b["original2016ProtocolSource"].__setitem__(
                "originalSignedSapVerified", True),
            lambda a,b,c,d: b["checks"][4].__setitem__("status", "SOURCE_SUPPORTED"),
            lambda a,b,c,d: c["observedInterim"].__setitem__("reportedDeaths", 900),
            lambda a,b,c,d: c["observedInterim"].__setitem__("fdaStaffReportedOsAllocatedAlpha", 0.1),
            lambda a,b,c,d: d["registry"].__setitem__("firstRecordEnteredDate", "2019-01-01"),
            lambda a,b,c,d: d["registry"].__setitem__("individualEndpointFieldVersionDated", True),
            lambda a,b,c,d: d["eventTiming"].__setitem__("euPfsEventsTargetApprox", 189),
            lambda a,b,c,d: a["analysis_snapshots"][0].__setitem__(
                "data_cutoff_date", "2017-05-09"),
        ]
        for index, attack in enumerate(attacks):
            items = copy.deepcopy(fixture)
            attack(*items)
            with self.subTest(index=index), self.assertRaises(ValueError):
                keynote024_historical_pdufa_timeline(*items)

    def test_response_does_not_mutate_inputs_or_allow_persistent_edits(self):
        fixture = sources()
        before = copy.deepcopy(fixture)
        response = keynote024_historical_pdufa_timeline(*fixture)
        response["events"][0]["title"] = "invented"
        again = keynote024_historical_pdufa_timeline(*fixture)
        self.assertNotEqual(again["events"][0]["title"], "invented")
        self.assertEqual(fixture, before)


if __name__ == "__main__":
    unittest.main()
