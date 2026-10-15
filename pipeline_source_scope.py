"""Canonical Pipeline-origin policy for downstream SEC, FDA and GEM scans.

Source files may feed Pipeline intake, but only records present in the Pipeline
universe can appear downstream. Source/issuer evidence never creates a trial.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline_universe import load_universe, read_rows


def pipeline_origins(data_dir, today=None):
    """Read the same canonical Pipeline record IDs as the Pipeline tab."""
    today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    frame = load_universe(Path(data_dir), today=today)
    if frame.empty:
        return set(), set()
    return (
        set(frame["record_id"].astype(str)),
        {str(ticker).strip().upper() for ticker in frame["ticker"]
         if str(ticker).strip()},
    )


def source_scope(data_dir, today=None):
    """Enumerate scan targets only after Pipeline has minted their identity."""
    root = Path(data_dir)
    record_ids, tickers = pipeline_origins(root, today=today)
    events = [
        row for row in read_rows(root / "pdufa_candidates.csv")
        if "APPLICATION|" + str(row.get("event_key") or "").strip() in record_ids
    ]
    companies = [
        row for row in read_rows(root / "company_registry.csv")
        if str(row.get("ticker") or "").strip().upper() in tickers
    ]
    return events, companies


def gem_pipeline_id(record, record_ids):
    """Resolve a GEM item only by exact Pipeline application or NCT identity."""
    event = str(record.get("Exact event") or "").strip()
    if event:
        identifier = "APPLICATION|" + event
        return identifier if identifier in record_ids else ""
    nct = str(record.get("NCT ID") or "").strip().upper()
    if nct:
        identifier = "TRIAL|" + nct
        return identifier if identifier in record_ids else ""
    return ""
