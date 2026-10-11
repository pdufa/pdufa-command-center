"""Step 3: evidence-gated clinical research scoring, separate from FDA predictions.

Only manually reviewed source-supported scores are calculated. Registry information
is discovery metadata, not proof of clinical benefit or corporate drug ownership.
SQLite stores append-only review snapshots, never writes to original trial files.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

WEIGHTS = {
    "Earlier clinical efficacy evidence": 25,
    "Safety and tolerability": 20,
    "Trial design quality": 25,
    "Statistical strength": 15,
    "Regulatory alignment": 15,
}
NCT = re.compile(r"^NCT\d{8}$")
PHASES = ("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3")
CATEGORIES = tuple(WEIGHTS)
DB_PATH = Path("data/pre_phase3_evaluations.sqlite3")


def valid_url(raw: str) -> bool:
    try:
        parsed = urlparse(str(raw or "").strip())
        return parsed.scheme == "https" and bool(parsed.hostname)
    except ValueError:
        return False


def _iso_date(raw: str) -> str:
    try:
        d = date.fromisoformat(str(raw))
        if d > datetime.now(timezone.utc).date():
            raise ValueError("Evidence date cannot be in the future.")
        return d.isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("Provide a valid, nonfuture evidence date (YYYY-MM-DD).") from exc


def _connect(db_path=DB_PATH):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at_utc TEXT NOT NULL,
          nct_id TEXT NOT NULL,
          ticker TEXT NOT NULL,
          drug TEXT NOT NULL,
          indication TEXT NOT NULL,
          phase TEXT NOT NULL,
          trial_source TEXT NOT NULL,
          ownership_verified INTEGER NOT NULL,
          ownership_evidence_url TEXT NOT NULL,
          ownership_evidence_date TEXT NOT NULL,
          category_json TEXT NOT NULL,
          score_total INTEGER,
          clinical_evidence_score INTEGER,
          trial_design_score INTEGER,
          status TEXT NOT NULL,
          explanation TEXT NOT NULL,
          reviewer TEXT NOT NULL,
          payload_checksum TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS evaluation_nct_ticker ON evaluation_history(nct_id,ticker,id)")
    return conn


def _score_category(category: str, raw: dict):
    score = raw.get("score")
    if score in (None, "", "NOT ASSESSED"):
        return {"score": None, "source_url": "", "evidence_date": "", "reason": ""}
    if isinstance(score, bool) or not isinstance(score, int) or not (0 <= score <= WEIGHTS[category]):
        raise ValueError(f"{category}: invalid numeric score.")
    url = str(raw.get("source_url") or "").strip()
    reason = str(raw.get("reason") or "").strip()
    if not valid_url(url) or len(reason) < 15:
        raise ValueError(f"{category}: require an HTTPS evidence link and explanation (15+ characters).")
    when = _iso_date(raw.get("evidence_date"))
    return {"score": score, "source_url": url, "evidence_date": when, "reason": reason}


def evaluate(review: dict) -> dict:
    nct_id = str(review.get("nct_id") or "").strip().upper()
    ticker = str(review.get("ticker") or "").strip().upper()
    if not NCT.fullmatch(nct_id):
        raise ValueError("A valid NCT identifier is required.")
    if not re.fullmatch(r"[A-Z0-9.\-]{1,15}", ticker):
        raise ValueError("A valid ticker is required; an unlinked trial is not scoreable.")
    drug = str(review.get("drug") or "").strip()
    indication = str(review.get("indication") or "").strip()
    phase = str(review.get("phase") or "").strip().upper()
    if not drug or not indication or not any(x in phase for x in PHASES):
        raise ValueError("Drug, indication, and Phase 1–3 trial phase are required.")
    trial_source = str(review.get("trial_source") or "").strip()
    if not valid_url(trial_source):
        raise ValueError("The trial must have an HTTPS source link.")
    owner = bool(review.get("ownership_verified", False))
    ownership_url = str(review.get("ownership_evidence_url") or "").strip()
    ownership_date = str(review.get("ownership_evidence_date") or "").strip()
    if owner:
        if not valid_url(ownership_url):
            raise ValueError("Verified ticker ownership requires a separate evidence URL.")
        ownership_date = _iso_date(ownership_date)
    else:
        ownership_url, ownership_date = "", ""
    incoming = review.get("categories") or {}
    categories = {name: _score_category(name, incoming.get(name, {})) for name in CATEGORIES}
    complete = all(item["score"] is not None for item in categories.values())
    status = "SCORED — DOCUMENTED REVIEW" if (complete and owner) else "NOT SCORED — INCOMPLETE OR UNVERIFIED"
    total = sum(item["score"] for item in categories.values()) if complete and owner else None
    # Subscores remain independent: evidence 60, design 40 (design + reg alignment).
    evidence_names = (CATEGORIES[0], CATEGORIES[1], CATEGORIES[3])
    design_names = (CATEGORIES[2], CATEGORIES[4])
    clinical = sum(categories[k]["score"] for k in evidence_names) if total is not None else None
    design = sum(categories[k]["score"] for k in design_names) if total is not None else None
    notes = [f"{name}: {item['reason']} (score {item['score']}/{WEIGHTS[name]}; {item['source_url']}, {item['evidence_date']})"
             for name, item in categories.items() if item["score"] is not None]
    missing = [name for name, item in categories.items() if item["score"] is None]
    explanation = "Research scoring only; not a trial-success probability, FDA PoA, or trading signal. "
    if not owner:
        explanation += "Company–trial ownership relationship not independently verified. "
    if missing:
        explanation += "Not assessed: " + "; ".join(missing) + ". "
    explanation += "Evidence reviewed: " + (" | ".join(notes) if notes else "none yet.")
    payload = {
        "nct_id": nct_id, "ticker": ticker, "drug": drug, "indication": indication,
        "phase": phase, "trial_source": trial_source, "ownership_verified": int(owner),
        "ownership_evidence_url": ownership_url, "ownership_evidence_date": ownership_date,
        "categories": categories, "score_total": total,
        "clinical_evidence_score": clinical, "trial_design_score": design,
        "status": status, "explanation": explanation,
        "reviewer": str(review.get("reviewer") or "").strip(),
    }
    if not payload["reviewer"]:
        raise ValueError("A reviewer name or identifier is required for the audit trail.")
    payload["payload_checksum"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return payload


def save_review(review, db_path=DB_PATH) -> int:
    record = evaluate(review)
    created = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as db:
        cursor = db.execute(
            """INSERT INTO evaluation_history (
            created_at_utc,nct_id,ticker,drug,indication,phase,trial_source,
            ownership_verified,ownership_evidence_url,ownership_evidence_date,
            category_json,score_total,clinical_evidence_score,trial_design_score,
            status,explanation,reviewer,payload_checksum
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (created, record["nct_id"], record["ticker"], record["drug"],
             record["indication"], record["phase"], record["trial_source"],
             record["ownership_verified"], record["ownership_evidence_url"],
             record["ownership_evidence_date"], json.dumps(record["categories"], ensure_ascii=False),
             record["score_total"], record["clinical_evidence_score"], record["trial_design_score"],
             record["status"], record["explanation"], record["reviewer"], record["payload_checksum"]))
        return cursor.lastrowid


def read_history(db_path=DB_PATH, nct_id="", ticker=""):
    with _connect(db_path) as db:
        q = "SELECT * FROM evaluation_history WHERE 1=1"
        args = []
        if nct_id:
            q += " AND nct_id=?"
            args.append(nct_id.upper())
        if ticker:
            q += " AND ticker=?"
            args.append(ticker.upper())
        q += " ORDER BY id DESC"
        return [dict(row) for row in db.execute(q, args).fetchall()]


def load_trial_catalog(source=Path("data/all_phase_trials.csv")):
    """Existing issuer-trial pairs are research leads until ownership verified."""
    path = Path(source)
    if not path.exists():
        return []
    rows = []
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            nct_id = str(row.get("nct_id") or "").strip().upper()
            ticker = str(row.get("ticker") or "").strip().upper()
            phase = str(row.get("phase") or "").strip().upper()
            if not NCT.fullmatch(nct_id) or not ticker or not any(p in phase for p in PHASES):
                continue
            key = (nct_id, ticker)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "NCT": nct_id, "Ticker": ticker,
                "Company": str(row.get("company") or "").strip(),
                "Drug": str(row.get("drug") or "").strip(),
                "Indication": str(row.get("indication") or "").strip(),
                "Phase": phase, "Status": str(row.get("status") or "").strip(),
                "Registry link": f"https://clinicaltrials.gov/study/{nct_id}",
                "Issuer match": "UNVERIFIED — REVIEW REQUIRED",
            })
    return rows


def render_pre_phase3():
    """Build review and history UI only when this tab is opened."""
    import streamlit as st
    import pandas as pd

    st.subheader("PRE PHASE 3 — Clinical Trial Evaluation")
    st.caption("Step 3 · Evidence-gated manual clinical review · Phase 1–3 · No date-window filters")
    st.warning("This is NOT FDA approval probability or a buy signal. An NCT–ticker pairing in the source inventory is not proof of drug ownership. Unreviewed evidence is NOT SCORED.")
    st.info("Saved reviews use a local SQLite database. On Streamlit Community Cloud, local storage may reset on redeployment or restart. Download review history after saving; durable cloud persistence is not yet configured.")

    try:
        catalog = load_trial_catalog()
    except (OSError, UnicodeError, csv.Error) as exc:
        st.error(f"Could not load the trial inventory: {exc}")
        return
    st.metric("Phase 1–3 company–trial leads", len(catalog))
    query = st.text_input("Find ticker, company, drug, indication, or NCT", placeholder="e.g., NCT05964335")
    if query:
        catalog = [r for r in catalog if query.lower() in " ".join(str(x) for x in r.values()).lower()]
    st.caption(f"Showing {min(300, len(catalog)):,} of {len(catalog):,} matching leads; search for others.")
    if catalog:
        st.dataframe(pd.DataFrame(catalog[:300]), use_container_width=True, hide_index=True)
    if not catalog:
        st.info("No matching Phase 1–3 trial leads. Check the existing all_phase_trials.csv collector.")
        return
    labels = [f"{r['Ticker']} · {r['NCT']} · {r['Drug'][:45]}" for r in catalog]
    selected_idx = st.selectbox("Choose trial to evaluate", options=list(range(len(labels))),
                                format_func=lambda i: labels[i])
    selected = catalog[selected_idx]
    nct, ticker = selected["NCT"], selected["Ticker"]

    with st.form(f"step3_review_{nct}_{ticker}"):
        st.markdown(f"**{ticker} — {nct}**")
        drug = st.text_input("Drug (verify identity)", value=selected["Drug"])
        indication = st.text_input("Indication (verify identity)", value=selected["Indication"])
        phase = st.text_input("Registered phase", value=selected["Phase"])
        reviewer = st.text_input("Reviewer / audit identifier")
        owner = st.checkbox("I independently verified the ticker–drug–trial relationship from a dated primary source")
        ownership_url = st.text_input("Company-to-trial evidence HTTPS URL")
        ownership_date = st.date_input("Company evidence publication date", value=date.today())
        st.markdown("#### Research category scores")
        st.caption("Scores are subjective documented research assessments, not validated chances of success. Leave Not assessed if there is insufficient evidence. Numeric zero means reviewed and assigned zero, not missing.")
        entered = {}
        for i, (name, max_points) in enumerate(WEIGHTS.items()):
            with st.expander(f"{name} / {max_points}", expanded=i==0):
                value = st.selectbox(f"{name}: assessment", ["NOT ASSESSED", *list(range(max_points + 1))],
                                     key=f"step3_rating_{nct}_{ticker}_{i}")
                source_url = st.text_input(f"{name}: evidence HTTPS URL", key=f"step3_source_{nct}_{ticker}_{i}")
                evidence_date = st.date_input(f"{name}: source publication date",
                                              value=date.today(), key=f"step3_date_{nct}_{ticker}_{i}")
                reason = st.text_area(f"{name}: explanation and key findings",
                                      key=f"step3_reason_{nct}_{ticker}_{i}")
                entered[name] = {"score": value, "source_url": source_url,
                                 "evidence_date": evidence_date.isoformat(), "reason": reason}
        submitted = st.form_submit_button("SAVE NEW AUDIT REVISION")
    if submitted:
        try:
            row_id = save_review({
                "nct_id": nct, "ticker": ticker, "drug": drug, "indication": indication,
                "phase": phase, "trial_source": selected["Registry link"],
                "ownership_verified": owner, "ownership_evidence_url": ownership_url,
                "ownership_evidence_date": ownership_date.isoformat(),
                "reviewer": reviewer, "categories": entered,
            })
            st.success(f"Saved review revision #{row_id}. Export history to keep a durable copy.")
        except (ValueError, sqlite3.Error, OSError) as exc:
            st.error(f"Review not saved: {exc}")

    try:
        history = read_history(nct_id=nct, ticker=ticker)
        all_history = read_history()
    except (OSError, sqlite3.Error) as exc:
        st.error(f"Could not load saved reviews: {exc}")
        return
    st.markdown("#### Versioned assessment history")
    if history:
        display_cols = ["id", "created_at_utc", "status", "score_total",
                        "clinical_evidence_score", "trial_design_score", "reviewer", "explanation"]
        st.dataframe(pd.DataFrame(history)[display_cols], hide_index=True, use_container_width=True)
    else:
        st.caption("No reviews yet for this trial. No score has been assigned.")
    if all_history:
        st.download_button("DOWNLOAD ALL STEP 3 AUDIT HISTORY (JSON)",
                           data=json.dumps(all_history, ensure_ascii=False, indent=2),
                           file_name="pre_phase3_step3_history.json",
                           mime="application/json")
