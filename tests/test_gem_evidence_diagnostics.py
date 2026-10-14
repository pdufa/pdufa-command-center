"""Regression guards for GEM gap labels and research-only rechecks."""
from __future__ import annotations

import unittest
from datetime import date

from gem_eligibility_diagnostics import GROUPS, classify, group_counts, report_rows
from scripts.gem_phase3_exact_recheck import audit_events
from scripts.gem_two_close_recheck import ATTESTED, recheck_records


def master(phase=False, finance=False, eligible=False, event="AAA|DRUG_20261201"):
    return {
        "Ticker": "AAA", "Drug": "Drug", "Exact Program / Event": event,
        "Phase 3 Verified": ("PASS — VERIFIED RESULTS RELEASE" if phase else
                             "PENDING — VERIFIED READOUT MISSING"),
        "Second Financing Closed": ("PASS — TWO POST-READOUT CLOSES" if finance else
                                    "PENDING — SECOND CLOSE UNVERIFIED"),
        "_eligible": eligible,
    }


class FakeSECVerifier:
    as_of = date(2026, 10, 14)

    def __init__(self, states=("VERIFIED", "VERIFIED")):
        self.states = list(states)
        self.calls = []

    def financing(self, item):
        self.calls.append(item)
        state = self.states[len(self.calls) - 1]
        return {"verification_status": state,
                "source_sha256": "hash" if state == "VERIFIED" else ""}


class GEMEvidenceTests(unittest.TestCase):
    def test_all_four_groups_are_derived_only_from_original_benchmarks(self):
        rows = [master(True, True, True), master(True), master(False, True), master()]
        details = report_rows(rows, sec_current=False, feed_current=False)
        self.assertEqual([r["Verification group"] for r in details], list(GROUPS))
        self.assertEqual(group_counts(details), dict.fromkeys(GROUPS, 1))
        self.assertEqual(sum(r["GEM eligible — saved"] for r in details), 1)
        self.assertIn("Current SEC recheck unavailable", details[0]["Missing / recheck needed"])

    def test_stale_source_never_confers_or_revokes_historical_eligibility(self):
        self.assertEqual(classify(master(True, True, True), sec_current=False)
                         ["Verification group"], GROUPS[0])
        self.assertFalse(classify(master(True, False, False), sec_current=True)
                         ["GEM eligible — saved"])
        inconsistent = classify(master(True, True, False))
        self.assertNotEqual(inconsistent["Verification group"], GROUPS[0])
        self.assertIn("conflicts", inconsistent["Missing / recheck needed"])

    def test_duplicate_financing_source_evidence_never_cross_attaches(self):
        row = master()
        matching = {"event_key": row["Exact Program / Event"], "recheck_status": "TRANSACTIONS_RECHECKED_REVIEW"}
        details = report_rows([row], rechecks=[matching, matching])
        self.assertEqual(details[0]["Latest SEC transaction audit"], "NOT RUN / NO MATCH")

    def test_phase3_registry_posting_remains_discovery_only(self):
        events = [{"event_key": "AAA|DRUG_20261201", "ticker": "AAA", "drug": "Drug",
                   "nct_id": "NCT01234567", "phase3_status": "UNVERIFIED"}]
        study = {"hasResults": True, "protocolSection": {
            "identificationModule": {"nctId": "NCT01234567"},
            "statusModule": {"resultsFirstPostDateStruct": {"date": "2026-08-01"}},
        }}
        out = audit_events(events, fetch_study=lambda _: study)
        self.assertEqual(out[0]["source_recheck_status"], "POSTED_RESULTS_DISCOVERY_ONLY")
        self.assertEqual(out[0]["gem_phase3_benchmark_upgraded"], "NO")

    def test_phase3_registry_wrong_trial_id_is_not_pass(self):
        events = [{"event_key": "AAA|DRUG_20261201", "ticker": "AAA",
                   "nct_id": "NCT01234567"}]
        out = audit_events(events, fetch_study=lambda _: {
            "hasResults": True,
            "protocolSection": {"identificationModule": {"nctId": "NCT99999999"}},
        })
        self.assertEqual(out[0]["source_recheck_status"], "CLINICAL_REGISTRY_PARTIAL_OR_BLOCKED")
        self.assertEqual(out[0]["nct_checked"], 0)

    def test_two_sec_documents_do_not_override_unverified_phase3(self):
        data = [{"event_key": "AAA|DRUG_20261201", "ticker": "AAA",
                 "phase3_status": "UNVERIFIED", "phase3_date": "",
                 "nct_id": "NCT01234567", "trial_evidence_url": ""}]
        financing = [{
            "event_key": "AAA|DRUG_20261201",
            "second_financing_audit_status": ATTESTED,
            "first_financing_date": "2026-05-01",
            "second_financing_date": "2026-08-01",
            "first_financing_source": "https://www.sec.gov/one",
            "second_financing_source": "https://www.sec.gov/two",
        }]
        verifier = FakeSECVerifier()
        out = recheck_records(verifier, data, financing)
        self.assertEqual(len(out), 1)
        self.assertEqual(len(verifier.calls), 2)
        self.assertTrue(all(x["_recheck_exact_sec_url"] is True for x in verifier.calls))
        self.assertEqual(out[0]["recheck_status"], "PHASE3_DATE_NOT_VERIFIED")
        self.assertEqual(out[0]["gem_entry_authorized"], "NO")

    def test_sec_403_keeps_recheck_blocked(self):
        event = [{"event_key": "AAA|DRUG_20261201", "ticker": "AAA",
                  "phase3_status": "RESULTS_VERIFIED", "phase3_date": "2026-04-01",
                  "nct_id": "NCT01234567", "trial_evidence_url": "https://issuer.example/"}]
        financing = [{"event_key": "AAA|DRUG_20261201",
                      "second_financing_audit_status": ATTESTED,
                      "first_financing_date": "2026-05-01",
                      "second_financing_date": "2026-08-01",
                      "first_financing_source": "https://www.sec.gov/one",
                      "second_financing_source": "https://www.sec.gov/two"}]
        out = recheck_records(FakeSECVerifier(("TECHNICAL_FAILURE", "TECHNICAL_FAILURE")),
                              event, financing)
        self.assertEqual(out[0]["recheck_status"], "SEC_SOURCE_BLOCKED_OR_FAILED")
        self.assertEqual(out[0]["gem_entry_authorized"], "NO")


if __name__ == "__main__":
    unittest.main()
