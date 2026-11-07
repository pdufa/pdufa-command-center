"""Offline, exact-identity tests for the 29-trial / 38-question FOCUS collector."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import collect_focus_survey_evidence as survey
import sync_focus_survey_evidence_to_sheets as sheets


def example(nct="NCT12345678", outcomes=True):
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct, "officialTitle": "Illustrative study"},
            "conditionsModule": {"conditions": ["Disease A"]},
            "armsInterventionsModule": {
                "interventions": [{"name": "Therapy X", "type": "DRUG"}],
                "armGroups": [{"label": "Therapy X", "type": "EXPERIMENTAL"},
                              {"label": "Active", "type": "ACTIVE_COMPARATOR"}],
            },
            "outcomesModule": {"primaryOutcomes": [{"measure": "Response"}]},
            "designModule": {"enrollmentInfo": {"count": 150, "type": "ACTUAL"}},
        },
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": ([{"title": "Clinical Response", "unitOfMeasure": "Percent",
                    "groups": [{"id": "G1", "title": "Therapy"}],
                    "classes": [{"categories": [{"measurements": [
                       {"groupId": "G1", "value": "40"}]}]}]}] if outcomes else [])
            },
            "adverseEventsModule": {"eventGroups": [
                {"title": "Therapy", "seriousNumAffected": 2, "seriousNumAtRisk": 100}]}
        }
    }


class TestSurveyCollection(unittest.TestCase):
    def test_canonical_roster_and_questions(self):
        records, groups = survey.validate_inputs(survey.load(survey.ROSTER), survey.load(survey.CATALOG))
        self.assertEqual(len(records), 29)
        self.assertEqual(len(groups), 20)
        self.assertEqual(sum(len(g["ingredients"]) for g in groups), 38)
        self.assertEqual(len({r["nct"] for r in records}), 29)

    def test_nct_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "REGISTRY_NCT_IDENTITY_MISMATCH"):
            survey.extract_registry(example("NCT12345678"), "NCT00000001")

    def test_source_observations_are_not_benefit_scores(self):
        registry = survey.extract_registry(example(), "NCT12345678")
        self.assertEqual(registry["reportedOutcomeMeasures"][0]["measurements"][0]["value"], "40")
        self.assertEqual(registry["seriousEventGroups"][0]["seriousAffected"], 2)
        self.assertEqual(registry["indications"], ["Disease A"])
        self.assertTrue(registry["activeComparatorResults"])

    def test_full_inventory_1102_slots_no_automatic_verified_grade(self):
        records, groups = survey.validate_inputs(survey.load(survey.ROSTER), survey.load(survey.CATALOG))
        packets = {}
        for row in records:
            raw = example(row["nct"])
            packets[row["nct"]] = {
                "nctId": row["nct"], "ticker": row["ticker"], "company": row["company"],
                "registryUrl": "https://clinicaltrials.gov/study/" + row["nct"],
                "registrySourceHash": survey.fingerprint(raw),
                "retrievedAt": "2026-11-07T20:00:00+00:00",
                "registry": survey.extract_registry(raw, row["nct"]),
                "literatureLeads": [], "sourceErrors": {}
            }
        slots = survey.build_slots(records, groups, packets, {})
        summary = survey.coverage(slots, records, packets)
        self.assertEqual(len(slots), 1102)
        self.assertEqual(summary["focusTrials"], 29)
        self.assertEqual(summary["surveyCategories"], 20)
        self.assertEqual(summary["surveyIngredients"], 38)
        self.assertEqual(summary["statuses"]["VERIFIED"], 0)
        self.assertGreater(summary["statuses"]["SOURCE_CAPTURED_NEEDS_REVIEW"], 0)
        self.assertEqual(sum(summary["statuses"].values()), 1102)
        self.assertEqual(summary["verifiedPercent"], 0.0)
        self.assertTrue(any(s["ingredientId"] == "seriousAes" and s["registryLeads"] for s in slots))

    def test_missing_results_never_fabricates_positive_efficacy(self):
        registry = survey.extract_registry(example(outcomes=False), "NCT12345678")
        self.assertEqual(registry["reportedOutcomeMeasures"], [])
        self.assertEqual(registry["responseMeasures"], [])
        self.assertEqual(registry["activeComparatorResults"], [])

    def test_reviewed_facts_require_exact_program_match(self):
        row = {"nct": "NCT12345678", "ticker": "TEST"}
        packet = {"registry": survey.extract_registry(example(), "NCT12345678")}
        r = {"ticker": "TEST", "drug": "Therapy X", "indication": "Disease A",
             "facts": {"clinicalBenefit": {"value": "Evidence-reviewed observation",
                      "status": "VERIFIED", "sourceUrl": "https://example.org/study",
                      "sourceDate": "2026-01-01", "method": "Independent review"}}}
        self.assertIsNotNone(survey.reviewed_fact([r], row, packet, "clinicalBenefit"))
        self.assertIsNone(survey.reviewed_fact([{**r, "indication": "Disease B"}],
                                               row, packet, "clinicalBenefit"))
        self.assertIsNone(survey.reviewed_fact([r, r], row, packet, "clinicalBenefit"))

    def test_sheet_tables_only_four_automation_owned_tabs(self):
        records, groups = survey.validate_inputs(survey.load(survey.ROSTER), survey.load(survey.CATALOG))
        flat = []
        for r in records:
            for g in groups:
                for item in g["ingredients"]:
                    flat.append({"nctId": r["nct"], "ticker": r["ticker"],
                        "company": r["company"], "surveyNumber": g["rank"],
                        "surveyName": g["name"], "ingredientId": item["id"],
                        "ingredientName": item["label"], "status": "MISSING",
                        "registryLeads": [], "publicationLeads": 0,
                        "reviewedValue": None, "reason": "Unreviewed"})
        fake_packets = {r["nct"]: {"registry": None, "literatureLeads": []} for r in records}
        report = survey.coverage(flat, records, fake_packets)
        tables = sheets.table_data(flat, report)
        self.assertEqual(len(tables), 4)
        self.assertTrue(all(x[0].startswith("FOCUS Survey Auto ") for x in tables))
        self.assertEqual(len(tables[0][2]), 1102)
        self.assertEqual(len(tables[1][2]), 20)
        self.assertEqual(len(tables[3][2]), 29)
        with self.assertRaisesRegex(ValueError, "PARTIAL"):
            sheets.table_data(flat[:38], report)


if __name__ == "__main__":
    unittest.main()
