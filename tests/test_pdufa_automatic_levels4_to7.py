"""Offline integration tests for bounded Level4-7 automation; no external services."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pdufa_automatic_levels4_to7 as A

ROSTER = json.loads((ROOT / "automation/focus-assessment-roster-snapshot-20261112.json").read_text())
MANIFEST = json.loads((ROOT / "automation/scientific-level-completion-queue.json").read_text())
STAMP = "2026-11-12T10:00:00+00:00"
NOW = datetime(2026,11,12,23,59,0,tzinfo=timezone.utc)


def record_for(nct):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct},
        "statusModule": {
            "overallStatus": "COMPLETED",
            "lastUpdatePostDateStruct": {"date": "2026-11-12"}},
        "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE3"],
                         "designInfo": {"allocation": "RANDOMIZED"}},
        "outcomesModule": {"primaryOutcomes":
                           [{"measure": "Symptom score", "timeFrame": "12 weeks"}]},
        "referencesModule": {"references": []}},
        "resultsSection": {}}


def fetched(nct):
    record = record_for(nct)
    raw = json.dumps(record, sort_keys=True).encode()
    return record, {
        "nct": nct, "source_url": A.REGISTRY+nct,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "retrieved_at_utc": STAMP,
    }, raw


class AutoLevel47Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stop = self.root / "OWNER_STOP"
        self.out = self.root / "artifacts"

    def run_pipeline(self, fetcher=fetched):
        return A.execute(roster=ROSTER, manifest=MANIFEST, output=self.out,
                         fetcher=fetcher, stop_file=self.stop, now=NOW)

    def test_one_source_fetch_per_nct_and_all_level4_7_audits(self):
        calls = []
        def fetch(nct):
            calls.append(nct)
            return fetched(nct)
        s = self.run_pipeline(fetch)
        self.assertEqual(len(calls), 32)
        self.assertEqual(len(set(calls)), 32)
        self.assertEqual(s["original_registry_sources_retrieved"], 32)
        self.assertEqual(s["trial_assessment_records"], 32*17)
        self.assertFalse(s["level7_model_trained"])
        self.assertEqual(s["scores_generated"], 0)
        self.assertEqual(s["level7_model"],
                         "MODEL_VALIDATION_EVIDENCE_GAPS_INVENTORIED_NOT_PREDICTIONS")
        for level in (4,5,6):
            doc = json.loads((self.out / f"level{level}-evidence.json").read_text())
            self.assertEqual(doc["total"],32)
            self.assertEqual(doc["retrieved"],32)
            self.assertFalse(doc["scientific_level_complete"])
            self.assertEqual(len(doc["reports"]),32)
        data = json.loads((self.out/"levels4-20-assessment-readiness.json").read_text())
        self.assertEqual(data["assessment_records"],544)
        self.assertTrue(all(v["score_out_of_100"] is None for v in data["assessments"]))
        self.assertTrue(all(v["fda_approval_probability"] is None for v in data["assessments"]))
        self.assertFalse(data["scientific_acceptance_automated"])
        one = ROSTER["trials"][0]["nct"]
        self.assertEqual(hashlib.sha256((self.out/"registry"/(one+".json")).read_bytes()).hexdigest(),
                         json.loads((self.out/"registry"/(one+".receipt.json")).read_text())["sha256"])
        self.assertTrue((self.out/"level7-model-readiness.json").exists())

    def test_one_failed_source_isolated_no_fictitious_level7_model(self):
        target=ROSTER["trials"][4]["nct"]
        def partly(nct):
            if nct==target:
                raise TimeoutError("registry temporary outage")
            return fetched(nct)
        s=self.run_pipeline(partly)
        self.assertEqual(s["original_registry_sources_retrieved"],31)
        self.assertEqual(s["level7_model"],
                         "BLOCKED_INCOMPLETE_LEVEL6_ORIGINAL_REGISTRY_RECEIPTS")
        self.assertEqual(len(s["source_issues"]),1)
        report=json.loads((self.out/"levels4-20-assessment-readiness.json").read_text())
        affected=[r for r in report["assessments"] if r["nct"]==target]
        self.assertEqual(len(affected),17)
        self.assertTrue(all(r["score_out_of_100"] is None for r in affected))
        self.assertTrue(all(r["science_complete"] is False for r in affected))

    def test_owner_stop_prevents_initial_or_continued_work(self):
        self.stop.touch()
        def wrong(_):
            raise AssertionError("must not fetch")
        with self.assertRaisesRegex(RuntimeError,"OWNER_STOP_ACTIVE"):
            self.run_pipeline(wrong)
        self.assertFalse(self.out.exists())

    def test_mismatched_source_identity_and_tampered_raw_discarded(self):
        first=ROSTER["trials"][0]["nct"]
        def tampered(nct):
            rec,metadata,raw=fetched(nct)
            if nct==first:
                metadata["sha256"]="0"*64
            return rec,metadata,raw
        s=self.run_pipeline(tampered)
        self.assertEqual(s["original_registry_sources_retrieved"],31)
        self.assertEqual(len(s["source_issues"]),1)
        self.assertFalse((self.out/"registry"/(first+".json")).exists())

    def test_source_last_posted_date_is_not_assumed_from_snapshot_date(self):
        rec,meta,_=fetched(ROSTER["trials"][0]["nct"])
        rec["protocolSection"]["statusModule"].pop("lastUpdatePostDateStruct")
        trial=A.phase_evidence(meta["nct"],rec,meta)
        self.assertEqual(trial["phase"],"UNKNOWN_OR_NOT_APPLICABLE")
        self.assertNotIn("phase_source",trial)
        self.assertEqual(trial["application_stage"],"UNKNOWN")

    def test_curated_manual_ratings_must_match_registry_phase_and_cutoff(self):
        rec,meta,_=fetched(ROSTER["trials"][0]["nct"])
        source=A.phase_evidence(meta["nct"],rec,meta)
        incoming={"schema_version":1,"as_of":"2026-11-12","trials":[{
            "nct":meta["nct"],"phase":"PHASE2","evidence":{}}]}
        with self.assertRaisesRegex(ValueError,"conflicts"):
            A.restore_curated(source,incoming,meta["nct"])
        incoming["trials"][0]["phase"]="PHASE3"
        incoming["trials"][0]["actual_outcome"]="approved"
        with self.assertRaisesRegex(ValueError,"Known FDA outcome"):
            A.restore_curated(source,incoming,meta["nct"])

    def test_fake_source_late_retrieval_rejected_at_fixed_cutoff(self):
        def late(nct):
            rec,meta,raw=fetched(nct)
            meta["retrieved_at_utc"]="2026-11-13T10:00:00+00:00"
            return rec,meta,raw
        s=self.run_pipeline(late)
        self.assertEqual(s["original_registry_sources_retrieved"],0)
        self.assertEqual(len(s["source_issues"]),32)
        self.assertEqual(s["scores_generated"],0)

    def test_source_publication_date_after_cutoff_is_not_scored(self):
        first=ROSTER["trials"][0]["nct"]
        def published_future(nct):
            rec,meta,_=fetched(nct)
            if nct==first:
                rec["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"]="2026-11-13"
            raw=json.dumps(rec,sort_keys=True).encode()
            meta["sha256"]=hashlib.sha256(raw).hexdigest()
            return rec,meta,raw
        s=self.run_pipeline(published_future)
        self.assertEqual(s["original_registry_sources_retrieved"],32)
        data=json.loads((self.out/"levels4-20-assessment-readiness.json").read_text())
        r=next(x for x in data["assessments"] if x["nct"]==first and x["level"]==6)
        self.assertIsNone(r["score_out_of_100"])
        self.assertEqual(s["scores_generated"],0)


if __name__=="__main__":
    unittest.main()
