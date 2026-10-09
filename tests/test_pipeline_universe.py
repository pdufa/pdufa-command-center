import unittest
from datetime import date
from pipeline_universe import build_universe, select_records, stage_counts, STAGES

TODAY = date(2026, 10, 9)

class PipelineUniverseTests(unittest.TestCase):
    def test_results_attach_by_exact_trial_without_duplicate_counts(self):
        trial = {"nct_id": "NCT00000001", "ticker": "A", "phases": "PHASE3",
                 "drug": "Drug A", "source_url": "https://clinicaltrials.gov/study/NCT00000001"}
        result = {"nct_id": "NCT00000001", "ticker": "A", "drug": "Drug A",
                  "phase3_results_posted_at": "2026-10-01",
                  "phase3_results_source": trial["source_url"],
                  "verification_status": "REGISTERED_RESULTS_POSTED"}
        frame = build_universe(clinical=[trial], announcements=[result], today=TODAY)
        self.assertEqual(len(select_records(frame, ["Phase 3"])), 1)
        self.assertEqual(len(select_records(frame, ["Phase 3 Results"])), 1)
        self.assertEqual(len(select_records(frame, ["Phase 3", "Phase 3 Results"])), 1)

    def test_predictions_and_elapsed_targets_do_not_become_decisions(self):
        row = {"event_key": "A|Drug A|2026-10-01", "ticker": "A",
               "pdufa_date": "2026-10-01", "model_class": "APPROVED"}
        frame = build_universe(regulatory=[row], today=TODAY)
        self.assertEqual(len(select_records(frame, ["PDUFA Decision"])), 1)
        self.assertEqual(len(select_records(frame, ["Post-Decision"])), 0)
        row["outcome"] = "APPROVED"
        frame = build_universe(regulatory=[row], today=TODAY)
        self.assertEqual(len(select_records(frame, ["Post-Decision"])), 1)
        self.assertEqual(frame.iloc[0]["decision_date"], "")

    def test_acceptance_is_source_backed_and_does_not_invent_submission_dates(self):
        row = {"event_key": "A|Drug A|2027-01-01", "ticker": "A",
               "regulatory_summary": "FDA accepted the Drug A NDA for review.",
               "pdufa_evidence_url": "https://www.sec.gov/Archives/example.htm"}
        frame = build_universe(regulatory=[row], today=TODAY)
        self.assertEqual(len(select_records(frame, ["FDA Acceptance"])), 1)
        self.assertEqual(len(select_records(frame, ["NDA/BLA Submission"])), 1)
        self.assertEqual(frame.iloc[0]["nda_submission_date"], "")
        row["regulatory_summary"] = "The company plans to submit an NDA; FDA has not accepted it."
        frame = build_universe(regulatory=[row], today=TODAY)
        self.assertEqual(len(select_records(frame, ["FDA Acceptance", "NDA/BLA Submission"])), 0)

    def test_different_programs_on_one_ticker_are_preserved(self):
        rows = [{"event_key": "A|Drug A|2027-01-01", "ticker": "A", "drug": "Drug A", "pdufa_date": "2027-01-01"},
                {"event_key": "A|Drug B|2027-01-01", "ticker": "A", "drug": "Drug B", "pdufa_date": "2027-01-01"}]
        frame = build_universe(regulatory=rows, today=TODAY)
        self.assertEqual(len(select_records(frame, ["PDUFA Decision"])), 2)
        self.assertEqual(len(select_records(frame, STAGES, "Drug B")), 1)
        self.assertEqual(stage_counts(frame)["Stage"].tolist(), list(STAGES))

    def test_source_backed_drug_metadata_is_attached_without_changing_stage(self):
        trial = {
            "nct_id": "NCT00000002", "ticker": "MLYS", "drug": "Lorundrostat",
            "phases": "PHASE2", "source_url": "https://clinicaltrials.gov/study/NCT00000002",
        }
        metadata = [{
            "ticker": "MLYS", "drug_alias": "Lorundrostat",
            "drug_modality": "Small molecule",
            "drug_class": "Aldosterone synthase inhibitor",
            "mechanism_target": "Inhibits CYP11B2",
            "route": "Oral", "use_status": "Investigational",
            "classification_source_url": "https://mineralystx.com/science/",
            "classification_note": "Source-backed test metadata",
        }]
        frame = build_universe(
            clinical=[trial], metadata=metadata, today=TODAY
        )
        row = frame.iloc[0]
        self.assertEqual(row["drug_modality"], "Small molecule")
        self.assertEqual(row["drug_class"], "Aldosterone synthase inhibitor")
        self.assertEqual(row["mechanism_target"], "Inhibits CYP11B2")
        self.assertEqual(row["route"], "Oral")
        self.assertEqual(row["use_status"], "Investigational")
        self.assertEqual(row["classification_status"], "SOURCE CLASSIFIED")
        self.assertEqual(len(select_records(frame, ["Phase 2"])), 1)

    def test_future_results_do_not_enter_the_posted_results_stage(self):
        row = {"nct_id": "NCT00000001", "ticker": "A", "phase": "PHASE3",
               "results_posted": "2027-01-01", "source_url": "https://clinicaltrials.gov/study/NCT00000001"}
        frame = build_universe(clinical=[row], today=TODAY)
        self.assertEqual(len(select_records(frame, ["Phase 3 Results"])), 0)

if __name__ == "__main__":
    unittest.main()
