"""Contracts: journal-reported interim design is not signed prospective SAP."""
import copy
import unittest

from app.scientific_pilot_interim_design import (
    published_keynote024_interim_design,
)
from app.scientific_pilot_keynote024_results import keynote024_published_results
from app.scientific_protocol_readiness import keynote024_protocol_readiness


def inputs():
    published = keynote024_published_results()
    dossier = {
        "nct_id": "NCT02142738", "source_sha256": "a" * 64,
        "read_only": True, "overall_score": None,
        "fda_approval_probability": None,
    }
    return published, keynote024_protocol_readiness(dossier, published)


class InterimDesignTests(unittest.TestCase):
    def test_published_plan_and_observed_interim_report_are_not_signed_sap(self):
        p, r = inputs()
        data = published_keynote024_interim_design(p, r)
        self.assertEqual(data["nctId"], "NCT02142738")
        self.assertEqual(data["reportedDesign"]["overallOneSidedAlphaPercent"], 2.5)
        first = data["reportedDesign"]["firstInterim"]
        self.assertEqual(first["plannedMinimumRandomized"], 191)
        self.assertEqual(first["plannedMinimumFollowupMonths"], 6)
        self.assertEqual(first["reportedAllocatedOneSidedAlphaPercent"], 0.5)
        second = data["reportedDesign"]["secondInterim"]
        self.assertEqual(second["plannedApproximatePfsEvents"], 175)
        self.assertEqual(second["reportedAllocatedOneSidedAlphaPercent"], 2.0)
        self.assertEqual(data["reportedDesign"]["osGroupSequential"]["plannedApproximateDeaths"], [110, 170])
        observed = data["observedInterim"]
        self.assertEqual(observed["reportedPfsEvents"], 189)
        self.assertEqual(observed["reportedDeaths"], 108)
        self.assertEqual(observed["reportedOsPValue"], 0.005)
        self.assertEqual(observed["fdaStaffReportedOsAllocatedAlpha"], 0.0118)
        self.assertTrue(data["sourceDateContext"]["originalSupplementSourceUrl"].startswith("https://"))
        self.assertFalse(data["sourceDateContext"]["originalSupplementRead"])
        self.assertFalse(data["sourceDateContext"]["contemporaneousSapAuthenticated"])
        self.assertFalse(data["reportedDesign"]["signedOriginalPlanAuthenticated"])
        self.assertFalse(data["reconciliation"]["scientificConclusionAuthorized"])
        self.assertFalse(data["reconciliation"]["alphaSpendingRecomputedFromSignedSAP"])
        self.assertFalse(data["reconciliation"]["inputReadinessGradeChanged"])
        self.assertFalse(data["reconciliation"]["reluctanceGradeChanged"])
        self.assertIsNone(data["scientificScore"])
        self.assertIsNone(data["fdaApprovalProbability"])
        self.assertTrue(data["readOnly"])
        self.assertFalse(data["tradingActionsEnabled"])

    def test_unverified_sap_cannot_be_silently_upgraded(self):
        p, r = inputs()
        mutations = [
            lambda a, b: a.__setitem__("nct_id", "NCT87654321"),
            lambda a, b: a.__setitem__("overall_score", 92),
            lambda a, b: b["inputReadiness"].__setitem__("grade", "PASS"),
            lambda a, b: b["reluctance"].__setitem__("grade", "LOW"),
            lambda a, b: b["original2016ProtocolSource"].__setitem__("pdfContentReviewed", True),
            lambda a, b: b["original2016ProtocolSource"].__setitem__("originalSignedSapVerified", True),
            lambda a, b: b["original2016ProtocolSource"].__setitem__("preInterimAlphaSpendingVerified", True),
            lambda a, b: b["original2016ProtocolSource"].__setitem__("sourceUrl", "https://untrusted.invalid"),
            lambda a, b: b["checks"][4].__setitem__("status", "SOURCE_SUPPORTED"),
            lambda a, b: a["analysis_snapshots"][0]["effects"]["progression_free_survival"].__setitem__("p_value", "0.5"),
            lambda a, b: a["analysis_snapshots"][0]["effects"]["overall_survival"].__setitem__("hazard_ratio", 0.9),
        ]
        for mutate in mutations:
            published, readiness = copy.deepcopy(p), copy.deepcopy(r)
            mutate(published, readiness)
            with self.subTest(mutation=str(mutate)), self.assertRaises(ValueError):
                published_keynote024_interim_design(published, readiness)

    def test_output_does_not_mutate_published_or_readiness(self):
        p, r = inputs()
        original = copy.deepcopy((p, r))
        data = published_keynote024_interim_design(p, r)
        data["reportedDesign"]["osGroupSequential"]["plannedApproximateDeaths"].clear()
        self.assertEqual((p, r), original)
        other = published_keynote024_interim_design(p, r)
        self.assertEqual(other["reportedDesign"]["osGroupSequential"]["plannedApproximateDeaths"], [110, 170])


if __name__ == "__main__":
    unittest.main()
