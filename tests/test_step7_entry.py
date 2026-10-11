"""Synthetic regression tests for all 8 independent research-entry gates."""
import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from step7_entry import evaluate_entry, analyze_post_readout_market, read_evidence, FIELDS

TODAY = date(2026,10,11)

def sample():
    market_bars = []
    for n in range(35):
        stamp = date(2026,9,5) + timedelta(days=n)
        market_bars.append({"date":stamp.isoformat(),"close":10.0+(n%3)*.01,"volume":100000})
    reg={"event_key":"ABC|DRUG_20261111","ticker":"ABC","drug":"Drug A",
         "nct_id":"NCT12345678","pdufa_date":"2026-11-11",
         "check_status":"PARTIAL","monitor_eligibility":"REVIEW"}
    att={"event_key":reg["event_key"],"ticker":"ABC","drug":"Drug A",
         "nct_id":"NCT12345678","reviewer":"Named reviewer","reviewed_at":"2026-10-10",
         "phase3_readout_date":"2026-09-15",
         "phase3_readout_source":"https://example.org/company/positive-topline",
         "phase3_readout_source_date":"2026-09-15",
         "primary_endpoint_status":"MET",
         "primary_endpoint_source":"https://example.org/primary-endpoint",
         "clinically_meaningful_benefit":"YES","effect_size":"12% absolute",
         "confidence_interval":"95% CI 5% to 19%",
         "benefit_review_source":"https://example.org/clinical-results",
         "safety_review_status":"NO_CRITICAL_UNRESOLVED",
         "safety_review_source":"https://example.org/safety-report",
         "financing_closures_attested":"YES",
         "financing_closure_review_source":"https://www.sec.gov/Archives/edgar/data/1234/00012345/a.htm",
         "atm_dilution_status":"NO_ACTIVE_UNRESOLVED",
         "atm_dilution_source":"https://www.sec.gov/Archives/edgar/data/1234/00012345/b.htm",
         "atm_reviewed_at":"2026-10-10","post_readout_setup_attested":"YES",
         "market_review_source":"https://example.org/chart",
         "market_reviewed_at":"2026-10-10"}
    financing={"event_key":reg["event_key"],
               "first_financing_date":"2026-09-17",
               "first_financing_source":"https://www.sec.gov/Archives/edgar/data/1234/000111/a.htm",
               "second_financing_date":"2026-09-28",
               "second_financing_source":"https://www.sec.gov/Archives/edgar/data/1234/000222/b.htm",
               "second_financing_closed":"YES","second_financing_audit_status":"VERIFIED_SECOND_POST_PHASE3_FINANCING",
               "verified_as_of":"2026-10-10"}
    sec={"financing_status":"CHECKED_NO_NEW_CLOSURE","last_successful_recheck_utc":"2026-10-10T15:00:00Z"}
    market={"checked_at_utc":"2026-10-11T02:00:00Z",
            "market_status":"MARKET_UPDATED",
            "market_source":"https://query1.finance.yahoo.com/v8/finance/chart/ABC",
            "last_session_freshness":"RECENT EOD","price_bars_json":json.dumps(market_bars)}
    return reg,att,financing,sec,market

class EntryGateTests(unittest.TestCase):
    def test_all_fields_valid_yields_only_attested_evidence_ready(self):
        args=sample()
        out=evaluate_entry(*args,TODAY)
        self.assertTrue(out["verdict"].startswith("ENTRY READY — ATTESTED"))
        self.assertEqual(len(out["gates"]),8)
        self.assertTrue(all(val.startswith("PASS") for val in out["gates"].values()))
        self.assertIn("NOT INDEPENDENTLY",out["verdict"])

    def test_no_attestation_never_ready(self):
        reg,_,fin,sec,market=sample()
        out=evaluate_entry(reg,None,fin,sec,market,TODAY)
        self.assertTrue(out["verdict"].startswith("REVIEW"))

    def test_ticker_only_match_cannot_establish_clinical_result(self):
        reg,att,fin,sec,market=sample()
        att["nct_id"]="NCT87654321"
        out=evaluate_entry(reg,att,fin,sec,market,TODAY)
        self.assertFalse(out["gates"]["trial_identity"].startswith("PASS"))
        self.assertFalse(out["gates"]["phase3_primary"].startswith("PASS"))

    def test_pvalue_alone_is_never_clinically_meaningful_benefit(self):
        reg,att,fin,sec,market=sample()
        att["effect_size"]=""
        att["confidence_interval"]=""
        self.assertFalse(evaluate_entry(reg,att,fin,sec,market,TODAY)["gates"]["clinical_benefit"].startswith("PASS"))

    def test_sec_403_disables_both_financing_gates(self):
        reg,att,fin,sec,market=sample()
        sec["financing_status"]="SOURCE_BLOCKED_RETAINED"
        out=evaluate_entry(reg,att,fin,sec,market,TODAY)
        self.assertFalse(out["gates"]["second_financing"].startswith("PASS"))
        self.assertFalse(out["gates"]["no_unresolved_dilution"].startswith("PASS"))

    def test_second_financing_must_be_after_readout_and_after_first(self):
        reg,att,fin,sec,market=sample()
        fin["second_financing_date"]="2026-09-13"
        out=evaluate_entry(reg,att,fin,sec,market,TODAY)
        self.assertFalse(out["gates"]["second_financing"].startswith("PASS"))

    def test_sec_sources_must_be_real_sec_archive_domain(self):
        reg,att,fin,sec,market=sample()
        fin["second_financing_source"]="https://sec.gov.evil.example/Archives/edgar/data/123/a.htm"
        out=evaluate_entry(reg,att,fin,sec,market,TODAY)
        self.assertFalse(out["gates"]["second_financing"].startswith("PASS"))

    def test_outdated_technical_check_never_passes(self):
        reg,att,fin,sec,market=sample()
        market["checked_at_utc"]="2026-09-29"
        out=evaluate_entry(reg,att,fin,sec,market,TODAY)
        self.assertFalse(out["gates"]["post_readout_price_base"].startswith("PASS"))
        self.assertFalse(out["gates"]["normalized_volume"].startswith("PASS"))

    def test_unstabilized_price_and_volume_fail(self):
        reg,att,fin,sec,market=sample()
        bars=json.loads(market["price_bars_json"])
        for i in range(-5,0):
            bars[i]["close"]=12 + i/10
            bars[i]["volume"]=500000
        market["price_bars_json"]=json.dumps(bars)
        out=evaluate_entry(reg,att,fin,sec,market,TODAY)
        self.assertFalse(out["gates"]["post_readout_price_base"].startswith("PASS"))
        self.assertFalse(out["gates"]["normalized_volume"].startswith("PASS"))

    def test_resolved_or_past_fda_event_is_excluded_even_if_gates_pass(self):
        reg,att,fin,sec,market=sample()
        reg["check_status"]="RESOLVED_APPROVED"
        self.assertTrue(evaluate_entry(reg,att,fin,sec,market,TODAY)["verdict"].startswith("EXCLUDED"))
        reg["check_status"]=""
        reg["pdufa_date"]="2026-10-09"
        self.assertTrue(evaluate_entry(reg,att,fin,sec,market,TODAY)["verdict"].startswith("EXCLUDED"))

    def test_incomplete_price_history_is_review(self):
        reg,att,fin,sec,market=sample()
        market["price_bars_json"]="[]"
        self.assertEqual(analyze_post_readout_market("[]","2026-09-15",TODAY)["price_base"],"NOT VERIFIED")
        self.assertFalse(evaluate_entry(reg,att,fin,sec,market,TODAY)["gates"]["post_readout_price_base"].startswith("PASS"))

    def test_duplicate_exact_event_is_invalidated(self):
        reg,att,fin,sec,market=sample()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"entries.csv"
            with path.open("w",newline="",encoding="utf-8") as fh:
                w=csv.DictWriter(fh,fieldnames=FIELDS);w.writeheader()
                w.writerow({k:att.get(k,"") for k in FIELDS})
                w.writerow({k:att.get(k,"") for k in FIELDS})
            self.assertIsNone(read_evidence(path)[reg["event_key"]])

if __name__=="__main__":
    unittest.main()
