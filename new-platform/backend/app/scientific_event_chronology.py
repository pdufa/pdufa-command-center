"""Check dated events against accepted source-review receipts.

A document cannot evidence an event that has not happened. This does not
independently authenticate the original document or its reviewer.
"""
from __future__ import annotations
from datetime import date
import re


def _day(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def event_covered_by_review(level, criterion, event_day, cutoff, *,
                            source_after_event=True):
    """Was a dated event available to this accepted original-source record?

    Use source_after_event=False only for an availability check made after
    publication of an older underlying original document.
    """
    accepted = level.get("acceptedEvidence") if isinstance(level, dict) else None
    receipt = accepted.get(criterion) if isinstance(accepted, dict) else None
    if not isinstance(receipt, dict) or receipt.get("retrievalProvenance") != "RECORDED":
        return False
    happened = event_day if type(event_day) is date else _day(event_day)
    source = _day(receipt.get("sourceDate"))
    retrieved = _day(receipt.get("sourceRetrievedAt"))
    verified = _day(receipt.get("sourceVerifiedAt"))
    reviewed = _day(receipt.get("reviewedAt"))
    asof = _day(cutoff)
    if any(d is None for d in (happened, source, retrieved, verified, reviewed, asof)):
        return False
    if not (source <= retrieved <= verified <= reviewed <= asof and happened <= retrieved):
        return False
    if source_after_event and happened > source:
        return False
    return True
