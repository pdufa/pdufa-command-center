"""Offline safety checks for source-verification delta publishing."""
import unittest

from scripts.source_audit_delta import compare


def report(run, checked, unresolved, scope="SCOPE_A"):
    return {"latest_run_id": str(run), "source_checked_at_utc": checked,
            "required_findings_due": 984,
            "required_findings_unresolved": unresolved,
            "verification_scope_sha256": scope, "status": "PARTIAL",
            "execution_status": "COMPLETE", "manifest_rejections": {}}


def queue(*names):
    return {(n, "FDA", "PDUFA_TARGET"): {
        "event_key": n, "ticker": n, "category": "FDA",
        "claim": "PDUFA_TARGET", "verification_required": "YES",
        "verification_status": "REVIEW_REQUIRED"} for n in names}


class SourceAuditDeltaTests(unittest.TestCase):
    def test_original_89_to_82_is_reported_as_seven_resolved(self):
        old = queue(*("X" + str(i) for i in range(89)))
        new = {k: v for k, v in old.items() if int(k[0][1:]) < 82}
        action, updated = compare(report(1, "2026-10-13T14:00:00Z", 89), old,
                                  report(2, "2026-10-13T15:00:00Z", 82), new)
        self.assertEqual(action, "PUBLISH")
        change = updated["comparison"]
        self.assertEqual((change["resolved_count"], change["new_count"],
                          change["still_unresolved_count"], change["net_reduction"]),
                         (7, 0, 82, 7))
        self.assertEqual([x["run_id"] for x in updated["verification_history"]], ["1", "2"])
        self.assertEqual(updated["required_findings_unresolved"], 82)

    def test_new_issues_are_not_counted_as_old_resolutions(self):
        before = queue("A", "B", "C")
        after = queue("A", "C", "D")
        action, updated = compare(report(1, "2026-10-13T14:00:00Z", 3), before,
                                  report(2, "2026-10-13T15:00:00Z", 3), after)
        self.assertEqual(action, "PUBLISH")
        change = updated["comparison"]
        self.assertEqual(change["resolved_count"], 1)
        self.assertEqual(change["new_count"], 1)
        self.assertEqual(change["net_reduction"], 0)
        self.assertEqual(change["resolved_examples"][0]["ticker"], "B")
        self.assertEqual(change["new_examples"][0]["ticker"], "D")

    def test_overlapping_older_scan_never_overwrites_newer_published_evidence(self):
        old = report(20, "2026-10-13T16:00:00Z", 3)
        newer_but_late = report(19, "2026-10-13T15:00:00Z", 4)
        self.assertEqual(compare(old, queue("A", "B", "C"), newer_but_late,
                                 queue("A", "B", "C", "D")), ("SKIP_STALE", None))
        self.assertEqual(compare(old, queue("A", "B", "C"),
                                 report(19, "2026-10-13T16:00:00Z", 3),
                                 queue("A", "B", "C")), ("SKIP_STALE", None))

    def test_scope_change_does_not_infer_verification_from_removed_event(self):
        action, updated = compare(report(1, "2026-10-13T14:00:00Z", 2), queue("A", "B"),
                                  report(2, "2026-10-13T15:00:00Z", 1, "DIFFERENT"),
                                  queue("A"))
        self.assertEqual(action, "PUBLISH")
        self.assertFalse(updated["comparison"]["available"])

    def test_missing_prior_queue_does_not_claim_resolved_issues(self):
        action, updated = compare(report(1, "2026-10-13T14:00:00Z", 2), {},
                                  report(2, "2026-10-13T15:00:00Z", 1), queue("A"))
        self.assertEqual(action, "PUBLISH")
        self.assertFalse(updated["comparison"]["available"])

    def test_incoming_queue_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            compare({}, {}, report(2, "2026-10-13T15:00:00Z", 10), queue("A"))

    def test_omitted_source_families_never_count_as_resolved_findings(self):
        previous = report(1, "2026-10-13T14:00:00Z", 2)
        partial = report(2, "2026-10-13T15:00:00Z", 1)
        partial.update(execution_status="INCOMPLETE",
                       manifest_rejections={"FDA": "Different attempt"})
        for before, after in ((previous, partial), (partial, previous)):
            before = {**before, "source_checked_at_utc": "2026-10-13T14:00:00Z"}
            after = {**after, "source_checked_at_utc": "2026-10-13T15:00:00Z"}
            old_rows = queue("A", "B") if before["required_findings_unresolved"] == 2 else queue("A")
            new_rows = queue("A", "B") if after["required_findings_unresolved"] == 2 else queue("A")
            action, updated = compare(before, old_rows, after, new_rows)
            self.assertEqual(action, "PUBLISH")
            self.assertFalse(updated["comparison"]["available"])
            self.assertNotIn("resolved_count", updated["comparison"])

    def test_rejected_manifest_blocks_resolution_even_with_complete_label(self):
        previous = report(1, "2026-10-13T14:00:00Z", 2)
        incoming = report(2, "2026-10-13T15:00:00Z", 1)
        incoming["manifest_rejections"] = {"SEC": "Different attempt"}
        _, updated = compare(previous, queue("A", "B"), incoming, queue("A"))
        self.assertFalse(updated["comparison"]["available"])

    def test_audit_history_is_bounded_and_contains_each_run_once(self):
        old = report(31, "2026-10-13T14:00:00Z", 1)
        old["verification_history"] = [
            {"run_id": str(i), "remaining": 1} for i in range(1, 32)]
        action, new = compare(old, queue("A"),
                              report(32, "2026-10-13T15:00:00Z", 1), queue("A"))
        self.assertEqual(action, "PUBLISH")
        self.assertEqual(len(new["verification_history"]), 30)
        self.assertEqual(new["verification_history"][-1]["run_id"], "32")
        self.assertEqual(new["verification_history"][-2]["run_id"], "31")


if __name__ == "__main__":
    unittest.main()
