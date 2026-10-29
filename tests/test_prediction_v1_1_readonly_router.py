"""Read-only evidence API authorization checks, no production router mount."""
import unittest
from types import SimpleNamespace
from fastapi import HTTPException
from research.prediction_v1_1_readonly_router import (
 read_evidence_status, _unconfigured_database, _unconfigured_identity, _unconfigured_catalog
)

class ResearchEvidenceRouterTests(unittest.TestCase):
 def test_unconfigured_dependencies_fail_closed(self):
  for dependency in (_unconfigured_database,_unconfigured_identity,_unconfigured_catalog):
   with self.assertRaises(HTTPException) as ctx:
    dependency()
   self.assertEqual(ctx.exception.status_code,503)
 def test_anonymous_is_denied(self):
  with self.assertRaises(HTTPException) as ctx:
   read_evidence_status("P1",db=object(),catalog={},principal=SimpleNamespace(is_authenticated=False))
  self.assertEqual(ctx.exception.status_code,403)
 def test_wrong_role_is_denied(self):
  principal=SimpleNamespace(is_authenticated=True,roles=("viewer",),program_ids=("P1",))
  with self.assertRaises(HTTPException) as ctx:
   read_evidence_status("P1",db=object(),catalog={},principal=principal)
  self.assertEqual(ctx.exception.status_code,403)
 def test_cross_program_access_is_denied(self):
  principal=SimpleNamespace(is_authenticated=True,roles=("evidence_reader",),program_ids=("P2",))
  with self.assertRaises(HTTPException) as ctx:
   read_evidence_status("P1",db=object(),catalog={},principal=principal)
  self.assertEqual(ctx.exception.status_code,403)

if __name__=="__main__":
 unittest.main()
