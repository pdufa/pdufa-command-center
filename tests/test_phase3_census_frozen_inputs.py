"""Frozen census lineage must survive live-source updates without relaxing its cutoff."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build_phase3_census_sources import INPUTS, ORIGINAL_PATHS, PROVENANCE, ROOT, build


class FrozenCensusTests(unittest.TestCase):
    def fixture(self, folder):
        root = Path(folder)
        for name in (*INPUTS, PROVENANCE):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        return root

    def test_frozen_inputs_reproduce_the_existing_741_trial_directory(self):
        saved = json.loads((ROOT / "new-platform/frontend/public/phase3-census-sources-2026-10-26.json").read_text())
        self.assertEqual(build(), saved)
        self.assertEqual(len(saved["companies"]), 130)
        self.assertEqual(sum(len(row["nctIds"]) for row in saved["companies"]), 741)
        self.assertEqual(saved["scope"], "RESEARCH_POINTERS_ONLY")

    def test_newer_or_missing_live_sources_cannot_rewrite_the_historical_directory(self):
        expected = build()
        with tempfile.TemporaryDirectory() as folder:
            root = self.fixture(folder)
            for name in (ORIGINAL_PATHS[0], ORIGINAL_PATHS[1], "data/phase_pipeline_market_caps.csv", ORIGINAL_PATHS[3]):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("live source changed after the frozen cutoff; not historical evidence\n")
            self.assertEqual(build(root), expected)
            for name in (ORIGINAL_PATHS[0], ORIGINAL_PATHS[1], "data/phase_pipeline_market_caps.csv", ORIGINAL_PATHS[3]):
                (root / name).unlink()
            self.assertEqual(build(root), expected)

    def test_changed_snapshot_bytes_or_forged_provenance_are_rejected(self):
        for name in INPUTS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = self.fixture(folder)
                path = root / name
                path.write_bytes(path.read_bytes() + b"\n")
                with self.assertRaises(ValueError):
                    build(root)
        with tempfile.TemporaryDirectory() as folder:
            root = self.fixture(folder)
            path = root / PROVENANCE
            data = json.loads(path.read_text())
            data["inputs"][0]["sourceCommit"] = "0" * 40
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                build(root)

    def test_missing_frozen_input_never_falls_back_to_a_live_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.fixture(folder)
            (root / INPUTS[2]).unlink()
            live = root / "data/phase_pipeline_market_caps.csv"
            live.write_bytes((ROOT / INPUTS[2]).read_bytes())
            with self.assertRaises(FileNotFoundError):
                build(root)
