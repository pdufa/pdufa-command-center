"""No worksheet content can certify clinical review or an FDA prediction."""
import contextlib
import csv
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import scientific_reviewer_handoff_audit as audit


class DualHandoffAuditTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        root = Path(self.workspace.name)
        self.nct_id = "NCT02142738"
        self.inventory = root / "source_inventory.csv"
        self.a = root / "reviewer_a.csv"
        self.b = root / "reviewer_b.csv"
        self.rows = audit._expected_base(self.nct_id)
        self._write(self.inventory, audit.BASE_FIELDS, self.rows)
        for slot, path in (("A", self.a), ("B", self.b)):
            items = [
                dict(row, reviewer_slot=slot, reviewer_name="",
                     qualification_verification="NOT_VERIFIED",
                     primary_document_url="", document_sha256="",
                     public_document_date="", evidence_section_or_table="",
                     finding_notes="", reviewer_decision="NOT_SUBMITTED",
                     reviewer_signature="", submission_status="NOT_SUBMITTED")
                for row in self.rows
            ]
            self._write(path, audit.BASE_FIELDS + audit.REVIEWER_FIELDS, items)

    def _write(self, path, header, rows):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n")
            writer.writeheader()
            writer.writerows(rows)

    def _edit(self, path, fn):
        header = audit.BASE_FIELDS + audit.REVIEWER_FIELDS
        items = audit._read_csv(path, header)
        fn(items)
        self._write(path, header, items)

    def _record(self, path, decision, source="https://clinicaltrials.gov/"):
        def mutate(items):
            row = items[0]
            row.update(reviewer_name="Reviewer claimed", qualification_verification="NOT_VERIFIED",
                       primary_document_url=source, document_sha256="a" * 64,
                       public_document_date="2016-10-08", evidence_section_or_table="Table 2",
                       finding_notes="Recorded observation; not authenticated",
                       reviewer_decision=decision, reviewer_signature="typed-name",
                       submission_status="NOT_SUBMITTED")
        self._edit(path, mutate)

    def test_blank_A_B_worksheets_are_structurally_valid_but_never_approved(self):
        result = audit.reconcile_handoff_files(self.nct_id, self.inventory, self.a, self.b)
        self.assertEqual(result["inventoryTasksValidated"], 320)
        self.assertEqual(result["candidateObservationsWithSyntacticProvenance"], {"A": 0, "B": 0})
        self.assertEqual(result["tasksIndependentlyAdjudicated"], 0)
        self.assertFalse(result["readyForScientificConclusion"])
        self.assertIsNone(result["fdaApprovalProbability"])
        self.assertIsNone(result["scientificScore"])
        self.assertFalse(result["promotionAllowed"])
        self.assertNotIn("reviewer_name", result)

    def test_candidate_observations_and_disagreements_still_leave_all_science_blocked(self):
        self._record(self.a, "supports")
        self._record(self.b, "contradicts")
        result = audit.reconcile_handoff_files(self.nct_id, self.inventory, self.a, self.b)
        self.assertEqual(result["candidateObservationsWithSyntacticProvenance"], {"A": 1, "B": 1})
        self.assertEqual(result["candidateDisagreementCount"], 1)
        self.assertEqual(result["candidateDisagreementTaskIds"], ["trial_design.randomization:1"])
        self.assertFalse(result["reviewerIdentitiesAuthenticated"])
        self.assertFalse(result["sourceDocumentsFetchedAndAuthenticated"])
        self.assertFalse(result["cryptographicReviewerSignaturesVerified"])
        self.assertEqual(result["tasksIndependentlyAdjudicated"], 0)
        self.assertFalse(result["promotionAllowed"])
        self.assertIsNone(result["fdaApprovalProbability"])

    def test_single_candidate_and_bad_provenance_do_not_count_as_dual_review(self):
        self._record(self.a, "supports", source="http://not-an-https-document.example/")
        self._record(self.b, "supports")
        result = audit.reconcile_handoff_files(self.nct_id, self.inventory, self.a, self.b)
        self.assertEqual(result["candidateObservationsWithSyntacticProvenance"], {"A": 0, "B": 1})
        self.assertEqual(result["candidateObservationsMissingValidProvenance"], {"A": 1, "B": 0})
        self.assertEqual(result["tasksWithOnlyOneCandidateObservation"], 1)
        self.assertEqual(result["candidateDisagreementCount"], 0)

    def test_cross_trial_rows_tampered_base_and_malformed_review_are_rejected(self):
        mutations = [
            ("inventory", lambda x: x[0].__setitem__("nct_id", "NCT04280705")),
            ("A", lambda x: x[0].__setitem__("reviewer_slot", "B")),
            ("A", lambda x: x[0].__setitem__("assessment", "other")),
            ("B", lambda x: x[1].__setitem__("depth", "mismatch")),
            ("B", lambda x: x[0].__setitem__("scientific_score", "98")),
            ("A", lambda x: x[0].__setitem__("independently_verified", "TRUE")),
            ("A", lambda x: x[0].__setitem__("qualification_verification", "VERIFIED")),
            ("B", lambda x: x[0].__setitem__("submission_status", "SIGNED")),
            ("A", lambda x: x[0].__setitem__("reviewer_decision", "APPROVED")),
        ]
        for target, mutate in mutations:
            with self.subTest(target=target, mutation=str(mutate)):
                # Reset all three CSVs, so each rejection tests only one tamper.
                self._write(self.inventory, audit.BASE_FIELDS, self.rows)
                for slot, path in (("A", self.a), ("B", self.b)):
                    blank = [
                        dict(row, reviewer_slot=slot, reviewer_name="",
                             qualification_verification="NOT_VERIFIED",
                             primary_document_url="", document_sha256="",
                             public_document_date="", evidence_section_or_table="",
                             finding_notes="", reviewer_decision="NOT_SUBMITTED",
                             reviewer_signature="", submission_status="NOT_SUBMITTED")
                        for row in self.rows
                    ]
                    self._write(path, audit.BASE_FIELDS + audit.REVIEWER_FIELDS, blank)
                if target == "inventory":
                    items = audit._read_csv(self.inventory, audit.BASE_FIELDS)
                    mutate(items)
                    self._write(self.inventory, audit.BASE_FIELDS, items)
                else:
                    self._edit(self.a if target == "A" else self.b, mutate)
                with self.assertRaises(ValueError):
                    audit.reconcile_handoff_files(self.nct_id, self.inventory, self.a, self.b)

    def test_missing_duplicate_and_additional_rows_or_columns_rejected(self):
        original = audit._read_csv(self.a, audit.BASE_FIELDS + audit.REVIEWER_FIELDS)
        for altered in (original[:-1], original + [original[-1]], [original[0]] + original[:-1]):
            self._write(self.a, audit.BASE_FIELDS + audit.REVIEWER_FIELDS, altered)
            with self.assertRaises(ValueError):
                audit.reconcile_handoff_files(self.nct_id, self.inventory, self.a, self.b)
        self._write(self.a, audit.BASE_FIELDS + audit.REVIEWER_FIELDS, original)
        self.a.write_text(self.a.read_text() + "\nEXTRA,BAD\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            audit.reconcile_handoff_files(self.nct_id, self.inventory, self.a, self.b)

    def test_cli_exit_code_is_nonzero_even_on_perfectly_matching_blank_templates(self):
        args = [
            "scientific_reviewer_handoff_audit", "--nct-id", self.nct_id,
            "--inventory", str(self.inventory),
            "--reviewer-a", str(self.a), "--reviewer-b", str(self.b),
        ]
        output = StringIO()
        with patch("sys.argv", args), contextlib.redirect_stdout(output):
            exit_code = audit.main()
        self.assertEqual(exit_code, 2)
        result = json.loads(output.getvalue())
        self.assertFalse(result["promotionAllowed"])
        self.assertIsNone(result["fdaApprovalProbability"])

    def test_oversized_and_extra_columns_rejected(self):
        self.a.write_bytes(b"1" * (audit._MAX_CSV_BYTES + 1))
        with self.assertRaises(ValueError):
            audit.reconcile_handoff_files(self.nct_id, self.inventory, self.a, self.b)
        self.assertRaises(ValueError, audit._expected_base, "WRONG-NCT")
