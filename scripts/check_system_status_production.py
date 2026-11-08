#!/usr/bin/env python3
"""Read-only external smoke check for the production SYSTEM STATUS page.

The same bounded read-only checks run against production by default or against a
real PR production build on an allowlisted CI loopback origin. The check never
promotes a build, triggers a scan, or changes data. Restricted/error pages fail closed.
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://pdufa-new-dashboard.vercel.app"
URL = DEFAULT_BASE_URL + "/installation-audit"
ALLOWED_HOSTS = {"pdufa-new-dashboard.vercel.app", "pdufa-new-dashboard-pdufa.vercel.app"}
REQUIRED_TEXT = (
    "System installation & evidence tracker",
    "Core Platform",
    "Pipeline",
    "POOL / PIPELINE",
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
    "These gate counts do not measure percentage of engineering hours remaining.",
    "SCIENCE and OUTCOME — protected evidence checks",
    "Verify current SCIENCE + OUTCOME evidence",
    "Deep Medical Intelligence · independent investigation",
    "OUTCOME · historical FDA validation",
    "Certification: NOT VERIFIED.",
    "Certification: NOT VALIDATED.",
)


def normalize_base_url(value: str) -> str:
    """Only this project's HTTPS hosts or explicit CI loopback origins."""
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid smoke base URL") from exc
    if (parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise ValueError("Smoke base URL must be an origin without credentials, path, query or fragment")
    local = parsed.hostname in ("localhost", "127.0.0.1")
    if local:
        if parsed.scheme not in ("http", "https") or port == 0:
            raise ValueError("CI loopback requires HTTP(S) and a valid port")
    elif parsed.hostname not in ALLOWED_HOSTS or parsed.scheme != "https" or port not in (None, 443):
        raise ValueError("Smoke base URL is not an allowed project HTTPS host or CI loopback")
    netloc = parsed.hostname
    if port is not None and port != (443 if parsed.scheme == "https" else 80):
        netloc += ":" + str(port)
    return urllib.parse.urlunsplit((parsed.scheme, netloc, "", "", ""))


def _origin(url: str):
    parsed = urllib.parse.urlsplit(url)
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def _same_origin(destination: str, requested: str) -> bool:
    try:
        return _origin(destination) == _origin(requested)
    except ValueError:
        return False


def verify_html(response_body: str) -> None:
    """Fail on login/challenge pages or incomplete table content."""
    document = html.unescape(response_body)
    missing = [item for item in REQUIRED_TEXT if item not in document]
    if missing:
        raise ValueError("Production page did not contain: " + ", ".join(missing))


def verify_unauthenticated_protected_api(path: str, base_url: str = DEFAULT_BASE_URL) -> None:
    """Unauthenticated requests must fail closed; do not fetch protected evidence."""
    if path not in ("/api/assessments", "/api/hop/readiness",
                   "/api/phase3-registry?exact_nct=NCT02142738"):
        raise ValueError("Unexpected protected API path")
    url = normalize_base_url(base_url) + path
    request = urllib.request.Request(
        url, headers={"User-Agent": "PDUFA-ReadOnly-Installation-Smoke/1.0", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            raise ValueError("Protected evidence was accessible without a session (HTTP " + str(response.status) + ")")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise ValueError("Protected endpoint did not return HTTP 401 (" + str(exc.code) + ")") from exc
        if not _same_origin(exc.geturl(), url):
            raise ValueError("Protected endpoint unexpectedly redirected away from the requested origin") from exc
        if urllib.parse.urlsplit(exc.geturl()).path != urllib.parse.urlsplit(url).path or urllib.parse.urlsplit(exc.geturl()).query != urllib.parse.urlsplit(url).query:
            raise ValueError("Protected endpoint redirected to a different path") from exc
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


def verify_phase3_census_production(base_url: str = DEFAULT_BASE_URL) -> None:
    """Read-only check that production serves the dated page AND exact CSV bytes.

    The source comes from the repository, never from runtime market data.
    A challenge/login page, redirected path, stale content, partial file,
    added candidates, or source-byte drift MUST fail rather than inflate
    qualified Pipeline coverage.
    """
    base = normalize_base_url(base_url)
    urls = [
        (base + "/installation-audit/phase3-census", "text/html", 2_000_000),
        (base + "/phase3-census-2026-10-26.csv", "text/csv", 160_000),
    ]
    bodies: list[bytes] = []
    for url, media, max_bytes in urls:
        req = urllib.request.Request(
            url, headers={"User-Agent": "PDUFA-ReadOnly-Phase3-Census-Smoke/1.0", "Accept": media},
        )
        with urllib.request.urlopen(req, timeout=18) as response:
            destination = urllib.parse.urlsplit(response.geturl())
            requested = urllib.parse.urlsplit(url)
            if not _same_origin(response.geturl(), url):
                raise ValueError("Unexpected census redirect origin")
            if destination.path != requested.path or destination.query:
                raise ValueError("Census route redirected to a different page")
            if response.status != 200:
                raise ValueError("Census public resource returned non-200")
            content_type = response.headers.get("content-type", "").lower()
            if media not in content_type and not (media == "text/csv" and "application/octet-stream" in content_type):
                raise ValueError("Census resource returned the wrong content type")
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValueError("Census resource exceeded the bounded read limit")
            bodies.append(data)

    document = html.unescape(bodies[0].decode("utf-8", errors="replace"))
    for phrase in (
        "Phase 3 market-cap census",
        "741 unique trial IDs",
        "not a complete qualified Pipeline",
    ):
        if phrase not in document:
            raise ValueError("Incomplete public Phase 3 research page: " + phrase)

    # The all-years research input can grow independently. This route serves
    # the immutable dated 741-trial publication, so compare against that exact
    # committed snapshot while retaining all identity and source-URL checks.
    original = (Path(__file__).resolve().parents[1]
                / "new-platform" / "frontend" / "public"
                / "phase3-census-2026-10-26.csv").read_bytes()
    if bodies[1] != original:
        raise ValueError("Production census CSV differs from committed 741-row original")
    rows = list(csv.DictReader(io.StringIO(original.decode("utf-8"))))
    nct = {row["nct_id"] for row in rows}
    tickers = {row["ticker"] for row in rows}
    if len(rows) != 741 or len(nct) != 741 or len(tickers) != 130 or any(
        row["source_url"] != "https://clinicaltrials.gov/study/" + row["nct_id"]
        for row in rows
    ):
        raise ValueError("Production census rows do not reconcile to original ClinicalTrials.gov IDs")
    print("PASS: target 741-trial explorer HTTP 200 and CSV byte-for-byte source match; 130 tickers. No Pipeline qualification inferred.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help="Allowed project HTTPS origin or CI localhost/127.0.0.1 origin")
    args = parser.parse_args(argv)
    try:
        base = normalize_base_url(args.base_url)
        url = base + "/installation-audit"
        print("Read-only SYSTEM STATUS GET: " + url, flush=True)
        request = urllib.request.Request(
            url, headers={"User-Agent": "PDUFA-ReadOnly-Installation-Smoke/1.0", "Accept": "text/html"}
        )
        with urllib.request.urlopen(request, timeout=18) as response:
            destination = urllib.parse.urlsplit(response.geturl())
            if not _same_origin(response.geturl(), url):
                raise ValueError("Unexpected redirect origin: " + str(destination.hostname))
            if destination.path != "/installation-audit" or destination.query:
                raise ValueError("Installation route redirected to a different page")
            if response.status != 200:
                raise ValueError("Unexpected response status: " + str(response.status))
            if "text/html" not in response.headers.get("content-type", "").lower():
                raise ValueError("Not an HTML response")
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError("Page exceeds inspection limit")
            verify_html(data.decode("utf-8", errors="replace"))
        for protected_path in ("/api/assessments", "/api/hop/readiness",
                               "/api/phase3-registry?exact_nct=NCT02142738"):
            verify_unauthenticated_protected_api(protected_path, base)
        verify_phase3_census_production(base)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print("NOT VERIFIED: production page unavailable or incomplete: " + str(exc), file=sys.stderr)
        return 1
    print("PASS: target route returned HTTP 200 with all 15 sections, both evidence panels, protected API guards and exact 741-row Phase 3 research inventory.")
    print("This verifies anonymous access security only; authenticated API operation and scientific evidence remain unverified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
