import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from collect_level7_focus_registry import capture, collect_trial
from level7_store import EvidenceStore


def registry(nct):
    document = {"protocolSection": {
        "identificationModule": {"nctId": nct},
        "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-01-01"}},
    }}
    return document, {"retrieved_at_utc": "2026-01-02T00:00:00+00:00"}, json.dumps(document).encode()


class RegistryCaptureTests(TestCase):
    def test_captures_exact_roster_and_reads_bytes_without_claiming_readiness(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            roster = path / "roster.json"
            trials = [{"nct": f"NCT{n:08d}"} for n in range(32)]
            roster.write_text(json.dumps({"records": trials}), encoding="utf-8")
            store = EvidenceStore(path / "evidence.sqlite")
            collect = lambda nct: collect_trial(nct, registry)
            result = capture(store, roster, collect)
            self.assertEqual(result, capture(store, roster, collect))
            self.assertEqual(result["total"], 32)
            self.assertEqual(result["verifiedRegistryDocuments"], 32)
            self.assertEqual(set(result["readiness"].values()), {"EVIDENCE_INCOMPLETE"})
            evidence, = store.history(trials[0]["nct"])
            self.assertEqual(store.document(evidence.sha256_digest), registry(trials[0]["nct"])[2])
            self.assertEqual(evidence.document_date, "2026-01-01")

    def test_marks_invalid_or_unreachable_registry_distinctly(self):
        for exception, expected in [
            (HTTPError("https://clinicaltrials.gov", 404, "", {}, None), "missing"),
            (URLError("timeout"), "inaccessible"),
            (ValueError("wrong study"), "conflicting"),
        ]:
            def fail(nct):
                raise exception

            with self.subTest(status=expected):
                evidence, raw = collect_trial("NCT00000001", fail)
                self.assertEqual(evidence.status, expected)
                self.assertIsNone(evidence.sha256_digest)
                self.assertIsNone(raw)
