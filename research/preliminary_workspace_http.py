"""Authenticated GET client for the existing Pipeline workspace API.

Use PDUFA_INTERNAL_API_KEY from the operator environment; never print the key.
No network calls occur on import. The backend may refresh external source caches
and allocate persistent program identities when preparing a page. No production
settings, memberships, scanner or trading mutations are requested by this client.
"""
from datetime import datetime, timezone
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener

from research.preliminary_workspace_adapter import triage_workspace_pages
from research.fda_official_document_fetch import _NoRedirects
from research.official_adjudication_packets import _unique_keys


def urlopen(request, *, timeout):
    # Never forward the internal authentication header through a redirect.
    return build_opener(_NoRedirects()).open(request, timeout=timeout)


def _invalid_constant(value):
    raise ValueError('nonfinite workspace JSON')


def make_workspace_get(base_url, *, api_key=None, timeout=20, allow_identity_allocation=False):
    return make_workspace_client(base_url, api_key=api_key, timeout=timeout,
                                 allow_identity_allocation=allow_identity_allocation)[0]


def make_workspace_client(base_url, *, api_key=None, timeout=20, allow_identity_allocation=False):
    if allow_identity_allocation is not True:
        raise ValueError('explicit authorization for possible staging program-ID allocation required')
    if not isinstance(base_url, str):
        raise ValueError("HTTPS backend origin required")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("HTTPS backend origin required")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("backend origin must not include path or query")
    try:
        if (not parsed.hostname or parsed.port not in (None, 443)
                or any(c.isspace() or ord(c) < 32 for c in base_url)):
            raise ValueError("invalid backend origin")
    except ValueError:
        raise ValueError("HTTPS backend origin on port 443 required") from None
    key = api_key if api_key is not None else os.environ.get("PDUFA_INTERNAL_API_KEY")
    if (not isinstance(key, str) or not key or key != key.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in key)):
        raise ValueError("PDUFA_INTERNAL_API_KEY is required")
    if type(timeout) not in (int, float) or not 0 < timeout <= 120:
        raise ValueError("bounded timeout required")
    origin = base_url.rstrip("/")

    def get_json(path):
        request = Request(
            origin + path,
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
            result = json.loads(raw, object_pairs_hook=_unique_keys, parse_constant=_invalid_constant)
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (UnicodeDecodeError, ValueError):
            raise ValueError("invalid workspace JSON") from None

    def get_page(*, offset, limit, version):
        query = urlencode({"offset": offset, "limit": limit, "version": version})
        return get_json("/api/workspace/page?" + query)

    return get_page, lambda: get_json("/api/workspace/summary")


def screen_backend_workspace(base_url, *, api_key=None, allow_identity_allocation=False):
    if allow_identity_allocation is not True:
        raise ValueError('explicit authorization for possible staging program-ID allocation required')
    page, summary = make_workspace_client(base_url, api_key=api_key,
                                          allow_identity_allocation=allow_identity_allocation)
    return triage_workspace_pages(page, get_summary=summary,
        now=datetime.now(timezone.utc).isoformat())


def safe_workspace_diagnostics(base_url, *, api_key=None, allow_identity_allocation=False):
    """Return aggregate screening diagnostics without exposing individual records."""
    report = screen_backend_workspace(base_url, api_key=api_key,
                                     allow_identity_allocation=allow_identity_allocation)
    keys = (
        "workspace_version", "workspace_as_of", "backend_rows_received",
        "market_cap_evidence_present", "fda_target_evidence_present",
        "candidate_for_evidence_review", "blocked", "prediction_status",
        "data_authenticity_verified",
    )
    result = {key: report[key] for key in keys}
    for key in ('retrieval_complete', 'summary_reconciled', 'snapshot_freshness_checked',
                'page_count', 'source_rows_sha256', 'hash_scope'):
        if key in report:
            result[key] = report[key]
    return result


def main(argv=None):
    """Operator runner; key comes only from the securely bound environment."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend-origin', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-staging-identity-allocation', action='store_true',
                        help='operator authorizes insert-only allocation of missing permanent IDs')
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('output exists; refusing overwrite')
    try:
        result = safe_workspace_diagnostics(args.backend_origin,
            allow_identity_allocation=args.allow_staging_identity_allocation)
    except ValueError as exc:
        parser.exit(2, str(exc) + '\n')
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
