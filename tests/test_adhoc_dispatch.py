"""Exercise ad hoc PIN authorization and GitHub dispatch without using real secrets/network."""
from supported_dashboard_checks import run_frontend_contract
import json
import inspect
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import nightly_scan_dashboard as mod


class DispatchAdhocTests(unittest.TestCase):
    def test_scan_navigation_and_history_remain_accessible_without_dispatch(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('scans-navigation-contract.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('scans-new-results.test.cjs'), 0)

    def test_dispatch_uses_auth_and_exact_workflow_payload(self):
        response = MagicMock()
        response.status = 204
        handle = MagicMock()
        handle.__enter__.return_value = response
        with patch.object(mod.urllib.request, "urlopen", return_value=handle) as urlopen:
            mod.dispatch_adhoc_error_check("synthetic-test-token")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertTrue(req.full_url.endswith("/actions/workflows/pdufa-adhoc-error-check.yml/dispatches"))
        self.assertEqual(req.get_header("Authorization"), "Bearer synthetic-test-token")
        self.assertEqual(json.loads(req.data), {"ref": "main"})

    def test_no_token_never_contacts_github(self):
        with patch.object(mod.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(ValueError):
                mod.dispatch_adhoc_error_check("")
        urlopen.assert_not_called()

    def test_nonaccepted_response_is_error(self):
        response = MagicMock()
        response.status = 202
        handle = MagicMock()
        handle.__enter__.return_value = response
        with patch.object(mod.urllib.request, "urlopen", return_value=handle):
            with self.assertRaises(RuntimeError):
                mod.dispatch_adhoc_error_check("synthetic-test-token")

    def render(self, pin_input, clicked=True, configured=True):
        fake = MagicMock()
        fake.markdown = MagicMock()
        fake.caption = MagicMock()
        fake.warning = MagicMock()
        fake.link_button = MagicMock()
        fake.text_input.return_value = pin_input
        fake.button.return_value = clicked
        fake.success = MagicMock()
        last = MagicMock(return_value={})
        secrets = {"PDUFA_GITHUB_TOKEN": "synthetic-test-token" if configured else "",
                   "PDUFA_SCAN_CONTROL_PIN": "synthetic-test-pin" if configured else ""}
        with patch.object(mod, "dashboard_secret", side_effect=secrets.get), \
             patch.object(mod, "st", fake), \
             patch.object(mod, "latest_adhoc_check_run", last), \
             patch.object(mod, "dispatch_adhoc_error_check") as dispatch:
            mod.render_adhoc_error_check_controls()
            return fake, dispatch

    def test_matching_pin_click_dispatches_once(self):
        ui, dispatch = self.render("synthetic-test-pin")
        dispatch.assert_called_once_with("synthetic-test-token")
        self.assertFalse(ui.button.call_args.kwargs["disabled"])
        ui.success.assert_called_once()

    def test_wrong_pin_cannot_dispatch_even_if_client_click_flag_is_true(self):
        ui, dispatch = self.render("invalid-pin", clicked=True)
        dispatch.assert_not_called()
        self.assertTrue(ui.button.call_args.kwargs["disabled"])

    def test_empty_pin_cannot_dispatch(self):
        ui, dispatch = self.render("", clicked=True)
        dispatch.assert_not_called()
        self.assertTrue(ui.button.call_args.kwargs["disabled"])

    def test_missing_server_secrets_offers_manual_github_fallback_only(self):
        ui, dispatch = self.render("synthetic-test-pin", configured=False)
        dispatch.assert_not_called()
        ui.button.assert_not_called()
        self.assertTrue(any("RUN AD HOC CHECK IN GITHUB" in call.args[0]
                            for call in ui.link_button.call_args_list))


if __name__ == "__main__":
    unittest.main()
