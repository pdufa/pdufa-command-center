"""Reproducible, unsigned Level 1–6 handoff bundle integrity checks."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/medical/level16_research_handoff_bundle.py"
spec = importlib.util.spec_from_file_location("level16_research_handoff_bundle", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ResearchHandoffBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for path in mod.SOURCES.values():
            dst = self.root / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, dst)

    def test_genuine_current_research_metadata_is_reproducible_but_unapproved(self):
        bundle = mod.build_bundle(self.root)
        self.assertEqual(bundle["kind"], "FOCUS_LEVEL16_UNSIGNED_RESEARCH_REVIEW_BUNDLE")
        self.assertEqual(bundle["status"], "BYTE_CONSISTENCY_ONLY_NOT_EVIDENCE_AUTHENTICATION")
        self.assertEqual(len(bundle["sourceSha256"]), 8)
        self.assertEqual(bundle["packet"]["focusTrialCount"], 32)
        self.assertEqual(bundle["packet"]["reviewPacketsPrepared"], 32)
        self.assertEqual(sum(len(t["levels"]) for t in bundle["packet"]["trials"]), 192)
        self.assertEqual(bundle["packet"]["independentlyAdjudicatedLevels"], 0)
        self.assertEqual(bundle["packet"]["independentlyAuthenticatedSources"], 0)
        self.assertEqual(bundle["packet"]["actualApprovalProbabilities"], 0)
        self.assertFalse(bundle["packet"]["stagingActivated"])
        self.assertIsNone(bundle["packet"]["trials"][0]["approvalProbability"])
        result = mod.verify_bundle(bundle, self.root)
        self.assertEqual(result["status"],
                         "LOCAL_RESEARCH_SNAPSHOT_AND_PACKET_BYTES_MATCH_ONLY")
        self.assertFalse(result["fdaPredictionPermitted"])
        self.assertEqual(result["independentlyAdjudicatedLevels"], 0)

    def test_orca2_publication_outcomes_are_embedded_as_unreviewed_case_data(self):
        bundle = mod.build_bundle(self.root)
        trial = next(t for t in bundle["packet"]["trials"] if t["nct"] == "NCT04576949")
        level3 = trial["levels"][2]["publicationFindingsUnreviewed"]
        self.assertEqual(len(level3["reportedEfficacyComparisons"]), 4)
        self.assertEqual(level3["reportedEfficacyComparisons"][0]["activePct"], 25.3)
        self.assertEqual(level3["reportedSafetyObservations"]["seriousAdverseEvents"]["cytisinicline"], 18)
        self.assertFalse(level3["sourceIndependentlyAuthenticated"])
        self.assertFalse(level3["scientificallyAdjudicated"])
        self.assertIsNone(trial["levels"][2]["score"])
        self.assertIsNone(trial["approvalProbability"])

    def test_original_published_efficacy_cannot_be_silently_rewritten(self):
        source = self.root / mod.SOURCES["orca2Publication"]
        original = mod.build_bundle(self.root)
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["efficacy"][0]["placeboPct"] = 0.0
        source.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(ValueError):
            mod.build_bundle(self.root)
        with self.assertRaises(ValueError):
            mod.verify_bundle(original, self.root)

    def test_orca3_publication_replication_and_discrepancy_leads_embedded(self):
        packet = mod.build_bundle(self.root)["packet"]
        trial = next(x for x in packet["trials"] if x["nct"] == "NCT05206370")
        levels = trial["levels"]
        for idx in (2, 3, 5):
            self.assertIsNotNone(levels[idx]["publicationFindingsUnreviewed"])
            self.assertFalse(levels[idx]["completionPermitted"])
            self.assertIsNone(levels[idx]["approvalProbability"])
            self.assertFalse(levels[idx]["publicationFindingsUnreviewed"]["scientificallyAdjudicated"])
        self.assertEqual(len(levels[2]["publicationFindingsUnreviewed"][
            "publicationTextDiscrepanciesUnreviewed"]), 2)
        self.assertEqual(levels[2]["publicationFindingsUnreviewed"][
            "reportedEfficacyComparisons"][1]["activePct"], 30.3)
        other = next(x for x in packet["trials"] if x["nct"] == "NCT04576949")
        self.assertNotEqual(other["levels"][2]["publicationFindingsUnreviewed"]["publicationUrl"],
                            levels[2]["publicationFindingsUnreviewed"]["publicationUrl"])
        self.assertEqual(packet["independentlyAdjudicatedLevels"], 0)

    def test_orca3_original_endpoints_cannot_be_silently_changed(self):
        source = self.root / mod.SOURCES["orca3Publication"]
        original = mod.build_bundle(self.root)
        data = json.loads(source.read_text(encoding="utf-8"))
        data["endpoints"][0]["activeCount"] = 200
        source.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            mod.build_bundle(self.root)
        with self.assertRaises(ValueError):
            mod.verify_bundle(original, self.root)

    def test_maple_hcm_original_vs_secondary_source_roles_and_continuous_endpoint(self):
        bundle = mod.build_bundle(self.root)
        trial = next(x for x in bundle["packet"]["trials"]
                     if x["nct"] == "NCT05767346")
        levels = trial["levels"]
        item = levels[2]["publicationFindingsUnreviewed"]
        self.assertEqual(item["endpointDataType"],
                         "CONTINUOUS_EXERCISE_CAPACITY_NOT_BINARY_ABSTINENCE")
        self.assertEqual(item["continuousPrimaryEndpointUnreviewed"][
            "adjustedBetweenGroupMeanDifference"], 2.3)
        self.assertEqual(item["continuousPrimaryEndpointUnreviewed"]["unit"], "mL/kg/min")
        self.assertEqual(len(item["secondaryContinuousComparisonsUnreviewed"]), 6)
        self.assertEqual(item["reportedEfficacyComparisons"], [])
        self.assertFalse(item["scientificallyAdjudicated"])
        self.assertEqual(levels[2]["independentScientificReviewStatus"], "NOT_ADJUDICATED")
        self.assertIsNone(trial["approvalProbability"])
        self.assertEqual(bundle["packet"]["independentlyAdjudicatedLevels"], 0)
        self.assertEqual(mod.verify_bundle(bundle, self.root)["independentlyAuthenticatedSources"], 0)

    def test_source_receipt_fails_on_changed_maple_hcm_pvo2(self):
        path = self.root / mod.SOURCES["mapleHcm"]
        original = mod.build_bundle(self.root)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["primaryEndpoint"]["adjustedBetweenGroupMeanDifference"] = 9.9
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            mod.build_bundle(self.root)
        with self.assertRaises(ValueError):
            mod.verify_bundle(original, self.root)

    def test_origin3_renal_two_dated_sources_are_bound_without_historical_prediction(self):
        bundle = mod.build_bundle(self.root)
        packet = bundle["packet"]
        trial = next(x for x in packet["trials"] if x["nct"] == "NCT04716231")
        clinical = trial["levels"][2]["renalEvidenceUnreviewed"]
        self.assertEqual(len(clinical["sourceLinks"]), 2)
        self.assertEqual(clinical["sourceLinks"][0]["publishedOnline"], "2025-11-06")
        self.assertEqual(clinical["sourceLinks"][1]["publishedOnline"], "2026-10-22")
        self.assertEqual(clinical["interimPrimaryProteinuriaUnreviewed"][
            "denominator"]["prespecifiedInterimAnalysisTotal"], 203)
        self.assertEqual(clinical["laterSecondaryKidneyFunctionUnreviewed"][
            "denominator"]["treatedTotal"], 428)
        self.assertFalse(clinical["historicalBlindBacktestPermitted"])
        self.assertEqual(packet["independentlyAdjudicatedLevels"], 0)
        self.assertEqual(packet["actualApprovalProbabilities"], 0)
        self.assertEqual(mod.verify_bundle(bundle, self.root)["approvedReviewerCount"], 0)

    def test_origin3_2026_late_evidence_cannot_be_modified_without_rejection(self):
        src = self.root / mod.SOURCES["origin3Renal"]
        before = mod.build_bundle(self.root)
        obj = json.loads(src.read_text(encoding="utf-8"))
        obj["reports"][1]["secondaryEfficacy"][0]["reportedBetweenGroupDifference"] = -3.3
        src.write_text(json.dumps(obj), encoding="utf-8")
        with self.assertRaises(ValueError):
            mod.build_bundle(self.root)
        with self.assertRaises(ValueError):
            mod.verify_bundle(before, self.root)

    def test_byte_identical_recomputation_is_stable(self):
        a = mod.build_bundle(self.root)
        b = mod.build_bundle(self.root)
        self.assertEqual(mod._json_bytes(a), mod._json_bytes(b))
        self.assertEqual(a["packetSha256"], b["packetSha256"])

    def test_harmless_source_whitespace_change_is_detected(self):
        old = mod.build_bundle(self.root)
        source = self.root / mod.SOURCES["coverage"]
        source.write_bytes(source.read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            mod.verify_bundle(old, self.root)
        self.assertNotEqual(old["sourceSha256"]["coverage"],
                            mod.build_bundle(self.root)["sourceSha256"]["coverage"])

    def test_source_trial_identity_change_fails_closed(self):
        source = self.root / mod.SOURCES["focusRoster"]
        obj = json.loads(source.read_text(encoding="utf-8"))
        obj["records"][0]["nct"] = "NCT99999999"
        source.write_text(json.dumps(obj), encoding="utf-8")
        with self.assertRaises(ValueError):
            mod.build_bundle(self.root)

    def test_forged_review_approval_and_prediction_are_rejected(self):
        original = mod.build_bundle(self.root)
        mutations = (
            lambda b: b["packet"].update(independentlyAdjudicatedLevels=6),
            lambda b: b["packet"].update(actualApprovalProbabilities=1),
            lambda b: b["packet"]["trials"][0]["levels"][0].update(
                sourceAuthenticationStatus="AUTHENTICATED"),
            lambda b: b["packet"]["trials"][0]["levels"][0].update(
                approvalProbability=0.99),
        )
        for mutate in mutations:
            b = copy.deepcopy(original)
            mutate(b)
            with self.assertRaises(ValueError):
                mod.verify_bundle(b, self.root)

    def test_forged_packet_hash_does_not_override_expected_data(self):
        b = mod.build_bundle(self.root)
        b["packet"]["trials"][0]["ticker"] = "WRONG"
        b["packetSha256"] = mod._sha256(mod._json_bytes(b["packet"]))
        with self.assertRaises(ValueError):
            mod.verify_bundle(b, self.root)

    def test_forbidden_approval_metadata_is_rejected(self):
        original = mod.build_bundle(self.root)
        for mutation in (
            lambda b: b.update(verifiedBy="invented reviewer"),
            lambda b: b.update(status="INDEPENDENTLY_AUTHENTICATED"),
            lambda b: b.update(schemaVersion=True),
            lambda b: b["sourceSha256"].update(newUnverifiedSource="f"*64),
        ):
            b = copy.deepcopy(original)
            mutation(b)
            with self.assertRaises(ValueError):
                mod.verify_bundle(b, self.root)

    def test_missing_and_symlinked_research_snapshot_rejected(self):
        source = self.root / mod.SOURCES["orca2Chronology"]
        source.unlink()
        with self.assertRaises(ValueError):
            mod.build_bundle(self.root)
        try:
            source.symlink_to(ROOT / mod.SOURCES["orca2Chronology"])
        except (OSError, NotImplementedError):
            self.skipTest("No symlink support in the current test environment")
        with self.assertRaises(ValueError):
            mod.build_bundle(self.root)

    def test_source_digest_cannot_be_forged_in_handoff(self):
        b = mod.build_bundle(self.root)
        b["sourceSha256"]["coverage"] = "0"*64
        with self.assertRaises(ValueError):
            mod.verify_bundle(b, self.root)


if __name__ == "__main__":
    unittest.main()
