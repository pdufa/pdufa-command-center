"""Read-only evidence API authorization checks, no production router mount."""
import unittest
import tempfile
from pathlib import Path
from research.prediction_v1_1_storage_adapter import open_research_evidence_store
from types import SimpleNamespace
from research.prediction_v1_1_authorization import ResearchPrincipal
from fastapi import HTTPException
from research.prediction_v1_1_readonly_router import (
 read_evidence_status, _unconfigured_database, _unconfigured_identity, _unconfigured_catalog
)

class ResearchEvidenceRouterTests(unittest.TestCase):
 def test_authorized_read_uses_integrity_checked_service(self):
  with tempfile.TemporaryDirectory() as root:
   conn=open_research_evidence_store(Path(root)/"test.sqlite3")
   principal=ResearchPrincipal("reader",frozenset({"evidence_reader"}),frozenset({"P1"}))
   result=read_evidence_status("P1",db=conn,catalog={"fields":[]},principal=principal)
   self.assertEqual(result["decision"],"ABSTAIN")
   self.assertEqual(result["integrity"],"CHECKED_LOCAL_CHAIN_ONLY")
   conn.close()
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
 def test_untrusted_object_cannot_read_even_with_matching_claims(self):
  principal=SimpleNamespace(is_authenticated=True,roles=("evidence_reader",),program_ids=("P1",))
  with self.assertRaises(HTTPException) as ctx:
   read_evidence_status("P1",db=object(),catalog={},principal=principal)
  self.assertEqual(ctx.exception.status_code,403)
 def test_cross_program_access_is_denied(self):
  principal=ResearchPrincipal("reader",frozenset({"evidence_reader"}),frozenset({"P2"}))
  with self.assertRaises(HTTPException) as ctx:
   read_evidence_status("P1",db=object(),catalog={},principal=principal)
  self.assertEqual(ctx.exception.status_code,403)

if __name__=="__main__":
 unittest.main()
