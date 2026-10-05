#!/usr/bin/env python3
"""Build a 2024 PDUFA historical cohort for $300M-$10B public companies.

Decision-safety rules
---------------------
1. Candidate universe is frozen in this file from independent 2024 PDUFA/FDA calendars.
2. Prediction evidence is SEC filing text filed no later than the earlier of:
   (a) PDUFA date - 1 day, or (b) actual FDA action date - 1 day.
3. The 2025 frozen eight-feature StandardScaler + LogisticRegression model is reused
   exactly; it is NOT refit on 2024 outcomes.
4. FDA outcomes are joined only after p_approval/model_class have been calculated.
5. Historical market cap is reconstructed near the event using a historical close
   and the latest SEC shares-outstanding fact filed by the cutoff.
6. Only $0.300B <= market cap <= $10.000B enters prediction_engine_history.csv.

This script also writes a staging/audit CSV so excluded or unresolved candidates
remain visible instead of disappearing silently.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HISTORY_PATH = DATA / "prediction_engine_history.csv"
AUDIT_PATH = DATA / "prediction_engine_audit.csv"
STAGING_PATH = DATA / "prediction_engine_2024_staging.csv"

SEC_UA = "PDUFA Research System asirifernandoc@gmail.com"
SEC_HEADERS = {
    "User-Agent": SEC_UA,
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}
SEC_DATA_HEADERS = {
    "User-Agent": SEC_UA,
    "Accept-Encoding": "gzip, deflate",
}
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": SEC_UA})

# Exact frozen model copied from 2025_L8_FROZEN_MODEL_SPEC.json.
FEATURES = [
    "efficacy_positive",
    "safety_risk",
    "cmc_risk",
    "reg_positive",
    "adcom",
    "prior_crl",
    "predecision_source_count",
    "predecision_text_chars",
]
SCALER_MEAN = np.array([
    0.2638888888888889,
    0.2777777777777778,
    0.6388888888888888,
    0.4027777777777778,
    0.06944444444444445,
    0.18055555555555555,
    9.347222222222221,
    36032.944444444445,
], dtype=float)
SCALER_SCALE = np.array([
    0.4407397681284009,
    0.4479032082388083,
    0.48032267960529396,
    0.4904567661947104,
    0.25420840580171006,
    0.38464951178128415,
    8.770467683941474,
    31657.2622609414,
], dtype=float)
INTERCEPT = 0.7238153805239734
COEFFICIENTS = np.array([
    0.31808835889768905,
    0.26438610689314707,
    -0.6710020725341329,
    -0.23183401071398632,
    0.6085977094504821,
    -0.7247571965663959,
    0.5335803565990395,
    0.47979991055063004,
], dtype=float)

# Candidate calendar: US-listed biotech/pharma exposures identified from 2024
# PDUFA calendars and primary FDA/company records. Market-cap filtering happens
# later, so sub-$300M and >$10B names can remain here for transparent exclusion.
BLIND_EVENTS = [
    # ticker, PDUFA date, action date, drug / application
    ("LGND", "2024-01-05", "2024-01-05", "berdazimer / ZELSUVMI"),
    ("IOVA", "2024-02-24", "2024-02-16", "lifileucel / AMTAGVI"),
    ("NERV", "2024-02-26", "2024-02-27", "roluperidone"),
    ("EYEN", "2024-03-04", "2024-03-04", "APP13007 / clobetasol"),
    ("MDGL", "2024-03-14", "2024-03-14", "resmetirom / REZDIFFRA"),
    ("AKBA", "2024-03-27", "2024-03-27", "vadadustat / VAFSEO"),
    ("CRSP", "2024-03-30", "2024-01-16", "exa-cel / CASGEVY TDT"),
    ("SUPN", "2024-04-05", "2024-04-08", "SPN-830"),
    ("ABEO", "2024-05-25", "2024-04-22", "pz-cel"),
    ("IBRX", "2024-04-23", "2024-04-22", "nogapendekin alfa inbakicept / ANKTIVA"),
    ("AQST", "2024-04-28", "2024-04-26", "diazepam buccal film / LIBERVANT"),
    ("DAWN", "2024-04-30", "2024-04-23", "tovorafenib / OJEMDA"),
    ("XFOR", "2024-04-30", "2024-04-26", "mavorixafor / XOLREMDI"),
    ("GNFT", "2024-06-10", "2024-06-10", "elafibranor / IQIRVO"),
    ("GERN", "2024-06-16", "2024-06-06", "imetelstat / RYTELO"),
    ("VRNA", "2024-06-26", "2024-06-26", "ensifentrine / OHTUVAYRE"),
    ("RCKT", "2024-06-30", "2024-06-28", "marnetegragene autotemcel / KRESLADI"),
    ("PHAT", "2024-07-19", "2024-07-18", "vonoprazan / VOQUEZNA non-erosive GERD"),
    ("ADAP", "2024-08-04", "2024-08-02", "afamitresgene autoleucel / TECELRA"),
    ("HUMA", "2024-08-10", "2024-12-19", "acellular tissue engineered vessel / SYMVESS"),
    ("CTXR", "2024-08-13", "2024-08-08", "denileukin diftitox / LYMPHIR"),
    ("ASND", "2024-08-14", "2024-08-09", "palopegteriparatide / YORVIPATH"),
    ("AGIO", "2024-08-20", "2024-08-06", "vorasidenib / VORANIGO"),
    ("SNDX", "2024-08-28", "2024-08-14", "axatilimab / NIKTIMVO"),
    ("VNDA", "2024-09-18", "2024-09-18", "tradipitant"),
    ("ZVRA", "2024-09-21", "2024-09-20", "arimoclomol / MIPLYFFA"),
    ("SPRY", "2024-10-02", "2024-08-09", "epinephrine nasal spray / neffy"),
    ("ITRM", "2024-10-25", "2024-10-25", "sulopenem etzadroxil/probenecid / ORLYNVAH"),
    ("DERM", "2024-11-04", "2024-11-04", "DFD-29 / EMROSI"),
    ("PTCT", "2024-11-13", "2024-11-13", "eladocagene exuparvovec / KEBILIDI"),
    ("AUTL", "2024-11-16", "2024-11-08", "obecabtagene autoleucel / AUCATZYL"),
    ("APLT", "2024-11-28", "2024-11-27", "govorestat"),
    ("BBIO", "2024-11-29", "2024-11-22", "acoramidis / ATTRUBY"),
    ("JAZZ", "2024-11-29", "2024-11-20", "zanidatamab / ZIIHERA"),
    ("SNDX", "2024-12-26", "2024-11-15", "revumenib / REVUFORJ"),
    ("IONS", "2024-12-19", "2024-12-19", "olezarsen / TRYNGOLZA"),
    ("LXRX", "2024-12-20", "2024-12-20", "sotagliflozin / ZYNQUISTA"),
    ("CKPT", "2024-12-28", "2024-12-13", "cosibelimab / UNLOXCYT"),
    ("NBIX", "2024-12-29", "2024-12-13", "crinecerfont / CRENESSITY"),
]

# Outcome reveal is deliberately separate from BLIND_EVENTS and is joined only
# after features and frozen-model predictions are calculated.
OUTCOMES = {
    "LGND|2024-01-05": "APPROVED",
    "IOVA|2024-02-24": "APPROVED",
    "NERV|2024-02-26": "CRL",
    "EYEN|2024-03-04": "APPROVED",
    "MDGL|2024-03-14": "APPROVED",
    "AKBA|2024-03-27": "APPROVED",
    "CRSP|2024-03-30": "APPROVED",
    "SUPN|2024-04-05": "CRL",
    "ABEO|2024-05-25": "CRL",
    "IBRX|2024-04-23": "APPROVED",
    "AQST|2024-04-28": "APPROVED",
    "DAWN|2024-04-30": "APPROVED",
    "XFOR|2024-04-30": "APPROVED",
    "GNFT|2024-06-10": "APPROVED",
    "GERN|2024-06-16": "APPROVED",
    "VRNA|2024-06-26": "APPROVED",
    "RCKT|2024-06-30": "CRL",
    "PHAT|2024-07-19": "APPROVED",
    "ADAP|2024-08-04": "APPROVED",
    "HUMA|2024-08-10": "APPROVED",
    "CTXR|2024-08-13": "APPROVED",
    "ASND|2024-08-14": "APPROVED",
    "AGIO|2024-08-20": "APPROVED",
    "SNDX|2024-08-28": "APPROVED",
    "VNDA|2024-09-18": "CRL",
    "ZVRA|2024-09-21": "APPROVED",
    "SPRY|2024-10-02": "APPROVED",
    "ITRM|2024-10-25": "APPROVED",
    "DERM|2024-11-04": "APPROVED",
    "PTCT|2024-11-13": "APPROVED",
    "AUTL|2024-11-16": "APPROVED",
    "APLT|2024-11-28": "CRL",
    "BBIO|2024-11-29": "APPROVED",
    "JAZZ|2024-11-29": "APPROVED",
    "SNDX|2024-12-26": "APPROVED",
    "IONS|2024-12-19": "APPROVED",
    "LXRX|2024-12-20": "CRL",
    "CKPT|2024-12-28": "APPROVED",
    "NBIX|2024-12-29": "APPROVED",
}

OUTCOME_SOURCES = {
    "NERV|2024-02-26": "https://ir.minervaneurosciences.com/node/11406/pdf",
    "SUPN|2024-04-05": "https://ir.supernus.com/news-releases/news-release-details/supernus-provides-regulatory-update-spn-830-0",
    "ABEO|2024-05-25": "https://investors.abeonatherapeutics.com/news-events/press-releases/detail/276/abeona-therapeutics-provides-regulatory-update-on-pz-cel",
    "RCKT|2024-06-30": "https://ir.rocketpharma.com/news-releases/news-release-details/rocket-pharmaceuticals-provides-regulatory-update-kresladitm",
    "APLT|2024-11-28": "https://ir.appliedtherapeutics.com/node/9861/pdf",
    "LXRX|2024-12-20": "https://investors.lexpharma.com/news-releases/news-release-details/lexicon-announces-receipt-complete-response-letter-zynquistatm",
}

FORMS = {
    "8-K", "10-K", "10-Q", "20-F", "6-K", "S-1", "S-3", "F-1", "F-3",
    "424B3", "424B4", "424B5", "DEF 14A", "PRE 14A", "SC 14D9",
}

KEY_TERMS = [
    "pdufa", "food and drug administration", "fda", "phase 3", "phase iii",
    "primary endpoint", "complete response letter", "crl", "priority review",
    "breakthrough", "fast track", "advisory committee", "adcom", "manufactur",
    "cgmp", "safety", "serious adverse", "statistically significant",
]

def get_json(url: str) -> dict[str, Any]:
    r = SESSION.get(url, headers=SEC_DATA_HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def get_text(url: str) -> str:
    r = SESSION.get(url, headers=SEC_DATA_HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def load_ticker_map() -> dict[str, dict[str, Any]]:
    raw = get_json("https://www.sec.gov/files/company_tickers.json")
    out = {}
    for row in raw.values():
        out[str(row["ticker"]).upper()] = {
            "cik": int(row["cik_str"]),
            "title": row.get("title", ""),
        }
    return out


def filing_rows(cik: int) -> list[dict[str, Any]]:
    cik10 = f"{cik:010d}"
    base = get_json(f"https://data.sec.gov/submissions/CIK{cik10}.json")
    rows: list[dict[str, Any]] = []

    def add_recent(recent: dict[str, list[Any]]) -> None:
        n = len(recent.get("filingDate", []))
        for i in range(n):
            rows.append({k: (v[i] if i < len(v) else "") for k, v in recent.items()})

    add_recent(base.get("filings", {}).get("recent", {}))
    for item in base.get("filings", {}).get("files", []) or []:
        name = item.get("name")
        if not name:
            continue
        try:
            older = get_json(f"https://data.sec.gov/submissions/{name}")
            add_recent(older)
        except Exception:
            pass
        time.sleep(0.11)

    # accession is the stable de-duplication key.
    dedup = {}
    for row in rows:
        acc = str(row.get("accessionNumber") or "")
        if acc:
            dedup[acc] = row
    return list(dedup.values())


def filing_url(cik: int, accession: str, primary_doc: str) -> str:
    acc = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{primary_doc}"


def plain_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def relevant_snippet(text: str, width: int = 1200) -> str:
    low = text.lower()
    hits = [low.find(term) for term in KEY_TERMS if low.find(term) >= 0]
    if hits:
        pos = min(hits)
        start = max(0, pos - 250)
    else:
        start = 0
    return text[start:start + width]


def collect_predecision_evidence(cik: int, cutoff: date, lookback_days: int = 730) -> tuple[list[dict[str, Any]], str]:
    start = cutoff - timedelta(days=lookback_days)
    rows = []
    for f in filing_rows(cik):
        try:
            fdate = datetime.strptime(str(f.get("filingDate")), "%Y-%m-%d").date()
        except Exception:
            continue
        if not (start <= fdate <= cutoff):
            continue
        form = str(f.get("form") or "")
        if form not in FORMS and not form.startswith("424B"):
            continue
        doc = str(f.get("primaryDocument") or "")
        acc = str(f.get("accessionNumber") or "")
        if not doc or not acc:
            continue
        url = filing_url(cik, acc, doc)
        try:
            txt = plain_text(get_text(url))
            snippet = relevant_snippet(txt)
        except Exception:
            continue
        if not snippet:
            continue
        rows.append({
            "filing_date": fdate.isoformat(),
            "form": form,
            "url": url,
            "snippet": snippet,
        })
        time.sleep(0.12)

    rows.sort(key=lambda x: x["filing_date"], reverse=True)
    combined = " ".join(r["snippet"] for r in rows).lower()
    return rows, combined


def contains_any(text: str, terms: list[str]) -> int:
    return int(any(term in text for term in terms))


def feature_vector(rows: list[dict[str, Any]], text: str) -> dict[str, float]:
    return {
        "efficacy_positive": contains_any(text, [
            "met the primary endpoint", "met its primary endpoint", "met both primary endpoints",
            "met both co-primary", "statistically significant", "positive phase 3",
            "positive phase iii", "positive topline", "positive top-line",
            "clinically meaningful improvement",
        ]),
        "safety_risk": contains_any(text, [
            "safety concern", "safety signal", "clinical hold", "serious adverse event",
            "serious treatment-emergent", "fatal adverse", "patient death",
            "treatment-related death", "boxed warning",
        ]),
        "cmc_risk": contains_any(text, [
            "manufacturing", "chemistry manufacturing and controls", "chemistry, manufacturing and controls",
            " cgm", "cgmp", "pre-license inspection", "pre-approval inspection",
            "manufacturing facility", "facility inspection",
        ]),
        "reg_positive": contains_any(text, [
            "priority review", "breakthrough therapy", "fast track designation",
            "regenerative medicine advanced therapy", "rmat designation",
        ]),
        "adcom": contains_any(text, ["advisory committee", "adcom"]),
        "prior_crl": contains_any(text, ["complete response letter", " crl"]),
        "predecision_source_count": float(len(rows)),
        "predecision_text_chars": float(len(text)),
    }


def frozen_probability(feats: dict[str, float]) -> float:
    x = np.array([float(feats[k]) for k in FEATURES], dtype=float)
    z = (x - SCALER_MEAN) / SCALER_SCALE
    logit = INTERCEPT + float(np.dot(COEFFICIENTS, z))
    return 1.0 / (1.0 + math.exp(-logit))


def shares_outstanding(cik: int, cutoff: date) -> tuple[float | None, str]:
    cik10 = f"{cik:010d}"
    try:
        facts = get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json")
    except Exception:
        return None, "SEC_COMPANYFACTS_ERROR"
    dei = facts.get("facts", {}).get("dei", {})
    fact = dei.get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    candidates = []
    for item in fact:
        try:
            filed = datetime.strptime(str(item.get("filed")), "%Y-%m-%d").date()
            end = datetime.strptime(str(item.get("end")), "%Y-%m-%d").date()
            val = float(item.get("val"))
        except Exception:
            continue
        # Filed-by-cutoff blocks future filings from leaking later share counts.
        if filed <= cutoff and end <= cutoff + timedelta(days=45) and val > 0:
            candidates.append((end, filed, val, item.get("form", "")))
    if not candidates:
        return None, "SEC_SHARES_NOT_FOUND"
    candidates.sort(key=lambda x: (x[0], x[1]))
    end, filed, val, form = candidates[-1]
    return val, f"SEC_COMPANYFACTS:{form}:{end.isoformat()}:{filed.isoformat()}"


def historical_close(ticker: str, anchor: date) -> tuple[float | None, str]:
    start = anchor - timedelta(days=10)
    end = anchor + timedelta(days=2)
    try:
        px = yf.Ticker(ticker).history(
            start=start.isoformat(),
            end=end.isoformat(),
            auto_adjust=False,
            actions=False,
        )
    except Exception:
        return None, "YF_PRICE_ERROR"
    if px is None or px.empty or "Close" not in px:
        return None, "YF_PRICE_NOT_FOUND"
    close = pd.to_numeric(px["Close"], errors="coerce").dropna()
    if close.empty:
        return None, "YF_PRICE_NOT_FOUND"
    # Use last close on/before anchor when timezone permits.
    try:
        idx_dates = pd.Index([pd.Timestamp(x).date() for x in close.index])
        mask = idx_dates <= anchor
        if mask.any():
            pos = np.where(mask)[0][-1]
            return float(close.iloc[pos]), f"YFINANCE:{pd.Timestamp(close.index[pos]).date().isoformat()}"
    except Exception:
        pass
    return float(close.iloc[-1]), "YFINANCE:NEAREST"


def historical_market_cap(ticker: str, cik: int, anchor: date, cutoff: date) -> tuple[float | None, str]:
    close, psrc = historical_close(ticker, anchor)
    shares, ssrc = shares_outstanding(cik, cutoff)
    if close is None or shares is None:
        return None, f"{psrc}|{ssrc}"
    return close * shares, f"{psrc}|{ssrc}"


def cap_bucket(cap_b: float) -> str:
    if cap_b < 1:
        return "$300M–$1B"
    if cap_b < 3:
        return "$1B–$3B"
    return "$3B–$10B"


def update_history(final_rows: list[dict[str, Any]]) -> None:
    hist = pd.read_csv(HISTORY_PATH, dtype=str)
    hist = hist[~hist["pdufa_date"].fillna("").str.startswith("2024-")].copy()

    add = pd.DataFrame(final_rows)
    for col in hist.columns:
        if col not in add:
            add[col] = ""
    add = add[hist.columns]
    out = pd.concat([add, hist], ignore_index=True)
    out["_d"] = pd.to_datetime(out["pdufa_date"], errors="coerce")
    out = out.sort_values(["_d", "ticker", "event_key"], na_position="last").drop(columns="_d")
    out.to_csv(HISTORY_PATH, index=False)


def update_audit(final_rows: list[dict[str, Any]]) -> None:
    audit = pd.read_csv(AUDIT_PATH, dtype=str)
    audit = audit[~audit["event_key"].fillna("").str.contains(r"\|2024-", regex=True)].copy()
    rows = []
    for r in final_rows:
        rows.append({
            "event_key": r["event_key"],
            "audit_status": "FROZEN_PREDECISION_2024",
            "failure_reason": "",
            "count_in_audited_accuracy": "YES",
            "verified_note": (
                "2024 frozen-model reconstruction; prediction uses SEC evidence only through "
                f"{r['evidence_cutoff']}; FDA outcome joined after score freeze; historical cap "
                "reconstructed from historical close x SEC filed shares."
            ),
            "source_url": r.get("source_url", ""),
            "canonical_pdufa_date": r["pdufa_date"],
            "audit_action": "KEEP_2024_TUNING_COHORT",
            "needs_rescore": "NO",
        })
    add = pd.DataFrame(rows)
    for col in audit.columns:
        if col not in add:
            add[col] = ""
    out = pd.concat([audit, add[audit.columns]], ignore_index=True)
    out.to_csv(AUDIT_PATH, index=False)


def main() -> None:
    ticker_map = load_ticker_map()
    staged: list[dict[str, Any]] = []
    blind_scored: list[dict[str, Any]] = []

    for ticker, pdufa_s, action_s, drug in BLIND_EVENTS:
        event_key = f"{ticker}|{pdufa_s}"
        pdufa = datetime.strptime(pdufa_s, "%Y-%m-%d").date()
        action = datetime.strptime(action_s, "%Y-%m-%d").date()
        cutoff = min(pdufa, action) - timedelta(days=1)
        anchor = min(pdufa, action)

        row: dict[str, Any] = {
            "event_key": event_key,
            "ticker": ticker,
            "drug": drug,
            "pdufa_date": pdufa_s,
            "action_date": action_s,
            "evidence_cutoff": cutoff.isoformat(),
            "status": "STARTED",
        }

        meta = ticker_map.get(ticker)
        if not meta:
            row["status"] = "EXCLUDED_NO_SEC_TICKER"
            staged.append(row)
            continue
        cik = int(meta["cik"])
        row["company"] = meta.get("title", "")
        row["cik"] = f"{cik:010d}"

        try:
            evidence, text = collect_predecision_evidence(cik, cutoff)
        except Exception as exc:
            row["status"] = "EXCLUDED_EVIDENCE_ERROR"
            row["error"] = type(exc).__name__
            staged.append(row)
            continue

        feats = feature_vector(evidence, text)
        row.update(feats)
        row["evidence_source_count"] = len(evidence)
        row["first_predecision_source"] = evidence[0]["url"] if evidence else ""

        # Prediction is frozen before market-cap/outcome reveal.
        p = frozen_probability(feats)
        model_class = "APPROVED" if p >= 0.5 else "CRL"
        row["p_approval"] = p
        row["model_class"] = model_class

        cap, cap_method = historical_market_cap(ticker, cik, anchor, cutoff)
        row["historical_market_cap_usd"] = cap
        row["market_cap_method"] = cap_method
        if cap is None:
            row["status"] = "EXCLUDED_CAP_UNRESOLVED"
            staged.append(row)
            continue
        cap_b = cap / 1_000_000_000.0
        row["historical_market_cap_billions"] = cap_b
        if cap_b < 0.300:
            row["status"] = "EXCLUDED_CAP_BELOW_300M"
            staged.append(row)
            continue
        if cap_b > 10.000:
            row["status"] = "EXCLUDED_CAP_ABOVE_10B"
            staged.append(row)
            continue

        row["market_cap_bucket"] = cap_bucket(cap_b)
        row["status"] = "BLIND_SCORE_FROZEN_CAP_PASS"
        blind_scored.append(row)
        staged.append(row)

    # Reveal outcomes only after every eligible prediction has been frozen.
    final_rows: list[dict[str, Any]] = []
    for row in blind_scored:
        event_key = row["event_key"]
        actual = OUTCOMES.get(event_key)
        if actual not in {"APPROVED", "CRL"}:
            row["status"] = "EXCLUDED_OUTCOME_UNRESOLVED"
            continue
        row["actual_outcome"] = actual
        row["correct"] = str(row["model_class"] == actual)
        row["actual_binary"] = "1" if actual == "APPROVED" else "0"
        row["predicted_binary"] = "1" if row["model_class"] == "APPROVED" else "0"
        row["source_url"] = OUTCOME_SOURCES.get(event_key, "")
        row["status"] = "INCLUDED_2024_300M_10B"
        final_rows.append({
            "ticker": row["ticker"],
            "pdufa_date": row["pdufa_date"],
            "event_key": row["event_key"],
            "p_approval": row["p_approval"],
            "model_class": row["model_class"],
            "actual_outcome": actual,
            "validation_period": "2024_FROZEN_PREDECISION_TUNE",
            "independence_status": "TUNING_COHORT",
            "historical_market_cap_billions": row["historical_market_cap_billions"],
            "market_cap_source": row["market_cap_method"],
            "market_cap_match_method": "HISTORICAL_CLOSE_X_SEC_FILED_SHARES",
            "market_cap_bucket": row["market_cap_bucket"],
            "cap_recovery_confidence": "HIGH",
            "cap_recovery_method": row["market_cap_method"],
            "correct": row["correct"],
            "actual_binary": row["actual_binary"],
            "predicted_binary": row["predicted_binary"],
            "public_approval_probability": "",
            "biopharmawatch_probability": "",
            "public_model_class": "",
            "public_evidence_note": (
                "2024 reconstruction used public SEC/FDA/calendar sources; a separate public-only "
                "probability is intentionally not fabricated."
            ),
            "internal_direction_class": row["model_class"],
            "internal_direction_note": (
                "Frozen 2025 eight-feature model applied without refit to pre-decision 2024 SEC evidence."
            ),
            "evidence_cutoff": row["evidence_cutoff"],
            "source_url": row["source_url"],
        })

    # Staging keeps every candidate, including cap exclusions.
    pd.DataFrame(staged).to_csv(STAGING_PATH, index=False)
    update_history(final_rows)
    update_audit(final_rows)

    included = len(final_rows)
    correct = sum(str(r["correct"]).lower() == "true" for r in final_rows)
    approvals = sum(r["actual_outcome"] == "APPROVED" for r in final_rows)
    crls = sum(r["actual_outcome"] == "CRL" for r in final_rows)
    accuracy = (correct / included * 100.0) if included else float("nan")
    print(json.dumps({
        "candidate_events": len(BLIND_EVENTS),
        "included_300m_10b": included,
        "approvals": approvals,
        "crls": crls,
        "frozen_model_correct": correct,
        "frozen_model_match_pct": None if included == 0 else round(accuracy, 2),
        "history_path": str(HISTORY_PATH),
        "staging_path": str(STAGING_PATH),
    }, indent=2))


if __name__ == "__main__":
    main()
