"""Conservative mapping of published Pipeline row fields to research triage.

Only explicit, source-supported fields are eligible. Membership in the
published Pipeline does not prove that the approved restrictions were applied.
"""
from datetime import date, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from research.preliminary_candidate_scope import preliminary_candidate_scope
from research.preliminary_pipeline_snapshot import _aware


def _https(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        return None
    try:
        parsed = urlparse(value)
        if (parsed.scheme == 'https' and parsed.hostname and not parsed.username
                and not parsed.password and not parsed.fragment and parsed.port in (None, 443)):
            return parsed.hostname
    except ValueError:
        pass
    return None


def map_published_row(row, *, as_of=None, max_cap_age_days=7):
    if not isinstance(row, dict):
        raise ValueError("published row must be an object")
    if type(max_cap_age_days) is not int or not 0 <= max_cap_age_days <= 30:
        raise ValueError("explicit bounded research cap freshness window required")
    key = row.get("programId")
    if not isinstance(key, str) or not key.startswith("PDUFA-"):
        raise ValueError("published row lacks permanent program identity")
    cap = row.get("marketCap")
    try:
        if isinstance(cap, bool) or not isinstance(cap, (int, str, Decimal)):
            raise InvalidOperation
        cap_value = Decimal(str(cap))
        if not cap_value.is_finite() or cap_value <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        cap_value = None
    cap_source = row.get("capSource")
    cap_checked = row.get("capChecked")
    try:
        checked_day = date.fromisoformat(cap_checked) if isinstance(cap_checked, str) else None
        if checked_day is not None and checked_day.isoformat() != cap_checked:
            checked_day = None
    except ValueError:
        checked_day = None
    checked_clock = _aware(cap_checked)
    if checked_clock is not None:
        checked_day = checked_clock.astimezone(timezone.utc).date()
    as_of_clock = _aware(as_of) if as_of is not None else None
    timely_cap = checked_day is not None and (as_of is None or as_of_clock is not None
        and 0 <= (as_of_clock.astimezone(timezone.utc).date() - checked_day).days <= max_cap_age_days
        and (checked_clock is None or checked_clock <= as_of_clock))
    cap_supported = bool(cap_value is not None and _https(cap_source)
                         and checked_day is not None)
    cap_supported = cap_supported and timely_cap
    fda_source = row.get("fdaSource")
    host = _https(fda_source)
    try:
        target = date.fromisoformat(row.get('pdufaDate'))
        target_valid = target.isoformat() == row.get('pdufaDate')
    except (ValueError, TypeError):
        target_valid = False
    fda_supported = (target_valid and host is not None
                     and (host == "fda.gov" or host.endswith(".fda.gov"))
                     and row.get("checkStatus") in ("VERIFIED", "FDA_VERIFIED"))
    # No assumption of listing status or active restriction membership from a
    # ticker alone. The caller must independently establish both.
    candidate = {
        "program_id": key,
        "publicly_traded": False,
        "market_cap_usd": cap_value if cap_supported else None,
        "pipeline_member": False,
        "fda_pdufa_target_confirmed": bool(fda_supported),
    }
    return {"candidate": candidate,
            "cap_source_present": cap_supported,
            "fda_source_present": bool(fda_supported),
            "listing_verified": False,
            "restrictions_verified": False,
            "scope": preliminary_candidate_scope(candidate)["scope"]}
