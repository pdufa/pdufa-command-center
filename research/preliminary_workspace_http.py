"""Authenticated read-only GET client for the existing Pipeline workspace API.

Use PDUFA_INTERNAL_API_KEY from the operator environment; never print the key.
No network calls occur on import. No writes or trading operations are available.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from research.preliminary_workspace_adapter import triage_workspace_pages


def make_workspace_get(base_url, *, api_key=None, timeout=20):
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("HTTPS backend origin required")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("backend origin must not include path or query")
    key = api_key if api_key is not None else os.environ.get("PDUFA_INTERNAL_API_KEY")
    if not key:
        raise ValueError("PDUFA_INTERNAL_API_KEY is required")
    origin = base_url.rstrip("/")

    def get_page(*, offset, limit, version):
        query = urlencode({"offset": offset, "limit": limit, "version": version})
        request = Request(
            origin + "/api/workspace/page?" + query,
            headers={"X-PDUFA-Internal-Key": key, "Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError("workspace returned non-200 status")
                raw = response.read(2_000_001)
        except (HTTPError, URLError) as exc:
            raise ValueError("workspace unavailable or access denied") from None
        if len(raw) > 2_000_000:
            raise ValueError("workspace page too large")
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("invalid workspace JSON") from None

    return get_page


def screen_backend_workspace(base_url, *, api_key=None):
    return triage_workspace_pages(make_workspace_get(base_url, api_key=api_key))


def safe_workspace_diagnostics(base_url, *, api_key=None):
    """Return aggregate screening diagnostics without exposing individual records."""
    report = screen_backend_workspace(base_url, api_key=api_key)
    keys = (
        "workspace_version", "workspace_as_of", "backend_rows_received",
        "market_cap_evidence_present", "fda_target_evidence_present",
        "candidate_for_evidence_review", "blocked", "prediction_status",
        "data_authenticity_verified",
    )
    return {key: report[key] for key in keys}
