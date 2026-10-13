"""Preserve prospective GEM research states without inventing historical trades.

This is a dated READ-ONLY, research-only observation, not a backtest-ready feature
snapshot. Converting it to gem_historical_snapshots.csv is prohibited without
point-in-time primary disclosure dates, complete financing sequence and
verified split-adjusted equity prices.
"""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import date

from gem_scans import STAGES

COLUMNS = (
    "observation_id", "as_of_pacific", "ticker", "nct_id",
    "exact_event", "drug", "stage", "phase3_tracking",
    "financing_watch", "second_financing_verified_closed",
    "pdufa_date", "days_to_pdufa",
    "feed_current", "research_qualification", "gem_score", "gem_rank",
    "phase3_source", "financing_source", "pdufa_source",
    "training_eligible", "realized_return_known",
)


def build_observations(items, status, *, as_of):
    if not isinstance(as_of, date) or isinstance(as_of, __import__("datetime").datetime):
        raise ValueError("as_of must be a date")
    current = status.get("feed_current") is True
    observed = set()
    output = []
    for item in items:
        ticker = str(item.get("Ticker") or "").strip().upper()
        event = str(item.get("Exact event") or "").strip()
        nct = str(item.get("NCT ID") or "").strip().upper()
        # Research leads without exact event and NCT must not be represented
        # as uniquely identified drug-development equity opportunities.
        if not ticker or not event or not nct.startswith("NCT"):
            continue
        for stage in STAGES:
            key = (as_of.isoformat(), event, stage)
            if key in observed:
                # Duplicated identity must NOT be deduplicated into a
                # supposedly verified event by choosing a preferred row.
                raise ValueError("Duplicate exact-event stage research snapshot")
            observed.add(key)
            qualification = str(item.get(stage + " qualifier") or "")
            raw_score = item.get(stage + " score")
            raw_rank = item.get(stage + " rank")
            approved_rank = current and qualification == "QUALIFIED — RESEARCH ONLY"
            if not approved_rank or raw_score is None or raw_rank is None:
                raw_score = raw_rank = None
            row = {
                "observation_id": hashlib.sha256(
                    ("\x1f".join(key)).encode("utf-8")
                ).hexdigest(),
                "as_of_pacific": as_of.isoformat(),
                "ticker": ticker, "nct_id": nct,
                "exact_event": event, "drug": str(item.get("Drug") or ""),
                "stage": stage,
                "phase3_tracking": str(item.get("Phase 3 tracking") or ""),
                "financing_watch": str(item.get("Financing watch") or ""),
                "second_financing_verified_closed": (
                    "YES" if item.get("2nd Financing Completed") ==
                    "YES — VERIFIED (HISTORICAL)" else "NO"
                ),
                "pdufa_date": str(item.get("PDUFA date") or ""),
                "days_to_pdufa": item.get("Days to PDUFA"),
                "feed_current": "YES" if current else "NO",
                "research_qualification": qualification if current else "SOURCE_HOLD",
                "gem_score": raw_score, "gem_rank": raw_rank,
                "phase3_source": str(item.get("Phase 3 source") or ""),
                "financing_source": str(item.get("Financing source") or ""),
                "pdufa_source": str(item.get("PDUFA source") or ""),
                "training_eligible": "NO — NOT HISTORICAL TRADE VERIFIED",
                "realized_return_known": "NO",
            }
            output.append(row)
    output.sort(key=lambda r: (
        r["stage"], r["ticker"], r["exact_event"],
    ))
    return output


def observations_csv(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
