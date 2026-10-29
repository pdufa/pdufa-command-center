"""Fail-closed authorization contract tests (not a login implementation)."""
import unittest
from research.prediction_v1_1_authorization import (
 ResearchPrincipal,authorize_research_read,authorize_research_review
)

class AuthorizationTests(unittest.TestCase):
 def test_reader_only_sees_granted_program(self):
  p=ResearchPrincipal("reader",frozenset({"evidence_reader"}),frozenset({"P1"}))
  self.assertTrue(authorize_research_read(p,"P1"))
  with self.assertRaises(PermissionError):
   authorize_research_read(p,"P2")
 def test_untrusted_identity_dict_rejected(self):
  with self.assertRaises(PermissionError):
   authorize_research_read({"principal":"reader","is_authenticated":True},"P1")
 def test_reviewer_cannot_review_own_submission(self):
  p=ResearchPrincipal("reviewer",frozenset({"evidence_reviewer"}),frozenset({"P1"}))
  with self.assertRaises(PermissionError):
   authorize_research_review(p,"P1","reviewer")
 def test_reviewer_requires_known_submitter(self):
  p=ResearchPrincipal("reviewer",frozenset({"evidence_reviewer"}),frozenset({"P1"}))
  with self.assertRaises(PermissionError):
   authorize_research_review(p,"P1","")
 def test_review_access_restricted_by_program(self):
  p=ResearchPrincipal("reviewer",frozenset({"evidence_reviewer"}),frozenset({"P1"}))
  with self.assertRaises(PermissionError):
   authorize_research_review(p,"P2","submitter")
  self.assertTrue(authorize_research_review(p,"P1","submitter"))

if __name__=="__main__":
 unittest.main()
