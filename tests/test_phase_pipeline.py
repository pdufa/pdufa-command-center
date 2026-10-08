import copy
import unittest
from datetime import date

from scripts.phase_pipeline import master_additions, manual_master_additions, phase3_gate, reconcile_records, registry_index, study_record

TODAY = date(2026, 10, 8)


def trial(nct="NCT00000001", phases="PHASE2", drug="StudyDrug", indication="Disease A"):
    return {
        "nct_id": nct, "ticker": "TEST", "company": "Test Therapeutics Inc.",
        "drug": drug, "indication": indication,
        "program_key": "TEST|" + drug.lower() + "|" + indication.lower(),
        "program_identity_status": "VERIFIED", "phases": phases,
        "trial_status": "RECRUITING", "start_date": "2026-10-01", "start_date_type": "ACTUAL",
        "source_updated": "2026-10-07", "checked_at": "2026-10-08T03:00:00+00:00",
        "source_url": "https://clinicaltrials.gov/study/" + nct,
        "market_cap": "500000000", "market_cap_status": "VERIFIED",
        "market_cap_source": "https://api.nasdaq.com/api/quote/TEST/summary?assetclass=stocks",
        "market_cap_checked_at": "2026-10-08T03:00:00+00:00",
    }


class PhasePipelineTests(unittest.TestCase):
    def test_manual_phase2_transfer_keeps_review_gates_and_recorded_stage(self):
        records = reconcile_records([], [trial()], TODAY)
        key = records[0]["program_key"]
        additions = manual_master_additions(records, [], {key: "2026-10-08T04:00:00+00:00"})
        self.assertEqual(len(additions), 1)
        row = additions[0]
        self.assertEqual(row["current_stage"], "PHASE 2 — MANUAL REVIEW")
        self.assertEqual(row["nct_id"], "NCT00000001")
        self.assertEqual(row["entry_gate"], "REVIEW")
        self.assertEqual(row["pipeline_evidence_status"], "REVIEW")
        self.assertEqual(row["pipeline_transfer_mode"], "MANUAL REVIEW")
        for field in ("pdufa_date", "phase3_date", "phase3_start_date", "approval_probability", "trade_score"):
            self.assertEqual(row[field], "")

    def test_manual_transfer_targets_one_drug_and_indication(self):
        first = trial()
        second = trial("NCT00000002", drug="OtherDrug")
        third = trial("NCT00000003", indication="Other Disease")
        records = reconcile_records([], [first, second, third], TODAY)
        selected = {first["program_key"]: "2026-10-08"}
        additions = manual_master_additions(records, [], selected)
        self.assertEqual([r["nct_id"] for r in additions], [first["nct_id"]])
        self.assertFalse(manual_master_additions(records, [], {}))

    def test_manual_transfer_does_not_duplicate_existing_or_graduated_programs(self):
        records = reconcile_records([], [trial()], TODAY)
        selected = {records[0]["program_key"]: "2026-10-08"}
        manual = manual_master_additions(records, [], selected)
        self.assertFalse(manual_master_additions(records, manual, selected))
        graduated = reconcile_records(records, [trial("NCT00000002", "PHASE3")], TODAY)
        automatic = master_additions(graduated, [])
        self.assertEqual(len(automatic), 1)
        self.assertFalse(manual_master_additions(graduated, automatic, selected))

    def test_manual_transfer_respects_market_cap_scope_and_mixed_phase_review(self):
        mixed = trial(phases="PHASE2|PHASE3")
        records = reconcile_records([], [mixed], TODAY)
        selected = {mixed["program_key"]: "2026-10-08"}
        row = manual_master_additions(records, [], selected)[0]
        self.assertEqual(row["current_stage"], "PHASE 2/3 — MANUAL REVIEW")
        self.assertEqual(row["phase3_start_date"], "")
        for cap in ("", "100000000", "10000000001"):
            records = reconcile_records([], [{**trial(), "market_cap": cap}], TODAY)
            self.assertFalse(manual_master_additions(records, [], selected))

    def test_phase2_waits_then_matching_phase3_moves(self):
        before = reconcile_records([], [trial()], TODAY)
        self.assertEqual(before[0]["destination"], "PIPELINE")
        after = reconcile_records(before, [trial("NCT00000002", "PHASE3")], TODAY)
        self.assertTrue(all(r["destination"] == "MASTER TABLE" for r in after))
        additions = master_additions(after, [])
        self.assertEqual(len(additions), 1)
        self.assertEqual(additions[0]["nct_id"], "NCT00000002")
        self.assertEqual(additions[0]["phase3_start_date"], "2026-10-01")
        for field in ("pdufa_date", "phase3_date", "approval_probability", "trade_score"):
            self.assertEqual(additions[0][field], "")
        self.assertEqual(additions[0]["entry_gate"], "REVIEW")

    def test_planned_and_estimated_starts_do_not_move(self):
        for patch in ({"trial_status": "NOT_YET_RECRUITING"}, {"start_date_type": "ESTIMATED"},
                      {"start_date": "2026-11-01"}, {"start_date": "2026-10"}):
            row = {**trial(phases="PHASE3"), **patch}
            self.assertEqual(phase3_gate(row, TODAY)[0], "REVIEW")
            self.assertFalse(master_additions(reconcile_records([], [row], TODAY), []))

    def test_combined_phase2_phase3_is_not_a_verified_transition(self):
        row = trial(phases="PHASE2|PHASE3")
        records = reconcile_records([], [row], TODAY)
        self.assertEqual(records[0]["destination"], "PIPELINE")
        self.assertEqual(records[0]["promotion_status"], "REVIEW")

    def test_ticker_alone_cannot_move_another_drug_or_indication(self):
        for field, value in (("drug", "OtherDrug"), ("indication", "Other Disease")):
            p2 = trial()
            args = {field: value}
            p3 = trial("NCT00000002", "PHASE3", **args)
            records = reconcile_records([], [p2, p3], TODAY)
            phase2 = next(r for r in records if r["nct_id"] == p2["nct_id"])
            self.assertEqual(phase2["destination"], "PIPELINE")

    def test_stale_conflicting_or_unchecked_evidence_does_not_pass(self):
        for patch in ({"source_updated": "2025-10-01"}, {"checked_at": "2026-09-01T00:00:00+00:00"},
                      {"program_identity_status": "REVIEW"}, {"source_updated": "2026-10-09"},
                      {"source_url": "https://clinicaltrials.gov/study/NCT00000099"}):
            self.assertEqual(phase3_gate({**trial(phases="PHASE3"), **patch}, TODAY)[0], "REVIEW")

    def test_repeat_scan_does_not_duplicate_or_reset_transition(self):
        first = reconcile_records([], [trial(), trial("NCT00000002", "PHASE3")], TODAY)
        second = reconcile_records(first, [trial(), trial("NCT00000002", "PHASE3")], TODAY)
        self.assertEqual(len(second), 2)
        self.assertEqual(master_additions(first, []), master_additions(second, []))
        self.assertFalse(master_additions(second, [{"ticker": "TEST", "nct_id": "NCT00000002"}]))

    def test_halted_trial_keeps_audit_history_but_loses_verified_status(self):
        first = reconcile_records([], [trial(), trial("NCT00000002", "PHASE3")], TODAY)
        stopped = {**trial("NCT00000002", "PHASE3"), "trial_status": "TERMINATED"}
        updated = reconcile_records(first, [stopped], TODAY)
        moved = next(r for r in updated if r["nct_id"] == "NCT00000002")
        self.assertEqual(moved["destination"], "MASTER TABLE")
        self.assertEqual(moved["promotion_status"], "REVIEW")
        self.assertEqual(moved["promoted_at"], first[0]["promoted_at"])
        self.assertEqual(master_additions(updated, [])[0]["check_status"], "REVIEW")

    def test_company_match_must_be_unique_and_exact(self):
        protocol = {"protocolSection": {
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Test Therapeutics", "class": "INDUSTRY"}},
            "designModule": {"phases": ["PHASE2"]},
            "identificationModule": {"nctId": "NCT00000001"},
            "conditionsModule": {"conditions": ["Disease"]},
            "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "Drug A"}]},
        }}
        registry = [{"ticker": "TEST", "company": "Test Therapeutics Inc."}]
        self.assertEqual(study_record(protocol, registry_index(registry), "2026-10-08")["ticker"], "TEST")
        registry.append({"ticker": "OTHER", "company": "Test Therapeutics Corporation"})
        self.assertIsNone(study_record(protocol, registry_index(registry), "2026-10-08"))
        different = copy.deepcopy(protocol)
        different["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"] = "Test Therapeutic Holdings"
        self.assertIsNone(study_record(different, registry_index(registry[:1]), "2026-10-08"))

    def test_missing_stale_or_out_of_range_cap_does_not_move(self):
        for patch in ({"market_cap": ""}, {"market_cap": "100000000"}, {"market_cap": "10000000001"},
                      {"market_cap_status": "REVIEW"}, {"market_cap_checked_at": "2026-10-01"}):
            row = {**trial(phases="PHASE3"), **patch}
            records = reconcile_records([], [row], TODAY)
            self.assertNotEqual(records[0]["destination"], "MASTER TABLE")
            self.assertFalse(master_additions(records, []))


if __name__ == "__main__":
    unittest.main()
