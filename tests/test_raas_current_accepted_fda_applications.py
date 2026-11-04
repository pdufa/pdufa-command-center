"""Audit three distinct NDA dates, only one Phase3 qualifier and no fake predictions."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "raas_current_accepted_fda_applications",
    ROOT/"scripts/raas_current_accepted_fda_applications.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def load():
    return (json.loads(mod.SOURCE.read_text(encoding="utf8")),
            json.loads(mod.REVIEWS.read_text(encoding="utf8")),
            mod.ROSTER.read_text(encoding="utf8"))

class CurrentFdaCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=load()

    def run_case(self, altered=None, *,as_of="2026-11-04"):
        return mod.build(*(altered or self.original),as_of=as_of)

    def test_three_separate_NDAs_one_strict_phase3_pipeline_eligible(self):
        rows,status=self.run_case()
        self.assertEqual(len(rows),3)
        self.assertEqual(status["uniquePublicIssuers"],1)
        self.assertEqual(status["acceptedNdaApplications"],3)
        self.assertEqual(status["minimumPhase3EligibleApplications"],1)
        self.assertEqual(status["phase2RegistrationApplicationsExcluded"],2)
        self.assertEqual(status["currentCapVerifiedEligiblePhase3Applications"],1)
        self.assertEqual(status["issuedBeforeTargetDates"],3)
        self.assertEqual(status["verifiedFdaOutcomes"],0)
        self.assertEqual(status["validatedFdaPassCrlExtensionPredictions"],0)
        self.assertEqual(len({r["applicationKey"] for r in rows}),3)
        gist=next(r for r in rows if r["trialNctId"]=="NCT05208047")
        self.assertEqual(gist["pivotalPhase"],3)
        self.assertEqual(gist["pdufaTargetDate"],"2026-11-30")
        self.assertEqual(gist["reviewDesignation"],"PRIORITY_REVIEW")
        self.assertEqual(gist["reviewedProvisionalMetricCount"],5)
        self.assertEqual(gist["marketCapUsd"],5390000000)
        self.assertEqual(gist["pipelineRestrictionResult"],
                         "PHASE3_PIVOTAL_QUALIFIES_IF_CAP_FRESH")
        phase2=[r for r in rows if r["pivotalPhase"]==2]
        self.assertEqual({r["trialNctId"] for r in phase2},
                         {"NCT05186753","NCT04996875"})
        self.assertEqual({r["pdufaTargetDate"] for r in phase2},
                         {"2026-12-30","2027-06-29"})
        self.assertTrue(all(r["pipelineRestrictionResult"]==
                            "PHASE2_PIVOTAL_EXCLUDED_BY_MIN_PHASE3" for r in phase2))
        self.assertTrue(all(r["full30MetricRaasScore"]==""
                            and r["fdaPassCrlExtensionProbability"]==""
                            and r["independentReviewedMetricCount"]==0 for r in rows))

    def test_acceptance_source_and_indication_exact_NDA_identity(self):
        rows,_=self.run_case()
        self.assertTrue(all(r["applicationAcceptedSourceUrl"].startswith("https://")
                            and r["trialSourceUrl"]==
                            f'https://clinicaltrials.gov/study/{r["trialNctId"]}'
                            for r in rows))
        self.assertTrue(all(r["outcomeAsOf"]==
                            "NO_VERIFIED_DECISION_AS_OF_SNAPSHOT" for r in rows))
        self.assertEqual(len({r["indication"] for r in rows}),3)
        self.assertEqual(len({r["pdufaTargetDate"] for r in rows}),3)

    def test_market_cap_expires_and_target_passage_requires_reverification(self):
        _,status=self.run_case(as_of="2026-11-12")
        self.assertEqual(status["currentCapVerifiedEligiblePhase3Applications"],0)
        rows,status=self.run_case(as_of="2026-12-01")
        self.assertEqual(status["issuedBeforeTargetDates"],2)
        gist=next(r for r in rows if r["trialName"]=="PEAK")
        self.assertEqual(gist["targetStatus"],"TARGET_PASSED_OUTCOME_MUST_BE_REVERIFIED")
        self.assertEqual(gist["marketCapVerification"],"STALE_CAP_REVERIFY")
        self.assertEqual(gist["outcomeAsOf"],"NO_VERIFIED_DECISION_AS_OF_SNAPSHOT")

    def test_phase2_is_not_silently_reclassified_and_duplicate_ndas_rejected(self):
        data,reviews,roster=self.original
        wrong=copy.deepcopy(data)
        next(r for r in wrong["applications"] if r["trialName"]=="SUMMIT")["phaseOfPivotalEvidence"]=3
        with self.assertRaisesRegex(ValueError,"PHASE3_ROSTER_MISMATCH"):
            self.run_case((wrong,reviews,roster))
        wrong=copy.deepcopy(data)
        wrong["applications"][1]["trialNctId"]="NCT05208047"
        with self.assertRaisesRegex(ValueError,"APPLICATION_IDENTITY"):
            self.run_case((wrong,reviews,roster))
        wrong=copy.deepcopy(data)
        wrong["applications"][0]["pdufaTargetDate"]="2026-05-01"
        with self.assertRaisesRegex(ValueError,"DATE_OR_REVIEW_STATUS"):
            self.run_case((wrong,reviews,roster))
        wrong=copy.deepcopy(data)
        wrong["applications"][2]["outcomeAsOf"]="APPROVAL"
        with self.assertRaisesRegex(ValueError,"APPLICATION_IDENTITY"):
            self.run_case((wrong,reviews,roster))

    def test_cap_bound_and_download_schema(self):
        data,reviews,roster=self.original
        wrong=copy.deepcopy(data)
        wrong["issuer"]["marketCapUsd"]=150000000
        rows,s=self.run_case((wrong,reviews,roster))
        self.assertEqual(s["currentCapVerifiedEligiblePhase3Applications"],0)
        self.assertEqual(next(r for r in rows if r["pivotalPhase"]==3)["pipelineRestrictionResult"],
                         "OUTSIDE_CAP_RESTRICTION")
        csv_out,summary=mod.generate(*self.original,as_of="2026-11-04")
        read=list(csv.DictReader(io.StringIO(csv_out)))
        self.assertEqual(len(read),3)
        self.assertEqual(json.loads(summary)["verifiedFdaOutcomes"],0)
        self.assertEqual(mod.safe("=DANGER()"),"'=DANGER()")

if __name__=="__main__":
    unittest.main()
