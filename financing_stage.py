"""Strict, program-specific post-Phase-3 second-financing status.

Announced is not proof financing started; a historic running flag is not
proof it is still running; a close requires verified closing evidence.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from stages import get, values, name, stage_date, fresh, ticker_of, StageIndex

FINANCING_OPTIONS = ("ANNOUNCED", "STARTED", "RUNNING", "FINISHED", "REVIEW / UNVERIFIED")
FINANCING_HELP = (
    "Post-Phase-3 second-financing status. FINISHED requires independently "
    "verified second-close evidence. STARTED requires documented commencement. "
    "Unknown, conflicting and stale in-progress evidence stays REVIEW / UNVERIFIED."
)
PACIFIC = ZoneInfo("America/Los_Angeles")

def _yes(value):
    return str(value).strip().upper() in {"YES", "TRUE", "1", "VERIFIED"}

def financing_stage(record, today=None):
    today = today or datetime.now(PACIFIC).date()
    row = values(record)
    raw = get(row, "second_financing_status", "Financing #2 Status").upper().replace("-", "_").replace(" ", "_")
    audit = get(row, "second_financing_audit_status").upper()
    evidence = get(row, "second_financing_source", "Financing Close Evidence")
    stamped = get(row, "verified_as_of", "financing_checked_at")
    close_date = stage_date(get(row, "second_financing_date", "Financing #2 Date"))
    if not raw and not audit:
        return "REVIEW / UNVERIFIED"

    if raw in {"CLOSED", "COMPLETE", "COMPLETED", "FINISHED", "SECOND_CLOSE_VERIFIED"} or any(
        _yes(get(row, key)) for key in ("second_financing_closed", "second_financing_close_verified")
    ):
        if (audit == "VERIFIED_SECOND_POST_PHASE3_FINANCING" and evidence and
                close_date and close_date <= today):
            return "FINISHED"
        return "REVIEW / UNVERIFIED"

    # A verified active financing must be supported by recent evidence.
    if not (audit.startswith("VERIFIED") and evidence and fresh(stamped, today)):
        return "REVIEW / UNVERIFIED"
    if raw in {"IN_PROGRESS", "RUNNING", "OPEN", "PENDING", "ACTIVE"}:
        return "RUNNING"
    if raw in {"STARTED", "LAUNCHED", "COMMENCED"}:
        return "STARTED"
    if raw in {"ANNOUNCED", "PRICED"}:
        return "ANNOUNCED"
    return "REVIEW / UNVERIFIED"


def add_financing_column(frame, index=None, source=None):
    """Insert event-specific FINANCING after DAYS TO PDUFA, preserving row IDs."""
    result = frame.copy()
    ticker = next((c for c in result.columns if name(c) == "ticker"), None)
    if ticker is None:
        return result
    if "FINANCING" in result and source is None:
        status = result.pop("FINANCING")
    else:
        if "FINANCING" in result:
            result = result.drop(columns=["FINANCING"])
        index = index or StageIndex()
        status = []
        for row_id, record in zip(result.index, result.to_dict("records")):
            own = (source.loc[row_id] if isinstance(source, pd.DataFrame) else source) if source is not None else record
            own = dict(own)
            if source is None and not get(values(own), "second_financing_status", "Financing #2 Status"):
                matched = index.matching_records(own)
                identities = {
                    (name(get(values(r), "drug")), name(get(values(r), "indication")),
                     get(values(r), "event_key")) for r in matched
                }
                if len(identities) == 1:
                    verified_states = {financing_stage(candidate, index.today)
                                       for candidate in matched} - {"REVIEW / UNVERIFIED"}
                    # Conflicting verified snapshots are not silently resolved.
                    if len(verified_states) == 1:
                        status.append(next(iter(verified_states)))
                        continue
            status.append(financing_stage(own, index.today))
    pivot = "DAYS TO PDUFA" if "DAYS TO PDUFA" in result else ticker
    result.insert(result.columns.get_loc(pivot) + 1, "FINANCING", status)
    return result
