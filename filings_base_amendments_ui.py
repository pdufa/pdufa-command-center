"""Read-only SEC/FDA base and amendment table for the existing SCANS page.

SEC rows: actual EDGAR form metadata only, not proof money closed.
FDA rows: canonical primary verification claims and dated regulatory
extensions. Public PDUFA extensions are not necessarily NDA amendments.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
FILINGS = ROOT / "data" / "sec_filing_watch.csv"
VERIFICATION = ROOT / "data" / "pdufa_source_verification.csv"
EXTENSIONS = ROOT / "data" / "fda_pdufa_extension_ledger.csv"


def read_csv(path):
    if not Path(path).is_file():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def table_rows(sec_filings, verification, extensions):
    """Build four transparent source-specific tables without imputing proof."""
    sec_base, sec_amend, fda_base, fda_amend = [], [], [], []
    for row in sec_filings:
        form = str(row.get("filing_type", "")).strip().upper()
        expected = "AMENDMENT" if form.endswith("/A") or form == "POS AM" else "BASE"
        if (row.get("category") != expected or
                row.get("evidence_scope") != "SEC_INDEX_METADATA_ONLY_NOT_FINANCING_CLOSURE"):
            continue
        record = {
            "Ticker": row.get("ticker", ""), "Form": form,
            "Filing date": row.get("filed_at", ""),
            "Accession": row.get("accession_number", ""),
            "Evidence": "SEC index only — closing not established",
            "Primary source": row.get("filing_url", ""),
        }
        (sec_amend if expected == "AMENDMENT" else sec_base).append(record)
    fda_by_key = {}
    for row in verification:
        if row.get("category") != "FDA" or row.get("claim") not in {"PDUFA_TARGET", "FDA_DECISION"}:
            continue
        key = row.get("event_key", "")
        fda_by_key[key] = row
        fda_base.append({
            "Ticker": row.get("ticker", ""), "Trial / event": key,
            "Claim": row.get("claim", ""),
            "Expected": row.get("expected", ""),
            "Observed": row.get("observed", ""),
            "Verification": row.get("verification_status", "REVIEW_REQUIRED"),
            "Primary source": row.get("source_url", ""),
        })
    seen = set()
    for item in extensions:
        try:
            seq = int(item.get("extension_sequence", "0"))
        except (TypeError, ValueError):
            continue
        old_date = item.get("prior_pdufa_date", "")
        new_date = item.get("current_pdufa_date", "")
        if seq < 1 or not old_date or not new_date or old_date == new_date:
            continue
        event = item.get("event_key", "")
        key = (event, old_date, new_date)
        if key in seen:
            continue
        seen.add(key)
        verified = fda_by_key.get(event, {})
        # The extension ledger is a research observation. Do not inherit
        # unrelated FDA target/decision verification from the base filing.
        authoritative = (
            verified.get("claim") == "PDUFA_TARGET"
            and verified.get("verification_status") == "VERIFIED"
            and verified.get("observed") == new_date
            and verified.get("reason", "").startswith(
                "Explicit dated FDA PDUFA extension supersedes " + old_date)
        )
        fda_amend.append({
            "Ticker": item.get("ticker", ""), "Trial / event": event,
            "Update type": "PDUFA-date extension",
            "Prior date": old_date, "Revised date": new_date,
            "Verification": "VERIFIED" if authoritative else "REVIEW_REQUIRED",
            "Primary source": verified.get("source_url", "") if authoritative else "",
        })
    # A verified documented extension can exist even before the separate
    # extension-tracking ledger is refreshed. Include it without duplication.
    for key, item in fda_by_key.items():
        if (item.get("claim") != "PDUFA_TARGET" or
                item.get("verification_status") != "VERIFIED"):
            continue
        pattern = r"^Explicit dated FDA PDUFA extension supersedes (\\d{4}-\\d{2}-\\d{2})$"
        found = re.match(pattern, item.get("reason", ""))
        if not found:
            continue
        old_date, new_date = found.group(1), item.get("observed", "")
        identity = (key, old_date, new_date)
        if identity in seen or not new_date or old_date == new_date:
            continue
        seen.add(identity)
        fda_amend.append({
            "Ticker": item.get("ticker", ""), "Trial / event": key,
            "Update type": "PDUFA-date extension",
            "Prior date": old_date, "Revised date": new_date,
            "Verification": "VERIFIED",
            "Primary source": item.get("source_url", ""),
        })
    for records, date_key in ((sec_base, "Filing date"), (sec_amend, "Filing date"),
                              (fda_base, "Trial / event"), (fda_amend, "Revised date")):
        records.sort(key=lambda r: str(r.get(date_key, "")), reverse=True)
    return {"SEC Base": sec_base, "SEC Amendments": sec_amend,
            "FDA Base": fda_base, "FDA Amendments": fda_amend}


def render_filings_base_amendments():
    st.markdown("### SEC & FDA — Base filings and amendments")
    st.caption(
        "Read-only source evidence. Weekdays: new/changed filings, trial events and "
        "unresolved cases; Sundays: full reconciliation at 10 PM Pacific. "
        "Filings-index metadata does not certify a financing close, and an "
        "FDA target-date extension is not proof of a formal NDA amendment.")
    sec_rows = read_csv(FILINGS)
    source_exists = bool(sec_rows)
    tables = table_rows(sec_rows, read_csv(VERIFICATION), read_csv(EXTENSIONS))
    metrics = pd.DataFrame([
        {"Agency": "SEC · EDGAR", "Base filings": len(tables["SEC Base"]) if source_exists else "PENDING",
         "Amendments": len(tables["SEC Amendments"]) if source_exists else "PENDING",
         "Scope": "Latest indexed SEC forms"},
        {"Agency": "FDA · regulatory cases", "Base filings": len(tables["FDA Base"]),
         "Amendments": len(tables["FDA Amendments"]),
         "Scope": "Primary target/decision claims + PDUFA extensions"},
    ])
    st.dataframe(metrics, use_container_width=True, hide_index=True)
    agency_sec, agency_fda = st.tabs(["SEC filings", "FDA actions and updates"])
    with agency_sec:
        if not source_exists:
            st.info("SEC form-level filing inventory has not been published yet. "
                    "It will populate from the next successful SEC index scan; "
                    "no missing amendments are assumed to be zero.")
        st.caption("SEC form /A (or POS AM) identifies a filing amendment. "
                   "Prospectus supplements and signed financing closings require "
                   "their own document-level checks.")
        base, amendments = st.tabs(["Base filings", "Amendments /A"])
        for tab, key in ((base, "SEC Base"), (amendments, "SEC Amendments")):
            with tab:
                records = tables[key]
                if records:
                    st.dataframe(pd.DataFrame(records), use_container_width=True,
                                 hide_index=True,
                                 column_config={"Primary source": st.column_config.LinkColumn(
                                     "EDGAR filing")})
                else:
                    st.caption("No classified index records available for this section.")
    with agency_fda:
        st.caption("FDA base rows are event-specific source checks. FDA amendment "
                   "rows represent documented/reported target-date extensions; "
                   "they do not represent an FDA-published application amendment register.")
        base, updates = st.tabs(["Base FDA claims", "Amendments / extensions"])
        for tab, key in ((base, "FDA Base"), (updates, "FDA Amendments")):
            with tab:
                records = tables[key]
                if records:
                    st.dataframe(pd.DataFrame(records), use_container_width=True,
                                 hide_index=True,
                                 column_config={"Primary source": st.column_config.LinkColumn(
                                     "Primary evidence")})
                else:
                    st.caption("No recorded primary evidence for this section; "
                               "a blank table does not establish no changes.")
