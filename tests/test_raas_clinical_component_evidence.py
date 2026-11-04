"""Tests for exact-trial observational clinical source reports, not FDA RAAS grades."""
import csv
import importlib.util
import io
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "raas_clinical_component_evidence",
    ROOT / "scripts/raas_clinical_component_evidence.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def trial(nct="NCT00000001", *, posted=True):
    return {
        "nctId": nct, "ticker": "TST",
        "sourceUrl": "https://clinicaltrials.gov/study/" + nct,
        "postedResults": posted,
        "postedPrimaryOutcomeCount": 1 if posted else 0,
        "primaryResults": [{
            "title": "Symptom improvement", "timeFrame": "Week 12", "unit": "points",
            "groups": [{"id": "GX", "title": "Study Drug 20 mg"},
                       {"id": "GY", "title": "Placebo"}],
            "measurements": [{"groupId": "GX", "value": "10.1"},
                             {"groupId": "GY", "value": "7.4"}],
            "comparisons": [{
                "groupIds": ["GX", "GY"], "pValue": "0.03",
                "method": "t-test", "paramType": "Mean Difference", "paramValue": "2.7",
                "ciPctValue": "95", "ciLowerLimit": "1.2", "ciUpperLimit": "4.1"
            }]
        }] if posted else [],
        "seriousEventDetails": [{"term": "Serious adverse events", "groups": [
            {"groupId": "GX", "numAffected": 3, "numAtRisk": 40},
            {"groupId": "GY", "numAffected": 5, "numAtRisk": 50}
        ]}] if posted else [],
    }


def index(records):
    return {"schemaVersion": 1, "scope": "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
            "sourceAsOf": "2026-11-04T22:00:00+00:00",
            "summary": {"researchNcts": len(records)}, "records": records}


class ComponentTests(unittest.TestCase):
    def test_complete_reporting_is_not_claimed_to_be_effectiveness(self):
        components, comparisons, safety, status = mod.build_components(
            index([trial()]))
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0]["reportingCompletenessDiagnosticScore"], 100)
        self.assertEqual(components[0]["documentedFeaturesOf5"], 5)
        self.assertEqual(components[0]["overallRaasScore"], "")
        self.assertEqual(status["fullValidatedRaasScores"], 0)
        self.assertEqual(len(comparisons), 1)
        self.assertEqual(comparisons[0]["groupIdsAsReported"], "GX;GY")
        self.assertEqual(comparisons[0]["groupTitlesAsReported"], "Study Drug 20 mg | Placebo")
        self.assertEqual(comparisons[0]["groupTitleResolution"], "ALL_EXACT_SOURCE_TITLES")
        self.assertEqual(status["comparisonRowsWithExactSourceGroupTitles"], 1)
        self.assertEqual(comparisons[0]["parameterValueAsReported"], "2.7")
        self.assertEqual(len(safety), 2)
        self.assertEqual(safety[0]["observedAffectedRatePercent"], 7.5)
        self.assertEqual(safety[1]["observedAffectedRatePercent"], 10.0)
        self.assertTrue(all("NOT_ADJUDICATED" in row["interpretation"]
                            for row in comparisons + safety))

    def test_protocol_only_has_no_reporting_grade_not_zero(self):
        t = trial(posted=False)
        components, comparisons, safety, status = mod.build_components(index([t]))
        self.assertEqual(components[0]["reportingCompletenessDiagnosticScore"], "")
        self.assertEqual(components[0]["documentedFeaturesOf5"], "")
        self.assertFalse(comparisons)
        self.assertFalse(safety)
        self.assertEqual(status["trialsWithExperimentalReportingDiagnostic"], 0)

    def test_posted_but_no_usable_details_has_zero_documentation_not_clinical_zero(self):
        t = trial()
        t["primaryResults"] = []
        t["seriousEventDetails"] = []
        components, comparisons, safety, status = mod.build_components(index([t]))
        self.assertEqual(components[0]["reportingCompletenessDiagnosticScore"], 0)
        self.assertEqual(components[0]["interpretation"], mod.SOURCE_ONLY)
        self.assertEqual(components[0]["overallRaasScore"], "")

    def test_missing_group_identity_and_unsafe_safety_denominators_rejected(self):
        t = trial()
        t["primaryResults"][0]["comparisons"][0]["groupIds"] = ["GX"]
        t["seriousEventDetails"][0]["groups"] = [
            {"groupId": "GX", "numAffected": 100, "numAtRisk": 50},
            {"groupId": "GY", "numAffected": None, "numAtRisk": 50},
            {"groupId": "GZ", "numAffected": 2, "numAtRisk": 0}
        ]
        components, comparisons, safety, status = mod.build_components(index([t]))
        self.assertEqual(len(comparisons), 0)
        self.assertEqual(len(safety), 0)
        self.assertFalse(components[0]["groupComparisonDocumented"])
        self.assertFalse(components[0]["safetyRateDenominatorsDocumented"])
        self.assertFalse(components[0]["statisticalResultDocumented"])
        self.assertEqual(components[0]["reportingCompletenessDiagnosticScore"], 20)

    def test_group_labels_fail_closed_on_missing_or_conflicting_id(self):
        t = trial()
        t["primaryResults"][0]["groups"] = [{"id":"GX","title":"Drug A"},
                                             {"id":"GX","title":"Drug B"},
                                             {"id":"GY","title":"Placebo"}]
        _, comparisons, _, status = mod.build_components(index([t]))
        self.assertEqual(comparisons[0]["groupTitleResolution"], "NOT_ALL_TITLES_SOURCE_RESOLVED")
        self.assertEqual(comparisons[0]["groupTitlesAsReported"], " | Placebo")
        self.assertEqual(status["comparisonRowsWithExactSourceGroupTitles"], 0)
        t["primaryResults"][0]["groups"] = []
        _, comparisons, _, status = mod.build_components(index([t]))
        self.assertEqual(comparisons[0]["groupTitlesAsReported"], " | ")
        self.assertEqual(status["comparisonRowsWithExactSourceGroupTitles"], 0)

    def test_missing_confidence_limits_are_not_imputed_from_p_value(self):
        t = trial()
        t["primaryResults"][0]["comparisons"][0]["ciLowerLimit"] = ""
        c, comparisons, _, _ = mod.build_components(index([t]))
        self.assertFalse(c[0]["confidenceIntervalDocumented"])
        self.assertTrue(c[0]["statisticalResultDocumented"])
        self.assertEqual(comparisons[0]["confidenceLowerAsReported"], "")
        self.assertEqual(c[0]["reportingCompletenessDiagnosticScore"], 80)

    def test_distinct_trial_rows_and_source_urls(self):
        a, b = trial("NCT00000001"), trial("NCT00000002")
        txt, contrast, events, status = mod.generate(index([a, b]))
        rows = list(csv.DictReader(io.StringIO(txt)))
        self.assertEqual({x["nctId"] for x in rows}, {"NCT00000001", "NCT00000002"})
        self.assertEqual(len(list(csv.DictReader(io.StringIO(contrast)))), 2)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(events)))), 4)
        self.assertEqual(__import__("json").loads(status)["researchTrials"], 2)

    def test_unpublished_result_in_protocol_fails(self):
        t = trial(posted=False)
        t["primaryResults"] = [trial()["primaryResults"][0]]
        with self.assertRaisesRegex(ValueError, "UNPUBLISHED"):
            mod.build_components(index([t]))

    def test_duplicate_and_identity_mismatches_fail(self):
        t = trial()
        with self.assertRaisesRegex(ValueError, "TRIAL_IDENTITY"):
            mod.build_components(index([t, t]))
        t["sourceUrl"] = "https://clinicaltrials.gov/study/NCT00000002"
        with self.assertRaisesRegex(ValueError, "TRIAL_IDENTITY"):
            mod.build_components(index([t]))

    def test_current_registry_has_a_full_NCT_component_census(self):
        import json
        if not mod.INDEX.exists():
            self.skipTest("No checkout source snapshot")
        live = json.loads(mod.INDEX.read_text(encoding="utf-8"))
        rows, comps, rates, status = mod.build_components(live)
        self.assertEqual(len(rows), 762)
        self.assertEqual(status["researchTrials"], 762)
        self.assertEqual(status["fullValidatedRaasScores"], 0)
        self.assertTrue(all(row["overallRaasScore"] == "" for row in rows))
        self.assertEqual(status["trialsWithExperimentalReportingDiagnostic"],
                         status["trialsWithPostedResults"])


if __name__ == "__main__":
    unittest.main()
