"""Fail-closed RAAS nightly registry delta tests: exact source and immutable history."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "raas_registry_evidence_change_audit",
    ROOT / "scripts/raas_registry_evidence_change_audit.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
T0 = "2026-11-03T12:00:00+00:00"
T1 = "2026-11-04T12:00:00+00:00"
T2 = "2026-11-05T12:00:00+00:00"
AUDIT1 = "2026-11-04T12:03:00+00:00"
AUDIT2 = "2026-11-05T12:03:00+00:00"


def trial(i: int) -> dict:
    nct = "NCT" + str(i + 10000000)
    return {
        "nctId": nct, "ticker": "TEST", "sourceUrl":
        "https://clinicaltrials.gov/study/" + nct,
        "sourceHash": "a" * 64, "retrievedAt": T0,
        "registryLastUpdated": "2026-11-01",
        "resultsFirstPosted": None, "registryStatus": "RECRUITING",
        "registeredPhases": ["PHASE3"],
        "registeredConditions": ["Disease"],
        "registeredInterventions": ["Test drug"],
        "registeredDesign": {"allocation": "RANDOMIZED"},
        "primaryDefinitions": [{"measure": "Endpoint", "timeFrame": "Week 12"}],
        "postedResults": False, "postedPrimaryOutcomeCount": 0,
        "postedOtherOutcomeCount": 0, "primaryResults": [],
        "seriousAdverseEventTermCount": 0, "seriousEventDetails": [],
        "evidenceState": "PROTOCOL_ONLY",
    }


def snapshot(time: str = T0) -> dict:
    records = [trial(i) for i in range(762)]
    return {
        "schemaVersion": 1, "scope": "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
        "sourceAsOf": time,
        "summary": {"researchNcts": 762, "registryRecords": 762,
                    "postedRegistryResults": 0,
                    "approvedOverallRaasScores": 0},
        "records": records,
    }


def refresh(index: dict, time: str = T1) -> dict:
    out = copy.deepcopy(index)
    out["sourceAsOf"] = time
    for x in out["records"]:
        x["retrievedAt"] = time
    return out


def receipt(index: dict, failures: tuple[str, ...] = ()) -> dict:
    return {
        "schemaVersion": 1, "scope": "RAAS_CT_GOV_LIVE_EVIDENCE",
        "latestAttemptAt": index["sourceAsOf"],
        "summary": {
            "attemptedThisRun": 762,
            "retrievedThisRun": 762 - len(failures),
            "failedThisRun": len(failures),
        },
        "errors": [{"nctId": x, "reason": "SOURCE_FETCH_FAILED"} for x in failures],
    }


def with_posted_results(index: dict, i: int = 0) -> dict:
    out = copy.deepcopy(index)
    r = out["records"][i]
    r.update({
        "sourceHash": "b" * 64, "postedResults": True,
        "evidenceState": "POSTED_RESULTS_UNGRADED",
        "resultsFirstPosted": "2026-11-04",
        "postedPrimaryOutcomeCount": 1,
        "primaryResults": [{
            "title": "Primary endpoint",
            "comparisons": [{"groupIds": ["OG000", "OG001"],
                             "paramValue": "-10", "pValue": "0.04"}],
        }],
        "seriousAdverseEventTermCount": 1,
        "seriousEventDetails": [{
            "term": "Infection", "groups": [
                {"groupId": "EG000", "numAffected": 3, "numAtRisk": 20}
            ]
        }],
    })
    out["summary"]["postedRegistryResults"] = 1
    return out


class ChangeAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old = snapshot()
        self.new = refresh(self.old)
        self.history = mod.empty_history()

    def audit(self, after=None, history=None, failures=(), recorded_at=AUDIT1,
              before=None):
        after = after if after is not None else self.new
        return mod.reconcile(
            before if before is not None else self.old,
            after, history if history is not None else self.history,
            receipt(after, failures), recorded_at
        )

    def test_first_completed_scan_with_unchanged_sources_never_invents_events(self):
        ledger, status = self.audit()
        self.assertEqual(ledger["events"], [])
        self.assertEqual(status["trackedResearchNcts"], 762)
        self.assertEqual(status["auditState"], "COMPLETE")
        self.assertEqual(status["changedNctsThisAudit"], 0)
        self.assertEqual(status["approvedRaasScoreUpdates"], 0)
        self.assertEqual(status["calibratedFdaForecastUpdates"], 0)

    def test_first_results_posting_is_ungraded_and_time_observed_not_backdated(self):
        new = with_posted_results(self.new)
        ledger, status = self.audit(after=new)
        self.assertEqual(status["changedNctsThisAudit"], 1)
        self.assertEqual(status["reviewNeededNctsThisAudit"], 1)
        self.assertEqual(status["firstPostedRegistryResultsThisAudit"], 1)
        self.assertEqual(status["changedPrimaryResultsThisAudit"], 1)
        self.assertEqual(status["changedSafetyEvidenceThisAudit"], 1)
        self.assertEqual(status["newEvents"], 1)
        ev = ledger["events"][0]
        self.assertEqual(ev["nctId"], new["records"][0]["nctId"])
        self.assertEqual(ev["ticker"], "TEST")
        self.assertEqual(ev["observedAt"], AUDIT1)
        self.assertIn("RESULTS_FIRST_POSTED", ev["changeCategories"])
        self.assertEqual(ev["approvedRaasScore"], None)
        self.assertEqual(ev["calibratedFdaProbability"], None)
        self.assertEqual(ev["after"]["postedResults"], True)
        self.assertEqual(ev["before"]["postedResults"], False)
        self.assertEqual(ev["after"]["seriousAdverseEventTermCount"], 1)
        self.assertIn("post-1-5", ev["candidateResearchMetricIds"])
        self.assertIn("public Phase 3 readout are not verified", ev["note"])

    def test_source_hash_only_and_admin_updates_are_not_clinical_evidence(self):
        new = copy.deepcopy(self.new)
        new["records"][0]["sourceHash"] = "b" * 64
        ledger, status = self.audit(after=new)
        self.assertEqual(status["reviewNeededNctsThisAudit"], 0)
        self.assertEqual(ledger["events"][0]["changeCategories"],
                         ["OTHER_OFFICIAL_SOURCE_PACKET_UPDATE"])
        self.assertEqual(ledger["events"][0]["candidateResearchMetricIds"], [])
        new["records"][0]["registryStatus"] = "COMPLETED"
        ledger2, status2 = self.audit(after=new)
        self.assertEqual(status2["reviewNeededNctsThisAudit"], 0)
        self.assertEqual(ledger2["events"][0]["changeCategories"],
                         ["TRIAL_STATUS_CHANGED"])

    def test_protocol_change_is_separate_from_clinical_results(self):
        new = copy.deepcopy(self.new)
        new["records"][0]["sourceHash"] = "b" * 64
        new["records"][0]["primaryDefinitions"] = [{"measure": "Revised",
                                                     "timeFrame": "Week 24"}]
        ledger, status = self.audit(after=new)
        self.assertEqual(status["changedPrimaryProtocolOrDesignThisAudit"], 1)
        self.assertEqual(status["changedPrimaryResultsThisAudit"], 0)
        self.assertEqual(status["reviewNeededNctsThisAudit"], 1)
        self.assertEqual(ledger["events"][0]["candidateResearchMetricIds"],
                         ["pre-1-2"])

    def test_history_append_preserves_first_event_and_subsequent_revision(self):
        post = with_posted_results(self.new)
        first, _ = self.audit(after=post)
        nxt = refresh(post, T2)
        nxt["records"][0]["sourceHash"] = "c" * 64
        nxt["records"][0]["primaryResults"][0]["comparisons"][0]["pValue"] = "0.03"
        updated, status = self.audit(before=post, after=nxt,
                                     history=first, recorded_at=AUDIT2)
        self.assertEqual(len(updated["events"]), 2)
        self.assertEqual(updated["events"][0], first["events"][0])
        self.assertEqual(status["totalRetainedHistoricalEvents"], 2)
        self.assertEqual(status["changedPrimaryResultsThisAudit"], 1)
        self.assertNotIn("RESULTS_FIRST_POSTED",
                         updated["events"][1]["changeCategories"])

    def test_missing_or_reassigned_nct_and_counterfeit_results_fail_closed(self):
        for change in ("remove", "ticker", "source", "grade", "silently_edit"):
            with self.subTest(change=change):
                now = copy.deepcopy(self.new)
                if change == "remove":
                    now["records"].pop(0)
                elif change == "ticker":
                    now["records"][0]["ticker"] = "OTHER"
                elif change == "source":
                    now["records"][0]["sourceUrl"] = "https://example.com"
                elif change == "grade":
                    now["summary"]["approvedOverallRaasScores"] = 1
                else:
                    now["records"][0]["primaryDefinitions"][0]["measure"] = "Changed"
                with self.assertRaisesRegex(ValueError, "RAAS_CHANGE_AUDIT_"):
                    self.audit(after=now)

    def test_failed_fetch_is_not_recast_as_no_change_or_source_update(self):
        nct = self.new["records"][0]["nctId"]
        ledger, status = self.audit(failures=(nct,))
        self.assertEqual(ledger["events"], [])
        self.assertEqual(status["auditState"], "COMPLETED_WITH_SOURCE_ERRORS")
        self.assertEqual(status["sourceFetchFailed"], 1)
        self.assertEqual(status["sourceFetchFailureNcts"], [nct])
        new = copy.deepcopy(self.new)
        new["records"][0]["sourceHash"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "FAILED_FETCH_WITH_NEW_HASH"):
            self.audit(after=new, failures=(nct,))

    def test_wrong_dates_and_corrupted_previous_event_are_blocked(self):
        with self.assertRaisesRegex(ValueError, "STALE_OR_SAME_SCAN"):
            self.audit(after=refresh(self.old, T0))
        first, _ = self.audit(after=with_posted_results(self.new))
        bad = copy.deepcopy(first)
        bad["events"][0]["approvedRaasScore"] = 75
        with self.assertRaisesRegex(ValueError, "HISTORY_EVENT_INVALID"):
            self.audit(history=bad)
        with self.assertRaisesRegex(ValueError, "RECORDED_BEFORE_SOURCE"):
            self.audit(recorded_at=T0)

    def test_incomplete_results_in_protocol_only_record_never_transfers(self):
        now = copy.deepcopy(self.new)
        now["records"][0]["primaryResults"] = [{"title": "Injected result"}]
        now["records"][0]["sourceHash"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "ROW_IDENTITY_OR_RESULTS_INVALID"):
            self.audit(after=now)


if __name__ == "__main__":
    unittest.main()
