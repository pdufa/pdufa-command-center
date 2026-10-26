import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_phase3_sec_issuer_identity import (
    SEC_TICKERS_URL, CENSUS_COUNT, CENSUS_ISSUERS, MAX_SOURCE_BYTES,
    NoRedirect, saved_issuers, parse_sec_directory, audit_130, run,
)


def sec_source(saved):
    source = {
        str(i): {
            "cik_str": int(item["cik"]),
            "ticker": item["ticker"],
            "title": item["saved_company"] or "Source listed company",
        } for i, item in enumerate(saved)
    }
    # Official complete directory holds many issuers besides the 130.
    return json.dumps(source).encode("utf-8")


class Response:
    def __init__(self, raw):
        self.raw = raw
        self.status = 200
        self.headers = {"content-type": "application/json"}
    def geturl(self):
        return SEC_TICKERS_URL
    def read(self, maximum):
        return self.raw[:maximum]
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


class Open:
    def __init__(self, raw):
        self.raw = raw
    def open(self, request, timeout):
        assert request.full_url == SEC_TICKERS_URL
        assert request.get_method() == "GET"
        assert timeout == 20
        return Response(self.raw)


class Phase3SECIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = saved_issuers()
        cls.raw = sec_source(cls.saved)
        cls.directory = parse_sec_directory(cls.raw)

    def test_exact_130_saved_cik_ticker_mappings_cover_741_ncts(self):
        self.assertEqual(len(self.saved), CENSUS_ISSUERS)
        self.assertEqual(len({x["ticker"] for x in self.saved}), CENSUS_ISSUERS)
        self.assertTrue(all(len(r["cik"]) == 10 for r in self.saved))
        self.assertEqual(CENSUS_COUNT, 741)
        self.assertEqual(self.saved, saved_issuers())

    def test_complete_correct_sec_directory_verifies_130_cik_mappings_without_fda(self):
        sha = hashlib.sha256(self.raw).hexdigest()
        result = audit_130(self.saved, self.directory, sha, "2026-10-26T16:00:00Z")
        self.assertEqual(result["issuer_ticker_cik_matches"], 130)
        self.assertEqual(result["issuer_mapping_unresolved"], 0)
        self.assertEqual(len(result["issuer_audit_rows"]), 130)
        self.assertTrue(result["all_sec_ticker_cik_mappings_matched"])
        self.assertEqual(result["official_source_sha256"], sha)
        self.assertEqual(result["official_source_url"], SEC_TICKERS_URL)
        self.assertIsNone(result["qualified_pipeline_total"])
        self.assertIsNone(result["validated_approval_probabilities"])
        self.assertIsNone(result["verified_us_fda_pdufa_total"])
        self.assertTrue(all(r["qualified_pipeline"] is None
             and r["approval_probability"] is None
             and not r["verified_us_fda_pdufa"]
             and not r["development_rights_verified"]
             for r in result["issuer_audit_rows"]))

    def test_missing_cik_conflict_and_duplicate_ticker_remain_unverified(self):
        changed = {k: [dict(item) for item in arr] for k, arr in self.directory.items()}
        one, two, three = self.saved[:3]
        changed.pop(one["ticker"])
        changed[two["ticker"]][0]["sec_cik"] = "9999999999"
        changed[three["ticker"]].append(dict(changed[three["ticker"]][0]))
        result = audit_130(self.saved, changed, "b"*64, "2026-10-26T16:00:00Z")
        self.assertEqual(result["issuer_ticker_cik_matches"], 127)
        self.assertEqual(result["issuer_mapping_unresolved"], 3)
        self.assertFalse(result["all_sec_ticker_cik_mappings_matched"])
        rows = {r["ticker"]: r for r in result["issuer_audit_rows"]}
        self.assertEqual(rows[one["ticker"]]["identity_disposition"], "TICKER_NOT_FOUND_IN_SEC_DIRECTORY")
        self.assertEqual(rows[two["ticker"]]["identity_disposition"], "SAVED_CIK_DIFFERS_FROM_SEC")
        self.assertEqual(rows[three["ticker"]]["identity_disposition"], "AMBIGUOUS_OFFICIAL_TICKER_MAPPING")

    def test_forged_or_truncated_saved_issuer_population_is_rejected(self):
        for case in [self.saved[:-1], self.saved + self.saved[:1], [self.saved[0]]*130]:
            with self.assertRaises(ValueError):
                audit_130(case, self.directory, "a"*64, "2026-10-26T16:00:00Z")
        with self.assertRaises(ValueError):
            audit_130(self.saved, self.directory, "invalid", "2026-10-26T16:00:00Z")

    def test_wrong_official_json_duplicate_aliases_and_oversized_payload(self):
        for invalid in [b"", b"not json", b"<html>login</html>", b"x" * (MAX_SOURCE_BYTES + 1),
                        json.dumps({"0": {"ticker":"FAKE","cik_str":42,"title":"X"}}).encode()]:
            with self.assertRaises(ValueError):
                parse_sec_directory(invalid)
        altered = json.loads(self.raw)
        altered["0"]["cik_str"] = "not an integer"
        with self.assertRaises(ValueError):
            parse_sec_directory(json.dumps(altered).encode())

    def test_mocked_readonly_sec_get_produces_bounded_artifact_with_zero_pipeline_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "sec_cik_audit.json"
            with patch("audit_phase3_sec_issuer_identity.urllib.request.build_opener",
                       return_value=Open(self.raw)):
                status = run(file)
            self.assertEqual(status, 0)
            content = json.loads(file.read_text())
            self.assertEqual(content["issuer_ticker_cik_matches"], 130)
            self.assertIsNone(content["qualified_pipeline_total"])
            self.assertEqual(len(content["issuer_audit_rows"]),130)

    def test_sec_source_redirect_handler_refuses_unapproved_redirects(self):
        with self.assertRaisesRegex(ValueError,"redirected"):
            NoRedirect().redirect_request(None,None,302,"Redirect",{}, "https://untrusted.invalid/")

if __name__ == "__main__":
    unittest.main()
