"""Integrity and non-promotion controls for RAAS V2 nightly research snapshots."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_fda_decision_accuracy_audit as audit
import raas_v2_prospective_source_readiness as v2
import raas_v2_source_provenance_manifest as provenance
import raas_v2_openfda_application_watch as public_watch
import raas_v2_sec_nov14_filing_watch as issuer_watch

SHA="a"*40
RUN="41735573512"
ASOF="2026-11-03T23:59:59Z"
ARCHIVED="2026-11-04T00:02:00Z"


def sample(path):
    d=Path(path)
    audit.export(audit.execute(asof=ASOF),
                 d/"raas-fda-three-way-prediction-accuracy.json",
                 d/"raas-fda-historical-source-review-queue.csv",
                 d/"raas-fda-upcoming-original-goal-review-queue.csv")
    v2.export(v2.execute(asof=ASOF),
              d/"raas-v2-prospective-source-readiness.json",
              d/"raas-v2-prospective-source-review.csv")
    research=public_watch.inspect_response(
        None,ASOF,"SOURCE_UNAVAILABLE","Offline test: no FDA API fetch")
    (d/"raas-v2-openfda-application-identity-watch.json").write_text(
        json.dumps(research)+"\n",encoding="utf-8")
    sec=issuer_watch.inspect_watch(
        {"CYTK":None,"SMMT":None},
        {"CYTK":"SOURCE_UNAVAILABLE","SMMT":"SOURCE_UNAVAILABLE"},
        {"CYTK":"offline fixture","SMMT":"offline fixture"},ASOF)
    (d/"raas-v2-sec-nov14-new-filing-review-leads.json").write_text(
        json.dumps(sec)+"\n",encoding="utf-8")
    return d


class NightlyManifestTests(unittest.TestCase):
    def test_seven_files_hashed_and_tied_to_run_without_becoming_prediction_receipt(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            m=provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                        RUN,SHA,ARCHIVED)
            self.assertEqual(len(m["fileDigests"]),7)
            self.assertEqual(m["githubWorkflowRunId"],RUN)
            self.assertEqual(m["sourceCommitSHA"],SHA)
            self.assertEqual(m["sourceResearchCases"],36)
            self.assertEqual(m["revisedPdufaTargetsExcludedFromOriginalGoalResearchCount"],4)
            self.assertEqual(m["independentlyCertifiedThreeWayForecasts"],0)
            self.assertIsNone(m["independentlyValidatedFDAAccuracyPct"])
            self.assertEqual(m["approvedRAASMetricCalibrations"],0)
            self.assertIn("NOT_PREDICTION_RECEIPT",m["scope"])
            self.assertEqual(m["fileDigests"][
                "raas-v2-prospective-source-review.csv"]["bytes"],
                (d/"raas-v2-prospective-source-review.csv").stat().st_size)
            target=d/"raas-v2-evidence-provenance.json"
            provenance.write_manifest(m,target)
            self.assertEqual(json.loads(target.read_text())["sourceCommitSHA"],SHA)

    def test_public_fda_watch_tampering_or_fake_decision_fails_closed(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            p=d/"raas-v2-openfda-application-identity-watch.json"
            for key,bad in (
                ("newImmutableThreeWayPredictions",1),
                ("independentlyAdjudicatedNov14FdaActions",1),
                ("canPromoteToFdaPredictionAccuracy",True),
            ):
                w=json.loads(p.read_text("utf-8"))
                w[key]=bad
                p.write_text(json.dumps(w),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,
                                            "PUBLIC_FDA_WATCH_CANNOT_PROMOTE_RESEARCH"):
                    provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                              RUN,SHA,ARCHIVED)
                w[key]=0 if key!="canPromoteToFdaPredictionAccuracy" else False
                p.write_text(json.dumps(w),encoding="utf-8")
            w=json.loads(p.read_text("utf-8"))
            w["cytk"]["fdaApprovedFebruaryRemsS001IsNovemberMapleHcm"]=True
            p.write_text(json.dumps(w),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,
                                        "PUBLIC_FDA_WATCH_CANNOT_PROMOTE_RESEARCH"):
                provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                          RUN,SHA,ARCHIVED)

    def test_sec_filing_lead_tampering_does_not_certify_fda_action(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            path=d/"raas-v2-sec-nov14-new-filing-review-leads.json"
            original=json.loads(path.read_text("utf-8"))
            for field,bad in (
                ("independentlyVerifiedNoFurtherFDAExtensions",1),
                ("independentlyVerifiedCurrentFDAApplicationCycles",1),
                ("newThreeWayForecastsFromFilings",1),
                ("approvedRAASMetricCalibrations",60),
            ):
                tampered=deepcopy(original)
                tampered[field]=bad
                path.write_text(json.dumps(tampered),encoding="utf-8")
                with self.subTest(field=field),self.assertRaisesRegex(
                    ValueError,"SEC_FILINGS_CANNOT_CERTIFY_FDA_REVIEW_OR_PREDICTIONS"):
                    provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                              RUN,SHA,ARCHIVED)
            tampered=deepcopy(original)
            tampered["rows"][0]["absenceOfNewFilingProvesNoFDAExtension"]=True
            path.write_text(json.dumps(tampered),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,
                "SEC_FILINGS_CANNOT_CERTIFY_FDA_REVIEW_OR_PREDICTIONS"):
                provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                          RUN,SHA,ARCHIVED)

    def test_public_ingredient_candidate_alone_cannot_claim_verified_Summit_BLA(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            p=d/"raas-v2-openfda-application-identity-watch.json"
            original=json.loads(p.read_text("utf-8"))
            candidate={
                "applicationNumberPubliclyIndexed":"BLA761999",
                "pendingSMMTBlaNumberIndependentlyVerified":False,
                "sameEGFRmNSCLCHarmonIReviewCycleVerified":False,
                "fdaOutcomeFromPublicProductIndexVerified":False,
            }
            for flag in ("pendingSMMTBlaNumberIndependentlyVerified",
                         "sameEGFRmNSCLCHarmonIReviewCycleVerified",
                         "fdaOutcomeFromPublicProductIndexVerified"):
                tampered=deepcopy(original)
                tampered["smmtPublicIndexedBlaCandidateCount"]=1
                tampered["smmt"]["approvedProductIngredientSearch"][
                    "matchingPublishedBlaCandidatesNeedIndependentReview"]=[
                        dict(candidate,**{flag:True})]
                p.write_text(json.dumps(tampered),encoding="utf-8")
                with self.subTest(flag=flag),self.assertRaisesRegex(
                        ValueError,"PUBLIC_FDA_WATCH_CANNOT_PROMOTE_RESEARCH"):
                    provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                              RUN,SHA,ARCHIVED)

    def test_dated_issuer_reiteration_cannot_claim_official_no_extension(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            p=d/"raas-v2-prospective-source-readiness.json"
            original=json.loads(p.read_text("utf-8"))
            for field,value in (
                ("nov14IndependentlyCertifiedNoLaterFdaGoalRevisions",1),
                ("nov14DatedIssuerSourcesPublicByAsOfCount",0),
                ("nov14IssuerSourcesOlderThan30DaysCount",0),
            ):
                altered=deepcopy(original)
                altered[field]=value
                p.write_text(json.dumps(altered),encoding="utf-8")
                with self.subTest(field=field),self.assertRaisesRegex(
                    ValueError,"ISSUER_REITERATIONS_CANNOT_VERIFY_NO_LATER_FDA_EXTENSION"):
                    provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                              RUN,SHA,ARCHIVED)
            altered=deepcopy(original)
            altered["nov14DatedIssuerGoalContinuityChecks"][0][
                "currentlyIndependentlyCertifiedUnrevisedFdaDeadline"]=True
            p.write_text(json.dumps(altered),encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,"ISSUER_REITERATIONS_CANNOT_VERIFY_NO_LATER_FDA_EXTENSION"):
                provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                          RUN,SHA,ARCHIVED)

    def test_report_without_all_seven_source_files_fails_closed(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            (d/"raas-v2-prospective-source-review.csv").unlink()
            with self.assertRaisesRegex(ValueError,"OUTPUT_MISSING_OR_LINK"):
                provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                          RUN,SHA,ARCHIVED)

    def test_not_allowed_to_archive_unapproved_output_as_successful_prediction(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            p=d/"raas-v2-prospective-source-readiness.json"
            r=json.loads(p.read_text())
            r["approvedRAASMetricCalibrations"]=60
            p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,"V2_SOURCE_REPORT_UNAPPROVED_STATE_MISSING"):
                provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                          RUN,SHA,ARCHIVED)

    def test_original_goal_exclusion_count_must_match_record_level_flags(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            p=d/"raas-v2-prospective-source-readiness.json"
            r=json.loads(p.read_text())
            r["knownRevisedDeadlineExcludedFromOriginalGoalCount"]=0
            p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,"V2_REVISED_GOAL_EXCLUSION_MISMATCH"):
                provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                          RUN,SHA,ARCHIVED)

    def test_csv_cannot_hide_a_revised_original_goal_flag(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            p=d/"raas-v2-prospective-source-review.csv"
            raw=p.read_text()
            self.assertIn("True",raw)
            p.write_text(raw.replace("True","False"))
            with self.assertRaisesRegex(ValueError,"V2_CSV_REVISED_GOAL_COUNT_DISAGREEMENT"):
                provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                          RUN,SHA,ARCHIVED)

    def test_manifest_rejects_future_report_clock_or_claimed_model_approval(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            with self.assertRaisesRegex(ValueError,"OUTPUT_CLOCK_OR_ORDER_INCONSISTENT"):
                provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                          RUN,SHA,"2026-11-03T20:00:00Z")
            good=provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                            RUN,SHA,ARCHIVED)
            good["independentlyValidatedFDAAccuracyPct"]=0.90
            with self.assertRaisesRegex(ValueError,"MANIFEST_CANNOT_PROMOTE_FORECAST"):
                provenance.write_manifest(good,d/"fake.json")

    def test_repository_run_and_commit_must_have_valid_ids(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            for repo,run,sha in (
                ("other/repo",RUN,SHA),
                ("pdufa/pdufa-command-center","junk",SHA),
                ("pdufa/pdufa-command-center",RUN,"bad"),
            ):
                with self.assertRaisesRegex(ValueError,"GITHUB_PROVENANCE_INVALID"):
                    provenance.build_manifest(d,repo,run,sha,ARCHIVED)


if __name__=="__main__":
    unittest.main()
