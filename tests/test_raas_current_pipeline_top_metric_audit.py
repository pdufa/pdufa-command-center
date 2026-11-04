"""Fail-closed verification of real current-issuer TOP research pilot."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "raas_current_pipeline_top_metric_audit",
    ROOT / "scripts/raas_current_pipeline_top_metric_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def load():
    return (json.loads(audit.SNAPSHOT.read_text(encoding="utf8")),
            json.loads(audit.REVIEWS.read_text(encoding="utf8")),
            audit.COHORT.read_text(encoding="utf8"),
            audit.LEDGER.read_text(encoding="utf8"))


class CurrentPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = load()

    def run_audit(self, *, as_of="2026-11-04", source=None):
        return audit.build(*(source if source is not None else self.raw),
                           as_of=as_of)

    def test_five_phase3_cases_three_cap_qualified_issuers_not_pdufa(self):
        rows, s = self.run_audit()
        self.assertEqual(len(rows), 150)
        self.assertEqual(s["pilotTrialCount"], 5)
        self.assertEqual(s["uniqueIssuers"], 3)
        self.assertEqual(s["trialsWithoutVerifiedToplineWindow"], 2)
        self.assertEqual(s["pilotMetricSlots"], 150)
        self.assertEqual(s["provisionalAiReviewedMetricSlots"], 24)
        self.assertEqual(s["missingMetricSlots"], 126)
        self.assertEqual(s["perTrialProvisionalReviewCount"],
                         {"NCT07363577":5, "NCT07671911":5,
                          "NCT07868419":5, "NCT07369154":4,
                          "NCT06736574":5})
        self.assertEqual(s["currentCapAndPhase3SourceVerifiedAsOf"], 5)
        self.assertEqual(s["humanIndependentReviewedMetricSlots"], 0)
        self.assertEqual(s["complete30MetricRaasScores"], 0)
        self.assertEqual(s["confirmedPdufaTargets"], 0)
        self.assertEqual(s["calibratedFdaPredictions"], 0)
        expected = set(audit.METRIC_IDS)
        for nct in s["pilotPhase3TrialNcts"]:
            matched = [r for r in rows if r["nctId"] == nct]
            self.assertEqual(len(matched),30)
            self.assertEqual({r["metricId"] for r in matched},expected)
            self.assertEqual({r["registryStatus"] for r in matched},{"RECRUITING"})
            self.assertTrue(all(r["currentSourceQualification"] ==
                                "CURRENT_CAP_AND_PHASE3_SOURCE_VERIFIED_NO_PDUFA"
                                for r in matched))
            self.assertTrue(all(r["pdufaTarget"] == ""
                                and r["full30MetricRaasScore"] == ""
                                and r["fdaPassCrlExtensionProbability"] == ""
                                for r in matched))

    def test_twentyfour_source_backed_clinical_financial_design_regulatory_grades_with_missing(self):
        rows, _ = self.run_audit()
        rated = [r for r in rows if r["provisionalMetricScore"] != ""]
        na = [r for r in rows if r["provisionalMetricScore"] == ""]
        self.assertEqual(len(rated),24)
        self.assertEqual(len(na),126)
        self.assertEqual({r["metricId"] for r in rated},
                         {"pre-1-1","pre-1-2","pre-1-4","pre-1-5","pre-3-2","pre-4-1"})
        self.assertTrue(all(r["provisionalMetricScore"] in (0,25,50,75,100)
                            for r in rated))
        self.assertTrue(all(r["sourceDate"] and r["sourceUrl"].startswith("https://")
                            and r["benchmarkSourceUrl"].startswith("https://")
                            and r["observedResult"] and r["uncertaintyReview"]
                            and r["criticalRiskReview"] for r in rated))
        self.assertTrue(all(r["provisionalMetricScore"] == "" and
                            r["sourceUrl"] == "" and
                            r["missingDataRequired"] == "MISSING_METRIC_SPECIFIC_REVIEW"
                            for r in na))

    def test_market_cap_and_status_sources_expire_instead_of_silent_requalification(self):
        rows, s = self.run_audit(as_of="2026-11-11")
        self.assertEqual(len(rows),150)
        self.assertEqual(s["provisionalAiReviewedMetricSlots"],24)
        self.assertEqual(s["currentCapAndPhase3SourceVerifiedAsOf"],0)
        self.assertEqual(set(s["eligibilityByNct"].values()),
                         {"STALE_MARKET_CAP_REVERIFY"})
        self.assertTrue(all(r["fdaPassCrlExtensionProbability"] == "" for r in rows))
        rows,s = self.run_audit(as_of="2026-12-10")
        self.assertEqual(s["currentCapAndPhase3SourceVerifiedAsOf"],0)
        self.assertEqual(set(s["eligibilityByNct"].values()),
                         {"STALE_MARKET_CAP_REVERIFY"})

    def test_reject_wrong_ticker_and_forged_nct_status(self):
        snap,reviews,cohort,ledger = self.raw
        bad = copy.deepcopy(snap)
        bad["trialSnapshots"][0]["ticker"]="FAKE"
        with self.assertRaisesRegex(ValueError,"CASE_PROVENANCE"):
            self.run_audit(source=(bad,reviews,cohort,ledger))
        changed=ledger.replace("NCT07363577,LBRX,","NCT07363577,FAKE,")
        with self.assertRaisesRegex(ValueError,"CASE_PROVENANCE"):
            self.run_audit(source=(snap,reviews,cohort,changed))
        changed=ledger.replace("NCT07671911,TRVI,https://clinicaltrials.gov/study/NCT07671911,RECRUITING",
                               "NCT07671911,TRVI,https://clinicaltrials.gov/study/NCT07671911,WITHDRAWN")
        rows,s = self.run_audit(source=(snap,reviews,cohort,changed))
        self.assertEqual(s["eligibilityByNct"]["NCT07671911"],
                         "NOT_ACTIVE_IN_CURRENT_REGISTRY")

    def test_forged_duplicate_wrong_drug_or_historical_prediction_rejected(self):
        snap,reviews,cohort,ledger = self.raw
        x=copy.deepcopy(reviews)
        source=next(r for r in x["records"] if r["nctId"]=="NCT07671911"
                    and r["stage"]=="pre")
        x["records"].append(dict(source))
        with self.assertRaisesRegex(ValueError,"METRIC_REVIEW_INVALID"):
            self.run_audit(source=(snap,x,cohort,ledger))
        x=copy.deepcopy(reviews)
        source=next(r for r in x["records"] if r["nctId"]=="NCT07363577"
                    and r["stage"]=="pre")
        source["drug"]="NOT_THE_SAME_PROGRAM"
        with self.assertRaisesRegex(ValueError,"METRIC_REVIEW_INVALID"):
            self.run_audit(source=(snap,x,cohort,ledger))
        bad=copy.deepcopy(snap)
        bad["trialSnapshots"][0]["pdufaTarget"]="2027-01-01"
        with self.assertRaisesRegex(ValueError,"CASE_PROVENANCE"):
            self.run_audit(source=(bad,reviews,cohort,ledger))
        with self.assertRaisesRegex(ValueError,"FUTURE_ASSESSMENT"):
            self.run_audit(as_of="2026-11-02")

    def test_missing_window_stays_absent_and_multiple_trials_one_cap(self):
        rows, status=self.run_audit()
        for nct in ("NCT06736574","NCT07369154"):
            matches=[r for r in rows if r["nctId"]==nct]
            self.assertEqual(len(matches),30)
            self.assertTrue(all(r["readoutExpectedWindow"]=="" for r in matches))
            self.assertTrue(all(r["readoutGuidancePublished"]=="" for r in matches))
            self.assertTrue(all(r["readoutGuidanceUrl"]=="" for r in matches))
            self.assertTrue(all(r["pdufaTarget"]=="" for r in matches))
        issuer_caps={}
        for row in rows:
            issuer_caps.setdefault(row["ticker"],set()).add(row["marketCapUsdAsOfSource"])
        self.assertEqual(len(issuer_caps),3)
        self.assertTrue(all(len(caps)==1 for caps in issuer_caps.values()))
        self.assertEqual(status["confirmedPdufaTargets"],0)
        self.assertEqual(status["complete30MetricRaasScores"],0)

    def test_missing_readout_window_must_not_be_invented(self):
        snap,reviews,cohort,ledger=self.raw
        bad=copy.deepcopy(snap)
        nova3=next(r for r in bad["trialSnapshots"] if r["nctId"]=="NCT07369154")
        nova3["readoutExpectedWindow"]="H1 2027"
        with self.assertRaisesRegex(ValueError,"CASE_PROVENANCE"):
            self.run_audit(source=(bad,reviews,cohort,ledger))
        bad=copy.deepcopy(snap)
        ocean2=next(r for r in bad["trialSnapshots"] if r["nctId"]=="NCT07868419")
        ocean2["readoutGuidanceUrl"]=None
        with self.assertRaisesRegex(ValueError,"CASE_PROVENANCE"):
            self.run_audit(source=(bad,reviews,cohort,ledger))

    def test_same_issuer_different_market_cap_quotes_are_rejected(self):
        snap,reviews,cohort,ledger=self.raw
        bad=copy.deepcopy(snap)
        ocean2=next(r for r in bad["trialSnapshots"] if r["nctId"]=="NCT07868419")
        ocean2["marketCapUsd"]+=100_000_000
        with self.assertRaisesRegex(ValueError,"CONFLICTING_ISSUER_MARKET_CAP"):
            self.run_audit(source=(bad,reviews,cohort,ledger))

    def test_quote_outside_allowed_range_not_verified_and_csv_excel_safe(self):
        snap,reviews,cohort,ledger = self.raw
        bad=copy.deepcopy(snap)
        for case in bad["trialSnapshots"]:
            if case["ticker"]=="TRVI":
                case["marketCapUsd"]=299_999_999
        _, s = self.run_audit(source=(bad,reviews,cohort,ledger))
        self.assertEqual(s["currentCapAndPhase3SourceVerifiedAsOf"],3)
        self.assertIn("OUTSIDE_MARKET_CAP_RESTRICTIONS",s["eligibilityByNct"].values())
        csv_text,json_text=audit.generate(*self.raw,as_of="2026-11-04")
        self.assertEqual(len(list(csv.DictReader(io.StringIO(csv_text)))),150)
        self.assertEqual(json.loads(json_text)["confirmedPdufaTargets"],0)
        self.assertEqual(audit.safe("=SUM(A1:A3)"),"'=SUM(A1:A3)")
        self.assertEqual(audit.safe(""),"")


if __name__=="__main__":
    unittest.main()
