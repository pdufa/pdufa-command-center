"""Bounded recovery and error transparency in the supported app.

The removed Streamlit importlib/file-watcher retry wrapper is no longer a
production boundary. Its safety intent now belongs to authenticated GET retry
and source startup opt-in tests on Next.js and FastAPI.
"""
import unittest
from supported_dashboard_checks import run_frontend_contract, run_backend_contract


class StartupImportRaceTests(unittest.TestCase):
    def test_backend_startup_source_work_requires_explicit_opt_in(self):
        self.assertGreater(run_backend_contract("test_startup_source_opt_in.py"), 0)

    def test_read_only_recovery_is_bounded_to_one_retry(self):
        self.assertGreater(run_frontend_contract("read-only-warm-retry.test.cjs"), 0)

    def test_permanent_auth_and_conflict_failures_do_not_retry(self):
        self.assertGreater(run_frontend_contract("read-only-warm-retry.test.cjs"), 0)

    def test_failed_sources_do_not_fall_back_to_another_research_backend(self):
        self.assertGreater(run_frontend_contract("research-only-backend.test.cjs"), 0)

    def test_missing_evidence_cannot_become_qualified_or_trade_ready(self):
        self.assertGreater(run_frontend_contract("research-readiness.test.cjs"), 0)

    def test_recovery_cannot_send_writes_or_ignore_authentication(self):
        self.assertGreater(run_frontend_contract("read-only-warm-retry.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("research-only-backend.test.cjs"), 0)


if __name__ == "__main__":
    unittest.main()
