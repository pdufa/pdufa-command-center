"""Step 5 bulk market scan: bounded concurrent EOD requests, checkpoints and ranks.

Runs ALL uniquely mapped ticker/CIK identifiers (never silently cap the
universe). Missing Stage 3 evidence is UNVERIFIED, not PRE/POST. Unverified
records receive only a neutral price/volume screen, NOT a PRE/POST score.
Stooq availability, symbol->issuer mapping and corporate actions are unverified.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

from market_step5 import (
    DEFAULT_DB, _factors, clean_ticker, date_value, evaluate_market,
    fetch_stooq_daily, https_source, read_history, save_snapshot, phase_check,
)
from sec_step4 import load_registry

NEUTRAL_WEIGHTS = {"momentum_30": 20, "relative_volume": 20, "trend_20": 20,
                   "dollar_liquidity": 20, "volatility_risk": 20}
VALID_PHASES = {"PRE_RESULTS", "POST_RESULTS"}
BULK_COLUMNS = [
    "ticker", "company", "cik", "status", "phase", "phase_status",
    "neutral_price_volume_score_0_100", "phase_specific_score_0_100",
    "as_of", "last_session", "close", "momentum_30_pct", "relative_volume",
    "avg_dollar_volume_20", "volatility_20_pct", "pdufa_window",
    "price_source", "evidence_url", "error",
]
DEFAULT_RESULTS = Path(__file__).resolve().parent / "data" / "market_bulk_latest.csv"


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                  separators=(",", ":")).encode("utf-8")).hexdigest()


def parse_phase_manifest(text, identities=None):
    """Optional per-ticker reviewer assertions with dated source links.

    Omitted phase => no false PRE or POST label. Manifest does not validate the
    underlying clinical result; an HTML URL alone is not independent proof.
    """
    if text is None or not str(text).strip():
        return {}
    if len(text) > 2_000_000:
        raise ValueError("Stage evidence CSV is oversized")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    required = {"ticker", "phase", "phase_url", "phase_date"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError("Phase manifest needs ticker,phase,phase_url,phase_date")
    mapping = {}
    for row in reader:
        ticker = clean_ticker(row.get("ticker"))
        if ticker in mapping:
            raise ValueError(f"Duplicate ticker in phase manifest: {ticker}")
        if identities is not None and ticker not in identities:
            raise ValueError(f"Unregistered ticker in phase manifest: {ticker}")
        phase = str(row.get("phase") or "").strip().upper()
        if phase not in VALID_PHASES:
            raise ValueError(f"Unsupported phase for {ticker}")
        mapping[ticker] = {
            "phase": phase,
            "phase_evidence": {"url": str(row.get("phase_url") or "").strip(),
                               "date": str(row.get("phase_date") or "").strip()},
            "readout_date": str(row.get("readout_date") or "").strip() or None,
            "pdufa_date": str(row.get("pdufa_date") or "").strip() or None,
            "pdufa_evidence": {"url": str(row.get("pdufa_url") or "").strip(),
                               "date": str(row.get("pdufa_source_date") or "").strip()},
        }
    return mapping


def neutral_score(report):
    """Price/volume-only screen independent of unverified clinical phase."""
    ind = report.get("market_indicators") or {}
    req = ("momentum_30_session_pct", "relative_volume_vs_prior20",
           "close_vs_sma20_pct", "avg_dollar_volume_20_usd",
           "annualized_historical_volatility_20_pct")
    if not all(ind.get(k) is not None for k in req):
        return None
    factors = _factors(ind["momentum_30_session_pct"] / 100,
                       ind["relative_volume_vs_prior20"],
                       ind["close_vs_sma20_pct"] / 100,
                       ind["avg_dollar_volume_20_usd"],
                       ind["annualized_historical_volatility_20_pct"] / 100)
    return round(sum(NEUTRAL_WEIGHTS[k] * factors[k] for k in NEUTRAL_WEIGHTS), 2)


class RatePacer:
    def __init__(self, min_interval=0.8):
        if not 0.1 <= min_interval <= 10:
            raise ValueError("Pacing must be between 0.1 and 10 seconds")
        self.lock = threading.Lock()
        self.next = 0.0
        self.min_interval = min_interval

    def wait(self):
        with self.lock:
            wait = max(0.0, self.next - time.monotonic())
            if wait:
                time.sleep(wait)
            self.next = time.monotonic() + self.min_interval


def _run_tables(db_path):
    db = sqlite3.connect(str(db_path), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("""CREATE TABLE IF NOT EXISTS market_bulk_runs(
        run_key TEXT PRIMARY KEY, as_of TEXT NOT NULL, roster_size INTEGER NOT NULL,
        manifest_sha TEXT NOT NULL, created_utc TEXT NOT NULL,
        updated_utc TEXT NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS market_bulk_results(
        run_key TEXT NOT NULL, ticker TEXT NOT NULL, status TEXT NOT NULL,
        updated_utc TEXT NOT NULL, payload_json TEXT NOT NULL,
        PRIMARY KEY(run_key,ticker)
    )""")
    return db


def read_bulk_results(db_path=DEFAULT_DB, run_key=None):
    path = Path(db_path)
    if not path.exists():
        return []
    with _run_tables(path) as db:
        if run_key:
            rows = db.execute("SELECT * FROM market_bulk_results WHERE run_key=? ORDER BY ticker",
                              (run_key,)).fetchall()
        else:
            latest = db.execute("SELECT run_key FROM market_bulk_runs ORDER BY updated_utc DESC LIMIT 1").fetchone()
            if not latest:
                return []
            rows = db.execute("SELECT * FROM market_bulk_results WHERE run_key=? ORDER BY ticker",
                              (latest["run_key"],)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]


def _save_bulk_result(db_path, run_key, row):
    with _run_tables(db_path) as db:
        db.execute("""INSERT INTO market_bulk_results
              (run_key,ticker,status,updated_utc,payload_json) VALUES (?,?,?,?,?)
              ON CONFLICT(run_key,ticker) DO UPDATE SET
                status=excluded.status,updated_utc=excluded.updated_utc,
                payload_json=excluded.payload_json""",
                (run_key, row["ticker"], row["status"],
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)))
        db.execute("UPDATE market_bulk_runs SET updated_utc=? WHERE run_key=?",
                   (datetime.now(timezone.utc).isoformat(), run_key))


def _result_row(report, identity, status="SUCCESS", error=""):
    ind = report.get("market_indicators") or {}
    return {
        "ticker": report["ticker"], "company": identity.get("company", ""),
        "cik": identity.get("cik", ""), "status": status,
        "phase": report.get("phase", "UNVERIFIED"),
        "phase_status": report.get("phase_status", "REVIEW — PHASE NOT CONFIRMED"),
        "neutral_price_volume_score_0_100": report.get("neutral_price_volume_score_0_100"),
        "phase_specific_score_0_100": report.get("technical_score_0_100"),
        "as_of": report.get("as_of"),
        "last_session": ind.get("last_market_session"),
        "close": ind.get("last_close_usd"),
        "momentum_30_pct": ind.get("momentum_30_session_pct"),
        "relative_volume": ind.get("relative_volume_vs_prior20"),
        "avg_dollar_volume_20": ind.get("avg_dollar_volume_20_usd"),
        "volatility_20_pct": ind.get("annualized_historical_volatility_20_pct"),
        "pdufa_window": report.get("pdufa_window"),
        "price_source": (report.get("source") or {}).get("source_url", ""),
        "evidence_url": (report.get("phase_evidence") or {}).get("url", ""),
        "error": error,
    }


def _failure(ticker, identity, cutoff, exc):
    return {"ticker": ticker, "company": identity.get("company", ""),
            "cik": identity.get("cik", ""), "status": "FAILED",
            "phase": "UNVERIFIED", "phase_status": "REVIEW — NOT SCANNED",
            "neutral_price_volume_score_0_100": None,
            "phase_specific_score_0_100": None, "as_of": cutoff.isoformat(),
            "last_session": None, "close": None, "momentum_30_pct": None,
            "relative_volume": None, "avg_dollar_volume_20": None,
            "volatility_20_pct": None, "pdufa_window": None,
            "price_source": "", "evidence_url": "", "error": str(exc)[:450]}


def _fetch_one(ticker, identity, cutoff, phase_entry, getter, pacer):
    pacer.wait()
    bars, source = getter(ticker, cutoff)
    # Preserve issuer ambiguity: only SEC CIK mapping was verified, not feed instrument.
    source = dict(source)
    source["registry_cik"] = identity["cik"]
    source["issuer_mapping"] = "REVIEW — EOD symbol/venue and corporate actions unverified"
    phase = phase_entry.get("phase", "UNVERIFIED")
    report = evaluate_market(
        ticker, bars, cutoff.isoformat(), phase,
        phase_evidence=phase_entry.get("phase_evidence"),
        readout_date=phase_entry.get("readout_date"),
        pdufa_date=phase_entry.get("pdufa_date"),
        pdufa_evidence=phase_entry.get("pdufa_evidence"), source=source)
    # Unknown phase -> score only in wholly separate neutral price-volume field.
    report["neutral_price_volume_score_0_100"] = neutral_score(report)
    report["neutral_score_note"] = (
        "Preliminary price-volume screen, NOT a PRE/POST Phase 3 market score "
        "or FDA/clinical/return probability")
    report["company_registry"] = {"ticker": ticker, "company": identity["company"],
                                   "cik": identity["cik"]}
    report["scan_type"] = "ALL REGISTERED TICKERS — REVIEW DATA QUALITY"
    if report["neutral_price_volume_score_0_100"] is None:
        return "REVIEW — INCOMPLETE PRICE DATA", report
    if report["technical_score_0_100"] is None:
        return "REVIEW — PHASE UNVERIFIED", report
    return "SCORED — PHASE REVIEWER ASSERTED", report


def _rank(rows, key, group=None):
    sorted_rows = sorted(
        (row for row in rows if row.get(key) is not None and
         (group is None or row.get("phase") == group)),
        key=lambda x: (-x[key], x["ticker"]))
    return [{"rank": idx + 1, **r} for idx, r in enumerate(sorted_rows)]


def summarize(rows, target_total=None):
    target_total = len(rows) if target_total is None else target_total
    statuses = {}
    for row in rows:
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    return {
        "roster": target_total, "completed_attempts": len(rows),
        "remaining": max(0, target_total - len(rows)),
        "status_counts": statuses,
        "neutral_ranking": _rank(rows, "neutral_price_volume_score_0_100"),
        "pre_results_ranking": _rank(rows, "phase_specific_score_0_100", "PRE_RESULTS"),
        "post_results_ranking": _rank(rows, "phase_specific_score_0_100", "POST_RESULTS"),
    }


def csv_output(rows):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=BULK_COLUMNS)
    writer.writeheader()
    writer.writerows([{key: row.get(key) for key in BULK_COLUMNS} for row in rows])
    return out.getvalue()


def run_bulk(as_of, identities=None, phase_manifest=None, db_path=DEFAULT_DB,
             getter=None, max_workers=3, min_interval=0.8, on_progress=None,
             max_new=None, retry_failures=True):
    """One action for entire registered universe; checkpoint each completed symbol.

    max_new limits a batch for explicit staged runs/tests only. Default scans
    ALL. Retry failures on rerun; previously successful stocks are skipped.
    """
    cutoff = date_value(as_of)
    if cutoff is None or cutoff > datetime.now(timezone.utc).date():
        raise ValueError("Invalid/future as-of date")
    if not isinstance(max_workers, int) or not 1 <= max_workers <= 4:
        raise ValueError("max_workers must be 1–4")
    if max_new is not None and (not isinstance(max_new, int) or max_new <= 0):
        raise ValueError("max_new must be positive")
    identities = identities if identities is not None else load_registry()
    registry = {clean_ticker(t): dict(row) for t, row in identities.items()
                if row.get("cik") and not row.get("conflict")}
    if not registry:
        raise ValueError("No uniquely mapped SEC ticker/CIK entries available")
    phases = phase_manifest or {}
    for ticker in phases:
        if ticker not in registry:
            raise ValueError(f"Phase manifest ticker not in registered universe: {ticker}")
    tickers = sorted(registry)
    run_key = _sha({"date": cutoff.isoformat(), "tickers": [(t, registry[t]["cik"]) for t in tickers],
                    "manifest": phases, "source": "STOOQ DELAYED EOD",
                    "model_version": "STEP5_BULK_V1"})
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _run_tables(db_path) as db:
        now = datetime.now(timezone.utc).isoformat()
        db.execute("""INSERT OR IGNORE INTO market_bulk_runs
             (run_key,as_of,roster_size,manifest_sha,created_utc,updated_utc)
             VALUES(?,?,?,?,?,?)""",
             (run_key, cutoff.isoformat(), len(tickers), _sha(phases), now, now))
    prior = {r["ticker"]: r for r in read_bulk_results(db_path, run_key)}
    todo = [ticker for ticker in tickers if
            ticker not in prior or (retry_failures and prior[ticker]["status"] == "FAILED")]
    if max_new is not None:
        todo = todo[:max_new]
    provider = getter or fetch_stooq_daily
    pacer = RatePacer(min_interval)
    processed_this_run = 0
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="step5-eod") as pool:
        futures = {pool.submit(_fetch_one, ticker, registry[ticker], cutoff,
                               phases.get(ticker, {}), provider, pacer): ticker
                   for ticker in todo}
        for completed in as_completed(futures):
            ticker = futures[completed]
            try:
                status, report = completed.result()
                # Save per-ticker market history, then checkpoint. If interrupted,
                # subsequent resume may create an idempotent snapshot and finish.
                save_snapshot(report, db_path)
                row = _result_row(report, registry[ticker], status)
            except (Exception) as exc:
                row = _failure(ticker, registry[ticker], cutoff, exc)
            _save_bulk_result(db_path, run_key, row)
            prior[ticker] = row
            processed_this_run += 1
            if on_progress:
                on_progress({"run_key": run_key, "ticker": ticker, "status": row["status"],
                             "attempted": len(prior), "total": len(tickers),
                             "remaining": max(0, len(tickers) - len(prior)),
                             "newly_processed": processed_this_run})
    rows = [prior[ticker] for ticker in tickers if ticker in prior]
    return {"run_key": run_key, "as_of": cutoff.isoformat(), **summarize(rows, len(tickers)),
            "rows": rows}


def main(argv=None):
    p = argparse.ArgumentParser(description="Step 5: explicitly scan entire registered biotech universe")
    p.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat())
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--output", type=Path, default=DEFAULT_RESULTS)
    p.add_argument("--phase-manifest", type=Path, default=None)
    p.add_argument("--max-workers", type=int, default=3)
    p.add_argument("--min-interval", type=float, default=0.8)
    p.add_argument("--max-new", type=int, default=None,
                   help="Optional staged chunk; omit to process EVERY registered ticker")
    p.add_argument("--no-retry-failures", action="store_true")
    args = p.parse_args(argv)
    registry = load_registry()
    manifest = parse_phase_manifest(
        args.phase_manifest.read_text(encoding="utf-8-sig") if args.phase_manifest else None,
        registry)
    result = run_bulk(args.as_of, identities=registry, phase_manifest=manifest,
                      db_path=args.db, max_workers=args.max_workers,
                      min_interval=args.min_interval, max_new=args.max_new,
                      retry_failures=not args.no_retry_failures,
                      on_progress=lambda r: print(f"{r['attempted']}/{r['total']} "
                                                  f"{r['ticker']}: {r['status']}",
                                                  flush=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(csv_output(result["rows"]), encoding="utf-8")
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(
        {key: val for key, val in result.items() if key != "rows"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"roster": result["roster"], "scanned": result["completed_attempts"],
                      "remaining": result["remaining"], "status_counts": result["status_counts"],
                      "csv": str(args.output), "summary": str(summary_path)}, indent=2))
    if not result["neutral_ranking"] and result["remaining"] == 0:
        print("No usable price/volume observations: provider availability may be blocked.")
        return 1
    return 0 if result["remaining"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
