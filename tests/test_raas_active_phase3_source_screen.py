"""No fabricated active phase-3 pipeline eligibility or PDUFA dates."""
import copy
import csv
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import raas_active_phase3_source_screen as mod

DATE = "2026-11-04T22:55:00+00:00"


def trial(nct, ticker, *, active="RECRUITING", phase="PHASE3"):
    return {
        "nctId": nct, "ticker": ticker,
        "sourceUrl": "https://clinicaltrials.gov/study/" + nct,
        "postedResults": False, "registryStatus": active,
        "registeredPhases": [phase], "registeredInterventions": ["Drug A", "Placebo"],
        "registeredConditions": ["Condition A"],
        "primaryResults": [], "primaryDefinitions": [],
        "seriousEventDetails": [], "evidenceState": "PROTOCOL_ONLY",
    }


def index(records):
    return {
        "schemaVersion": 1,
        "scope": "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
        "sourceAsOf": DATE, "summary": {"researchNcts": len(records)},
        "records": records,
    }


def roster(items):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=("nct_id", "ticker", "company", "status", "source_url"))
    w.writeheader()
    for r in items:
        w.writerow({
            "nct_id": r["nctId"], "ticker": r["ticker"], "company": r["ticker"]+" Inc",
            "status": r["registryStatus"], "source_url": r["sourceUrl"],
        })
    return buf.getvalue()


def caps(items):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=(
        "ticker", "market_cap", "market_cap_source", "market_cap_checked_at",
        "market_cap_status"))
    w.writeheader()
    for ticker, dollars, at in items:
        w.writerow({
            "ticker": ticker, "market_cap": dollars,
            "market_cap_source": f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks",
            "market_cap_checked_at": at, "market_cap_status": "VERIFIED",
        })
    return buf.getvalue()


def reviews():
    return {
        "schemaVersion": 1, "scope": "RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY",
        "records": [],
    }


class ActiveScreenTests(unittest.TestCase):
    def test_phase_cap_freshness_and_active_status_must_all_pass(self):
        trials = [
            trial("NCT00000001", "AAA"),
            trial("NCT00000002", "BBB", active="COMPLETED"),
            trial("NCT00000003", "CCC", phase="PHASE2"),
            trial("NCT00000004", "DDD"),
            trial("NCT00000005", "EEE"),
        ]
        cap_data = caps([
            ("AAA", 500_000_000, "2026-11-04T04:00:00+00:00"),
            ("BBB", 900_000_000, "2026-11-04T04:00:00+00:00"),
            ("CCC", 950_000_000, "2026-11-04T04:00:00+00:00"),
            ("DDD", 12_000_000_000, "2026-11-04T04:00:00+00:00"),
            ("EEE", 2_000_000_000, "2026-10-20T04:00:00+00:00"),
        ])
        out, s = mod.build(index(trials), roster(trials), cap_data, reviews())
        self.assertEqual(s["researchTrials"], 5)
        self.assertEqual(s["sourceActivePhase3CapResearchCandidates"], 1)
        self.assertEqual(s["sourceActivePhase3CapIssuers"], 1)
        self.assertEqual(next(r for r in out if r["nctId"] == "NCT00000001")[
            "sourceActivePhase3CapScreen"], True)
        self.assertEqual(next(r for r in out if r["ticker"] == "EEE")[
            "marketCapSnapshotFresh"], False)
        self.assertEqual(next(r for r in out if r["ticker"] == "DDD")[
            "marketCapIn300mTo10bRange"], False)
        self.assertEqual(s["confirmedFdaPdufaCandidatesFromThisScreen"], 0)
        self.assertEqual(s["fullyIndependentlyReviewedOverallRaasRatings"], 0)
        self.assertTrue(all(r["fdaUsPathwayIndependentVerification"] == "NOT_VERIFIED"
                            and r["applicationAcceptedForReview"] == "NOT_VERIFIED"
                            and r["fullRaasOverallRating"] == ""
                            and r["fdaPassCrlExtensionProbability"] == "" for r in out))

    def test_wrong_nct_registry_or_ticker_fails_closed(self):
        rows = [trial("NCT00000001", "AAA")]
        cs = caps([("AAA", 500_000_000, "2026-11-03T04:00:00+00:00")])
        x = copy.deepcopy(rows)
        x[0]["ticker"] = "BAD"
        with self.assertRaisesRegex(ValueError, "CROSS_NCT_SOURCE"):
            mod.build(index(x), roster(rows), cs, reviews())
        x = copy.deepcopy(rows)
        x.append(copy.deepcopy(x[0]))
        with self.assertRaisesRegex(ValueError, "TRIAL_IDENTITY"):
            mod.build(index(x), roster(x), cs, reviews())

    def test_missing_cap_never_implies_under_300m_and_future_quote_not_fresh(self):
        rows = [trial("NCT00000001", "AAA")]
        out, _ = mod.build(index(rows), roster(rows), caps([]), reviews())
        self.assertEqual(out[0]["marketCapUsd"], "")
        self.assertIn("CURRENT_SEVEN_DAY_MARKET_CAP_NOT_VERIFIED",
                      out[0]["missingSourceChecks"])
        fresh = caps([("AAA", 500_000_000, "2026-11-06T04:00:00+00:00")])
        out, _ = mod.build(index(rows), roster(rows), fresh, reviews())
        self.assertFalse(out[0]["marketCapSnapshotFresh"])
        self.assertFalse(out[0]["sourceActivePhase3CapScreen"])

    def test_csv_spreadsheet_safe_and_762_full_source_rows(self):
        if not all(p.exists() for p in [mod.INDEX, mod.ROSTER, mod.CAPS, mod.REVIEWS]):
            self.skipTest("Complete committed source census not present")
        idx = json.loads(mod.INDEX.read_text())
        raw, status = mod.generate(
            idx, mod.ROSTER.read_text(), mod.CAPS.read_text(),
            json.loads(mod.REVIEWS.read_text()))
        rows = list(csv.DictReader(io.StringIO(raw)))
        s = json.loads(status)
        self.assertEqual(s["researchTrials"], 762)
        self.assertEqual(len(rows), 762)
        self.assertEqual(s["confirmedFdaPdufaCandidatesFromThisScreen"], 0)
        self.assertEqual(s["calibratedFdaPredictions"], 0)
        self.assertGreater(s["sourceActivePhase3CapResearchCandidates"], 0)
        self.assertEqual(len({r["nctId"] for r in rows}), 762)
        self.assertEqual(s["sourceActivePhase3CapResearchCandidates"],
                         sum(r["sourceActivePhase3CapScreen"] == "True" for r in rows))
        self.assertEqual(mod._safe("=HYPERLINK(A1)"), "'=HYPERLINK(A1)")


if __name__ == "__main__":
    unittest.main()
