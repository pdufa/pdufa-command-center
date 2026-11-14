"""Levels 2–6 must fail closed without a valid Level 1 phase-first contract."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "app" / "scientific_levels_two_to_six.py"
spec = importlib.util.spec_from_file_location("levels_two_to_six_guard_test_module", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BASE = {
    "executionStatus": "INTAKE_ONLY",
    "scientificValidation": "NOT_VERIFIED",
    "fdaPrediction": "ABSTAIN",
    "assessmentCutoff": "2026-02-01",
    "phase": "PHASE2",
    "trialStatus": "RECRUITING",
}


class LevelsTwoToSixContractTests(unittest.TestCase):
    def test_valid_phase_two_is_unscored_and_phase_appropriate(self):
        result = module.assess_levels_two_to_six(BASE, trial_id="NCT12345678")
        self.assertEqual(set(result), {"2", "3", "4", "5", "6"})
        self.assertEqual(result["6"]["criteria"]["applicationDossier"], "NOT_YET_EXPECTED")
        for level in result.values():
            self.assertIsNone(level["score"])
            self.assertEqual(level["fdaPrediction"], "ABSTAIN")
            self.assertEqual(level["scientificValidation"], "NOT_VERIFIED")

    def test_unverified_phase_first_contract_blocks_all_levels(self):
        cases = [
            {"trialStatus": "UNKNOWN_STATUS"},
            {"phase": "PHASE9"},
            {"fdaPrediction": "APPROVAL"},
            {"scientificValidation": "VERIFIED"},
            {"executionStatus": "BLOCKED_UNVERIFIED_PHASE"},
        ]
        for mutation in cases:
            with self.subTest(mutation=mutation):
                result = module.assess_levels_two_to_six(
                    {**BASE, **mutation}, trial_id="NCT12345678"
                )
                for level in result.values():
                    self.assertEqual(level["status"], "BLOCKED_UNVERIFIED_PHASE")
                    self.assertFalse(level["reviewReadiness"]["complete"])
                    self.assertEqual(level["fdaPrediction"], "ABSTAIN")

    def test_invalid_nct_blocks_all_levels(self):
        result = module.assess_levels_two_to_six(BASE, trial_id="NCTwrong")
        self.assertTrue(all(level["status"] == "BLOCKED_UNVERIFIED_PHASE" for level in result.values()))


    def test_verification_cannot_precede_publication(self):
        evidence = {
            "2.protocol": {
                "nctId": "NCT12345678",
                "source": "https://clinicaltrials.gov/study/NCT12345678",
                "sourceDate": "2026-01-20",
                "reviewedAt": "2026-01-25",
                "sourceVerified": True,
                "sourceVerifiedAt": "2026-01-10",
                "sourceVerifiedBy": "reviewer-1",
                "sourceVerificationMethod": "DIRECT_DOCUMENT_REVIEW",
                "judgment": "SUPPORTS",
                "rationale": "Protocol source review",
                "reviewerId": "reviewer-1",
                "documentType": "PROTOCOL",
                "evidenceExcerpt": "Design section",
            }
        }
        result = module.assess_levels_two_to_six(
            BASE, trial_id="NCT12345678", evidence=evidence
        )
        self.assertEqual(result["2"]["criteria"]["protocol"], "REJECTED_EVIDENCE")
        self.assertEqual(result["2"]["rejectionReasons"]["protocol"], "INVALID_CHRONOLOGY")
        self.assertEqual(result["2"]["fdaPrediction"], "ABSTAIN")


    def test_verified_exact_trial_review_is_accepted_without_scoring(self):
        evidence = {
            "2.protocol": {
                "nctId": "NCT12345678",
                "source": "https://clinicaltrials.gov/study/NCT12345678",
                "sourceDate": "2026-01-10",
                "reviewedAt": "2026-01-15",
                "sourceVerified": True,
                "sourceVerifiedAt": "2026-01-15",
                "sourceVerifiedBy": "reviewer-1",
                "sourceVerificationMethod": "DIRECT_DOCUMENT_REVIEW",
                "judgment": "INCONCLUSIVE",
                "rationale": "Protocol requires further clinical review",
                "reviewerId": "reviewer-1",
                "documentType": "PROTOCOL",
                "evidenceExcerpt": "Design section",
            }
        }
        result = module.assess_levels_two_to_six(
            BASE, trial_id="NCT12345678", evidence=evidence
        )
        level = result["2"]
        self.assertEqual(level["criteria"]["protocol"], "INCONCLUSIVE")
        self.assertEqual(level["reviewedCount"], 1)
        self.assertEqual(level["status"], "PARTIAL")
        self.assertFalse(level["reviewReadiness"]["complete"])
        self.assertIsNone(level["score"])
        self.assertEqual(level["fdaPrediction"], "ABSTAIN")

    def test_wrong_trial_review_is_rejected(self):
        evidence = {
            "2.protocol": {
                "nctId": "NCT87654321",
                "source": "https://clinicaltrials.gov/study/NCT87654321",
                "sourceDate": "2026-01-10",
                "reviewedAt": "2026-01-15",
                "sourceVerified": True,
                "sourceVerifiedAt": "2026-01-15",
                "sourceVerifiedBy": "reviewer-1",
                "sourceVerificationMethod": "DIRECT_DOCUMENT_REVIEW",
                "judgment": "SUPPORTS",
                "rationale": "Wrong trial evidence",
                "reviewerId": "reviewer-1",
                "documentType": "PROTOCOL",
                "evidenceExcerpt": "Design section",
            }
        }
        result = module.assess_levels_two_to_six(
            BASE, trial_id="NCT12345678", evidence=evidence
        )
        self.assertEqual(result["2"]["criteria"]["protocol"], "REJECTED_EVIDENCE")
        self.assertEqual(result["2"]["rejectionReasons"]["protocol"], "INVALID_TRIAL_ID")
        self.assertEqual(result["2"]["reviewedCount"], 0)


    def test_levels_three_to_six_accept_exact_review_but_never_score(self):
        for number, criterion in (
            (3, "statisticalAnalysisPlan"),
            (4, "adverseEvents"),
            (5, "indicationDefinition"),
            (6, "regulatoryPathway"),
        ):
            with self.subTest(level=number):
                evidence = {
                    f"{number}.{criterion}": {
                        "nctId": "NCT12345678",
                        "source": "https://clinicaltrials.gov/study/NCT12345678",
                        "sourceDate": "2026-01-10",
                        "reviewedAt": "2026-01-15",
                        "sourceVerified": True,
                        "sourceVerifiedAt": "2026-01-15",
                        "sourceVerifiedBy": "reviewer-1",
                        "sourceVerificationMethod": "DIRECT_DOCUMENT_REVIEW",
                        "judgment": "INCONCLUSIVE",
                        "rationale": "Further independent assessment required",
                        "reviewerId": "reviewer-1",
                        "documentType": "REGISTRY_RECORD",
                        "evidenceExcerpt": "Study information",
                    }
                }
                result = module.assess_levels_two_to_six(
                    BASE, trial_id="NCT12345678", evidence=evidence
                )
                level = result[str(number)]
                self.assertEqual(level["criteria"][criterion], "INCONCLUSIVE")
                self.assertEqual(level["reviewedCount"], 1)
                self.assertFalse(level["reviewReadiness"]["complete"])
                self.assertIsNone(level["score"])
                self.assertEqual(level["fdaPrediction"], "ABSTAIN")

    def test_phase_two_late_regulatory_evidence_cannot_override_not_yet_expected(self):
        evidence = {
            "6.applicationDossier": {
                "nctId": "NCT12345678",
                "sourceVerified": True,
                "judgment": "SUPPORTS",
            }
        }
        result = module.assess_levels_two_to_six(
            BASE, trial_id="NCT12345678", evidence=evidence
        )
        self.assertEqual(result["6"]["criteria"]["applicationDossier"], "NOT_YET_EXPECTED")
        self.assertEqual(result["6"]["reviewedCount"], 0)
        self.assertIsNone(result["6"]["score"])


    def test_unpublished_claim_requires_exact_trial_and_search_provenance(self):
        evidence = {
            "3.primaryEndpointResults": {
                "availability": "NOT_PUBLIC",
                "nctId": "NCT12345678",
                "source": "https://clinicaltrials.gov/study/NCT12345678",
                "checkedAt": "2026-01-20",
                "searchRationale": "Checked public registry results and linked publications",
            }
        }
        result = module.assess_levels_two_to_six(
            BASE, trial_id="NCT12345678", evidence=evidence
        )
        self.assertEqual(result["3"]["criteria"]["primaryEndpointResults"], "UNPUBLISHED")
        self.assertIn("primaryEndpointResults", result["3"]["unpublishedCriteria"])
        self.assertEqual(result["3"]["reviewedCount"], 0)
        self.assertIsNone(result["3"]["score"])

        evidence["3.primaryEndpointResults"]["nctId"] = "NCT87654321"
        result = module.assess_levels_two_to_six(
            BASE, trial_id="NCT12345678", evidence=evidence
        )
        self.assertEqual(
            result["3"]["criteria"]["primaryEndpointResults"],
            "UNVERIFIED_UNPUBLISHED_CLAIM",
        )
        self.assertEqual(result["3"]["fdaPrediction"], "ABSTAIN")

    def test_post_cutoff_review_is_rejected(self):
        evidence = {
            "4.adverseEvents": {
                "nctId": "NCT12345678",
                "source": "https://clinicaltrials.gov/study/NCT12345678",
                "sourceDate": "2026-01-10",
                "reviewedAt": "2026-02-02",
                "sourceVerified": True,
                "sourceVerifiedAt": "2026-01-15",
                "sourceVerifiedBy": "reviewer-1",
                "sourceVerificationMethod": "DIRECT_DOCUMENT_REVIEW",
                "judgment": "SUPPORTS",
                "rationale": "Safety review",
                "reviewerId": "reviewer-1",
                "documentType": "REGISTRY_RECORD",
                "evidenceExcerpt": "Adverse events",
            }
        }
        result = module.assess_levels_two_to_six(
            BASE, trial_id="NCT12345678", evidence=evidence
        )
        self.assertEqual(result["4"]["criteria"]["adverseEvents"], "REJECTED_EVIDENCE")
        self.assertEqual(result["4"]["rejectionReasons"]["adverseEvents"], "INVALID_CHRONOLOGY")
        self.assertEqual(result["4"]["reviewedCount"], 0)


    def test_verification_after_review_is_rejected(self):
        evidence = {
            "5.indicationDefinition": {
                "nctId": "NCT12345678",
                "source": "https://clinicaltrials.gov/study/NCT12345678",
                "sourceDate": "2026-01-10",
                "reviewedAt": "2026-01-15",
                "sourceVerified": True,
                "sourceVerifiedAt": "2026-01-20",
                "sourceVerifiedBy": "reviewer-1",
                "sourceVerificationMethod": "DIRECT_DOCUMENT_REVIEW",
                "judgment": "SUPPORTS",
                "rationale": "Indication review",
                "reviewerId": "reviewer-1",
                "documentType": "REGISTRY_RECORD",
                "evidenceExcerpt": "Condition and population",
            }
        }
        result = module.assess_levels_two_to_six(
            BASE, trial_id="NCT12345678", evidence=evidence
        )
        self.assertEqual(result["5"]["criteria"]["indicationDefinition"], "REJECTED_EVIDENCE")
        self.assertEqual(result["5"]["rejectionReasons"]["indicationDefinition"], "INVALID_CHRONOLOGY")
        self.assertEqual(result["5"]["reviewedCount"], 0)
        self.assertEqual(result["5"]["fdaPrediction"], "ABSTAIN")


if __name__ == "__main__":
    unittest.main()
