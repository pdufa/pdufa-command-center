#!/usr/bin/env python3
"""Publish shared, dated research observations without changing list qualification.

Company facts are stored once per issuer. Trial/application facts use the existing
exact source keys; this module never assigns permanent PDUFA numbers. Cells are
[value, status, source-index, observation-date, original-retrieval-date, note].
Absent cells mean MISSING, never zero, false, or a failed restriction.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "new-platform" / "backend"))
from app.pipeline_universe_rules import original_pipeline_universe
from app.enrichment_calculations import cash_runway_months

BASE = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/"
READY = {"OBSERVED", "CALCULATED", "MODELED"}
STATES = ("OBSERVED", "CALCULATED", "MODELED", "STALE", "REVIEW", "CONFLICTING", "MISSING")
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,14}$")
UNIVERSE = ("all_phase_trials.csv", "phase_pipeline.csv", "phase3_announcements.csv",
            "pdufa_candidates.csv", "fda_review_engine.csv", "prediction_engine_history.csv", "drug_metadata.csv")


def field(key, label, group, kind, scope, source, rule="", age=90):
    return dict(id=key, label=label, group=group, kind=kind, scope=scope,
                source=source, rule=rule, maxAgeDays=age)


INPUT_FIELDS = [
    field("ticker", "Ticker", "Identity", "retrieved", "program", "Published issuer/trial identity"),
    field("company", "Company", "Identity", "retrieved", "program", "ClinicalTrials.gov / SEC"),
    field("cik", "SEC CIK", "Identity", "retrieved", "company", "SEC issuer registry"),
    field("exchange", "Exchange", "Identity", "retrieved", "company", "Issuer listing registry"),
    field("drug", "Drug / intervention", "Identity", "retrieved", "program", "ClinicalTrials.gov / application evidence"),
    field("indication", "Disease / indication", "Identity", "retrieved", "program", "ClinicalTrials.gov / application evidence"),
    field("nct_id", "NCT trial ID", "Identity", "retrieved", "program", "ClinicalTrials.gov"),
    field("exact_key", "Exact program key", "Identity", "calculated", "program", "Existing Pipeline identity rules", "Reuse the existing TRIAL / APPLICATION / RESULT key; permanent PDUFA numbers are unchanged."),
    field("application_id", "FDA application ID", "FDA / regulatory", "retrieved", "program", "FDA application evidence"),
    field("application_type", "FDA application type", "FDA / regulatory", "retrieved", "program", "NDA / BLA source disclosure"),
    field("pdufa_date", "PDUFA target", "FDA / regulatory", "retrieved", "program", "Source Verification Ledger: PDUFA_TARGET", age=7),
    field("submission_date", "Application submission date", "FDA / regulatory", "retrieved", "program", "FDA / exact-program company disclosure"),
    field("acceptance_date", "FDA acceptance date", "FDA / regulatory", "retrieved", "program", "FDA / exact-program company disclosure"),
    field("designations", "FDA special designations", "FDA / regulatory", "retrieved", "program", "Exact-event designation evidence", "Positive documented designations only; no positive record does not mean none.", 30),
    field("fda_outcome", "FDA decision", "FDA / regulatory", "retrieved", "program", "Source Verification Ledger: FDA_DECISION"),
    field("decision_date", "FDA decision date", "FDA / regulatory", "retrieved", "program", "FDA decision letter"),
    field("days_to_pdufa", "Days to PDUFA", "FDA / regulatory", "calculated", "program", "Verified PDUFA target", "Target date minus Pacific as-of date; inherits target evidence status.", 7),
    field("regulatory_readiness", "Regulatory readiness assessment", "FDA / regulatory", "modeled", "program", "Source-reviewed assessment", "Recorded review grade and rationale; not an FDA probability."),
    field("phase", "Registered phase", "Clinical", "retrieved", "program", "ClinicalTrials.gov"),
    field("trial_status", "Registered trial status", "Clinical", "retrieved", "program", "ClinicalTrials.gov"),
    field("primary_completion", "Primary completion date", "Clinical", "retrieved", "program", "ClinicalTrials.gov", "Registry primary completion is not a public readout date."),
    field("results_posted", "Results first posted", "Clinical", "retrieved", "program", "ClinicalTrials.gov", "Posted results do not establish efficacy or success."),
    field("enrollment", "Enrollment", "Clinical", "retrieved", "program", "ClinicalTrials.gov exact-trial detail"),
    field("primary_p_values", "Reported primary p-values", "Clinical", "retrieved", "program", "Exact-NCT primary endpoint evidence", "Keep endpoints, comparison and inequality modifiers; no efficacy inference."),
    field("has_results", "Registry results posted", "Clinical", "calculated", "program", "Registry results-post date", "True only when a valid nonfuture results-post date is recorded; absent remains missing."),
    field("days_to_completion", "Days to primary completion", "Clinical", "calculated", "program", "Registry primary completion date", "Registered date minus Pacific as-of date; partial dates are not converted to exact dates."),
    field("clinical_strength", "Clinical strength assessment", "Clinical", "modeled", "program", "Source-reviewed clinical assessment", "Recorded effect-size review; not trial success or approval probability."),
    field("market_cap", "Market capitalization (USD)", "Financial", "retrieved", "company", "Verified market-cap ledger", age=7),
    field("cash", "Unrestricted cash (USD)", "Financial", "retrieved", "company", "SEC companyfacts: cash and equivalents", age=7),
    field("operating_cash_flow", "Operating cash flow (USD)", "Financial", "retrieved", "company", "SEC companyfacts, stated 3/12-month period", age=7),
    field("shares", "Shares outstanding", "Financial", "retrieved", "company", "SEC companyfacts", age=7),
    field("first_financing", "First financing closed", "Financial", "retrieved", "program", "Exact-event document-level SEC closing recheck", age=7),
    field("second_financing", "Second financing closed", "Financial", "retrieved", "program", "Exact-event two-close SEC recheck", "An announced offering or prospectus does not prove a closing.", 7),
    field("monthly_burn", "Monthly operating burn (USD)", "Financial", "calculated", "company", "SEC operating cash flow", "Negative reported operating cash flow / reported period months. Nonnegative cash flow has no burn estimate.", 7),
    field("cash_runway", "Cash-only runway (months)", "Financial", "calculated", "company", "Matched-period SEC cash / operating cash flow", "Unrestricted cash / monthly burn; no financing or investment proceeds assumed. Reporting periods must match.", 7),
    field("last_close", "Last daily close (USD)", "Market", "retrieved", "company", "Labeled saved market-data provider", age=4),
    field("avg_volume_20", "Prior 20-session mean volume", "Market", "calculated", "company", "Same-provider daily bars", "Mean of the 20 completed sessions before the latest session.", 4),
    field("relative_volume", "Relative volume", "Market", "calculated", "company", "Same-provider daily bars", "Latest session volume / prior 20-session mean volume.", 4),
    field("sma20", "20-session moving average", "Market", "calculated", "company", "Same-provider daily closes", "Arithmetic mean of the latest 20 completed daily closes.", 4),
    field("sma50", "50-session moving average", "Market", "calculated", "company", "Same-provider daily closes", "Arithmetic mean of the latest 50 completed daily closes.", 4),
    field("sma200", "200-session moving average", "Market", "calculated", "company", "Same-provider daily closes", "Arithmetic mean of the latest 200 completed daily closes.", 4),
    field("rsi14", "RSI (14)", "Market", "calculated", "company", "Same-provider daily closes", "Wilder smoothing of 14-session gains/losses; flat series = 50.", 4),
    field("atr14", "ATR (14)", "Risk / upside", "calculated", "company", "Same-provider daily high/low/close", "Wilder mean true range; requires high/low data, not close-only bars.", 4),
    field("macd", "MACD (12,26,9)", "Risk / upside", "calculated", "company", "Same-provider daily closes", "SMA-seeded EMA12 minus EMA26; EMA9 signal. At least 35 daily sessions.", 4),
    field("volatility20", "20-session annualized volatility (%)", "Risk / upside", "calculated", "company", "Same-provider daily closes", "Sample standard deviation of 20 daily log returns × sqrt(252) × 100.", 4),
    field("debt", "Current and noncurrent debt (USD)", "Risk / upside", "retrieved", "company", "SEC companyfacts", "Only complete, matched-period current and noncurrent debt facts are added.", 7),
    field("approved_sales", "Approved-drug sales disclosures", "Risk / upside", "retrieved", "company", "Verified approved-product sales ledger", "Product disclosures retain currency and period; company revenue is not substituted for product sales."),
    field("milestone_success", "Next milestone assessment", "Risk / upside", "modeled", "program", "Source-reviewed milestone assessment", "Research grade, not a calibrated probability."),
    field("risk_adjusted_upside", "Risk-adjusted upside assessment", "Risk / upside", "modeled", "program", "Source-reviewed valuation assumptions", "Requires recorded measurements, rationale and source; no inferred price target.", 7),
    field("commercial_potential", "Commercial potential assessment", "Risk / upside", "modeled", "program", "Source-reviewed market assessment", "Requires exact-program source, measurements and rationale."),
]
INPUT_FIELDS += [
    field("trial_start_date", "Trial start date", "Clinical", "retrieved", "program", "ClinicalTrials.gov"),
    field("primary_endpoint", "Primary endpoint", "Clinical", "retrieved", "program", "Exact-NCT endpoint evidence"),
    field("application_status", "Application status", "FDA / regulatory", "retrieved", "program", "Exact-event source disclosure", age=7),
    field("revenue", "Company revenue (USD)", "Financial", "retrieved", "company", "SEC companyfacts", "Company revenue is distinct from approved-product sales.", 7),
    field("daily_volume", "Last completed session volume", "Market", "retrieved", "company", "Same-provider daily bars", age=4),
    field("historical_prices", "Historical daily prices", "Market", "retrieved", "company", "Labeled saved provider history", age=4),
    field("avg_dollar_volume", "20-session average dollar volume", "Market", "calculated", "company", "Same-provider close and volume", "Mean of close × volume over the latest 20 completed daily sessions.", 4),
    field("momentum_30d", "30-session price change (%)", "Market", "calculated", "company", "Same-provider daily closes", "100 × (latest close / close 30 completed sessions earlier − 1).", 4),
]
BY_ID = {f["id"]: f for f in INPUT_FIELDS}

# Continue the registry already saved in the earlier setup draft. Keep its IDs,
# source/derived/model classifications and safety settings instead of substituting
# a different set of fifty fields.
REGISTRY_PATH = ROOT/"new-platform/backend/config/enrichment_field_registry.json"
REGISTRY = json.loads(REGISTRY_PATH.read_text())
FIELD_MAP = {
    "company_name": "company", "ticker": "ticker", "cik": "cik", "program_id": None,
    "nct_id": "nct_id", "drug_name": "drug", "indication": "indication", "trial_phase": "phase",
    "trial_status": "trial_status", "trial_start_date": "trial_start_date", "primary_completion_date": "primary_completion",
    "enrollment": "enrollment", "primary_endpoint": "primary_endpoint", "primary_endpoint_result": None,
    "p_value": "primary_p_values", "adverse_events": None, "comparator_effect": None,
    "application_number": "application_id", "application_type": "application_type", "application_status": "application_status",
    "pdufa_date": "pdufa_date", "priority_review": None, "fast_track": None, "breakthrough_therapy": None,
    "orphan_drug": None, "clinical_hold": None, "prior_crl": None,
    "cash_balance": "cash", "operating_cash_flow": "operating_cash_flow", "debt": "debt", "shares_outstanding": "shares",
    "revenue": "revenue", "financing_event": None, "cash_runway_months": "cash_runway", "dilution_pct": None,
    "last_price": "last_close", "daily_volume": "daily_volume", "historical_prices": "historical_prices",
    "market_cap": "market_cap", "avg_dollar_volume": "avg_dollar_volume", "relative_volume": "relative_volume",
    "momentum_30d": "momentum_30d", "realized_volatility": "volatility20", "clinical_score": None,
    "evidence_completeness": None, "regulatory_probability": None, "base_case_upside": None,
    "downside_estimate": None, "reward_risk_ratio": None, "expected_return": None,
}
GROUPS = {"identity": "Identity", "clinical": "Clinical", "regulatory": "FDA / regulatory", "financial": "Financial", "market": "Market", "assessment": "Assessments"}
LABELS = {"program_id": "Permanent Program ID", "p_value": "Reported primary p-values", "cash_balance": "Unrestricted cash (USD)",
          "last_price": "Last completed daily close (USD)", "financing_event": "Exact-program financing events",
          "evidence_completeness": "Available non-modeled fields (%)", "regulatory_probability": "Modeled regulatory probability",
          "base_case_upside": "Modeled base-case upside (%)", "downside_estimate": "Modeled downside (%)", "expected_return": "Modeled expected return (%)"}
RULES = {"program_id": "Permanent PDUFA numbers stay in the live program registry. They are not reassigned or inferred by this collector.",
         "evidence_completeness": "Fresh available fields / 44 non-modeled inputs × 100, excluding this metric. Availability is not scientific quality or list qualification.",
         "regulatory_probability": "Requires an explicitly recorded model, assumptions and calibration evidence. Research grades are not converted into probabilities.",
         "reward_risk_ratio": "Positive modeled upside / absolute negative modeled downside. Both source-reviewed inputs required.",
         "financing_event": "Separate event dates and sources remain under review until exact-program deal identity is adjudicated."}
FIELDS = []
for entry in REGISTRY["fields"]:
    key, mapped = entry["key"], FIELD_MAP[entry["key"]]
    original = BY_ID.get(mapped, {})
    FIELDS.append(field(key, LABELS.get(key) or original.get("label") or key.replace("_", " ").capitalize(),
                        GROUPS[entry["group"]], {"source": "retrieved", "derived": "calculated", "modeled": "modeled"}[entry["kind"]],
                        original.get("scope", "program"), original.get("source", entry["source"]), RULES.get(key, original.get("rule", "")), original.get("maxAgeDays", 90)))
assert len(FIELDS) == len(FIELD_MAP) == 50
assert Counter(f["kind"] for f in FIELDS) == {"retrieved": 35, "calculated": 10, "modeled": 5}


def day(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except (ValueError, TypeError):
        return None


def exact_day(value):
    return day(value) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value or "")) else None


def number(value):
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError, OverflowError):
        return None


def link(value):
    try:
        p = urlsplit(str(value or ""))
        return bool(p.scheme == "https" and p.hostname and not p.username and not p.password)
    except ValueError:
        return False


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_json(path, fallback):
    return json.loads(path.read_text()) if path.is_file() else fallback


def unique(items, key):
    grouped = defaultdict(list)
    for r in items:
        if r.get(key):
            grouped[r[key]].append(r)
    return {k: v[0] for k, v in grouped.items() if len(v) == 1}


class Issuer:
    def __init__(self, ticker, today):
        self.ticker, self.today = ticker, today
        self.sources, self.company, self.records = [], {}, {}

    def put(self, dest, key, value, url, observed="", retrieved="", *, state="OBSERVED", note=""):
        if value is None or value == "" or value == [] or value == {}:
            return
        if isinstance(value, float) and not math.isfinite(value):
            return
        observed, retrieved = str(observed or ""), str(retrieved or "")
        check = day(retrieved)
        if not link(url):
            state = "REVIEW"
            url = ""
        elif not check or check > self.today or (day(observed) and day(observed) > self.today):
            state = "REVIEW"
        elif (self.today - check).days > BY_ID[key]["maxAgeDays"] and state in READY:
            state = "STALE"
        if url not in self.sources:
            self.sources.append(url)
        dest[key] = [value, state, self.sources.index(url), observed, retrieved, note]

    def derive(self, dest, key, value, dependencies, note=""):
        deps = [dest.get(k) for k in dependencies]
        if not deps or any(c is None for c in deps):
            return
        state = "CALCULATED" if all(c[1] in READY for c in deps) else (
            "CONFLICTING" if any(c[1] == "CONFLICTING" for c in deps) else
            "REVIEW" if any(c[1] == "REVIEW" for c in deps) else "STALE")
        # Conservative lineage: calculations inherit the oldest input check.
        oldest = min(deps, key=lambda c: c[4] or "")
        self.put(dest, key, value, self.sources[oldest[2]], oldest[3], oldest[4], state=state, note=note)


def ema(values, period):
    if len(values) < period:
        return []
    result = [statistics.mean(values[:period])]
    for value in values[period:]:
        result.append(result[-1] + (2 / (period + 1)) * (value - result[-1]))
    return result


def market_metrics(bars):
    """Reject duplicate/invalid sessions rather than silently shorten history."""
    if not isinstance(bars, list) or not bars:
        return {}
    seen, ordered = set(), sorted(bars, key=lambda r: r.get("date", ""))
    for b in ordered:
        d, c, v = exact_day(b.get("date")), number(b.get("close")), number(b.get("volume"))
        if not d or d in seen or d.weekday() > 4 or c is None or c <= 0 or v is None or v < 0:
            raise ValueError("Invalid/duplicate market session")
        seen.add(d)
    closes = [float(b["close"]) for b in ordered]
    result = {"last_close": closes[-1]}
    for period in (20, 50, 200):
        if len(closes) >= period:
            result["sma" + str(period)] = statistics.mean(closes[-period:])
    if len(closes) >= 21:
        average = statistics.mean(float(b["volume"]) for b in ordered[-21:-1])
        result["avg_volume_20"] = average
        if average > 0:
            result["relative_volume"] = float(ordered[-1]["volume"]) / average
        returns = [math.log(closes[i] / closes[i-1]) for i in range(len(closes)-20, len(closes))]
        result["volatility20"] = statistics.stdev(returns) * math.sqrt(252) * 100
        result["avg_dollar_volume"] = statistics.mean(float(b["close"])*float(b["volume"]) for b in ordered[-20:])
    result["daily_volume"] = float(ordered[-1]["volume"])
    result["historical_prices"] = ordered
    if len(closes) >= 31:
        result["momentum_30d"] = 100*(closes[-1]/closes[-31]-1)
    if len(closes) >= 15:
        changes = [b-a for a, b in zip(closes, closes[1:])]
        gain = statistics.mean(max(c, 0) for c in changes[:14])
        loss = statistics.mean(max(-c, 0) for c in changes[:14])
        for change in changes[14:]:
            gain, loss = (gain*13+max(change, 0))/14, (loss*13+max(-change, 0))/14
        result["rsi14"] = 50 if gain == loss == 0 else 100 if loss == 0 else 100-100/(1+gain/loss)
        if all(number(b.get("high")) is not None and number(b.get("low")) is not None
               and float(b["high"]) >= float(b["close"]) >= float(b["low"]) > 0 for b in ordered):
            tr = [max(float(b["high"])-float(b["low"]), abs(float(b["high"])-closes[i-1]),
                      abs(float(b["low"])-closes[i-1])) for i, b in enumerate(ordered) if i]
            atr = statistics.mean(tr[:14])
            for value in tr[14:]:
                atr = (atr*13+value)/14
            result["atr14"] = atr
    if len(closes) >= 35:
        fast, slow = ema(closes, 12), ema(closes, 26)
        line = [a-b for a, b in zip(fast[14:], slow)]
        signal = ema(line, 9)[-1]
        result["macd"] = dict(line=line[-1], signal=signal, histogram=line[-1]-signal)
    return result


def financial_fields(issuer, snap, cik):
    if not snap:
        return
    evidence = snap.get("evidence") or {}
    url = evidence.get("companyfacts_url", "")
    if (str(snap.get("cik", "")).zfill(10) != str(cik).zfill(10) or not str(cik).isdigit()
            or url != f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"):
        return
    dest = issuer.company
    retrieved = snap.get("as_of", "")
    def fact(key, value, evidence_key, note=""):
        meta = evidence.get(evidence_key) or {}
        end, filed = day(meta.get("period_end")), day(meta.get("filed"))
        state = "OBSERVED"
        if (not end or not filed or filed > issuer.today or end > filed or not meta.get("accession")
                or meta.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A") or snap.get("review_flags")):
            state = "REVIEW"
        elif (issuer.today-end).days > 150:
            state = "STALE"
        issuer.put(dest, key, number(value), url, meta.get("period_end", ""), retrieved, state=state, note=note)
    if snap.get("cash_includes_restricted") is False:
        fact("cash", snap.get("cash_usd"), "cash")
    months = number(snap.get("operating_cash_flow_months"))
    fact("operating_cash_flow", snap.get("operating_cash_flow_usd"), "operating_cash_flow", f"Reported period: {months:g} months" if months else "Period not reported")
    fact("shares", snap.get("shares_outstanding"), "shares")
    fact("revenue", snap.get("company_revenue_usd"), "revenue")
    flow = number(snap.get("operating_cash_flow_usd"))
    if flow is not None and flow < 0 and months in (3, 12):
        issuer.derive(dest, "monthly_burn", -flow/months, ["operating_cash_flow"])
        if ("cash" in dest and dest["cash"][0] >= 0
                and dest["cash"][3] == dest.get("operating_cash_flow", [None]*4)[3]):
            issuer.derive(dest, "cash_runway", cash_runway_months(dest["cash"][0], flow*3/months), ["cash", "monthly_burn"])
    current, noncurrent = number(snap.get("current_debt_usd")), number(snap.get("noncurrent_debt_usd"))
    a, b = evidence.get("current_debt") or {}, evidence.get("noncurrent_debt") or {}
    if (current is not None and noncurrent is not None and a.get("period_end") == b.get("period_end")
            and b.get("accession") and b.get("form") in ("10-Q", "10-K", "10-Q/A", "10-K/A")
            and day(b.get("period_end")) and day(b.get("filed"))
            and day(b["period_end"]) <= day(b["filed"]) <= issuer.today):
        fact("debt", current+noncurrent, "current_debt", "Current + noncurrent debt; excludes unreported debt categories.")


def build(data_dir, *, today=None, now=None):
    data_dir = Path(data_dir)
    today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    now = now or datetime.now(timezone.utc).isoformat()
    required = {name: rows(data_dir/name) for name in UNIVERSE}
    if not required["all_phase_trials.csv"] or not required["pdufa_candidates.csv"]:
        raise ValueError("Required universe source is empty; previous publication retained")
    original = original_pipeline_universe(required, today)
    if not original:
        raise ValueError("Empty universe; previous publication retained")
    optional_names = ("company_registry.csv", "phase_pipeline_market_caps.csv", "second_financing_status.csv",
                      "gem_two_close_recheck.csv", "step7_market_status.csv", "prediction_engine_designations.csv",
                      "pdufa_source_verification.csv", "phase2_primary_p_evidence.csv", "approved_drug_sales_verified.csv")
    raw = {n: rows(data_dir/n) if (data_dir/n).is_file() else [] for n in optional_names}
    registry = unique(raw["company_registry.csv"], "ticker")
    caps = unique(raw["phase_pipeline_market_caps.csv"], "ticker")
    primary = unique(required["pdufa_candidates.csv"], "event_key")
    fda = unique(required["fda_review_engine.csv"], "event_key")
    financings = unique(raw["second_financing_status.csv"], "event_key")
    checks = unique(raw["gem_two_close_recheck.csv"], "event_key")
    designations = unique(raw["prediction_engine_designations.csv"], "event_key")
    market = unique(raw["step7_market_status.csv"], "ticker")
    market_intake = read_json(data_dir/"shared_market.json", {})
    shared_market = unique(market_intake.get("snapshots", []), "ticker")
    old_fin = read_json(data_dir/"gem_runway_evidence.json", {})
    extra_fin = read_json(data_dir/"shared_financials.json", {})
    financials = unique(old_fin.get("snapshots", []), "ticker")
    for ticker, snap in unique(extra_fin.get("snapshots", []), "ticker").items():
        if snap.get("as_of", "") > financials.get(ticker, {}).get("as_of", ""):
            financials[ticker] = snap
    reviews = read_json(data_dir/"candidate_assessment_reviews.json", {}).get("programs", {})
    membership = read_json(data_dir/"gem_stage_membership.json", {}).get("stages", {})
    active = {stage: {key for key, r in membership.get(stage, {}).get("entries", {}).items()
                      if r.get("status") == "ACTIVE"} for stage in ("GEM_JR", "GEM")}
    verified = defaultdict(list)
    for r in raw["pdufa_source_verification.csv"]:
        verified[(r.get("event_key"), r.get("claim"))].append(r)
    p_values, sales = defaultdict(list), defaultdict(list)
    for r in raw["phase2_primary_p_evidence.csv"]:
        p_values[(r.get("nct_id"), r.get("ticker"))].append(r)
    for r in raw["approved_drug_sales_verified.csv"]:
        sales[r.get("ticker")].append(r)
    issuers = {}
    for key, r in sorted(original.items()):
        ticker = r.get("ticker", "").upper()
        bucket = ticker if TICKER.fullmatch(ticker) else "UNRESOLVED"
        issuer = issuers.setdefault(bucket, Issuer(ticker, today))
        dest = {}
        issuer.records[key] = dict(ticker=ticker, drug=r.get("drug", ""), nctId=r.get("nct_id", ""),
                                   lists=["PIPELINE"]+[s for s in active if key in active[s]], fields=dest)
        source, observed, retrieved = r.get("source_url", ""), r.get("source_updated", ""), r.get("checked_at", "")
        for field_id, column in (("ticker", "ticker"), ("company", "company"), ("drug", "drug"),
                                 ("indication", "indication"), ("nct_id", "nct_id"), ("phase", "registered_phase"),
                                 ("trial_status", "status"), ("trial_start_date", "start_date"), ("primary_completion", "primary_completion"), ("results_posted", "results_posted")):
            value = r.get(column)
            issuer.put(dest, field_id, value, source, observed, retrieved)
        issuer.put(dest, "exact_key", key, BASE+"all_phase_trials.csv" if key.startswith("TRIAL|") else source,
                   observed, retrieved, state="CALCULATED")
        for output, input_key in (("days_to_completion", "primary_completion"), ("has_results", "results_posted")):
            value = exact_day(r.get(input_key))
            if value and (output != "has_results" or value <= today):
                issuer.derive(dest, output, value <= today if output == "has_results" else (value-today).days, [input_key])
        pv = p_values.get((r.get("nct_id"), ticker), [])
        if pv:
            issuer.put(dest, "primary_p_values", [{k: v.get(k) for k in ("primary_endpoint", "comparison", "p_value", "p_value_modifier")} for v in pv],
                       pv[0].get("source_url"), pv[0].get("protocol_last_update"), min(v.get("observed_at_utc", "") for v in pv))
            issuer.put(dest, "primary_endpoint", list(dict.fromkeys(v.get("primary_endpoint", "") for v in pv if v.get("primary_endpoint"))),
                       pv[0].get("source_url"), pv[0].get("protocol_last_update"), min(v.get("observed_at_utc", "") for v in pv))
        if key.startswith("APPLICATION|"):
            event = key[len("APPLICATION|"):]
            app, engine = primary.get(event, {}), fda.get(event, {})
            url, checked = app.get("pdufa_evidence_url", ""), app.get("last_checked", "")
            issuer.put(dest, "application_status", app.get("check_status"), url, "", checked, state="REVIEW", note="Saved monitoring status; FDA application status requires claim-level verification.")
            for output, value in (("application_id", engine.get("fda_application_identity")),
                                  ("application_type", app.get("application_type") if app.get("application_type") in ("NDA", "BLA", "sNDA", "sBLA") else None),
                                  ("submission_date", app.get("nda_submission_date")), ("acceptance_date", app.get("fda_acceptance_date")),
                                  ("decision_date", app.get("decision_date"))):
                issuer.put(dest, output, value if value not in ("UNKNOWN", "UNVERIFIED", "NOT VERIFIED") else None,
                           url, "", checked, state="REVIEW", note="Saved exact-event disclosure; claim-level verification required.")
            for output, claim, value in (("pdufa_date", "PDUFA_TARGET", app.get("pdufa_date")),
                                        ("fda_outcome", "FDA_DECISION", app.get("outcome"))):
                evidence = verified.get((event, claim), [])
                ok = len(evidence) == 1 and evidence[0].get("verification_status") == "VERIFIED"
                proof = evidence[0] if len(evidence) == 1 else {}
                if ok:
                    expected, observed_claim = str(proof.get("expected", "")).strip(), str(proof.get("observed", "")).strip()
                    ok = bool(value) and (str(value) in (expected, observed_claim) if claim == "PDUFA_TARGET"
                                          else str(value).strip().upper() in (expected+" "+observed_claim).upper().split())
                issuer.put(dest, output, value, proof.get("source_url") or url, "", proof.get("checked_at") or checked,
                           state="OBSERVED" if ok else "REVIEW", note=proof.get("reason", "Exact claim awaits source verification."))
            if exact_day(app.get("pdufa_date")):
                issuer.derive(dest, "days_to_pdufa", (day(app["pdufa_date"])-today).days, ["pdufa_date"])
            des = designations.get(event, {})
            positives = [k for k, v in des.items() if v.upper() in ("YES", "TRUE", "1", "CONFIRMED", "VERIFIED")
                         and k not in ("designation_audit_status",)]
            if positives:
                issuer.put(dest, "designations", positives, des.get("designation_source_url", ""), "", "", state="REVIEW",
                           note="Positive saved designations; original verification date is not recorded.")
            finance, check = financings.get(event, {}), checks.get(event, {})
            for ordinal in ("first", "second"):
                close, url = finance.get(ordinal+"_financing_date"), finance.get(ordinal+"_financing_source")
                # TRANSACTIONS_RECHECKED_REVIEW explicitly leaves separate deal
                # identity/ordinal association unadjudicated. Do not promote it.
                ok = (check.get("recheck_status") == "VERIFIED_SECOND_POST_PHASE3_FINANCING"
                      and check.get(ordinal+"_sec_status") == "VERIFIED" and check.get(ordinal+"_close_date") == close
                      and check.get(ordinal+"_sec_url") == url and bool(check.get(ordinal+"_sec_sha256")))
                issuer.put(dest, ordinal+"_financing", close, url, close, check.get("checked_at_utc") or finance.get("verified_as_of"),
                           state="OBSERVED" if ok else "REVIEW", note="Separate closing sequence requires exact-event SEC verification.")
        for output, review_key in (("regulatory_readiness", "regulatoryFeasibility"), ("clinical_strength", "effectSize"),
                                   ("milestone_success", "milestoneSuccess"), ("risk_adjusted_upside", "riskAdjustedUpside"),
                                   ("commercial_potential", "commercialPotential")):
            review = reviews.get(key, {}).get(review_key, {})
            grade = number(review.get("grade"))
            if grade in (0, 1, 2, 3, 4) and review.get("rationale") and review.get("measurements") is not None:
                source_date, reviewed = day(review.get("sourceDate")), day(review.get("reviewedAt"))
                state = "CONFLICTING" if review.get("conflict") else "MODELED" if source_date and reviewed and source_date <= reviewed <= today else "REVIEW"
                issuer.put(dest, output, dict(grade=grade, measurements=review["measurements"]), review.get("source"),
                           review.get("sourceDate"), review.get("reviewedAt"), state=state, note=review["rationale"])
    for bucket, issuer in issuers.items():
        ticker = issuer.ticker
        reg = registry.get(ticker, {})
        for output, value in (("cik", reg.get("cik10")), ("exchange", reg.get("exchange"))):
            issuer.put(issuer.company, output, value, BASE+"company_registry.csv", state="REVIEW", note="Saved issuer mapping; original verification timestamp unavailable.")
        cap = caps.get(ticker, {})
        issuer.put(issuer.company, "market_cap", number(cap.get("market_cap")), cap.get("market_cap_source"),
                   cap.get("market_cap_checked_at"), cap.get("market_cap_checked_at"),
                   state="OBSERVED" if cap.get("market_cap_status") == "VERIFIED" else "REVIEW")
        financial_fields(issuer, financials.get(ticker), reg.get("cik10", ""))
        m = market.get(ticker, {})
        try:
            bars = json.loads(m.get("price_bars_json") or "[]")
            remote = shared_market.get(ticker, {})
            if remote.get("session", "") >= m.get("last_session", "") and remote.get("bars"):
                bars = remote["bars"]
                m = dict(market_source=remote.get("source"), last_session=remote.get("session"), checked_at_utc=remote.get("checkedAt"))
                provider_note = "Alpaca " + remote.get("feed", "") + "; split-adjusted; " + ("single-exchange volume." if remote.get("feed") == "IEX" else "consolidated feed.")
            else:
                provider_note = "Saved provider history; no cross-provider bar mixing."
            session = day(m.get("last_session"))
            stale = not session or not 0 <= (today-session).days <= 4
            for field_id, value in market_metrics(bars).items():
                issuer.put(issuer.company, field_id, value, m.get("market_source"), m.get("last_session"), m.get("checked_at_utc"),
                           state="STALE" if stale else "OBSERVED" if field_id in ("last_close", "daily_volume", "historical_prices") else "CALCULATED", note=provider_note)
        except (ValueError, TypeError, KeyError):
            pass
        disclosed = sales.get(ticker, [])
        if disclosed:
            issuer.put(issuer.company, "approved_sales", [{k: v.get(k) for k in ("approved_product", "period", "individual_sales", "currency", "source_url")} for v in disclosed],
                       disclosed[0].get("source_url"), "", min(v.get("verified_on", "") for v in disclosed), note="Separate product/period disclosures; no sum across periods.")
    # Project observations onto the original draft registry. Additional existing
    # chart metrics are not substituted for its clinical/safety fields.
    for issuer in issuers.values():
        old_company = issuer.company
        issuer.company = {f["id"]: old_company[FIELD_MAP[f["id"]]] for f in FIELDS
                          if f["scope"] == "company" and FIELD_MAP[f["id"]] in old_company}
        for record in issuer.records.values():
            old = record["fields"]
            record["fields"] = {f["id"]: old[FIELD_MAP[f["id"]]] for f in FIELDS
                                if f["scope"] == "program" and FIELD_MAP[f["id"]] in old}
            dest = record["fields"]
            designation = old.get("designations")
            if designation:
                for name in ("priority_review", "fast_track", "breakthrough_therapy", "orphan_drug"):
                    if name in designation[0]:
                        dest[name] = [True, *designation[1:]]
            dates = {name: old[name][0] for name in ("first_financing", "second_financing") if name in old}
            if dates:
                cell = old.get("first_financing") or old["second_financing"]
                dest["financing_event"] = [dates, "REVIEW", *cell[2:]]
            available = sum((issuer.company if f["scope"] == "company" else dest).get(f["id"], [None, "MISSING"])[1] in READY
                            for f in FIELDS if f["kind"] != "modeled" and f["id"] != "evidence_completeness")
            report_url = BASE+"shared_enrichment/index.json"
            if report_url not in issuer.sources:
                issuer.sources.append(report_url)
            dest["evidence_completeness"] = [available/44*100, "CALCULATED", issuer.sources.index(report_url), today.isoformat(), now,
                                             "Calculated at publication from 44 non-modeled inputs; not a trial quality or qualification score."]
    counts = {s: {"records": 0, "fields": {f["id"]: dict(Counter({state: 0 for state in STATES})) for f in FIELDS}} for s in ("PIPELINE", "GEM_JR", "GEM")}
    for issuer in issuers.values():
        for record in issuer.records.values():
            for stage in record["lists"]:
                counts[stage]["records"] += 1
                for f in FIELDS:
                    cell = (issuer.company if f["scope"] == "company" else record["fields"]).get(f["id"])
                    counts[stage]["fields"][f["id"]][cell[1] if cell else "MISSING"] += 1
    manifests = []
    for name in sorted(set(UNIVERSE+optional_names+("gem_runway_evidence.json", "shared_financials.json", "shared_market.json", "candidate_assessment_reviews.json", "gem_stage_membership.json"))):
        p = data_dir/name
        manifests.append(dict(file=name, available=p.is_file(), sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None))
    index = dict(schemaVersion=1, generatedAt=now, asOf=today.isoformat(), status="PARTIAL", fields=FIELDS, lists=counts,
                 registrySha256=hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest(),
                 companyCount=len(issuers), sourceFiles=manifests,
                 financialCollection={k: extra_fin.get(k) for k in ("status", "configuration", "attempted", "collected", "remaining", "generatedAt")},
                 marketCollection={k: market_intake.get(k) for k in ("status", "configuration", "attempted", "collected", "remaining", "generatedAt", "feed")},
                 note="50 shared research fields. Field availability is separate from selected restrictions and list qualification. FS/FA and saved list selections are unchanged.")
    payloads = {bucket: dict(schemaVersion=1, ticker=issuer.ticker, generatedAt=now, asOf=today.isoformat(),
                            sources=issuer.sources, company=issuer.company, records=issuer.records) for bucket, issuer in issuers.items()}
    return index, payloads


def publish(data_dir, *, today=None):
    index, payloads = build(data_dir, today=today)
    target = Path(data_dir)/"shared_enrichment"
    target.mkdir(parents=True, exist_ok=True)
    shards = target/"records"
    shards.mkdir(exist_ok=True)
    for key, payload in payloads.items():
        p = shards/(key+".json")
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False)+"\n")
        tmp.replace(p)
    # Index last: never mark a failed/incomplete build as a new successful run.
    p = target/"index.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(index, separators=(",", ":"), ensure_ascii=False, allow_nan=False)+"\n")
    tmp.replace(p)
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data")
    args = parser.parse_args()
    result = publish(args.data_dir)
    print(json.dumps({"status": result["status"], "fields": len(result["fields"]), "companies": result["companyCount"],
                      "records": {s: v["records"] for s, v in result["lists"].items()}}))
