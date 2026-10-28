"""Regression tests for cross-trial ABTECT evidence contamination."""
import unittest

from scripts.trial_source_identity import (
    SourceIdentityMismatch,
    require_exact_trial_identity,
)


class TrialSourceIdentityTests(unittest.TestCase):
    def check(self, nct, protocol):
        return require_exact_trial_identity(
            expected_nct="NCT05535946",
            expected_protocol="ABX464-107",
            source_nct=nct,
            source_protocol=protocol,
        )

    def test_exact_maintenance_identity_accepted(self):
        self.assertIsNone(self.check("NCT05535946", "ABX464-107"))

    def test_induction_nct_rejected(self):
        with self.assertRaises(SourceIdentityMismatch):
            self.check("NCT05507216", "ABX464-107")

    def test_induction_protocol_rejected(self):
        with self.assertRaises(SourceIdentityMismatch):
            self.check("NCT05535946", "ABX464-106")

    def test_both_induction_identifiers_rejected(self):
        with self.assertRaises(SourceIdentityMismatch):
            self.check("NCT05507216", "ABX464-106")

    def test_missing_identifiers_rejected(self):
        for nct, protocol in [(None, "ABX464-107"), ("NCT05535946", None), (None, None)]:
            with self.subTest(nct=nct, protocol=protocol):
                with self.assertRaises(SourceIdentityMismatch):
                    self.check(nct, protocol)

    def test_ambiguous_or_embedded_identifiers_rejected(self):
        for nct, protocol in [
            ("NCT05535946 NCT05507216", "ABX464-107"),
            ("https://clinicaltrials.gov/study/NCT05535946", "ABX464-107"),
            ("NCT05535946", "ABX464-107 / ABX464-106"),
            ("nct05535946", "ABX464-107"),
        ]:
            with self.subTest(nct=nct, protocol=protocol):
                with self.assertRaises(SourceIdentityMismatch):
                    self.check(nct, protocol)


if __name__ == "__main__":
    unittest.main()
