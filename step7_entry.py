"""Step 7 source-gated post-Phase-3 entry eligibility.

Only exact event and NCT identity joins; no fuzzy ticker-only trial success.
All verdicts are fail-closed. Source URLs/attestations are assertions, not
independent SEC or clinical source-document verification by this program.
"""
from __future__ import annotations

import csv
import math
import re
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

FIELDS = (
    "event_key", "nct_id", "ticker", "drug", "reviewer", "reviewed_at",
    "phase3_readout_date", "phase3_readout_source", "phase3_readout_source_date",
    "primary_endpoint_status", "primary_endpoint_source",
    "clinically_meaningful_benefit", "effect_size", "confidence_interval",
    "benefit_review_source", "safety_review_status", "safety_review_source",
    "financing_closures_attested", "financing_closure_review_source",
    "atm_dilution_status", "atm_dilution_source", "atm_reviewed_at",
    "post_readout_setup_attested", "market_review_source", "market_reviewed_at",
)
GATES = ("trial_identity", "phase3_primary", "clinical_benefit",
         "safety", "second_financing", "no_unresolved_dilution",
         "post_readout_price_base", "normalized_volume")
NCT = re.compile(r"^NCT\d{8}$")
EVENT = re.compile(r"^[A-Z0-9.-]{1,12}\|[A-Z0-9_]+$")


def day(raw):
    try:
        return date.fromisoformat(str(raw or "").strip()[:10])
    except ValueError:
        return None


def safe_source(url, *, sec=False):
    try:
        u = urlparse(str(url or "").strip())
        host = (u.hostname or "").lower()
        if u.scheme != "https" or not host:
            return False
        if u.username or u.password or u.port not in (None, 443):
            return False
        if sec:
            return (host in {"www.sec.gov", "sec.gov"} and
                    u.path.startswith("/Archives/edgar/data/"))
        return True
    except ValueError:
        return False


def dated_source(row, source, checked, today, days=45, *, sec=False):
    check = day(row.get(checked))
    return bool(safe_source(row.get(source), sec=sec) and check
                and today - timedelta(days=days) <= check <= today)


def read_evidence(path):
    path = Path(path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        data = list(csv.DictReader(f))
    exact = {}
    for row in data:
        key = (row.get("event_key") or "").strip()
        if EVENT.fullmatch(key):
            # Duplicate keys deliberately invalidate evidence; never quietly
            # select an arbitrary "most recent" approval attestation.
            if key in exact:
                exact[key] = None
            else:
                exact[key] = row
    return exact


def sample_template(events):
    """Blank evidence-entry template, not a set of certifications."""
    result = []
    for row in events:
        key = str(row.get("Exact financing event") or row.get("event_key") or "")
        if not EVENT.fullmatch(key):
            continue
        record = {field: "" for field in FIELDS}
        record.update({"event_key": key, "ticker": key.split("|",1)[0],
                       "drug": row.get("Drug", "")})
        result.append(record)
    return result


def parse_bars(value):
    """30+ preserved raw EOD close/volume rows, not summary metrics alone."""
    import json
    if not value:
        return []
    try:
        data = json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list) or len(data) > 90:
        return []
    found = {}
    for item in data:
        try:
            session = day(item.get("date"))
            close = float(item.get("close"))
            volume = float(item.get("volume"))
            if not session or not math.isfinite(close) or close <= 0 or not math.isfinite(volume) or volume <= 0:
                return []
            if session in found:
                return []
            found[session] = (close, volume)
        except (TypeError, ValueError, AttributeError):
            return []
    return [(d, *found[d]) for d in sorted(found)]


def analyze_post_readout_market(raw_bars, readout, as_of):
    """Transparent conservative mechanical base/volume observations.

    Not an independent chart certification; cannot replace a dated human
    technical review. Require >=10 complete trading bars AFTER readout,
    >=20 bars for the prior-volume comparison and a recent last session.
    """
    obs = {"price_base": "NOT VERIFIED", "volume_normalized": "NOT VERIFIED",
           "last_session": "", "range10_pct": None, "volume5_vs_prior20": None}
    bars = parse_bars(raw_bars)
    start = day(readout)
    today = day(as_of)
    if not start or not today or start >= today or len(bars) < 31:
        return obs
    if bars[-1][0] > today or (today - bars[-1][0]).days > 5:
        return obs
    if sum(d > start and d <= today for d, _, _ in bars) < 10:
        return obs
    closing = [p for _,p,_ in bars[-10:]]
    band = (max(closing) / min(closing) - 1) * 100
    prior_volume = [v for _,_,v in bars[-25:-5]]
    recent_volume = [v for _,_,v in bars[-5:]]
    if len(prior_volume) != 20 or min(prior_volume) <= 0:
        return obs
    ratio = (sum(recent_volume)/5) / (sum(prior_volume)/20)
    obs.update({
        "last_session": bars[-1][0].isoformat(),
        "range10_pct": round(band, 2),
        "volume5_vs_prior20": round(ratio, 3),
        "price_base": "MECHANICAL PASS — MANUAL REVIEW REQUIRED" if band <= 15 else "NOT STABILIZED",
        "volume_normalized": "MECHANICAL PASS — MANUAL REVIEW REQUIRED" if 0.50 <= ratio <= 1.25 else "NOT NORMALIZED",
    })
    return obs


def evaluate_entry(event, evidence, financing, sec_recheck, market, now):
    """Return auditable gating; never infer facts from status keywords alone."""
    now = now.date() if isinstance(now, datetime) else now
    key = event.get("event_key", "")
    gates = {k:"REVIEW — EVIDENCE MISSING" for k in GATES}
    reasons = []
    attested = evidence or {}
    if not EVENT.fullmatch(key) or not isinstance(attested, dict):
        return {"event_key":key,"verdict":"REVIEW — MISSING EXACT-EVENT EVIDENCE",
                "gates":gates,"market_observations":{}}
    expected_ticker = key.split("|",1)[0]
    reg_nct = str(event.get("nct_id") or "").strip().upper()
    readout = day(attested.get("phase3_readout_date"))
    release_source_date = day(attested.get("phase3_readout_source_date"))
    # Phase 3 readouts can precede PDUFA by many months; only the review
    # must be recent, while the original announcement date must fit the event.
    readout_provenance = bool(
        readout and release_source_date and
        readout <= release_source_date <= min(readout + timedelta(days=30), now)
        and safe_source(attested.get("phase3_readout_source")))
    identity_ok = (reg_nct and NCT.fullmatch(reg_nct)
                   and reg_nct == str(attested.get("nct_id") or "").upper().strip()
                   and expected_ticker == str(attested.get("ticker") or "").strip().upper()
                   and str(attested.get("drug") or "").strip().casefold() ==
                       str(event.get("drug") or "").strip().casefold()
                   and bool(str(attested.get("reviewer") or "").strip())
                   and readout_provenance)
    if identity_ok: gates["trial_identity"] = "PASS — REVIEWER ATTESTED EXACT NCT + DRUG"
    reviewed = day(attested.get("reviewed_at"))
    if identity_ok and readout and readout <= now and reviewed and 0 <= (now-reviewed).days <= 30:
        if (str(attested.get("primary_endpoint_status") or "").upper() == "MET"
                and safe_source(attested.get("primary_endpoint_source"))):
            gates["phase3_primary"] = "PASS — REVIEWER ATTESTED PRIMARY ENDPOINT"
        if (str(attested.get("clinically_meaningful_benefit") or "").upper() == "YES"
                and str(attested.get("effect_size") or "").strip()
                and str(attested.get("confidence_interval") or "").strip()
                and safe_source(attested.get("benefit_review_source"))):
            gates["clinical_benefit"] = "PASS — REVIEWER ATTESTED BENEFIT / EFFECT / CI"
        if (str(attested.get("safety_review_status") or "").upper() == "NO_CRITICAL_UNRESOLVED"
                and safe_source(attested.get("safety_review_source"))):
            gates["safety"] = "PASS — REVIEWER ATTESTED SAFETY"
    first = day(financing.get("first_financing_date"))
    second = day(financing.get("second_financing_date"))
    fin_review = day(financing.get("verified_as_of"))
    sec_checked = day(sec_recheck.get("last_successful_recheck_utc"))
    sec_status = str(sec_recheck.get("financing_status") or "").upper()
    sec_ok = (sec_checked and 0 <= (now-sec_checked).days <= 2
              and sec_status not in {"SOURCE_BLOCKED_RETAINED","PARTIAL_SOURCE_REVIEW",
                                     "NO_SOURCE","SOURCE_UNAVAILABLE","NOT_CHECKED"}
              and "BLOCKED" not in sec_status and "ERROR" not in sec_status)
    closures_ok = (identity_ok and readout and first and second and
                   readout <= first < second <= now
                   and fin_review and 0 <= (now-fin_review).days <= 30
                   and str(financing.get("second_financing_closed") or "").upper() == "YES"
                   and str(financing.get("second_financing_audit_status") or "").upper() == "VERIFIED_SECOND_POST_PHASE3_FINANCING"
                   and safe_source(financing.get("first_financing_source"),sec=True)
                   and safe_source(financing.get("second_financing_source"),sec=True)
                   and sec_ok
                   and str(attested.get("financing_closures_attested") or "").upper() == "YES"
                   and safe_source(attested.get("financing_closure_review_source"),sec=True))
    if closures_ok:
        gates["second_financing"] = "PASS — REVIEWED ORDERED POST-READOUT SEC CLOSURES"
    if closures_ok and dated_source(attested, "atm_dilution_source", "atm_reviewed_at", now, days=7, sec=True):
        if str(attested.get("atm_dilution_status") or "").upper() == "NO_ACTIVE_UNRESOLVED":
            gates["no_unresolved_dilution"] = "PASS — REVIEWER ATTESTED NO UNRESOLVED ATM/DILUTION"
    market_now = day(market.get("checked_at_utc"))
    valid_market = (
        market_now is not None and 0 <= (now-market_now).days <= 2
        and market.get("market_status") == "MARKET_UPDATED"
        and safe_source(market.get("market_source"))
        and market.get("last_session_freshness") == "RECENT EOD")
    observation = analyze_post_readout_market(market.get("price_bars_json"), readout, now) if valid_market else {}
    market_review = (
        identity_ok and dated_source(attested, "market_review_source","market_reviewed_at",now,days=5)
        and str(attested.get("post_readout_setup_attested") or "").upper() == "YES")
    if market_review and observation.get("price_base","").startswith("MECHANICAL PASS"):
        gates["post_readout_price_base"] = "PASS — MEASURED BASE + REVIEWER ATTESTED"
    if market_review and observation.get("volume_normalized","").startswith("MECHANICAL PASS"):
        gates["normalized_volume"] = "PASS — MEASURED VOLUME + REVIEWER ATTESTED"
    pdufa = day(event.get("pdufa_date"))
    resolved = (str(event.get("outcome") or "").upper() in
                {"APPROVED","CRL","REJECTED","WITHDRAWN","REFUSED"}
                or str(event.get("check_status") or "").upper().startswith("RESOLVED_")
                or str(event.get("monitor_eligibility") or "").upper() == "EXCLUDED")
    expired = bool(pdufa and pdufa < now)
    if resolved or expired:
        verdict = "EXCLUDED — DECIDED OR PAST PDUFA"
    elif not pdufa:
        verdict = "REVIEW — VERIFIED PDUFA DATE MISSING"
    elif all(g.startswith("PASS") for g in gates.values()):
        verdict = "ENTRY READY — ATTESTED EVIDENCE / NOT INDEPENDENTLY AUDITED"
    else:
        verdict = "REVIEW — ENTRY GATES NOT CLEARED"
    for name,val in gates.items():
        if not val.startswith("PASS"):
            reasons.append(name+": "+val)
    return {"event_key":key,"verdict":verdict,"gates":gates,
            "market_observations":observation,"missing":reasons,
            "clinical_verification":"REVIEWER ATTESTED, NOT AUTOMATICALLY VERIFIED BY ISSUER API"
                if gates["phase3_primary"].startswith("PASS") else "NOT VERIFIED",
            "source_note":"Reviewer-attested evidence is not independently validated from linked SEC/issuer documents by this engine."}
