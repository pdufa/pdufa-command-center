"use strict";
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_system_status_production import verify_phase3_census_production

SOURCE = (Path(__file__).resolve().parents[1]
          / "data" / "phase3_all_years_300m_10b_trials.csv").read_bytes()
PAGE = (
    "<html><h1>Phase 3 market-cap census</h1>"
    "<p>741 unique trial IDs are published here. "
    "It is not a complete qualified Pipeline.</p></html>"
).encode("utf-8")


class FakeResponse:
    def __init__(self, url: str, content: bytes, media: str, status=200):
        self.url = url
        self.content = content
        self.status = status
        self.headers = {"content-type": media}

    def geturl(self):
        return self.url

    def read(self, max_bytes):
        return self.content[:max_bytes]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def response_pair(*, page=PAGE, csv=SOURCE):
    base = "https://pdufa-new-dashboard.vercel.app"
    return [
        FakeResponse(base + "/installation-audit/phase3-census", page, "text/html"),
        FakeResponse(base + "/phase3-census-2026-10-26.csv", csv, "text/csv; charset=utf-8"),
    ]


class Phase3CensusProductionSmokeTests(unittest.TestCase):
    def test_exact_production_page_and_full_source_copy_pass_without_qualification(self):
        with patch("check_system_status_production.urllib.request.urlopen", side_effect=response_pair()) as fetch:
            verify_phase3_census_production()
            self.assertEqual(fetch.call_count, 2)

    def test_partial_or_fake_741_trials_cannot_pass(self):
        with patch("check_system_status_production.urllib.request.urlopen",
                   side_effect=response_pair(csv=SOURCE[:-140])):
            with self.assertRaisesRegex(ValueError, "differs from committed"):
                verify_phase3_census_production()

    def test_missing_qualified_pipeline_warning_cannot_pass(self):
        with patch("check_system_status_production.urllib.request.urlopen",
                   side_effect=response_pair(page=b"<h1>Phase 3 market-cap census</h1>")):
            with self.assertRaisesRegex(ValueError, "Incomplete public Phase 3"):
                verify_phase3_census_production()

    def test_redirect_to_login_is_not_production_route_verified(self):
        pair = response_pair()
        pair[0].url = "https://pdufa-new-dashboard.vercel.app/login"
        with patch("check_system_status_production.urllib.request.urlopen", side_effect=pair):
            with self.assertRaisesRegex(ValueError, "different page"):
                verify_phase3_census_production()

    def test_false_origin_is_rejected(self):
        pair = response_pair()
        pair[1].url = "https://attacker.example/phase3-census-2026-10-26.csv"
        with patch("check_system_status_production.urllib.request.urlopen", side_effect=pair):
            with self.assertRaisesRegex(ValueError, "redirect origin"):
                verify_phase3_census_production()

    def test_non_200_and_wrong_mime_are_not_certified(self):
        pair = response_pair()
        pair[0].status = 503
        with patch("check_system_status_production.urllib.request.urlopen", side_effect=pair):
            with self.assertRaisesRegex(ValueError, "non-200"):
                verify_phase3_census_production()
        pair = response_pair()
        pair[1].headers["content-type"] = "text/html"
        with patch("check_system_status_production.urllib.request.urlopen", side_effect=pair):
            with self.assertRaisesRegex(ValueError, "wrong content type"):
                verify_phase3_census_production()

    def test_oversized_public_csv_fails_closed(self):
        pair = response_pair(csv=b"x" * 200_000)
        with patch("check_system_status_production.urllib.request.urlopen", side_effect=pair):
            with self.assertRaisesRegex(ValueError, "bounded read"):
                verify_phase3_census_production()


if __name__ == "__main__":
    unittest.main()
