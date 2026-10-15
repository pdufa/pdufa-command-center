"""Read completed, published filings results; never start a scan on refresh."""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from scan_status_ui import API, _json_get
from scripts.filings_section_scan import SECTIONS, SNAPSHOTS

DATA_FILES = (
    "sec_filing_watch.csv", "pdufa_source_verification.csv",
    "fda_pdufa_extension_ledger.csv", "pdufa_source_review_queue.csv",
    "company_registry.csv", "pdufa_candidates.csv", "gem_phase3_exact_recheck.csv",
    "gem_two_close_recheck.csv", "second_financing_status.csv",
)
RAW = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/"


def fetch_published_file(revision, relative, refresh_bucket=0, *, optional=False):
    suffix = "?refresh=" + str(refresh_bucket) if revision == "main" else ""
    request = urllib.request.Request(RAW + revision + "/data/" + relative + suffix,
        headers={"User-Agent": "pdufa-filings-details-refresh", "Accept": "text/plain"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read(8_000_001)
            if response.status != 200 or len(body) > 8_000_000:
                raise ValueError("Published details are unavailable or oversized")
            return body
    except urllib.error.HTTPError as error:
        if optional and error.code == 404:
            return None
        raise


@st.cache_data(max_entries=3, show_spinner=False)
def download_published_files(revision, refresh_bucket=0):
    if revision != "main" and not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Invalid publication revision")
    paths = list(DATA_FILES)
    optional = {"sec_filing_watch.csv"}
    snapshots = {}
    for section, (source, _) in SECTIONS.items():
        prefix = SNAPSHOTS + "/" + section.lower() + "/"
        report_path = prefix + "report.json"
        paths.append(report_path)
        optional.add(report_path)
        snapshots[report_path] = [prefix + source.lower() + "_verification.csv",
            prefix + ("sec_filing_watch.csv" if source == "SEC" else "fda_extensions.csv")]
    # Fetch one immutable revision when available. A missing/new manual
    # snapshot is optional; its scope and all hashes are checked before use.
    with ThreadPoolExecutor(max_workers=6) as pool:
        bodies = list(pool.map(lambda path: fetch_published_file(
            revision, path, refresh_bucket, optional=path in optional), paths))
        files = {path: body for path, body in zip(paths, bodies) if body is not None}
        artifacts = [path for report_path, names in snapshots.items() if report_path in files for path in names]
        bodies = list(pool.map(lambda path: fetch_published_file(
            revision, path, refresh_bucket, optional=True), artifacts))
        files.update((path, body) for path, body in zip(artifacts, bodies) if body is not None)
    return files


@st.cache_data(ttl=60, show_spinner=False)
def published_filings_files():
    """Refresh every minute, caching large CSVs by published data commit."""
    try:
        commits = _json_get(API + "/commits?path=data&per_page=1")
        revision = commits[0]["sha"]
        if not re.fullmatch(r"[a-f0-9]{40}", revision):
            raise ValueError("Invalid data revision")
        return download_published_files(revision), ""
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        # Public raw reads keep completed results available when an optional
        # API token is absent or GitHub's unauthenticated API is rate-limited.
        try:
            return download_published_files("main", int(time.time() // 60)), ""
        except (OSError, ValueError, KeyError, TypeError):
            return None, "Latest published details are unavailable; showing the last available snapshot."
