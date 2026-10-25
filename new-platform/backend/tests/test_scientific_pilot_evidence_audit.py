"""Offline source-chronology and safety denominator audit tests.

Fixtures represent registry structures; no invented values are attributed to
the actual trial. CI is not a live database validation.
"""
import copy
import unittest

from app.scientific_pilot_evidence_audit import (
    ASCO_2015, NCT, ORIGINAL_PROTOCOL_LISTING, LATER_PROTOCOL,
    keynote024_preinterim_evidence_audit,
)
from app.scientific_pilot_keynote024_results import keynote024_published_results


def registry(*, groups=None):
    doc = {"protocolSection": {"identificationModule": {"nctId": NCT}}}
    if groups is not None:
        doc["resultsSection"] = {"adverseEventsModule": {"eventGroups": groups}}
    return doc


def synthetic_groups():
    return [
        {
            "id": "EG000", "title": "Synthetic Treatment First Course",
            "seriousNumAffected": 4, "seriousNumAtRisk": 10,
            "otherNumAffected": 6, "otherNumAtRisk": 10,
            "deathsNumAffected": 0, "deathsNumAtRisk": 10,
        },
        {
            "id": "EG001", "title": "Synthetic Switched-over Treatment",
            "seriousNumAffected": 2, "seriousNumAtRisk": 5,
            "otherNumAffected": 3, "otherNumAtRisk": 5,
            "deathsNumAffected": 0, "deathsNumAtRisk": 5,
        },
    ]


class Keynote024EvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.research = keynote024_published_results()

    def test_early_public_design_is_not_a_signed_protocol_or_sap(self):
        report = keynote024_preinterim_evidence_audit(registry(), self.research)
        self.assertEqual(report["nctId"], NCT)
        self.assertEqual(report["earlyDesignEvidence"]["sourceUrl"], ASCO_2015)
        self.assertEqual(report["earlyDesignEvidence"]["publicationDate"], "2015-05-20")
        self.assertFalse(report["earlyDesignEvidence"]["preinterimDocumentVerified"])
        self.assertFalse(report["earlyDesignEvidence"]["signedSapVerified"])
        self.assertFalse(report["earlyDesignEvidence"]["originalMultiplicityVerified"])
        self.assertTrue(report["readOnly"])
        self.assertIsNone(report["scientificScore"])
        self.assertIsNone(report["fdaApprovalProbability"])
        self.assertFalse(report["inputReadinessGradeChanged"])
        self.assertFalse(report["reluctanceGradeChanged"])
        self.assertFalse(report["independentProtocolSapReviewComplete"])

    def test_chronology_keeps_journal_supplement_unreviewed_and_later_sap_distinct(self):
        report = keynote024_preinterim_evidence_audit(registry(), self.research)
        steps = {m["id"]: m for m in report["timeline"]}
        self.assertEqual(len(report["timeline"]), 7)
        self.assertEqual(steps["contemporaneous_trial_design"]["sourceUrl"], ASCO_2015)
        self.assertEqual(steps["supplementary_protocol_listed"]["sourceUrl"],
                         ORIGINAL_PROTOCOL_LISTING)
        self.assertEqual(steps["supplementary_protocol_listed"]["evidenceStatus"],
                         "linked_document_not_content_reviewed")
        self.assertEqual(steps["later_protocol_date"]["sourceUrl"], LATER_PROTOCOL)
        self.assertEqual(steps["later_protocol_date"]["date"], "2017-12-20")
        self.assertTrue(all(x["proofOfOriginalSap"] is False for x in report["timeline"]))
        self.assertEqual(steps["primary_analysis_cutoff"]["date"], "2016-05-09")
        self.assertEqual(steps["long_term_followup_cutoff"]["date"], "2020-06-01")

    def test_absent_registry_safety_never_turns_into_zero_affected(self):
        report = keynote024_preinterim_evidence_audit(registry(), self.research)
        safety = report["registrySafety"]
        self.assertEqual(safety["status"], "no_groups_documented_in_snapshot")
        self.assertEqual(safety["groups"], [])
        self.assertTrue(safety["missingGroupsDoNotImplyZeroEvents"])
        self.assertFalse(safety["publishedTreatmentRelatedAeRatesReconciled"])
        self.assertFalse(safety["randomizedArmComparisonValidated"])

    def test_registry_event_course_denominators_are_kept_separate(self):
        report = keynote024_preinterim_evidence_audit(
            registry(groups=synthetic_groups()), self.research)
        safety = report["registrySafety"]
        self.assertEqual(safety["groupCount"], 2)
        self.assertEqual(safety["status"], "groups_reported")
        initial, switched = safety["groups"]
        self.assertEqual(initial["counts"]["seriousEvents"]["numAffected"], 4)
        self.assertEqual(initial["counts"]["seriousEvents"]["numAtRisk"], 10)
        self.assertEqual(switched["counts"]["seriousEvents"]["numAffected"], 2)
        self.assertEqual(switched["counts"]["seriousEvents"]["numAtRisk"], 5)
        self.assertEqual(initial["sourceLocator"],
                         "resultsSection.adverseEventsModule.eventGroups[0]")
        self.assertFalse(initial["independentlyVerified"])
        self.assertFalse(safety["randomizedArmComparisonValidated"])
        self.assertFalse(safety["publishedTreatmentRelatedAeRatesReconciled"])

    def test_mismatched_nct_or_published_results_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            keynote024_preinterim_evidence_audit(
                registry() | {"protocolSection": {
                    "identificationModule": {"nctId": "NCT87654321"},
                }}, self.research)
        changed = copy.deepcopy(self.research)
        changed["analysis_snapshots"][0]["data_cutoff_date"] = "2019-01-01"
        with self.assertRaisesRegex(ValueError, "chronology mismatch"):
            keynote024_preinterim_evidence_audit(registry(), changed)

    def test_registry_bad_denominators_and_duplicates_fail_closed(self):
        invalids = [
            [{"id": "EG000", "title": "A", "seriousNumAffected": 11,
              "seriousNumAtRisk": 10}],
            [{"id": "EG000", "title": "A", "seriousNumAffected": -1,
              "seriousNumAtRisk": 10}],
            [{"id": "EG000", "title": "A", "seriousNumAffected": True,
              "seriousNumAtRisk": 10}],
            [{"id": "EG000", "title": "A"}, {"id": "EG000", "title": "B"}],
            [{"id": "EG000", "title": "A"}] * 25,
        ]
        for groups in invalids:
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                keynote024_preinterim_evidence_audit(registry(groups=groups), self.research)

    def test_safety_source_count_absent_is_unknown_not_zero(self):
        source = registry(groups=[{"id": "EG001", "title": "Unknown count"}])
        r = keynote024_preinterim_evidence_audit(source, self.research)
        counts = r["registrySafety"]["groups"][0]["counts"]
        self.assertIsNone(counts["deaths"]["numAffected"])
        self.assertIsNone(counts["deaths"]["numAtRisk"])
        self.assertIsNone(counts["seriousEvents"]["numAffected"])


if __name__ == "__main__":
    unittest.main()
