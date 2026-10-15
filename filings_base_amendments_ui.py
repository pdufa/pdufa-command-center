"""Read-only SEC/FDA base and amendment table for the existing SCANS page.

SEC rows: actual EDGAR form metadata only, not proof money closed.
FDA rows: canonical primary verification claims and dated regulatory
extensions. Public PDUFA extensions are not necessarily NDA amendments.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from scan_status_ui import required_issue_queue

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
FILINGS = ROOT / "data" / "sec_filing_watch.csv"
VERIFICATION = ROOT / "data" / "pdufa_source_verification.csv"
EXTENSIONS = ROOT / "data" / "fda_pdufa_extension_ledger.csv"
RESEARCH_QUEUE = ROOT / "data" / "pdufa_source_review_queue.csv"
REGISTRY = ROOT / "data" / "company_registry.csv"
CANDIDATES = ROOT / "data" / "pdufa_candidates.csv"
PHASE3_CHECKS = ROOT / "data" / "gem_phase3_exact_recheck.csv"
SEC_PAIR_CHECKS = ROOT / "data" / "gem_two_close_recheck.csv"
FINANCING_HISTORY = ROOT / "data" / "second_financing_status.csv"
PACIFIC = ZoneInfo("America/Los_Angeles")


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
        pattern = r"^Explicit dated FDA PDUFA extension supersedes (\d{4}-\d{2}-\d{2})$"
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




def pacific_date(value):
    """Interpret actual timestamps in Pacific time; date-only values are dates."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", raw):
        return raw
    try:
        when = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if when.tzinfo is None:
            return ""  # Never silently guess a timezone for a detection.
        return when.astimezone(PACIFIC).date().isoformat()
    except (ValueError, OverflowError, TypeError):
        return ""


def program_base_rows(candidates, phase3_checks, finance_checks, financing_history,
                      verification):
    """Exact-event clinical + BOTH financing benchmarks alongside each agency claim.

    Prior 'second-financing verified' history is *not* live SEC verification,
    nor does a primary clinical status imply GEM gate eligibility.
    """
    p3 = {r.get("event_key"): r for r in phase3_checks if r.get("event_key")}
    sec_pairs = {r.get("event_key"): r for r in finance_checks if r.get("event_key")}
    hist = {r.get("event_key"): r for r in financing_history if r.get("event_key")}
    agency = {
        (r.get("event_key"), r.get("category")): r for r in verification
        if r.get("category") in {"SEC", "FDA"} and
        r.get("claim") in {"FINANCING_CLOSURE", "PDUFA_TARGET", "FDA_DECISION"}
    }
    sec, fda = [], []
    for event in candidates:
        key = str(event.get("event_key", "")).strip()
        ticker = str(event.get("ticker", "")).strip().upper()
        if not key or not ticker:
            continue
        p = p3.get(key, {})
        pair = sec_pairs.get(key, {})
        history = hist.get(key, {})
        readout_date = p.get("saved_phase3_date") or event.get("phase3_date", "")
        clinical_status = p.get("saved_phase3_status") or event.get("phase3_status", "UNVERIFIED")
        trial_url = p.get("saved_trial_source") or event.get("trial_evidence_url", "")
        nct = p.get("nct_ids") or event.get("nct_id", "")
        p3_review = p.get("source_recheck_status", "NOT_RECHECKED")
        # Documented readout and exact trial match can be reviewed separately.
        phase3_supported = (
            clinical_status in {"PRIMARY_MET_VERIFIED", "RESULTS_VERIFIED"}
            and bool(readout_date) and bool(trial_url) and bool(nct)
        )
        first_close = pair.get("first_close_date") or history.get("first_financing_date", "")
        second_close = pair.get("second_close_date") or history.get("second_financing_date", "")
        first_sec = pair.get("first_sec_status", "NOT_CHECKED")
        second_sec = pair.get("second_sec_status", "NOT_CHECKED")
        two_docs = (first_sec == "VERIFIED" and second_sec == "VERIFIED" and
                    pair.get("recheck_status") == "TRANSACTIONS_RECHECKED_REVIEW")
        # Both SEC docs may be independently verified but separate financing
        # identity and exact post-readout sequence can remain adjudication gaps.
        funding_status = ("BOTH_DOCUMENTS_VERIFIED_SEQUENCE_REVIEW" if two_docs
                          else "SECOND_FINANCING_REVIEW_REQUIRED")
        gap_flags = []
        if not phase3_supported or p3_review != "EXACT_PROGRAM_VERIFIED":
            gap_flags.append("PHASE3_EXACT_EVIDENCE")
        if not two_docs:
            gap_flags.append("TWO_FINANCING_DOCUMENTS")
        else:
            gap_flags.append("TWO_FINANCING_SEQUENCE")
        common = {
            "Ticker": ticker, "Trial / event": key,
            "Drug": event.get("drug", ""),
            "Phase 3 readout": readout_date or "NOT ESTABLISHED",
            "Phase 3 evidence status": clinical_status or "UNVERIFIED",
            "Phase 3 exact recheck": p3_review,
            "Phase 3 source": trial_url if str(trial_url).startswith("https://") else "",
            "Trial NCT": nct,
            "1st finance close": first_close or "NOT ESTABLISHED",
            "2nd finance close": second_close or "NOT ESTABLISHED",
            "2nd finance status": funding_status,
            "Finance evidence": pair.get("second_sec_url") or history.get("second_financing_source", ""),
            "Research gaps": " | ".join(gap_flags),
            "GEM eligibility": "NOT CERTIFIED",
        }
        sec_claim = agency.get((key, "SEC"), {})
        sec.append({
            **common,
            "Agency verification": sec_claim.get("verification_status", "NOT_CHECKED"),
            "Agency claim": sec_claim.get("claim", "FINANCING_CLOSURE"),
            "Agency source": sec_claim.get("source_url", ""),
        })
        fda_claim = agency.get((key, "FDA"), {})
        fda.append({
            **common,
            "Agency verification": fda_claim.get("verification_status", "NOT_CHECKED"),
            "Agency claim": fda_claim.get("claim", "PDUFA_TARGET"),
            "Agency source": fda_claim.get("source_url", ""),
        })
    sec.sort(key=lambda r: (r["Ticker"], r["Trial / event"]))
    fda.sort(key=lambda r: (r["Ticker"], r["Trial / event"]))
    return {"SEC": sec, "FDA": fda}


def today_amendments(source_rows, fda_amendments, extension_history, *, today):
    """Never mistake an old extension refreshed today for a new amendment."""
    sec = [
        r for r in source_rows
        if r.get("category") == "AMENDMENT"
        and pacific_date(r.get("filed_at")) == today
    ]
    # Only first-detected extension events count. The FDA extension ledger's
    # last_updated_at changes routinely and cannot establish first detection.
    history_dates = {
        (r.get("event_key"), r.get("prior_pdufa_date"), r.get("current_pdufa_date")):
        pacific_date(r.get("extension_detected_at"))
        for r in extension_history
    }
    fda = [
        r for r in fda_amendments
        if history_dates.get((r.get("Trial / event"), r.get("Prior date"),
                              r.get("Revised date"))) == today
    ]
    return {"SEC": sec, "FDA": fda}


def missing_research_rows(queue, category, registry, *, fda_extensions=None):
    """Separate outstanding source claims; never turn gaps into verified rows.

    A research link is a navigation starting point, not the source of
    verified evidence. The status and original reason stay unchanged.
    """
    if category not in {"SEC", "FDA"}:
        raise ValueError("Unsupported research queue category")
    cik_by_ticker = {
        str(row.get("ticker", "")).strip().upper(): str(row.get("cik10", "")).strip()
        for row in registry
    }
    fda_portal = "https://www.accessdata.fda.gov/scripts/cder/daf/"
    seen = set()
    records = []
    for item in queue:
        if (str(item.get("category", "")).upper() != category or
                str(item.get("verification_required", "")).upper() != "YES" or
                str(item.get("verification_status", "")).upper() in {"VERIFIED", "NOT_APPLICABLE"}):
            continue
        ticker = str(item.get("ticker", "")).strip().upper()
        event = str(item.get("event_key", "")).strip()
        claim = str(item.get("claim", "")).strip()
        key = (event, claim)
        if key in seen:
            continue
        seen.add(key)
        cik = cik_by_ticker.get(ticker, "")
        edgar_link = ("https://www.sec.gov/edgar/browse/?CIK=" + cik
                      if re.fullmatch(r"\d{10}", cik) else "")
        primary = str(item.get("source_url", "")).strip()
        records.append({
            "Ticker": ticker,
            "Trial / event": event,
            "Missing item": claim,
            "Why research is needed": str(item.get("reason", "")).strip()
                or "Exact primary-source verification is outstanding",
            "Verification": str(item.get("verification_status", "")).strip() or "REVIEW_REQUIRED",
            "Expected": str(item.get("expected", "")).strip(),
            "Observed": str(item.get("observed", "")).strip(),
            "Primary source": primary if primary.startswith("https://") else "",
            "Research portal": edgar_link if category == "SEC" else fda_portal,
            "Checked": str(item.get("checked_at", "")).strip(),
        })
    # An unverified FDA extension is itself an item for research even when
    # the official source-verification queue has no separate extension claim.
    if category == "FDA":
        for item in (fda_extensions or []):
            if item.get("Verification") == "VERIFIED":
                continue
            event = str(item.get("Trial / event", "")).strip()
            prior, revised = str(item.get("Prior date", "")), str(item.get("Revised date", ""))
            key = (event, "PDUFA_EXTENSION", prior, revised)
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "Ticker": str(item.get("Ticker", "")).strip().upper(),
                "Trial / event": event,
                "Missing item": "PDUFA_EXTENSION",
                "Why research is needed":
                    "Confirm exact-program FDA PDUFA extension and revised action date; "
                    "reported regulatory updates are not automatically verified",
                "Verification": "REVIEW_REQUIRED",
                "Expected": prior, "Observed": revised,
                "Primary source": "",
                "Research portal": fda_portal,
                "Checked": "",
            })
    records.sort(key=lambda item: (item["Ticker"], item["Trial / event"], item["Missing item"]))
    return records


def render_missing_research(category, queue, notice, registry, *, extensions=None):
    records = missing_research_rows(queue, category, registry, fda_extensions=extensions)
    incomplete = bool(notice and ("unavailable" in notice.lower() or "local" in notice.lower()))
    count = str(len(records)) if not incomplete else str(len(records)) + "+ (partial)"
    with st.expander(f"🔎 Missing {category} items to research — {count}", expanded=False):
        st.caption("Unresolved exact-program evidence and source discrepancies. "
                   "Neither a missing item nor a filing-index result is proof of "
                   "a completed financing or FDA decision.")
        if notice:
            st.warning(notice)
        if not records:
            st.info("No outstanding items in the available source review queue."
                    if not incomplete else
                    "Source review queue unavailable; missing-item total cannot be determined.")
            return
        query = st.text_input(
            f"Filter missing {category} items", key=f"missing_{category.lower()}_research_filter",
            placeholder="Ticker, trial, claim, or reason",
        ).strip().lower()
        selected = [
            row for row in records if not query or
            any(query in str(value).lower() for value in row.values())
        ]
        st.caption(f"Showing {len(selected)} of {len(records)} research items."
                   + (" Queue may be stale or incomplete." if incomplete else ""))
        if selected:
            st.dataframe(
                pd.DataFrame(selected), use_container_width=True, hide_index=True,
                column_config={
                    "Primary source": st.column_config.LinkColumn("Existing evidence"),
                    "Research portal": st.column_config.LinkColumn("Open SEC / FDA"),
                },
            )
            st.download_button(
                f"Download {category} missing-item checklist",
                data=pd.DataFrame(selected).to_csv(index=False),
                file_name=f"{category.lower()}_missing_research.csv",
                mime="text/csv", key=f"download_{category.lower()}_missing_research",
            )
        else:
            st.info("No missing research items match that filter.")


def render_filings_base_amendments():
    """Two independent, simultaneously visible SEC and FDA sections."""
    sec_rows = read_csv(FILINGS)
    has_sec_inventory = bool(sec_rows)
    tables = table_rows(sec_rows, read_csv(VERIFICATION), read_csv(EXTENSIONS))
    queue_frame, queue_notice = required_issue_queue()
    queue_rows = queue_frame.to_dict("records")
    registry_rows = read_csv(REGISTRY)

    st.markdown("## SEC FILINGS")
    st.caption("SEC EDGAR · Monday–Saturday amendments/new filings · Sunday full rescan "
               "at 10 PM Pacific. Indexed forms are not proof that financing closed.")
    sec_base_count = str(len(tables["SEC Base"])) if has_sec_inventory else "PENDING"
    sec_amend_count = str(len(tables["SEC Amendments"])) if has_sec_inventory else "PENDING"
    first, second = st.columns(2)
    first.metric("SEC base filings", sec_base_count)
    second.metric("SEC amendments", sec_amend_count)
    if not has_sec_inventory:
        st.info("The SEC filing inventory is awaiting its first published source scan. "
                "No missing filings or amendments are interpreted as zero.")

    st.markdown("#### SEC — Base filings")
    if tables["SEC Base"]:
        st.dataframe(pd.DataFrame(tables["SEC Base"]), use_container_width=True,
                     hide_index=True,
                     column_config={"Primary source": st.column_config.LinkColumn("EDGAR filing")})
    else:
        st.caption("No SEC base filing records available yet.")
    st.markdown("#### SEC — Amendments (/A)")
    if tables["SEC Amendments"]:
        st.dataframe(pd.DataFrame(tables["SEC Amendments"]), use_container_width=True,
                     hide_index=True,
                     column_config={"Primary source": st.column_config.LinkColumn("EDGAR amendment")})
    else:
        st.caption("No SEC amendments in the available filing inventory.")
    st.caption("An 8-K/A or S-3/A is an amended SEC filing. Prospectus supplements "
               "and independently verified funded closings are separate claims.")
    render_missing_research("SEC", queue_rows, queue_notice, registry_rows)

    st.divider()
    st.markdown("## FDA FILINGS & REGULATORY ACTIONS")
    st.caption("FDA event-specific applications/targets/decisions and separately tracked "
               "PDUFA-date extensions. An extension does not necessarily represent "
               "a formal NDA/BLA amendment.")
    first, second = st.columns(2)
    first.metric("FDA base regulatory claims", len(tables["FDA Base"]))
    second.metric("FDA extensions / updates", len(tables["FDA Amendments"]))

    st.markdown("#### FDA — Base application / decision evidence")
    if tables["FDA Base"]:
        st.dataframe(pd.DataFrame(tables["FDA Base"]), use_container_width=True,
                     hide_index=True,
                     column_config={"Primary source": st.column_config.LinkColumn("FDA / primary source")})
    else:
        st.caption("No primary FDA source claims have been published yet.")
    st.markdown("#### FDA — Amendments / PDUFA extensions")
    if tables["FDA Amendments"]:
        st.dataframe(pd.DataFrame(tables["FDA Amendments"]), use_container_width=True,
                     hide_index=True,
                     column_config={"Primary source": st.column_config.LinkColumn("Extension evidence")})
    else:
        st.caption("No FDA extension evidence available yet. "
                   "This does not prove no amendments occurred.")
    st.caption("Verified source evidence is kept separate from review-only updates. "
               "Neither table independently authorizes GEM trade entry.")
    render_missing_research("FDA", queue_rows, queue_notice, registry_rows,
                            extensions=tables["FDA Amendments"])
