from datetime import date
from hashlib import sha256
import json
import unittest

from app.extended_clinical_assessment import assess_clinical_level

NCT = "NCT00000001"


def digest(value):
    return sha256(value.encode()).hexdigest()


def registry(phase="PHASE3"):
    document = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2025-01-01"}, "overallStatus": "COMPLETED"},
            "designModule": {"phases": [phase]},
            "conditionsModule": {"conditions": ["Example condition", "Second condition"]},
            "eligibilityModule": {"eligibilityCriteria": "Individuals aged 18 years or older."},
        },
        "documents": [{"filename": "Prot_001.pdf", "hasProtocol": True, "date": "2025-01-01",
                       "uploadDate": "2025-01-01T10:00"}],
    }
    frozen = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return {
        "nct_id": NCT, "source_url": f"https://clinicaltrials.gov/api/v2/studies/{NCT}",
        "published_at": "2025-01-01", "captured_at": "2025-01-02T00:00:00Z",
        "raw_sha256": digest("original"), "input_sha256": digest(frozen), "document_json": frozen,
    }


def receipt(excerpt, *, cycle="Original 1", trial=NCT, indication="Example condition", path="document.pdf"):
    section = f"Trial {trial}; indication {indication}; NDA 12345; {cycle}. {excerpt}"
    text = f"Overview.\n\n{section}\n\nAppendix."
    return {
        "source_url": f"https://www.fda.gov/{path}", "text": text, "text_sha256": digest(text),
        "raw_sha256": digest("original FDA source document"),
        "identity_excerpt": section, "excerpt": excerpt, "locator": "page 4",
        "indication": indication, "application": "NDA 12345", "cycle": cycle,
        "published_at": "2025-01-01", "captured_at": "2025-01-02T00:00:00Z",
    }


class AdvancedClinicalTest(unittest.TestCase):
    def assess(self, level, evidence=(), **options):
        return assess_clinical_level(level, options.pop("source", registry()), nct=NCT, evidence=evidence, **options)

    def test_levels_have_distinct_findings_and_never_infer_a_prediction(self):
        criteria = {
            13: ("subgroup_interaction", "The interaction test was exploratory."),
            14: ("review_pathway", "The FDA granted priority review."),
            15: ("inspection", "The report describes facility inspection observations."),
            16: ("committee_question", "The committee voted on the following question."),
        }
        for level, (identifier, passage) in criteria.items():
            with self.subTest(level=level):
                result = self.assess(level, [receipt(passage)])
                check = next(item for item in result["checks"] if item["id"] == identifier)
                self.assertEqual(check["state"], "SOURCE_PASSAGE_CHECKED")
                self.assertEqual(check["citations"][0]["excerpt"], passage)
                self.assertEqual(result["score"]["status"], "NOT_SCORED")
                self.assertEqual(result["fdaPrediction"]["outcome"], "ABSTAIN")
                self.assertIsNone(result["fdaPrediction"]["probability"])

    def test_conflicting_passages_are_preserved_and_duplicates_collapse(self):
        initial = receipt("The advisory committee meeting was announced.", path="initial")
        revised = receipt("The advisory committee meeting was canceled.", path="revised")
        result = self.assess(16, [revised, initial, revised])
        check = result["checks"][0]
        self.assertEqual(check["state"], "UNRECONCILED_FINDINGS")
        self.assertEqual([x["excerpt"] for x in check["citations"]], [initial["excerpt"], revised["excerpt"]])
        self.assertEqual(result["evidenceStatus"], "UNRECONCILED_FINDINGS")

    def test_different_application_cycles_do_not_become_one_finding(self):
        initial = receipt("The agency provided priority review.", path="initial")
        supplement = receipt("The agency provided standard review.", cycle="S-1")
        result = self.assess(14, [initial, supplement])
        self.assertEqual(result["checks"][0]["state"], "UNRESOLVED_APPLICATION_OR_CYCLE")
        self.assertEqual({x["cycle"] for x in result["checks"][0]["citations"]}, {"original 1", "s-1"})

    def test_indication_scope_prevents_cross_indication_comparisons(self):
        first = receipt("The comparator was placebo.", path="first")
        second = receipt("The comparator was usual care.", indication="Second condition")
        result = self.assess(13, [first, second])
        self.assertEqual(result["checks"][2]["state"], "UNRESOLVED_INDICATION_SCOPE")

    def test_original_fda_bytes_are_checked_when_collector_provides_them(self):
        valid = receipt("FDA granted priority review.")
        valid["raw_bytes"] = b"original FDA source document"
        accepted = self.assess(14, [valid])
        self.assertEqual(accepted["checks"][0]["state"], "SOURCE_PASSAGE_CHECKED")
        self.assertEqual(accepted["checks"][0]["citations"][0]["raw_sha256"], valid["raw_sha256"])
        self.assertNotIn("raw_bytes", accepted["checks"][0]["citations"][0])
        for corrupted in (b"altered original", "original FDA source document"):
            with self.subTest(corrupted=corrupted):
                result = self.assess(14, [{**valid, "raw_bytes": corrupted}])
                self.assertEqual(len(result["rejectedEvidence"]), 1)
                self.assertIn("bytes digest mismatch", result["rejectedEvidence"][0]["reason"])
                self.assertTrue(all(not check["citations"] for check in result["checks"]))

    def test_source_independently_checked_before_a_passage_is_used(self):
        valid = receipt("The committee voted on the question.")
        invalid = [
            {**valid, "source_url": "https://www.fda.gov@fake.example/document.pdf"},
            {**valid, "text": valid["text"] + "Changed after capture."},
            {**valid, "raw_sha256": None},
            {**valid, "raw_sha256": "not-a-digest"},
            receipt(valid["excerpt"], trial="NCT00000002"),
            {**valid, "excerpt": "The committee voted unanimously."},
            {**valid, "cycle": "S-2"},
            receipt(valid["excerpt"], indication="Different condition"),
            {**valid, "captured_at": "2024-01-02T00:00:00Z"},
            {**valid, "captured_at": "2025-01-02T00:00:00"},
        ]
        result = self.assess(16, invalid)
        self.assertEqual(len(result["rejectedEvidence"]), len(invalid))
        self.assertEqual(result["evidenceStatus"], "INSUFFICIENT_EVIDENCE")
        self.assertTrue(all(not item["citations"] for item in result["checks"]))

    def test_regulatory_receipts_require_exact_application_and_cycle_in_source(self):
        valid = receipt("FDA granted priority review.")
        cases = [
            {**valid, "application": "NDA 99999"},
            {**valid, "cycle": "S-2"},
            {**valid, "identity_excerpt": valid["identity_excerpt"].replace("NDA 12345", "NDA 99999")},
            {**valid, "identity_excerpt": valid["identity_excerpt"].replace("Original 1", "S-2")},
            {**valid, "source_url": "https://www.fda.gov.evil.example/document.pdf"},
            {**valid, "source_url": "http://www.fda.gov/document.pdf"},
        ]
        for item in cases:
            with self.subTest(item=item):
                result = self.assess(14, [item])
                self.assertEqual(len(result["rejectedEvidence"]), 1)
                self.assertTrue(all(not check["citations"] for check in result["checks"]))
                self.assertEqual(result["fdaPrediction"]["outcome"], "ABSTAIN")

    def test_later_supplementary_capture_cannot_leak_into_frozen_snapshot(self):
        for level in (13, 14, 15, 16):
            with self.subTest(level=level):
                item = receipt("FDA priority review and subgroup analyses were described.")
                item["captured_at"] = "2025-01-03T00:00:00Z"
                result = self.assess(level, [item])
                self.assertEqual(len(result["rejectedEvidence"]), 1)
                self.assertIn("after the frozen registry snapshot", result["rejectedEvidence"][0]["reason"])
                # Level 13 independently cites the frozen registry population.
                # Reject only the late supplementary source; retain preexisting
                # registry citations rather than treating them as leakage.
                citations = [citation for check in result["checks"]
                             for citation in check["citations"]]
                self.assertTrue(all(citation.get("captured_at", citation.get("capturedAt"))
                                    != item["captured_at"] for citation in citations))
                self.assertEqual(result["fdaPrediction"]["outcome"], "ABSTAIN")

    def test_original_document_digest_is_retained_for_each_regulatory_citation(self):
        item = receipt("FDA granted priority review.")
        result = self.assess(14, [item])
        citation = result["checks"][0]["citations"][0]
        self.assertEqual(citation["raw_sha256"], item["raw_sha256"])
        self.assertEqual(citation["text_sha256"], item["text_sha256"])

    def test_missing_original_digest_never_becomes_checked_regulatory_evidence(self):
        for level in (14, 15, 16):
            with self.subTest(level=level):
                item = receipt("FDA inspection and advisory committee priority review.")
                item.pop("raw_sha256")
                result = self.assess(level, [item])
                self.assertEqual(len(result["rejectedEvidence"]), 1)
                self.assertTrue(all(not check["citations"] for check in result["checks"]))
                self.assertEqual(result["fdaPrediction"]["outcome"], "ABSTAIN")

    def test_exact_trial_protocol_can_support_subgroup_method(self):
        item = receipt("The subgroup analysis plan was prespecified.")
        item["source_url"] = f"https://cdn.clinicaltrials.gov/large-docs/01/{NCT}/Prot_001.pdf"
        self.assertEqual(self.assess(13, [item])["checks"][0]["state"], "SOURCE_PASSAGE_CHECKED")
        self.assertEqual(self.assess(14, [item])["rejectedEvidence"][0]["state"], "REJECTED_EVIDENCE")
        item["source_url"] = item["source_url"].replace("001.pdf", "002.pdf")
        self.assertEqual(self.assess(13, [item])["rejectedEvidence"][0]["state"], "REJECTED_EVIDENCE")

    def test_level13_reuses_original_protocol_from_runtime_snapshot(self):
        source = registry()
        document = json.loads(source["document_json"])
        identity = f"Trial {NCT} for Example condition."
        passage = "Demographic subgroups are described in the analysis plan."
        document["originalDocuments"] = [{
            "url": f"https://cdn.clinicaltrials.gov/large-docs/01/{NCT}/Prot_001.pdf",
            "verification": "ORIGINAL_LINKED_PDF_RETRIEVED", "extractedText": identity + "\n" + passage,
            "capturedAt": source["captured_at"], "registeredDocumentDate": "2025-01-01", "sha256": digest("pdf"),
            "pages": [{"page": 1, "text": identity}, {"page": 2, "text": passage}],
        }]
        source["document_json"] = json.dumps(document, separators=(",", ":"), sort_keys=True)
        source["input_sha256"] = digest(source["document_json"])
        citation = self.assess(13, source=source)["checks"][0]["citations"][0]
        self.assertEqual((citation["excerpt"], citation["locator"], citation["raw_sha256"]),
                         (passage, "PDF page 2", digest("pdf")))
        historical = self.assess(13, source=source, cutoff=date(2025, 1, 2))
        self.assertEqual(historical["checks"][0]["state"], "MISSING")

    def test_unknown_phase_and_early_phase_have_distinct_gaps(self):
        unknown = self.assess(15, source=registry("NA"))
        early = self.assess(15, source=registry("PHASE1"))
        self.assertEqual([x["id"] for x in unknown["checks"]], ["phase_first"])
        self.assertEqual({x["state"] for x in early["checks"]}, {"NOT_YET_EXPECTED"})
        self.assertEqual(early["fdaPrediction"]["outcome"], "ABSTAIN")

    def test_historical_cutoff_rejects_new_registry_and_withholds_regulatory_content(self):
        with self.assertRaisesRegex(ValueError, "cutoff"):
            self.assess(14, cutoff=date(2025, 1, 1))
        report = self.assess(14, [receipt("FDA approved the product after priority review.")], cutoff=date(2025, 1, 2))
        self.assertNotIn("approved the product", json.dumps(report))
        self.assertFalse(report["historicalAccuracyEligible"])
        self.assertEqual(report["evidenceStatus"], "INSUFFICIENT_EVIDENCE")

    def test_registry_digest_chronology_and_identity_are_required(self):
        source = registry()
        for broken in [
            {**source, "input_sha256": "0" * 64},
            {**source, "published_at": "2024-01-01"},
            {**source, "nct_id": "NCT00000002"},
            {**source, "source_url": "https://example.com/trial"},
        ]:
            with self.subTest(source=broken), self.assertRaises(ValueError):
                self.assess(13, source=broken)
