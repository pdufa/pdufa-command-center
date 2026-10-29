import unittest
from research.prediction_v1_1_identity_boundary import principal_from_verified_claims,ResearchIdentityUnavailable

class IdentityBoundaryTests(unittest.TestCase):
 def test_claims_rejected_without_trusted_verifier(self):
  with self.assertRaises(ResearchIdentityUnavailable):
   principal_from_verified_claims({"subject":"alice","roles":{"evidence_reader"},"program_ids":{"P1"}})
 def test_untrusted_json_role_lists_rejected(self):
  with self.assertRaises(ResearchIdentityUnavailable):
   principal_from_verified_claims({"subject":"alice","roles":["evidence_reader"],"program_ids":["P1"]},verified_by_provider=True)
 def test_missing_verified_subject_rejected(self):
  with self.assertRaises(ResearchIdentityUnavailable):
   principal_from_verified_claims({"subject":"","roles":{"evidence_reader"},"program_ids":{"P1"}},verified_by_provider=True)

if __name__=="__main__":
 unittest.main()
