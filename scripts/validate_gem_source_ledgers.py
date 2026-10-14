#!/usr/bin/env python3
"""Strict GEM search input checks. Missing evidence stays REVIEW, never repaired by shifting columns."""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

KEY = re.compile(r"^[A-Z0-9.-]{1,15}\|[^\s|]+$")
TICKER = re.compile(r"^[A-Z0-9.-]{1,15}$")
NCT = re.compile(r"^NCT\d{8}$")
REQUIRED_CORE = {
    "NTLA|LONVOZ_HAE_20270310",
    "ZBIO|OBEXELIMAB_IGG4RD_20270527",
    "PRAX|ULIXACALTAMIDE_ET_20270129",
    "MLYS|LORUNDROSTAT_20261222",
    "SVRA|MOLBREEVI_PAP_20261122",
    "SRRK|APITEGROMAB_20260930",
}
PASS_STATUS = "VERIFIED_SECOND_POST_PHASE3_FINANCING"
POSITIVE = {"PRIMARY_MET_VERIFIED", "VERIFIED_SUCCESS", "RESULTS_VERIFIED"}


def read_strict(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file, strict=True)
        fields = next(reader)
        if len(fields) != len(set(fields)) or not fields:
            raise ValueError(f"{path}: missing or duplicated CSV header")
        records = []
        for line_number, values in enumerate(reader, 2):
            if len(values) != len(fields):
                raise ValueError(
                    f"{path}:{line_number}: {len(values)} CSV columns; expected {len(fields)}"
                )
            records.append(dict(zip(fields, values)))
        return records


def as_day(value, *, field, key):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key}: {field} is not an ISO date: {value!r}")


def https_primary(url, *, sec=False):
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and not parsed.username and not parsed.password
        and (not sec or (parsed.hostname in ("sec.gov", "www.sec.gov")
                         and parsed.path.startswith("/Archives/edgar/data/")))
    )


def validate(root="data"):
    root = Path(root)
    events = read_strict(root / "pdufa_candidates.csv")
    finance = read_strict(root / "second_financing_status.csv")
    if not events or not finance:
        raise ValueError("GEM discovery ledgers must not be empty")
    by_event = {}
    for event in events:
        key = event.get("event_key", "")
        ticker = event.get("ticker", "")
        if not KEY.fullmatch(key) or not TICKER.fullmatch(ticker):
            raise ValueError(f"invalid GEM event key/ticker: {key!r} / {ticker!r}")
        if not key.startswith(ticker + "|") or key in by_event:
            raise ValueError(f"duplicate or mismatched GEM event: {key}")
        if not event.get("company") or event["company"].startswith('"'):
            raise ValueError(f"{key}: company field looks like a broken CSV quote")
        as_day(event.get("pdufa_date"), field="pdufa_date", key=key)
        as_day(event.get("phase3_date"), field="phase3_date", key=key)
        nct = event.get("nct_id") or ""
        if nct and not NCT.fullmatch(nct) and event.get("phase3_status") in POSITIVE:
            raise ValueError(f"{key}: qualified Phase 3 missing valid exact NCT")
        by_event[key] = event
    seen = set()
    pass_keys = set()
    for row in finance:
        key = row.get("event_key", "")
        if key not in by_event or key in seen:
            raise ValueError(f"unlinked or duplicated financing event: {key!r}")
        seen.add(key)
        first = as_day(row.get("first_financing_date"), field="first_financing_date", key=key)
        second = as_day(row.get("second_financing_date"), field="second_financing_date", key=key)
        as_day(row.get("verified_as_of"), field="verified_as_of", key=key)
        if row.get("second_financing_audit_status") == PASS_STATUS:
            if not (
                row.get("second_financing_status") == "CLOSED"
                and row.get("second_financing_closed") == "YES"
                and first and second and first < second
                and https_primary(row.get("first_financing_source", ""), sec=True)
                and https_primary(row.get("second_financing_source", ""), sec=True)
            ):
                raise ValueError(f"{key}: claimed second close lacks distinct dates/SEC sources")
            pass_keys.add(key)
    for key in REQUIRED_CORE:
        if key not in pass_keys:
            raise ValueError(f"{key}: source-audited GEM financing evidence lost")
        event = by_event[key]
        close = next(x for x in finance if x["event_key"] == key)
        phase3 = as_day(event["phase3_date"], field="phase3_date", key=key)
        if (event.get("phase3_status") not in POSITIVE
                or not NCT.fullmatch(event.get("nct_id") or "")
                or not https_primary(event.get("trial_evidence_url", ""))
                or not phase3 or phase3 > date.fromisoformat(close["first_financing_date"])):
            raise ValueError(f"{key}: core GEM clinical/finance sequence is broken")
    for key in ("COGT|BEZUCLASTINIB_NONADVSM_20261230",
                "COGT|BEZUCLASTINIB_GIST_20261130"):
        if key in pass_keys:
            raise ValueError(f"{key}: premature GEM financing promotion")
    return {
        "regulatory_programs": len(events),
        "financing_block_programs": len(finance),
        "legacy_second_close_claims": len(pass_keys),
        "core_source_audited_programs": len(REQUIRED_CORE),
        "manual_entry_authorized": False,
        "status": "SAVED DATA STRUCTURE VALID — NOT LIVE SOURCE VERIFICATION",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate(args.data_dir), sort_keys=True))
    except (OSError, UnicodeError, csv.Error, ValueError) as ex:
        parser.exit(1, "GEM SEARCH DATA INVALID: " + str(ex) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
