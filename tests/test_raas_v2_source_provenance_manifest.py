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
    return d


class NightlyManifestTests(unittest.TestCase):
    def test_five_files_hashed_and_tied_to_run_without_becoming_prediction_receipt(self):
        with TemporaryDirectory() as td:
            d=sample(td)
            m=provenance.build_manifest(d,"pdufa/pdufa-command-center",
                                        RUN,SHA,ARCHIVED)
            self.assertEqual(len(m["fileDigests"]),5)
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

    def test_report_without_all_five_source_files_fails_closed(self):
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
