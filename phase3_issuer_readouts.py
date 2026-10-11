"""Dated, exact-trial issuer readouts; publication does not imply success.

Registry follow-up can remain active and results unposted after corporate
topline disclosure. Preserve that distinction when screening pre-readout work.
"""
from datetime import date, datetime
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ISSUER_SOURCE = "ISSUER_TOPLINE_RELEASE"
REVIEW_STATUS = "ISSUER_TOPLINE_EXACT_TRIAL_REVIEW"
ANNOUNCED = "ANNOUNCED — EXACT-TRIAL SOURCE REVIEW"
ISSUER_HOSTS = {
    "ABVX": {"ir.abivax.com", "abivax.gcs-web.com"},
    "ACAD": {"acadia.com", "ir.acadia.com"},
}
PACIFIC = ZoneInfo("America/Los_Angeles")


def identity(row):
    values = [str(row.get(k) or "").strip().casefold()
              for k in ("ticker", "nct_id", "drug", "indication")]
    # The all-trials ledger includes comparator Placebo in its drug string.
    # Ignore only that exact comparator, never a second active intervention
    # or an unreviewed drug/dose alias.
    values[2] = " | ".join(sorted(part.strip() for part in values[2].split("|")
                                  if part.strip() and part.strip() != "placebo"))
    return tuple(values)


def issuer_readout_index(records, as_of):
    """Accept only reviewed primary sources and exact ticker/NCT/program keys.

    An announced result remains announced; it does not expire like an
    unreleased check. Collection dates still cannot leak into earlier cutoffs.
    """
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        cutoff = as_of.astimezone(PACIFIC).date()
    elif isinstance(as_of, date):
        cutoff = as_of
    else:
        cutoff = date.fromisoformat(str(as_of))
    found = {}
    for row in records or []:
        if not isinstance(row, dict) or row.get("source_type") != ISSUER_SOURCE:
            continue
        try:
            key = identity(row)
            ticker = key[0].upper()
            nct = key[1].upper()
            released = date.fromisoformat(str(row.get("phase3_results_posted_at") or ""))
            first_seen = datetime.fromisoformat(str(row.get("first_seen_at") or "").replace("Z", "+00:00"))
            checked = datetime.fromisoformat(str(row.get("last_checked_at") or "").replace("Z", "+00:00"))
            source = urlparse(str(row.get("phase3_results_source") or ""))
            registry = "https://clinicaltrials.gov/study/" + nct
            if not (re.fullmatch(r"NCT\d{8}", nct) and all(key)
                    and row.get("verification_status") == REVIEW_STATUS
                    and source.scheme == "https"
                    and source.hostname in ISSUER_HOSTS.get(ticker, set())
                    and registry in str(row.get("source_list_note") or "")
                    and first_seen.tzinfo and checked.tzinfo
                    and released <= first_seen.astimezone(PACIFIC).date() <= cutoff
                    and first_seen <= checked
                    and checked.astimezone(PACIFIC).date() <= cutoff):
                continue
            if isinstance(as_of, datetime) and checked > as_of:
                continue
            old = found.get(key)
            if old is None or released < date.fromisoformat(old["phase3_results_posted_at"]):
                found[key] = row
        except (ValueError, TypeError, AttributeError):
            continue
    return found
