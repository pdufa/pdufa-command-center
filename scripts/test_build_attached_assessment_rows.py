import csv
import tempfile
import unittest
from pathlib import Path
from build_attached_assessment_rows import build

class AttachedRowTests(unittest.TestCase):
    def test_exact_rows(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/"events.csv"
            output=Path(d)/"expanded.csv"
            source.write_text("event_id,ticker,drug,indication,decision_date,source_url\n"+
                              "one,AAA,Drug A,Ind A,2026-06-01,https://example.org/a\n"+
                              "two,BBB,Drug B,Ind B,2026-07-01,https://example.org/b\n")
            build(source,output,expected=2)
            with output.open(newline="") as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),4)
            self.assertEqual(rows[1]["level"],"L01")
            self.assertEqual(rows[2]["row_type"],"MAIN")
            self.assertEqual(rows[3]["parent_event_id"],"two")
            self.assertEqual(rows[1]["prediction"],"")
    def test_refuses_missing_events(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/"events.csv"
            source.write_text("event_id,ticker,drug,indication,decision_date,source_url\n"+
                              "one,AAA,Drug A,Ind A,2026-06-01,https://example.org/a\n")
            with self.assertRaisesRegex(ValueError,"Expected 183 sourced events"):
                build(source,Path(d)/"expanded.csv")
if __name__=="__main__":
    unittest.main()
