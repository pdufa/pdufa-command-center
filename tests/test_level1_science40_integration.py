"""Level 1 integration safety tests: provenance intake must not certify SCIENCE.

Standard library only: safe to run on a small Windows PC without installing
the entire backend dependency set. Test data are synthetic and never written.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_python(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


provenance = load_python("scripts/stage4_evidence_provenance.py", "level1_provenance_gate")
science = load_python(
    "new-platform/backend/app/science_40_dossier.py", "level1_science40_gate"
)


class LevelOneIntegrationTests(unittest.TestCase):
    def test_valid_source_receipt_never_certifies_scientific_truth(self):
        receipt = {
            "nct": "NCT05507203",
            "source_type": "trial_registry",
            "url": "https://clinicaltrials.gov/study/NCT05507203",
            "document_date": "2026-10-01",
            "accessed_date": "2026-10-27",
            "evidence_excerpt": "Synthetic provenance example, not clinical evidence",
            "reviewer": "example-reviewer",
            "phase": "Phase 3",
        }
        observed = provenance.validate_evidence(receipt)
        self.assertTrue(observed["provenance_complete"])
        self.assertFalse(observed["scientifically_verified"])
        self.assertEqual(observed["verification_status"], "pending")

    def test_source_report_only_does_not_gain_science_40_readiness(self):
        # Synthetic, metadata-complete *report* with no independent signoff.
        # It must not be treated as a certified clinical conclusion.
        source = {
            "source_url": "https://example.org/synthetic-study",
            "source_kind": "ISSUER_DISCLOSURE",
            "published_at": "2026-05-30",
            "examined_at": "2026-10-27",
            "source_sha256": "a" * 64,
            "finding": "Synthetic claim, not an independently verified result",
            "interpretation": "SUPPORTS",
            "depth_level": 1,
            "review_status": "VERIFIED",
        }
        case = science.evaluate_science_40(
            exact_key="APPLICATION|TEST|SYNTHETIC",
            evidence={"S01": source},
            as_of="2026-10-27",
        )
        self.assertEqual(case["layers"], 8)
        self.assertEqual(case["totalAssessments"], 40)
        self.assertEqual(case["maximumInvestigationDepth"], 20)
        self.assertEqual(case["independentlyReviewedAssessments"], 0)
        self.assertEqual(case["readinessGrade"], "RELUCTANT")
        self.assertIsNone(case["approvalProbability"])
        self.assertIsNone(case["independentScientificConclusion"])
        self.assertIs(case["tradeAuthorized"], False)

    def test_unknown_source_key_not_silently_promoted(self):
        case = science.evaluate_science_40(
            exact_key="APPLICATION|TEST|SYNTHETIC",
            evidence={"provenance_only": {"nct": "NCT05507203"}},
            as_of="2026-10-27",
        )
        self.assertEqual(case["unmappedEvidenceKeys"], ["provenance_only"])
        self.assertEqual(case["submittedSourceObservations"], 0)
        self.assertEqual(case["independentlyReviewedAssessments"], 0)


if __name__ == "__main__":
    unittest.main()
