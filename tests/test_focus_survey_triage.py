"""Offline checks for evidence triage, source provenance and Sheets isolation."""
from __future__ import annotations
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import triage_focus_survey_evidence as triage
import sync_focus_survey_triage_to_sheets as sheets

class TestFocusSurveyTriage(unittest.TestCase):
    def test_publications_are_not_accepted_on_search_hits_alone(self):
        registry={"interventions":[{"name":"AD109"},{"name":"Placebo"}],
                  "indications":["Obstructive Sleep Apnea"]}
        self.assertEqual(triage.classify_article({"title":"Study of AD109 dosing"},registry)[0],
                         "DRUG_TITLE_LEAD")
        self.assertEqual(triage.classify_article({"title":"Obstructive Sleep Apnea prevalence"},registry)[0],
                         "INDICATION_CONTEXT_ONLY")
        self.assertEqual(triage.classify_article({"title":"Unrelated chemistry review"},registry)[0],
                         "UNLINKED_SEARCH_LEAD")
        self.assertEqual(triage.classify_article({
            "title":"Placebo responses", "exactNctInAbstract":True},registry)[0],
            "EXACT_NCT_LEAD")
        self.assertFalse(triage.matches_title("Effect of unrelated vehicle treatment","vehicle"))
        self.assertFalse(triage.matches_title("AD1098 new drug","AD109"))

    def test_registry_fact_preserves_numerator_denominator(self):
        packet={"nctId":"NCT12345678","ticker":"TEST","company":"Company",
                "registryUrl":"https://clinicaltrials.gov/study/NCT12345678",
                "retrievedAt":"2026-11-07T18:00:00Z","registrySourceHash":"a"*64,
                "registry":{"reportedOutcomeMeasures":[{"title":"Response", "unit":"Percent",
                    "timeFrame":"Week 12", "groups":[{"id":"G1","title":"Active"}],
                    "measurements":[{"groupId":"G1","value":"42","spread":"5"}]}],
                "adverseEventGroups":[{"title":"Active","seriousAffected":2,
                                      "seriousAtRisk":100,"otherAffected":12,
                                      "otherAtRisk":100}],
                "treatmentArms":[{"label":"Active","type":"EXPERIMENTAL",
                                  "interventionNames":["Drug X"]}]}}
        obs=triage.extract_observations(packet)
        self.assertEqual(len(obs),4)
        self.assertEqual(next(o["observedValue"] for o in obs if
                              o["observationKind"]=="SERIOUS_ADVERSE_EVENTS"),"2/100")
        self.assertEqual(next(o["observedValue"] for o in obs if
                              o["observationKind"]=="REGISTERED_NUMERIC_OUTCOME"),"42")
        self.assertTrue(all(o["status"]=="SOURCE_OBSERVED_REVIEW_REQUIRED" for o in obs))
        self.assertFalse(any(o.get("numericalScore") for o in obs))

    def test_tampered_nct_is_rejected(self):
        roster=[{"nct":"NCT12345678","ticker":"T","company":"Company"}]
        slots=[{"nctId":"NCT12345678","ingredientId":str(i)} for i in range(38)]
        with self.assertRaisesRegex(ValueError,"SOURCE_PACKET_NOT_CAPTURED"):
            triage.collect_packets(roster,slots)

    def test_current_29_trial_matrix_triage_and_protected_tabs(self):
        roster=triage.read_json(triage.ROSTER)["records"]
        slots=triage.read_json(triage.EVIDENCE)["slots"]
        packets=triage.collect_packets(roster,slots)
        self.assertEqual(len(roster),29)
        self.assertEqual(len(slots),1102)
        obs,publications,report=triage.triage_all(roster,slots,packets)
        self.assertGreater(len(obs),100)
        self.assertGreater(len(publications),100)
        self.assertEqual(report["verifiedSurveyAnswersFromTriage"],0)
        self.assertEqual(report["registryTrials"],29)
        self.assertEqual(report["ingredientSlots"],1102)
        self.assertEqual(report["distinctTrialPublicationLeads"],len(publications))
        self.assertEqual(len({p["nctId"] for p in publications})>0,True)
        self.assertTrue(all(o["sourceUrl"].endswith(o["nctId"]) for o in obs))
        self.assertTrue(all(p["status"]=="PUBLICATION_RESEARCH_LEAD_NOT_VALIDATED"
                            for p in publications))
        self.assertEqual(sum(report["publicationCategories"].values()),len(publications))
        # Generating triage reports must not touch the authoritative 1,102-slot matrix.
        before=triage.EVIDENCE.read_bytes()
        triage.run()
        self.assertEqual(triage.EVIDENCE.read_bytes(),before)
        tables=sheets.prepare_tables()
        self.assertEqual([x[0] for x in tables],[
            "FOCUS Survey Auto Review","FOCUS Survey Auto Literature"])
        self.assertEqual(len(tables[0][2]),len(obs))
        self.assertEqual(len(tables[1][2]),len(publications))
        self.assertTrue(all(x[0].startswith("FOCUS Survey Auto ") for x in tables))

if __name__=="__main__":
    unittest.main()
