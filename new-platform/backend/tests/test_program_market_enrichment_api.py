"""Endpoint-level market enrichment checks without live credentials or a database."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from app.main import read_program_market_enrichment, require_internal_key, require_storage


class _Session:
    def __init__(self, identity):
        self.identity = identity
        self.requested_id = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get(self, model, program_id):
        self.requested_id = program_id
        return self.identity


class MarketEnrichmentEndpointTests(unittest.TestCase):
    def test_unconfigured_or_wrong_internal_key_is_rejected(self):
        with patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only-key"}):
            for supplied in (None, "wrong-key"):
                with self.assertRaises(HTTPException) as raised:
                    require_internal_key(supplied)
                self.assertEqual(raised.exception.status_code, 401)
            require_internal_key("test-only-key")
        with patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": ""}):
            with self.assertRaises(HTTPException) as raised:
                require_internal_key("test-only-key")
            self.assertEqual(raised.exception.status_code, 503)

    def test_review_service_rejects_ephemeral_storage(self):
        with patch("app.main.REQUIRE_POSTGRES", True), patch(
            "app.main.DATABASE_URL", "sqlite:///./checklists_dev.sqlite3"
        ), patch("app.main._DB_STATE", {"available": False, "reason": "STARTING"}):
            with self.assertRaises(HTTPException) as raised:
                require_storage()
        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("PostgreSQL", raised.exception.detail)

    def test_exact_registry_mapping(self):
        identity = SimpleNamespace(ticker="ABC", source_key="EXACT|NCT01234567")
        session = _Session(identity)
        with patch("app.main.Session", return_value=session), patch(
            "app.program_market_enrichment.enrich_program_market",
            return_value={"programId": "PDUFA-000165", "exactKey": identity.source_key, "status": "OK"},
        ) as enrich:
            response = read_program_market_enrichment("PDUFA-000165", "1M")
        self.assertEqual(session.requested_id, 165)
        enrich.assert_called_once_with("PDUFA-000165", identity.source_key, "ABC", "1M")
        self.assertEqual(response["exactKey"], identity.source_key)

    def test_unknown_program_never_calls_alpaca(self):
        with patch("app.main.Session", return_value=_Session(None)), patch(
            "app.program_market_enrichment.enrich_program_market"
        ) as enrich:
            with self.assertRaises(HTTPException) as raised:
                read_program_market_enrichment("PDUFA-000165", "1Y")
        self.assertEqual(raised.exception.status_code, 404)
        enrich.assert_not_called()

    def test_invalid_id_and_range_never_access_storage(self):
        with patch("app.main.Session") as session:
            for program_id, range_label in [("BAD-000165", "1Y"), ("PDUFA-000165", "2Y")]:
                with self.assertRaises(HTTPException) as raised:
                    read_program_market_enrichment(program_id, range_label)
                self.assertEqual(raised.exception.status_code, 422)
        session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
