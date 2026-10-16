"""Exact-program ranking adapter and reference dashboard entry point."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from gem_stage_dossier import exact_event
from gem_trading_advisory import load_market_rows, assess_gem_trade, _score_gem_trade
from ticker_toggle_panel import clean_ticker


def _show(value, default="NOT AVAILABLE"):
    if value is None:
        return default
    value = str(value).strip()
    if not value or value.lower() in ("none", "nan", "nat", "<na>"):
        return default
    return value


def _rankings(stage, active, root, today):
    """Build exact-program lookup once, without inventing unknown entry scores."""
    market = load_market_rows(root)
    mapped = {}
    source_status = {}
    if stage == "GEM":
        try:
            from gem_master_list import build_gem_master_list
            from gem_scans_ui import _saved_gem_scans, FILES
            path = Path(root)
            signature = tuple((name, (path / name).stat().st_mtime_ns
                      if (path / name).exists() else 0) for name in FILES)
            items, source_status = _saved_gem_scans(str(path), signature, today)
            for row in build_gem_master_list(items):
                key = (clean_ticker(row.get("Ticker")), str(row.get("Exact Program / Event") or ""))
                if key in mapped:
                    mapped[key] = None  # ambiguous exact identity: fail closed
                else:
                    mapped[key] = row
        except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError):
            mapped = {}
            source_status = {}
    results = []
    for i, record in enumerate(active):
        event = exact_event(root, record.get("Exact program"))
        ticker = clean_ticker(record.get("Ticker"))
        master = mapped.get((ticker, str(record.get("Exact program") or "")))
        profile = assess_gem_trade(master or {"Ticker": ticker, "_eligible": False},
                                   market, source_status, today)
        score = (_score_gem_trade(master, profile, source_status) if master
                 else {"entry": None, "exit_risk": None,
                       "entry_status": "NOT VERIFIED", "exit_status": "NOT VERIFIED",
                       "entry_factors": [], "exit_factors": [],
                       "entry_coverage": 0, "exit_coverage": 0})
        score["quality"] = master.get("GEM Score /100") if master and master.get("_eligible") else None
        results.append((record, event, master, profile, score))
    return results



def render_visual_stage(stage, root="data"):
    # Import lazily: the adapter uses the established exact-program lookup.
    from gem_reference_dashboard import render_reference_stage
    render_reference_stage(stage, root)
