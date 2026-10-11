"""Standalone Step 4 source-level financing completion review interface.

No writes to PRE PHASE 3; an SEC archive response and an affirmative reviewer
attestation are required to record an actual company financing close.
"""
import json
import sqlite3

import pandas as pd
import streamlit as st

from sec_financing_closure import (
    candidates, fetch_sec_document, financing_gate, read_reviews, review_closure, save_review,
)


def render_financing_closure(ticker, identity, snapshot, user_agent, sec_ready):
    st.markdown("### Verified financing closure — Step 4 upgrade")
    st.caption(
        "A registration statement, prospectus, financing announcement, or bare 8-K "
        "DOES NOT count as financing completed. Only a dated, explicit completion "
        "statement found inside an issuer-matched SEC 8-K document or exhibit, "
        "affirmatively reviewed and matched to the specific deal, can enter the ledger."
    )
    st.warning(
        "This does not automatically prove it was the **required second post-Phase 3 financing**. "
        "An open ATM, another raise, post-readout staging, and trading entry readiness "
        "remain separate mandatory checks. The ledger alone never marks ENTRY READY."
    )
    rows = [r for r in snapshot.get("filing_review_queue", []) or []
            if r.get("form") in {"8-K", "8-K/A"}]
    if not rows:
        st.info("No eligible 8-K filing in the existing SEC review queue. "
                "Refresh the issuer's SEC financial scan first. "
                "Filing metadata alone is not proof financing closed.")
    else:
        with st.form("sec_financing_fetch_document"):
            selected = st.selectbox(
                "Issuer-matched SEC 8-K to inspect",
                list(range(len(rows))),
                format_func=lambda i: (
                    f"{rows[i]['filed']} · {rows[i]['form']} · {rows[i]['accession']}"
                ))
            exhibit = st.text_input(
                "Optional exhibit filename (from this filing's SEC archive)",
                placeholder="ex99-1.htm — leave empty to check primary filing")
            fetch = st.form_submit_button(
                "FETCH AND INSPECT FINANCING CLOSING EVIDENCE",
                disabled=not sec_ready)
        if not sec_ready:
            st.info("Configure a genuine SEC_USER_AGENT contact first. "
                    "Without SEC access, closing status stays NOT VERIFIED.")
        if fetch:
            try:
                doc = fetch_sec_document(
                    rows[selected], identity["cik"], snapshot["as_of"],
                    user_agent, document_name=exhibit.strip() or None)
                doc.update({"ticker": ticker, "company": identity["company"]})
                st.session_state["sec_financing_inspected"] = doc
                st.success(f"Fetched SEC document for {ticker}. "
                           "Review the extracted source text before recording a close.")
            except (ValueError, OSError, RuntimeError, UnicodeError) as exc:
                st.session_state.pop("sec_financing_inspected", None)
                st.error(f"SEC financing evidence unavailable: {exc}. "
                         "No financing has been verified.")

    inspected = st.session_state.get("sec_financing_inspected")
    if inspected and inspected.get("ticker") == ticker and inspected.get("cik") == identity["cik"]:
        st.caption("SEC evidence: " + inspected["source_url"])
        st.caption("Filing date: " + inspected["filed"] +
                   " · SEC document SHA-256: " + inspected["document_sha256"])
        items = candidates(inspected)
        if not items:
            st.warning(
                "No sufficiently explicit dated closing clause in the fetched document. "
                "Try the issuer's relevant 8-K exhibit; otherwise leave NOT VERIFIED."
            )
        else:
            st.markdown("#### Matching direct financing-completion statements")
            st.caption("These are **candidate clauses only**. A human must confirm "
                       "the deal, closing date, and that it describes an actual past close.")
            with st.form("sec_financing_attest_review"):
                chosen = st.selectbox(
                    "Exact SEC closing statement to review",
                    list(range(len(items))),
                    format_func=lambda i: items[i]["excerpt"][:210],
                    key="sec_financing_statement_choice")
                st.info(items[chosen]["excerpt"])
                deal_label = st.text_input(
                    "Specific financing deal identifier",
                    placeholder="July 2026 completed registered-direct offering")
                closed_date = st.text_input(
                    "Actual closing date stated in this SEC clause (YYYY-MM-DD)")
                attest = st.checkbox(
                    "I reviewed the SEC document and confirmed this clause concerns "
                    "THIS issuer, THIS financing, and an actual completed closing.")
                save = st.form_submit_button(
                    "CONFIRM SEC EVIDENCE AND RECORD FINANCING CLOSE",
                    disabled=not sec_ready)
            if save:
                try:
                    event = review_closure(
                        inspected, items[chosen]["id"], closed_date,
                        deal_label, reviewer_confirmed=attest, as_of=snapshot["as_of"])
                    revision = save_review(event)
                    st.success(f"Recorded reviewed SEC closing event #{revision}. "
                               "Entry readiness still requires Phase 3, ATM/dilution "
                               "and market checks.")
                except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
                    st.error(f"Could not verify financing close: {exc}. "
                             "No entry-ready status assigned.")

    st.markdown("#### Previously reviewed financing closings")
    try:
        saved = read_reviews(ticker)
    except (sqlite3.Error, OSError) as exc:
        st.error(f"Cannot read financing closure ledger: {exc}")
        return
    if saved:
        st.dataframe(pd.DataFrame([
            {"Deal": r["event"]["deal_label"],
             "Closing date": r["event"]["closing_date"],
             "Filing date": r["event"]["source_filed"],
             "Financing type": r["event"]["financing_type"],
             "Gross proceeds USD": r["event"]["gross_proceeds_usd"],
             "Net proceeds USD": r["event"]["net_proceeds_usd"],
             "Status": r["event"]["status"],
             "SEC source": r["event"]["source_url"]}
            for r in saved]), hide_index=True, use_container_width=True,
            column_config={"SEC source": st.column_config.LinkColumn("SEC source")})
        st.download_button(
            "DOWNLOAD FINANCING CLOSURE AUDIT LEDGER (JSON)",
            data=json.dumps(saved, indent=2), mime="application/json",
            file_name=f"{ticker}_sec_financing_closures.json")
    else:
        st.caption("No reviewed closing event saved for this ticker.")

    with st.form("sec_financing_required_deal_gate"):
        required = st.text_input(
            "Which SPECIFIC financing must be completed before you consider entering?",
            placeholder="Match exact recorded financing deal identifier")
        check = st.form_submit_button("CHECK REQUIRED FINANCING CLOSURE GATE")
    if check:
        gate = financing_gate(ticker, required, as_of=snapshot["as_of"], cik=identity["cik"])
        if gate["closure_verified"]:
            st.success(gate["status"] + " · Closed: " + gate["closing_date"])
            st.warning("NOT ENTRY READY: closing evidence alone does not establish "
                       "second-financing order, inactive ATM, sufficient runway, "
                       "successful Phase 3 or a stabilized trading setup.")
        else:
            st.warning(gate["status"])
