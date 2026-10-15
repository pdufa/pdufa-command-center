"""Canonical Pipeline-origin policy for downstream SEC, FDA and GEM scans.

Source files may feed Pipeline intake, but only records present in the Pipeline
universe can appear downstream. Source/issuer evidence never creates a trial.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline_universe import load_universe, read_rows


def pipeline_origins(data_dir, today=None):
    """Read the same canonical Pipeline record IDs as the Pipeline tab."""
    today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    if isinstance(today, str):
        today = date.fromisoformat(today[:10])
    frame = load_universe(Path(data_dir), today=today)
    if frame.empty:
        return set(), {}
    return (
        set(frame["record_id"].astype(str)),
        {str(row["record_id"]): str(row["ticker"]).strip().upper()
         for row in frame.to_dict("records")},
    )


def source_scope(data_dir, today=None):
    """Enumerate scan targets only after Pipeline has minted their identity."""
    root = Path(data_dir)
    record_ids, _pipeline_tickers = pipeline_origins(root, today=today)
    events = [
        row for row in read_rows(root / "pdufa_candidates.csv")
        if "APPLICATION|" + str(row.get("event_key") or "").strip() in record_ids
    ]
    # Only issuer rows connected to Pipeline application events being scanned.
    # Other Pipeline stages are displayed NOT_CHECKED until an application exists.
    matched_tickers = {str(row.get("ticker") or "").strip().upper() for row in events}
    companies = [
        row for row in read_rows(root / "company_registry.csv")
        if str(row.get("ticker") or "").strip().upper() in matched_tickers
    ]
    return events, companies


def gem_pipeline_id(record, record_ids, pipeline_tickers):
    """Require exact Pipeline application/NCT identity and compatible company."""
    event = str(record.get("Exact event") or "").strip()
    if event:
        identifier = "APPLICATION|" + event
    else:
        nct = str(record.get("NCT ID") or "").strip().upper()
        identifier = "TRIAL|" + nct if nct else ""
    if not identifier or identifier not in record_ids:
        return ""
    # NCT alone never authorizes a cross-issuer stock-program join.
    claimed = str(record.get("Ticker") or "").strip().upper()
    canonical = str(pipeline_tickers.get(identifier) or "").strip().upper()
    if claimed and canonical and claimed != canonical:
        return ""
    return identifier
