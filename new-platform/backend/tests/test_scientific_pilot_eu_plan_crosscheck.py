"""EU regulator-hosted cross-source match is not original signed SAP."""
import copy
import unittest

from app.scientific_pilot_eu_plan_crosscheck import (
    EU_URL, EU_NUMBER, NCT, keynote024_eu_protocol_crosscheck,
)
from app.scientific_pilot_interim_design import published_keynote024_interim_design
from app.scientific_protocol_readiness import keynote024_protocol_readiness
from app.scientific_pilot_keynote024_results import keynote024_published_results


def _evidence():
    published = keynote024_published_results()
    dossier = {
        "nct_id": NCT, "source_sha256": "a" * 64,
        "read_only": True, "overall_score": None,
        "fda_approval_probability": None,
    }
    readiness = keynote024_protocol_readiness(dossier, published)
    interim = published_keynote024_interim_design(published, readiness)
    return interim, published, readiness


class EuropeanRegistryCrosscheckTests(unittest.TestCase):
    def test_eu_register_first_entered_2014_but_field_versions_not_verified(self):
        result = keynote024_eu_protocol_crosscheck(*_evidence())
        reg = result["registry"]
        self.assertEqual(reg["eudractNumber"], EU_NUMBER)
        self.assertEqual(reg["sourceUrl"], EU_URL)
        self.assertEqual(reg["firstRecordEnteredDate"], "2014-06-19")
        self.assertEqual(reg["competentAuthorityDecisionDate"], "2014-06-19")
        self.assertTrue(reg["recordFirstEnteredBeforeInterim"])
        self.assertFalse(reg["individualEndpointFieldVersionDated"])
        self.assertFalse(reg["original2014FieldContentAuthenticated"])
        self.assertFalse(reg["signed2016SAPAvailable"])
        self.assertFalse(reg["authoredBySeparateOrganization"])
        self.assertTrue(result["identityBridge"]["identityCrosscheckOnly"])
        self.assertEqual(result["identityBridge"]["nciSecondaryId"], EU_NUMBER)
        self.assertFalse(result["identityBridge"]["separateClinicalTrial"])

    def test_eu_primary_endpoint_and_event_counts_match_published_plan(self):
        result = keynote024_eu_protocol_crosscheck(*_evidence())
        self.assertEqual(len(result["comparisons"]), 6)
        by_key = {c["key"]: c for c in result["comparisons"]}
        self.assertEqual(by_key["primary_pfs"]["euSection"], "E.5.1")
        self.assertIsNone(by_key["primary_pfs"]["reportedPlannedCount"])
        self.assertEqual(by_key["planned_pfs_events"]["euSection"], "E.5.1.1")
        self.assertEqual(by_key["planned_pfs_events"]["reportedPlannedCount"], 175)
        self.assertEqual(by_key["planned_os_first"]["reportedPlannedCount"], 110)
        self.assertEqual(by_key["planned_os_second"]["reportedPlannedCount"], 170)
        self.assertTrue(all(c["crossSourceAgreement"] for c in result["comparisons"]))
        self.assertTrue(all(c["revisionHistoryVerified"] is False for c in result["comparisons"]))
        self.assertTrue(all(c["independentSignedSAPConfirmation"] is False
                            for c in result["comparisons"]))
        self.assertEqual(result["identityBridge"]["nciTrialId"], NCT)

    def test_event_timing_caveat_prevents_fabricating_a_deviation(self):
        result = keynote024_eu_protocol_crosscheck(*_evidence())
        event = result["eventTiming"]
        self.assertEqual(event["euPfsEventsTargetApprox"], 175)
        self.assertEqual(event["reportedPfsEventsObserved"], 189)
        self.assertEqual(event["euOsFirstDeathsTargetApprox"], 110)
        self.assertEqual(event["reportedOsInterimDeathsObserved"], 108)
        self.assertTrue(event["euAllowsPfsTimingDelayIfOsUnder110"])
        self.assertFalse(event["actualDataMonitoringCommitteeTimingReconciled"])
        self.assertTrue(event["eventDifferenceNotAutomaticProtocolDeviation"])
        self.assertEqual(event["euSourceSection"], "E.5.1.1")

    def test_correlated_sponsor_sources_do_not_validate_trial_or_grade(self):
        result = keynote024_eu_protocol_crosscheck(*_evidence())
        decision = result["researchConclusions"]
        self.assertTrue(decision["primaryPfsDesignCorroboratedAcrossSources"])
        self.assertTrue(decision["approximateEventTargetsAgreeAcrossSources"])
        for flag in ("alphaSpendingInEuRegistryVerified",
                     "originalEffectiveProtocolAmendmentsVerified",
                     "preInterimSignedSapVerified", "independentReplicationCompleted",
                     "safetyBenefitRiskAdjudicated", "inputReadinessGradeChanged",
                     "reluctanceGradeChanged", "canBeUsedToAssignClinicalSuccessGrade"):
            self.assertIs(decision[flag], False, flag)
        self.assertIsNone(result["scientificScore"])
        self.assertIsNone(result["fdaApprovalProbability"])
        self.assertTrue(result["readOnly"])
        self.assertFalse(result["fsFaModified"])
        self.assertFalse(result["tradingActionsEnabled"])

    def test_swapped_trial_tampered_plan_and_false_grades_fail_closed(self):
        original = _evidence()
        changes = [
            lambda a, b, c: a.__setitem__("nctId", "NCT87654321"),
            lambda a, b, c: b.__setitem__("nct_id", "NCT87654321"),
            lambda a, b, c: c.__setitem__("nctId", "NCT87654321"),
            lambda a, b, c: b.__setitem__("overall_score", 89),
            lambda a, b, c: a.__setitem__("fdaApprovalProbability", 0.91),
            lambda a, b, c: c["inputReadiness"].__setitem__("grade", "PASS"),
            lambda a, b, c: c["reluctance"].__setitem__("grade", "LOW"),
            lambda a, b, c: c["original2016ProtocolSource"].__setitem__("originalSignedSapVerified", True),
            lambda a, b, c: a["reportedDesign"]["secondInterim"].__setitem__(
                "plannedApproximatePfsEvents", 185),
            lambda a, b, c: a["reportedDesign"]["osGroupSequential"].__setitem__(
                "plannedApproximateDeaths", [109, 170]),
            lambda a, b, c: a["observedInterim"].__setitem__(
                "reportedDeaths", 500),
            lambda a, b, c: a["sourceDateContext"].__setitem__(
                "originalSupplementRead", True),
            lambda a, b, c: b["analysis_snapshots"][0].__setitem__(
                "data_cutoff_date", "2018-01-01"),
        ]
        for index, change in enumerate(changes):
            a, b, c = copy.deepcopy(original)
            change(a, b, c)
            with self.subTest(index=index), self.assertRaises(ValueError):
                keynote024_eu_protocol_crosscheck(a, b, c)

    def test_outputs_are_independent_from_caller_mutation(self):
        a, b, c = _evidence()
        before = copy.deepcopy((a, b, c))
        first = keynote024_eu_protocol_crosscheck(a, b, c)
        first["comparisons"][0]["euSection"] = "INVALID"
        second = keynote024_eu_protocol_crosscheck(a, b, c)
        self.assertEqual(second["comparisons"][0]["euSection"], "E.5.1")
        self.assertEqual((a, b, c), before)


if __name__ == "__main__":
    unittest.main()
