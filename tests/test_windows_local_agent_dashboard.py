"""Safety and status tests for the local-only PDUFA engineering dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import http.client
from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/windows_local_agent_dashboard.py"
SPEC = importlib.util.spec_from_file_location("pdufa_live_dashboard", SCRIPT)
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class DashboardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        for key, val in {
            "HOME": home, "LEDGER": home / "ledger.json",
            "HEARTBEAT": home / "heartbeat.json",
            "LOCK": home / "RUNNING.lock", "STOP": home / "STOP",
        }.items():
            swap = patch.object(D, key, val)
            swap.start()
            self.addCleanup(swap.stop)
        self.home = home

    def make_records(self):
        records = {
            str(i): {
                "stage": i, "name": "Engineering task " + str(i),
                "status": "PENDING", "attempts": 0,
                "draft_pr": None, "blocker": None,
            } for i in range(4, 21)
        }
        records["4"].update(status="DRAFT_PR_CREATED", attempts=1,
                            draft_pr=D.PR_PREFIX + "1121")
        records["5"].update(status="RUNNING", attempts=1)
        self.write(self.home / "ledger.json", {
            "mode": "CONTINUOUS_RUNNING",
            "tasks": records, "updated_utc": now_utc(),
        })
        self.write(self.home / "heartbeat.json", {
            "mode": "WORKING", "updated_utc": now_utc(), "level": 5,
        })
        (self.home / "RUNNING.lock").write_text('{"pid":1}', encoding="utf-8")

    @staticmethod
    def write(path, payload):
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_progress_counts_all_17_stages_without_scientific_signoff(self):
        self.make_records()
        data = D.snapshot()
        self.assertEqual(data["worker"]["state"], "LIVE")
        self.assertEqual(data["totals"], {
            "drafts": 1, "blocked": 0, "pending": 15,
            "running": 5, "total": 17,
        })
        self.assertEqual([x["level"] for x in data["stages"]], list(range(4, 21)))
        self.assertEqual(data["scientific_levels_verified"], 0)
        self.assertFalse(data["automatic_merge"])
        self.assertFalse(data["production_deploy"])
        self.assertEqual(data["stages"][0]["pr"], D.PR_PREFIX + "1121")

    def test_stale_heartbeat_never_claims_worker_is_live(self):
        self.make_records()
        self.write(self.home / "heartbeat.json", {
            "mode": "WORKING",
            "updated_utc": (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat(),
        })
        self.assertEqual(D.snapshot()["worker"]["state"], "NOT_VERIFIED")
        (self.home / "RUNNING.lock").unlink()
        self.assertNotEqual(D.snapshot()["worker"]["state"], "LIVE")

    def test_stop_request_does_not_claim_worker_stopped(self):
        self.make_records()
        (self.home / "STOP").write_text("owner requested", encoding="utf-8")
        self.assertEqual(D.snapshot()["worker"]["state"], "STOP_REQUESTED")

    def test_malformed_files_are_handled_without_exposing_data(self):
        (self.home / "ledger.json").write_text('{"tasks": 123}', encoding="utf-8")
        self.assertEqual(len(D.snapshot()["stages"]), 17)
        self.assertEqual(D.snapshot()["worker"]["state"], "NOT_VERIFIED")
        (self.home / "ledger.json").write_text("not json", encoding="utf-8")
        self.assertEqual(D.snapshot()["worker"]["state"], "NOT_INSTALLED")
        self.assertEqual(D.snapshot()["totals"]["drafts"], 0)

    def test_pr_urls_must_be_exact_expected_github_links(self):
        self.make_records()
        ledger = D._read_json(D.LEDGER)
        ledger["tasks"]["4"]["draft_pr"] = "javascript:alert(1)"
        self.write(D.LEDGER, ledger)
        data = D.snapshot()
        self.assertIsNone(data["stages"][0]["pr"])
        self.assertEqual(data["totals"]["drafts"], 0)
        ledger["tasks"]["4"]["draft_pr"] = D.PR_PREFIX + "123?query=1"
        self.write(D.LEDGER, ledger)
        self.assertIsNone(D.snapshot()["stages"][0]["pr"])

    def test_valid_statuses_only_and_blockers_are_sanitized(self):
        self.make_records()
        ledger = D._read_json(D.LEDGER)
        ledger["tasks"]["4"]["status"] = "FALSE_SCIENTIFIC_COMPLETE"
        ledger["tasks"]["4"]["blocker"] = "secrets:private"
        self.write(D.LEDGER, ledger)
        data = D.snapshot()
        self.assertEqual(data["stages"][0]["status"], "PENDING")
        self.assertIsNone(data["stages"][0]["blocker"])

    def start_server(self):
        token = "isolated-test-token"
        # Bind on an ephemeral local port so tests never conflict with a running
        # Windows dashboard on the user's real port.
        server = ThreadingHTTPServer((D.HOST, 0), D.make_handler(token, 0))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server.server_port, token

    @staticmethod
    def request(port, method, path, headers=None):
        connection = http.client.HTTPConnection(D.HOST, port, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.read().decode("utf-8")
        finally:
            connection.close()

    def test_http_status_endpoint_and_page_are_local_only(self):
        self.make_records()
        port, token = self.start_server()
        code, body = self.request(port, "GET", "/api/status")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["totals"]["running"], 5)
        code, html = self.request(port, "GET", "/")
        self.assertEqual(code, 200)
        self.assertIn("Live development", html)
        self.assertIn(token, html)
        self.assertIn("Stages 04", html)
        self.assertNotIn("password", html.lower())
        code, _ = self.request(port, "GET", "/", {"Host": "malicious.site"})
        self.assertEqual(code, 403)

    def test_stop_requires_a_local_token_and_approved_origin(self):
        self.make_records()
        port, token = self.start_server()
        code, _ = self.request(port, "POST", "/api/stop")
        self.assertEqual(code, 403)
        self.assertFalse(D.STOP.exists())
        code, _ = self.request(port, "POST", "/api/stop", {
            "X-PDUFA-Dashboard-Token": token,
            "Origin": "https://other.example",
        })
        self.assertEqual(code, 403)
        self.assertFalse(D.STOP.exists())
        code, _ = self.request(port, "POST", "/api/stop", {
            "X-PDUFA-Dashboard-Token": token,
            "Origin": "http://127.0.0.1:" + str(port),
        })
        self.assertEqual(code, 202)
        self.assertTrue(D.STOP.exists())
        self.assertEqual(D.snapshot()["worker"]["state"], "STOP_REQUESTED")


if __name__ == "__main__":
    unittest.main()
