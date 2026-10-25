#!/usr/bin/env python3
"""Read-only external smoke check for the production SYSTEM STATUS page.

The check deliberately makes one unauthenticated HTTPS GET, never promotes a build,
triggers a scan, or changes any production data. A restricted/error page fails closed.
"""
from __future__ import annotations

import html
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = "https://pdufa-new-dashboard.vercel.app/installation-audit"
ALLOWED_HOSTS = {"pdufa-new-dashboard.vercel.app", "pdufa-new-dashboard-pdufa.vercel.app"}
REQUIRED_TEXT = (
    "System installation & evidence tracker",
    "Core Platform",
    "Pipeline",
    "GEM JR / GEM / WT",
    "Scientific Assessment",
    "Historical Trial Database",
    "Prediction Engine",
    "Evidence Verification",
    "Regulatory Intelligence",
    "Investment Analysis",
    "Nightly Scanning",
    "Results & Reporting",
    "Automation",
    "Backup & Recovery",
    "Prediction Validation",
    "Final Acceptance",
    "No numerical installation percentage is asserted",
    "SCIENCE and OUTCOME — protected evidence checks",
    "Verify current SCIENCE + OUTCOME evidence",
    "SCIENCE · 40 investigations",
    "OUTCOME · historical FDA validation",
    "Certification: NOT VERIFIED.",
    "Certification: NOT VALIDATED.",
)


def verify_html(response_body: str) -> None:
    """Fail on login/challenge pages or incomplete table content."""
    document = html.unescape(response_body)
    missing = [item for item in REQUIRED_TEXT if item not in document]
    if missing:
        raise ValueError("Production page did not contain: " + ", ".join(missing))


def verify_unauthenticated_protected_api(path: str) -> None:
    """Unauthenticated requests must fail closed; do not fetch protected evidence."""
    if path not in ("/api/assessments", "/api/hop/readiness"):
        raise ValueError("Unexpected protected API path")
    url = urllib.parse.urljoin(URL, path)
    request = urllib.request.Request(
        url, headers={"User-Agent": "PDUFA-ReadOnly-Installation-Smoke/1.0", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            raise ValueError("Protected evidence was accessible without a session (HTTP " + str(response.status) + ")")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise ValueError("Protected endpoint did not return HTTP 401 (" + str(exc.code) + ")") from exc
        if urllib.parse.urlsplit(exc.geturl()).hostname not in ALLOWED_HOSTS:
            raise ValueError("Protected endpoint unexpectedly redirected away from the production host") from exc
        if "application/json" not in exc.headers.get("content-type", "").lower():
            raise ValueError("Protected endpoint returned non-JSON data") from exc
        body = exc.read(65_537)
        if len(body) > 65_536:
            raise ValueError("Protected endpoint returned an oversized error response") from exc
        try:
            data = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Protected endpoint returned invalid JSON") from error
        if data != {"error": "Authentication required"}:
            raise ValueError("Protected endpoint returned unexpected data to an unauthenticated user")
    print("PASS: " + path + " denies anonymous access with HTTP 401 and no evidence payload.")


def main() -> int:
    print("Read-only production GET: " + URL, flush=True)
    try:
        request = urllib.request.Request(
            URL, headers={"User-Agent": "PDUFA-ReadOnly-Installation-Smoke/1.0", "Accept": "text/html"}
        )
        with urllib.request.urlopen(request, timeout=18) as response:
            destination = urllib.parse.urlsplit(response.geturl())
            if destination.scheme != "https" or destination.hostname not in ALLOWED_HOSTS:
                raise ValueError("Unexpected redirect origin: " + str(destination.hostname))
            if response.status != 200:
                raise ValueError("Unexpected response status: " + str(response.status))
            if "text/html" not in response.headers.get("content-type", "").lower():
                raise ValueError("Not an HTML response")
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError("Page exceeds inspection limit")
            verify_html(data.decode("utf-8", errors="replace"))
        for protected_path in ("/api/assessments", "/api/hop/readiness"):
            verify_unauthenticated_protected_api(protected_path)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print("NOT VERIFIED: production page unavailable or incomplete: " + str(exc), file=sys.stderr)
        return 1
    print("PASS: production route returned HTTP 200 with all 15 sections, both evidence panels, and protected API guards.")
    print("This verifies anonymous access security only; authenticated API operation and scientific evidence remain unverified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
