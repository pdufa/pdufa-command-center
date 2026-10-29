"""Research-only PDUFA target provenance classification.

A sponsor's dated statement may document a PDUFA goal date without being
an FDA-issued confirmation. URL host alone never verifies document contents.
No category returned here authorizes a prediction or source-record mutation.
"""
from datetime import date
from urllib.parse import urlparse


def _host(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        return None
    try:
        u = urlparse(value)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.fragment or u.port not in (None, 443):
            return None
        return u.hostname.lower()
    except ValueError:
        return None


def classify_target_provenance(row):
    if not isinstance(row, dict):
        raise ValueError("source row must be an object")
    value = row.get("pdufaDate")
    try:
        valid_date = isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        valid_date = False
    host = _host(row.get("fdaSource"))
    fda_host = bool(host and (host == "fda.gov" or host.endswith(".fda.gov")))
    sec_host = bool(host and (host == "sec.gov" or host.endswith(".sec.gov")))
    status = row.get("checkStatus")
    accepted = status in ("VERIFIED", "FDA_VERIFIED")
    # A sponsor/SEC URL is a lead for document-level review, not verification.
    if not valid_date:
        category = "INVALID_OR_MISSING_DATE"
    elif fda_host and accepted:
        category = "FDA_HOST_AND_STATUS_CLAIM_REQUIRES_DOCUMENT_REVIEW"
    elif fda_host:
        category = "FDA_HOST_LEAD_REQUIRES_DOCUMENT_REVIEW"
    elif sec_host:
        category = "SEC_FILING_LEAD_REQUIRES_SPONSOR_DATE_REVIEW"
    elif host:
        category = "OTHER_SOURCE_LEAD_REQUIRES_REVIEW"
    else:
        category = "DATE_WITHOUT_USABLE_SOURCE"
    return {
        "category": category,
        "valid_target_date": valid_date,
        "fda_host": fda_host,
        "sec_filing_host": sec_host,
        "accepted_status_claim": accepted,
        "document_content_verified": False,
        "prediction_status": "ABSTAIN",
    }
