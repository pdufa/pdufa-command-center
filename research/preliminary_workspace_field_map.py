"""Conservative mapping of published Pipeline row fields to research triage.

Only explicit, source-supported fields are eligible. Membership in the
published Pipeline does not prove that the approved restrictions were applied.
"""
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from research.preliminary_candidate_scope import preliminary_candidate_scope


def map_published_row(row, *, as_of=None):
    if not isinstance(row, dict):
        raise ValueError("published row must be an object")
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
    cap_supported = bool(cap_value is not None and isinstance(cap_source, str)
                         and urlparse(cap_source).scheme == "https"
                         and urlparse(cap_source).hostname
                         and isinstance(cap_checked, str) and cap_checked)
    fda_source = row.get("fdaSource")
    fda_supported = (bool(row.get("pdufaDate"))
                     and isinstance(fda_source, str)
                     and urlparse(fda_source).scheme == "https"
                     and (urlparse(fda_source).hostname == "fda.gov"
                          or urlparse(fda_source).hostname.endswith(".fda.gov"))
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
