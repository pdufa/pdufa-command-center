"""Isolated scientific assessment authentication and response tests."""
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from app.main import require_internal_key, get_scientific_assessment


class ScientificAssessmentAuthenticationTests(unittest.TestCase):
    def test_missing_configuration_is_unavailable(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as error:
                require_internal_key(None)
            self.assertEqual(error.exception.status_code, 503)

    def test_missing_or_wrong_key_is_rejected(self):
        with patch.dict(os.environ, {"PDUFA_INTERNAL_API_KEY": "unit-test-secret"}):
            for key in (None, "", "incorrect"):
                with self.subTest(key=key):
                    with self.assertRaises(HTTPException) as error:
                        require_internal_key(key)
                    self.assertEqual(error.exception.status_code, 401)

    def test_correct_key_is_accepted(self):
        with patch.dict(os.environ, {"PDUFA_INTERNAL_API_KEY": "unit-test-secret"}):
            self.assertIsNone(require_internal_key("unit-test-secret"))

    def test_authorized_payload_keeps_missing_evidence_unscored(self):
        with patch.dict(os.environ, {"PDUFA_INTERNAL_API_KEY": "unit-test-secret"}):
            require_internal_key("unit-test-secret")
            payload = get_scientific_assessment("TRIAL|NCT12345678")
            self.assertIsNone(payload["assessment"]["overall_score"])
            self.assertEqual(payload["sourceStatus"], "not_loaded")

    def test_invalid_identity_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            get_scientific_assessment("invalid")
        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
