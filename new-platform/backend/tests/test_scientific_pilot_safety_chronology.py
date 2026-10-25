"""Scientific source-separated historical safety denominators and crossover tests."""
import copy
import unittest

from app.scientific_pilot_keynote024_results import keynote024_published_results
from app.scientific_pilot_evidence_audit import keynote024_preinterim_evidence_audit
from app.scientific_pilot_safety_chronology import keynote024_safety_chronology


def audit():
    research = keynote024_published_results()
    archive = {"protocolSection": {"identificationModule": {"nctId": "NCT02142738"}},
               "resultsSection": {"adverseEventsModule": {"eventGroups": []}}}
    return research, keynote024_preinterim_evidence_audit(archive, research)


class SafetyChronologyTests(unittest.TestCase):
    def test_original_randomized_and_as_treated_counts_are_different(self):
        published, registry = audit()
        result = keynote024_safety_chronology(published, registry)
        early = result["original2016"]
        self.assertEqual(early["randomized"], {
            "pembrolizumab": 154, "chemotherapy": 151,
        })
        self.assertEqual(early["asTreated"], {
            "pembrolizumab": 154, "chemotherapy": 150,
        })
        self.assertEqual(early["unexposedChemotherapyRandomized"], 1)
        self.assertTrue(early["roundingArithmeticChecked"])
        self.assertFalse(early["patientLevelVerified"])
        self.assertFalse(early["clinicalSafetyAppraisalComplete"])

    def test_original_published_ae_numerators_denominators_not_pooled(self):
        published, registry = audit()
        safety = keynote024_safety_chronology(published, registry)
        groups = {
            row["classification"]: row
            for row in safety["original2016"]["reportedTreatRelatedSafety"]
        }
        self.assertEqual(len(groups), 5)
        self.assertEqual(groups["treatment_related_any_grade"]["pembrolizumab"],
                         {"affected": 113, "atRisk": 154, "reportedPercent": 73.4})
        self.assertEqual(groups["treatment_related_any_grade"]["chemotherapy"],
                         {"affected": 135, "atRisk": 150, "reportedPercent": 90.0})
        self.assertEqual(groups["treatment_related_grade_3_to_5"]["pembrolizumab"],
                         {"affected": 41, "atRisk": 154, "reportedPercent": 26.6})
        self.assertEqual(groups["treatment_related_grade_3_to_5"]["chemotherapy"],
                         {"affected": 80, "atRisk": 150, "reportedPercent": 53.3})
        self.assertEqual(groups["serious_treatment_related_any_grade"]["pembrolizumab"]["affected"], 33)
        self.assertEqual(groups["serious_treatment_related_any_grade"]["chemotherapy"]["affected"], 31)
        self.assertEqual(groups["treatment_related_discontinuation_any_grade"]["pembrolizumab"]["affected"], 11)
        self.assertEqual(groups["treatment_related_discontinuation_any_grade"]["chemotherapy"]["affected"], 16)
        self.assertEqual(groups["treatment_related_death"]["pembrolizumab"]["affected"], 1)
        self.assertEqual(groups["treatment_related_death"]["chemotherapy"]["affected"], 3)
        self.assertTrue(all(row["sourceReportedNotIndependentlyVerified"] for row in groups.values()))

    def test_immune_aes_are_not_treatment_related_traes(self):
        published, registry = audit()
        immune = keynote024_safety_chronology(published, registry)["immuneMediated2016"]
        self.assertEqual(immune["anyGradePercent"], {
            "pembrolizumab": 29.2, "chemotherapy": 4.7,
        })
        self.assertEqual(immune["grade3to4Percent"], {
            "pembrolizumab": 9.7, "chemotherapy": 0.7,
        })
        self.assertTrue(immune["notEquivalentToTreatmentRelatedAE"])
        self.assertTrue(immune["noGrade5ImmuneMediatedEventsReported"])

    def test_2019_publication_has_distinct_2017_data_cutoff(self):
        published, registry = audit()
        result = keynote024_safety_chronology(published, registry)
        followup = result["updated2019"]
        self.assertEqual(followup["sourceId"], "30620668")
        self.assertEqual(followup["publicationDate"], "2019-01-08")
        self.assertEqual(followup["analysisDataCutoff"], "2017-07-10")
        self.assertEqual(followup["reportedGrade3to5TreatmentRelatedPercent"], {
            "pembrolizumab": 31.2, "chemotherapy": 53.3,
        })
        self.assertEqual(followup["reportedOnStudyCrossoverPatients"], 82)
        self.assertEqual(followup["intentionToTreatOS"]["hazardRatio"], 0.63)
        self.assertEqual(followup["twoStageCrossoverAdjustedOS"]["hazardRatio"], 0.49)
        self.assertTrue(followup["mustNotOverwriteOriginal2016"])
        self.assertFalse(followup["publishedAEAffectedCountsExtracted"])

    def test_registry_counts_not_converted_to_journal_trae(self):
        published, registry = audit()
        result = keynote024_safety_chronology(published, registry)
        crossover = result["registryReconciliation"]
        self.assertEqual(crossover["archivedGroupsObserved"], 0)
        self.assertFalse(crossover["countsPooledAcrossTreatmentCourses"])
        self.assertFalse(crossover["registryAEGroupMatchesJournalTRAE"])
        self.assertFalse(crossover["crossSystemAEReconciliationCompleted"])
        self.assertTrue(crossover["missingOriginalSapStillBlocking"])
        self.assertFalse(result["inputReadinessGradeChanged"])
        self.assertFalse(result["reluctanceGradeChanged"])
        self.assertIsNone(result["scientificScore"])
        self.assertIsNone(result["fdaApprovalProbability"])
        self.assertFalse(result["tradingActionsEnabled"])

    def test_wrong_trial_or_original_safety_values_fail_closed(self):
        published, registry = audit()
        mutations = [
            lambda a, b: a.__setitem__("nct_id", "NCT87654321"),
            lambda a, b: b.__setitem__("nctId", "NCT87654321"),
            lambda a, b: a.__setitem__("overall_score", 95),
            lambda a, b: b.__setitem__("scientificScore", 95),
            lambda a, b: a["analysis_snapshots"][0].__setitem__(
                "arm_counts_randomized", {"pembrolizumab": 154, "chemotherapy": 150}),
            lambda a, b: a["analysis_snapshots"][0]["safety"][
                "treatment_related_adverse_events_grade_3_to_5_percent"
            ].__setitem__("chemotherapy", 53.0),
            lambda a, b: b["registrySafety"].__setitem__(
                "randomizedArmComparisonValidated", True),
            lambda a, b: b["registrySafety"].__setitem__(
                "publishedTreatmentRelatedAeRatesReconciled", True),
            lambda a, b: b["registrySafety"].__setitem__("groupCount", 100),
        ]
        for change in mutations:
            data, source = copy.deepcopy(published), copy.deepcopy(registry)
            change(data, source)
            with self.subTest(change=repr(change)), self.assertRaises(ValueError):
                keynote024_safety_chronology(data, source)

    def test_outputs_are_independent_immutable_per_call(self):
        published, registry = audit()
        first = keynote024_safety_chronology(published, registry)
        first["original2016"]["reportedTreatRelatedSafety"].clear()
        second = keynote024_safety_chronology(published, registry)
        self.assertEqual(len(second["original2016"]["reportedTreatRelatedSafety"]), 5)


if __name__ == "__main__":
    unittest.main()
