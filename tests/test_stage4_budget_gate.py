import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "stage4_budget_gate.py"
spec = importlib.util.spec_from_file_location("stage4_budget_gate", MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class BudgetGateTests(unittest.TestCase):
    def test_rejects_invalid_budget(self):
        for value in ("nan", "inf", "-1", "bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                gate.validate_budget(value)

    def test_accepts_zero_and_ten(self):
        self.assertEqual(gate.validate_budget("0"), 0)
        self.assertEqual(gate.validate_budget("10"), 10)

    def test_missing_queue_is_idle(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = gate.inspect_queue(Path(tmp) / "missing.json")
            self.assertEqual(result["status"], "idle")

    def test_only_explicit_approval_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps([{"id": "one", "approved": True}, {"id": "two"}, {"id": "three", "approved": False}]))
            self.assertEqual(gate.inspect_queue(path)["approved_tasks"], 1)

    def test_rejects_string_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps([{"id": "one", "approved": "true"}]))
            with self.assertRaises(ValueError):
                gate.inspect_queue(path)

    def test_rejects_non_object_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps([None]))
            with self.assertRaises(ValueError):
                gate.inspect_queue(path)

    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps([{"id": "a"}, {"id": "a"}]))
            with self.assertRaises(ValueError):
                gate.inspect_queue(path)

    def test_rejects_missing_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps([{"approved": True}]))
            with self.assertRaises(ValueError):
                gate.inspect_queue(path)

    def test_rejects_unsafe_task_ids(self):
        for task_id in ("../escape", "with spaces", "x" * 129, "é"):
            with self.subTest(task_id=task_id), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "queue.json"
                path.write_text(json.dumps([{"id": task_id, "approved": True}]))
                with self.assertRaises(ValueError):
                    gate.inspect_queue(path)

    def test_rejects_oversized_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text(json.dumps([{"id": f"task_{i}"} for i in range(101)]))
            with self.assertRaises(ValueError):
                gate.inspect_queue(path)

    def test_rejects_non_list_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            path.write_text("{}")
            with self.assertRaises(ValueError):
                gate.inspect_queue(path)


if __name__ == "__main__":
    unittest.main()
