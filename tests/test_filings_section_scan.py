"""Section requests target one agency; snapshots never promote trading gates."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.filings_section_scan import (
    FIELDS, SNAPSHOTS, VERSION, collect, digest, extension_observations,
    load_snapshot, overlay_findings, publish, scope_hash, section_config,
    summary, write_csv,
)


class SectionScanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.events = [{"event_key": "ABC|drug", "ticker": "ABC", "drug": "Drug"}]
        self.companies = [{"ticker": "ABC", "cik10": "0000000001"}]
        write_csv(self.data / "pdufa_candidates.csv", self.events, self.events[0])
        write_csv(self.data / "company_registry.csv", self.companies, self.companies[0])
        write_csv(self.data / "pdufa_source_verification.csv", [], FIELDS)

    def row(self, source="FDA", **changes):
        return {**dict.fromkeys(FIELDS, ""), "event_key": "ABC|drug", "ticker": "ABC",
                "category": source, "claim": "PDUFA_TARGET" if source == "FDA" else "FINANCING_CLOSURE",
                "verification_status": "REVIEW_REQUIRED", "verification_required": "YES",
                "checked_at": "2026-10-15T18:00:00+00:00", **changes}

    def fake_verifier(self, source, data, out, mode):
        rows = [self.row(source)]
        if source == "SEC":
            rows.append(self.row(source, event_key="REGISTRY:ABC", claim="FILINGS_INVENTORY"))
            (out / "sec_filing_watch.csv").write_text("ticker\n", encoding="utf-8")
        write_csv(out / (source.lower() + "_verification.csv"), rows, FIELDS)
        return {**summary(rows), "scan_mode": mode, "verification_version": VERSION,
                "verification_scope_sha256": scope_hash(self.events, self.companies),
                "scope_coverage_verified": False}

    def test_all_four_buttons_target_the_requested_agency_and_mode(self):
        expected = {"SEC_BASE": ("SEC", "FULL"), "SEC_AMENDMENTS": ("SEC", "DELTA"),
                    "FDA_BASE": ("FDA", "FULL"), "FDA_AMENDMENTS": ("FDA", "DELTA")}
        before = {p.name: p.read_bytes() for p in self.data.glob("*.csv")}
        for section, config in expected.items():
            with self.subTest(section=section):
                out = self.root / section
                with patch("scripts.filings_section_scan.verify_source", side_effect=self.fake_verifier) as verify:
                    result = collect(section, self.data, out)
                self.assertEqual(section_config(section), config)
                self.assertEqual(verify.call_count, 1)
                self.assertEqual(verify.call_args.args[0], config[0])
                self.assertEqual(verify.call_args.kwargs["mode"], config[1])
                self.assertEqual(result["evidence_status"], "PARTIAL")
                publish(section, self.data, out)
                self.assertTrue((self.data / SNAPSHOTS / section.lower() / "report.json").is_file())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.data.glob("*.csv")})
        with self.assertRaises(ValueError):
            section_config("ALL")

    def test_publication_rejects_altered_evidence_and_new_candidate_scope(self):
        out = self.root / "artifacts"
        with patch("scripts.filings_section_scan.verify_source", side_effect=self.fake_verifier):
            collect("FDA_BASE", self.data, out)
        original = (out / "fda_verification.csv").read_bytes()
        (out / "fda_verification.csv").write_bytes(original + b"\n")
        with self.assertRaisesRegex(ValueError, "checksum"):
            publish("FDA_BASE", self.data, out)
        (out / "fda_verification.csv").write_bytes(original)
        updated = [{**self.events[0], "pdufa_date": "2026-12-15"}]
        write_csv(self.data / "pdufa_candidates.csv", updated, updated[0])
        with self.assertRaisesRegex(ValueError, "scope"):
            publish("FDA_BASE", self.data, out)
        self.assertFalse((self.data / SNAPSHOTS).exists())

    def test_counts_or_missing_events_cannot_be_published(self):
        out = self.root / "artifacts"
        with patch("scripts.filings_section_scan.verify_source", side_effect=self.fake_verifier):
            collect("FDA_BASE", self.data, out)
        report = json.loads((out / "report.json").read_text())
        report["required_findings_unresolved"] = 0
        (out / "report.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "counts"):
            load_snapshot(out, self.data, "FDA_BASE")
        write_csv(out / "fda_verification.csv", [], FIELDS)
        report["artifact_sha256"]["fda_verification.csv"] = digest((out / "fda_verification.csv").read_bytes())
        (out / "report.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "omits"):
            load_snapshot(out, self.data, "FDA_BASE")

    def test_new_claim_replaces_only_its_own_older_observation(self):
        old_fda = self.row()
        other_agency = self.row("SEC")
        fresh = self.row(verification_status="VERIFIED", checked_at="2026-10-15T19:00:00Z")
        result = overlay_findings([old_fda, other_agency], [fresh])
        self.assertEqual(result, [fresh, other_agency])
        self.assertEqual(overlay_findings(result, [old_fda]), result)

    def test_repeated_fda_scan_keeps_original_extension_detection(self):
        finding = self.row(verification_status="VERIFIED", observed="2027-01-15",
            reason="Explicit dated FDA PDUFA extension supersedes 2026-10-15")
        first = extension_observations([finding], [], "2026-10-15T19:00:00Z")
        second = extension_observations([finding], first, "2026-10-16T19:00:00Z")
        self.assertEqual(first, second)
        self.assertEqual(second[0]["extension_detected_at"], "2026-10-15T19:00:00Z")
        self.assertEqual(extension_observations([self.row()], [], "2026-10-15T19:00:00Z"), [])


if __name__ == "__main__":
    unittest.main()
