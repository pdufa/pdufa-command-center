#!/usr/bin/env python3
"""Read-only external smoke check for the production SYSTEM STATUS page.

The check deliberately makes one unauthenticated HTTPS GET, never promotes a build,
triggers a scan, or changes any production data. A restricted/error page fails closed.
"""
from __future__ import annotations

import html
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
)


def verify_html(response_body: str) -> None:
    """Fail on login/challenge pages or incomplete table content."""
    document = html.unescape(response_body)
    missing = [item for item in REQUIRED_TEXT if item not in document]
    if missing:
        raise ValueError("Production page did not contain: " + ", ".join(missing))


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
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print("NOT VERIFIED: production page unavailable or incomplete: " + str(exc), file=sys.stderr)
        return 1
    print("PASS: exact production route returned HTTP 200 with all 15 sections.")
    print("This verifies basic page delivery only, not all application runtime functions or scientific evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
