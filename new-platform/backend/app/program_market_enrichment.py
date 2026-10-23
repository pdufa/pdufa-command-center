"""Read-only program-identity bridge for Alpaca market enrichment.

The caller resolves the immutable ProgramIdentity row from the database and passes
its program_id, source_key and ticker. This module never guesses ticker-to-trial
associations or changes qualification, restrictions, scoring or trading state.
"""
from __future__ import annotations

from .alpaca_market_chart import get_alpaca_bars
from .market_signal_analysis import summarize_daily_bars
from .market_evidence_review import market_evidence_review
from .decision_readiness import decision_readiness
from .decision_readiness import decision_readiness


def enrich_program_market(program_id: str, source_key: str, ticker: str, range_label: str = "1Y") -> dict:
    if not isinstance(program_id, str) or not program_id.startswith("PDUFA-"):
        raise ValueError("An immutable program ID is required")
    if not isinstance(source_key, str) or not source_key.strip():
        raise ValueError("Exact source key is required")
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Ticker is required")
    chart = get_alpaca_bars(ticker, range_label)
    bars = chart.get("bars") or []
    status = chart.get("status", "ALPACA_UNAVAILABLE")
    last = bars[-1] if status == "OK" and bars else None
    signals = summarize_daily_bars(bars) if status == "OK" else summarize_daily_bars([])
    review = market_evidence_review(program_id, source_key, signals)
    readiness = decision_readiness(
        program_id=program_id, exact_key=source_key,
        assessment_score=None, assessment_coverage=None,
        market_review=review, catalyst_verified=False,
        financing_risk_reviewed=False,
    )
    review = market_evidence_review(program_id, source_key, signals)
    readiness = decision_readiness(program_id=program_id, exact_key=source_key,
        assessment_score=None, assessment_coverage=None, market_review=review,
        catalyst_verified=False, financing_risk_reviewed=False)
    return {
        "programId": program_id,
        "exactKey": source_key,
        "ticker": ticker.upper(),
        "provider": "ALPACA",
        "feed": chart.get("feed"),
        "status": status,
        "coverage": chart.get("coverage"),
        "asOf": chart.get("asOf"),
        "latestDailyClose": last["close"] if last else None,
        "latestIexVolume": last["volume"] if last else None,
        "barsAvailable": len(bars) if status == "OK" else 0,
        "marketSignals": signals,
        "marketEvidenceReview": review,
        "decisionReadiness": readiness,
        "source": chart.get("source"),
        "researchOnly": True,
        "orderExecutionEnabled": False,
        "qualificationChanges": False,
        "restrictionChanges": False,
        "fsFaChanges": False,
    }
