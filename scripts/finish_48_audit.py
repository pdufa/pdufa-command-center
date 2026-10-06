#!/usr/bin/env python3
"""
Finish the 48-row PDUFA audit queue using the already-frozen 2025 eight-feature model.

What this script does
---------------------
1. Requires the current repository to contain exactly 48 audit rows with needs_rescore=YES.
2. Drops rows already proven to be duplicate / invalid / wrong-identity / out-of-period.
3. Reconstructs 16 unique valid canonical events using ONLY SEC evidence filed before the
   earlier of (PDUFA date - 1 day) or (actual FDA action date - 1 day).
4. Reuses the exact StandardScaler + LogisticRegression parameters in build_2024_cohort.py.
5. Joins outcomes only after scores are frozen.
6. Leaves KNSA 2026-06-19 excluded because the public record confirms a June 2026 approval
   of the manufacturing transfer but does not expose a source-level exact FDA action date.
7. Writes a 48-row resolution ledger and clears the rescore queue without erasing provenance.

Estimated runtime: ~8-25 minutes in GitHub Actions, depending on SEC/Yahoo response time.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
import pandas as pd

# Running "python scripts/finish_48_audit.py" puts scripts/ on sys.path.
from build_2024_cohort import (
    load_ticker_map,
    collect_predecision_evidence,
    feature_vector,
    frozen_probability,
    historical_market_cap,
    cap_bucket,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HISTORY_PATH = DATA / "prediction_engine_history.csv"
AUDIT_PATH = DATA / "prediction_engine_audit.csv"
QUEUE_PATH = DATA / "prediction_engine_rescore_queue.csv"
REPORT_PATH = DATA / "prediction_engine_audit_48_resolution.csv"
SUMMARY_PATH = DATA / "prediction_engine_audit_48_summary.json"

EXPECTED_PENDING = 48

# 16 unique canonical events recoverable with a decision-safe cutoff.
# outcome_source is outcome-era evidence and is NEVER fed into the feature collector.
REPAIR_EVENTS = [
    {
        "canonical_event_key": "ETON|2025-05-28",
        "ticker": "ETON",
        "pdufa_date": "2025-05-28",
        "action_date": "2025-05-28",
        "drug": "KHINDIVI / ET-400 (hydrocortisone oral solution)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://ir.etonpharma.com/news-releases/news-release-details/eton-pharmaceuticals-announces-us-fda-approval-khindivitm",
        "original_keys": ["ETON|2025-02-28"],
    },
    {
        "canonical_event_key": "CAPR|2025-08-31",
        "ticker": "CAPR",
        "pdufa_date": "2025-08-31",
        "action_date": "2025-07-11",
        "drug": "deramiocel",
        "actual_outcome": "CRL",
        "outcome_source": "https://www.sec.gov/Archives/edgar/data/1133869/000155837025009186/capr-20250711xex99d1.htm",
        "original_keys": ["CAPR|2025-03-04"],
    },
    {
        "canonical_event_key": "LQDA|2025-05-24",
        "ticker": "LQDA",
        "pdufa_date": "2025-05-24",
        "action_date": "2025-05-23",
        "drug": "YUTREPIA (treprostinil inhalation powder)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://www.liquidia.com/news-releases/news-release-details/us-fda-approves-liquidias-yutrepiatm-treprostinil-inhalation",
        "original_keys": ["LQDA|2025-05-24"],
    },
    {
        "canonical_event_key": "CYTK|2025-12-26",
        "ticker": "CYTK",
        "pdufa_date": "2025-12-26",
        "action_date": "2025-12-19",
        "drug": "MYQORZO (aficamten)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://ir.cytokinetics.com/press-releases/press-release-details/2025/Cytokinetics-Announces-FDA-Approval-of-MYQORZO-aficamten-for-the-Treatment-of-Adults-with-Symptomatic-Obstructive-Hypertrophic-Cardiomyopathy-to-Improve-Functional-Capacity-and-Symptoms/",
        "original_keys": ["CYTK|2025-12-26"],
    },
    {
        "canonical_event_key": "DNLI|2026-04-05|tividenofusp-alfa",
        "ticker": "DNLI",
        "pdufa_date": "2026-04-05",
        "action_date": "2026-03-24",
        "drug": "AVLAYAH (tividenofusp alfa-eknm / DNL310)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://investors.denalitherapeutics.com/news-releases/news-release-details/denali-therapeutics-announces-us-fda-approval-avlayahtm",
        "original_keys": ["DNLI|2026-01-05|ofusp alfa (dnl310"],
    },
    {
        "canonical_event_key": "RGNX|2026-02-08|rgx-121 seeking accelerated approval was submitted to the fda in march 2025",
        "ticker": "RGNX",
        "pdufa_date": "2026-02-08",
        "action_date": "2026-02-07",
        "drug": "RGX-121 (clemidsogene lanparvovec)",
        "actual_outcome": "CRL",
        "outcome_source": "https://ir.regenxbio.com/news-releases/news-release-details/regenxbio-announces-regulatory-update-rgx-121-bla-mps-ii/",
        "original_keys": ["RGNX|2026-02-08|rgx-121 seeking accelerated approval was submitted to the fda in march 2025"],
    },
    {
        "canonical_event_key": "VNDA|2026-02-21|bysanti",
        "ticker": "VNDA",
        "pdufa_date": "2026-02-21",
        "action_date": "2026-02-20",
        "drug": "BYSANTI (milsaperidone)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://www.sec.gov/Archives/edgar/data/1347178/000162828026010376/vnda8-k2232026exhibit991.htm",
        "original_keys": ["VNDA|2026-02-21|hetlioz"],
    },
    {
        "canonical_event_key": "RCKT|2026-03-28|kresladi",
        "ticker": "RCKT",
        "pdufa_date": "2026-03-28",
        "action_date": "2026-03-26",
        "drug": "KRESLADI (marnetegragene autotemcel)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapy-severe-leukocyte-adhesion-deficiency-type-i",
        "original_keys": ["RCKT|2026-03-28|kresladi"],
    },
    {
        "canonical_event_key": "SRRK|2026-09-30|apitegromab",
        "ticker": "SRRK",
        "pdufa_date": "2026-09-30",
        "action_date": "2026-09-11",
        "drug": "ISEMBYLD (apitegromab-mstn)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://investors.scholarrock.com/news-releases/news-release-details/scholar-rock-announces-fda-approval-isembyldtm-apitegromab-mstn",
        "original_keys": ["SRRK|2026-03-31|apitegromab upon the successful fda reinspection of catalent indiana"],
    },
    {
        "canonical_event_key": "TLX|2026-09-11|tlx101-px",
        "ticker": "TLX",
        "pdufa_date": "2026-09-11",
        "action_date": "2026-09-11",
        "drug": "PIXCLARA (floretyrosine F 18 / TLX101-Px)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://telixpharma.com/news-views/fda-approves-telixs-brain-cancer-imaging-drug-pixclara/",
        "original_keys": [
            "TLX|2026-04-10|tlx101-px (pixclara",
            "TLX|2026-03-13|tlx101-px (pixclara",
        ],
    },
    {
        "canonical_event_key": "ARVN|2026-06-05|vepdegestrant",
        "ticker": "ARVN",
        "pdufa_date": "2026-06-05",
        "action_date": "2026-05-01",
        "drug": "VEPPANU (vepdegestrant)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-vepdegestrant-er-positive-her2-negative-esr1-mutated-advanced-or-metastatic-breast",
        "original_keys": ["ARVN|2026-05-08|vepdegestrant and assigned a pdufa action date of june 5"],
    },
    {
        "canonical_event_key": "LNTH|2026-06-29|lnth-2501",
        "ticker": "LNTH",
        "pdufa_date": "2026-06-29",
        "action_date": "2026-06-26",
        "drug": "LNTH-2501 (gallium 68 edotreotide)",
        "actual_outcome": "CRL",
        "outcome_source": "https://investor.lantheus.com/news-releases/news-release-details/lantheus-receives-complete-response-letter-fda-lnth-2501-ga-68",
        "original_keys": ["LNTH|2026-06-26|lnth"],
    },
    {
        "canonical_event_key": "VRDN|2026-06-30|veligrotug to the fda in october 2025",
        "ticker": "VRDN",
        "pdufa_date": "2026-06-30",
        "action_date": "2026-06-26",
        "drug": "LUMVOA (veligrotug-vvze)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://investors.viridiantherapeutics.com/news/news-details/2026/Viridian-Therapeutics-Announces-U-S--FDA-Approval-and-Launch-of-Lumvoa-veligrotug-vvze-for-the-Treatment-of-Thyroid-Eye-Disease/default.aspx",
        "original_keys": ["VRDN|2026-06-30|veligrotug to the fda in october 2025"],
    },
    {
        "canonical_event_key": "MNKD|2026-07-26|sbla",
        "ticker": "MNKD",
        "pdufa_date": "2026-07-26",
        "action_date": "2026-07-23",
        "drug": "FUROSCIX ReadyFlow (furosemide injection autoinjector)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://www.sec.gov/Archives/edgar/data/899460/000119312526316041/d63182d8k.htm",
        "original_keys": ["MNKD|2026-07-26|sbla"],
    },
    {
        "canonical_event_key": "RARE|2026-08-23|dtx401",
        "ticker": "RARE",
        "pdufa_date": "2026-08-23",
        "action_date": "2026-08-19",
        "drug": "GENGLYCOS (pariglasgene brecaparvovec-opnr / DTX401)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://ir.ultragenyx.com/news-releases/news-release-details/ultragenyx-announces-us-fda-approval-genglycostm-gene-therapy",
        "original_keys": ["RARE|2026-02-23|dtx401"],
    },
    {
        "canonical_event_key": "IONS|2026-09-22|alexander",
        "ticker": "IONS",
        "pdufa_date": "2026-09-22",
        "action_date": "2026-09-03",
        "drug": "ZANVASTRO (zilganersen)",
        "actual_outcome": "APPROVED",
        "outcome_source": "https://ir.ionis.com/news-releases/news-release-details/zanvastrotm-zilganersen-approved-fda-first-and-only-disease",
        "original_keys": ["IONS|2026-09-22|alexander"],
    },
]

KNSA_KEY = "KNSA|2026-06-19|license"

def bool_text(v: bool) -> str:
    return "True" if v else "False"

def main() -> None:
    hist = pd.read_csv(HISTORY_PATH, dtype=str, keep_default_na=False)
    audit = pd.read_csv(AUDIT_PATH, dtype=str, keep_default_na=False)
    queue = pd.read_csv(QUEUE_PATH, dtype=str, keep_default_na=False)

    pending_audit = audit[audit["needs_rescore"].str.upper().eq("YES")].copy()
    pending_queue = queue[queue["needs_rescore"].str.upper().eq("YES")].copy()

    if len(pending_audit) != EXPECTED_PENDING:
        raise SystemExit(f"ABORT: expected {EXPECTED_PENDING} pending audit rows, found {len(pending_audit)}")
    if len(pending_queue) != EXPECTED_PENDING:
        raise SystemExit(f"ABORT: expected {EXPECTED_PENDING} pending queue rows, found {len(pending_queue)}")

    pending_keys = set(pending_audit["event_key"].astype(str))
    queue_keys = set(pending_queue["original_event_key"].astype(str))
    if pending_keys != queue_keys:
        raise SystemExit("ABORT: audit and rescore queue pending key sets do not match")

    configured_originals = {k for e in REPAIR_EVENTS for k in e["original_keys"]}
    if KNSA_KEY not in pending_keys:
        raise SystemExit("ABORT: KNSA verification row missing from pending cohort")

    # Any pending row not represented by a repair event or KNSA is a verified remove-only row.
    remove_only_keys = pending_keys - configured_originals - {KNSA_KEY}

    # Sanity: current queue says exactly 30 REMOVE_ONLY rows. TLX Mar-13 is intentionally merged
    # into the same canonical Pixclara event as TLX Apr-10, so it is configured as a repair source
    # but does not create a second output row.
    q_remove = set(
        pending_queue.loc[pending_queue["queue_class"].eq("REMOVE_ONLY"), "original_event_key"].astype(str)
    )
    if len(q_remove) != 30:
        raise SystemExit(f"ABORT: expected 30 REMOVE_ONLY rows, found {len(q_remove)}")
    if not q_remove.issubset(remove_only_keys | configured_originals):
        raise SystemExit("ABORT: unexpected REMOVE_ONLY key classification")

    ticker_map = load_ticker_map()
    repaired_rows = []
    event_results = {}

    for ev in REPAIR_EVENTS:
        ticker = ev["ticker"]
        pdufa = datetime.strptime(ev["pdufa_date"], "%Y-%m-%d").date()
        action = datetime.strptime(ev["action_date"], "%Y-%m-%d").date()
        cutoff = min(pdufa, action) - timedelta(days=1)
        anchor = min(pdufa, action)

        meta = ticker_map.get(ticker)
        if not meta:
            raise SystemExit(f"ABORT: SEC ticker mapping not found for {ticker}")
        cik = int(meta["cik"])

        evidence, text = collect_predecision_evidence(cik, cutoff)
        feats = feature_vector(evidence, text)
        p = frozen_probability(feats)
        model_class = "APPROVED" if p >= 0.5 else "CRL"

        cap, cap_method = historical_market_cap(ticker, cik, anchor, cutoff)
        if cap is None:
            raise SystemExit(f"ABORT: historical market cap unresolved for {ev['canonical_event_key']}")
        cap_b = cap / 1_000_000_000.0
        if not (0.300 <= cap_b <= 10.000):
            raise SystemExit(
                f"ABORT: repaired event outside configured $300M-$10B cohort: "
                f"{ev['canonical_event_key']} cap={cap_b:.4f}B"
            )

        actual = ev["actual_outcome"]
        correct = model_class == actual
        year = ev["pdufa_date"][:4]
        row = {
            "ticker": ticker,
            "pdufa_date": ev["pdufa_date"],
            "event_key": ev["canonical_event_key"],
            "p_approval": p,
            "model_class": model_class,
            "actual_outcome": actual,
            "validation_period": f"{year}_AUDIT_REPAIR_FROZEN_MODEL",
            "independence_status": "RETROSPECTIVE_AUDIT_REPAIR_NOT_BLIND",
            "historical_market_cap_billions": cap_b,
            "market_cap_source": cap_method,
            "market_cap_match_method": "HISTORICAL_CLOSE_X_SEC_FILED_SHARES",
            "market_cap_bucket": cap_bucket(cap_b),
            "cap_recovery_confidence": "HIGH",
            "cap_recovery_method": cap_method,
            "correct": bool_text(correct),
            "actual_binary": "1" if actual == "APPROVED" else "0",
            "predicted_binary": "1" if model_class == "APPROVED" else "0",
            "public_approval_probability": "",
            "biopharmawatch_probability": "",
            "public_model_class": "",
            "public_evidence_note": (
                "Audit repair reconstructed retrospectively from SEC evidence filed on or before "
                f"{cutoff.isoformat()}; frozen 2025 model reused without refit; outcome evidence "
                "was joined only after the score was frozen. This is not a blind prediction."
            ),
            "internal_direction_class": model_class,
            "internal_direction_note": (
                "Frozen 2025 eight-feature model applied without refit during 48-row audit repair."
            ),
        }
        repaired_rows.append(row)
        event_results[ev["canonical_event_key"]] = {
            **ev,
            "evidence_cutoff": cutoff.isoformat(),
            "p_approval": p,
            "model_class": model_class,
            "correct": correct,
            "historical_market_cap_billions": cap_b,
            "cap_method": cap_method,
            "evidence_source_count": len(evidence),
        }

    # ---------------------------
    # Update prediction history
    # ---------------------------
    # Remove every currently-pending row first, then add one row per unique canonical repair.
    hist = hist[~hist["event_key"].isin(pending_keys)].copy()
    canonical_keys = {r["event_key"] for r in repaired_rows}
    hist = hist[~hist["event_key"].isin(canonical_keys)].copy()

    add = pd.DataFrame(repaired_rows)
    for col in hist.columns:
        if col not in add.columns:
            add[col] = ""
    add = add[hist.columns]
    hist_out = pd.concat([hist, add], ignore_index=True)
    hist_out["_date"] = pd.to_datetime(hist_out["pdufa_date"], errors="coerce")
    hist_out = hist_out.sort_values(["_date", "ticker", "event_key"], na_position="last").drop(columns="_date")

    if hist_out["event_key"].duplicated().any():
        dupes = hist_out.loc[hist_out["event_key"].duplicated(False), "event_key"].tolist()
        raise SystemExit(f"ABORT: duplicate history event keys after repair: {dupes[:10]}")

    # ---------------------------
    # Update audit ledger
    # ---------------------------
    audit_out = audit.copy()

    # First resolve all 48 old pending rows as exclusions/superseded rows. Same-key canonical
    # repairs are overwritten below with the final repaired status.
    for key in pending_keys:
        mask = audit_out["event_key"].eq(key)
        if not mask.any():
            raise SystemExit(f"ABORT: pending audit key vanished: {key}")
        audit_out.loc[mask, "needs_rescore"] = "NO"
        audit_out.loc[mask, "count_in_audited_accuracy"] = "NO"
        audit_out.loc[mask, "audit_status"] = "RESOLVED_EXCLUDED_OR_SUPERSEDED"
        old_note = audit_out.loc[mask, "verified_note"].astype(str)
        audit_out.loc[mask, "verified_note"] = old_note + " | 48-row audit resolution: source row removed from canonical history."

    # KNSA is closed without forcing a prediction into audited accuracy.
    kmask = audit_out["event_key"].eq(KNSA_KEY)
    audit_out.loc[kmask, "audit_status"] = "RESOLVED_EXCLUDED_ACTION_DATE_NOT_SOURCE_VERIFIED"
    audit_out.loc[kmask, "audit_action"] = "EXCLUDE_NO_EXACT_ACTION_DATE"
    audit_out.loc[kmask, "verified_note"] = (
        "PDUFA target 2026-06-19 verified and subsequent SEC filing confirms FDA approved Samsung "
        "Biologics as replacement ARCALYST CDMO in June 2026, but an exact source-level FDA action "
        "date was not recovered. Excluded rather than inventing a cutoff."
    )

    # Add/replace canonical audit rows.
    for ev in REPAIR_EVENTS:
        res = event_results[ev["canonical_event_key"]]
        note = (
            f"48-row audit repair. Canonical PDUFA={ev['pdufa_date']}; FDA action={ev['action_date']} "
            f"({ev['actual_outcome']}); evidence cutoff={res['evidence_cutoff']}; "
            f"frozen model p={res['p_approval']:.6f}, class={res['model_class']}; "
            "retrospective reconstruction, not blind."
        )
        row = {
            "event_key": ev["canonical_event_key"],
            "audit_status": "RESCORED_DECISION_SAFE_CANONICAL",
            "failure_reason": "",
            "count_in_audited_accuracy": "YES",
            "verified_note": note,
            "source_url": ev["outcome_source"],
            "canonical_pdufa_date": ev["pdufa_date"],
            "audit_action": "KEEP_RESCORED_CANONICAL",
            "needs_rescore": "NO",
        }
        same = audit_out["event_key"].eq(ev["canonical_event_key"])
        if same.any():
            for col, val in row.items():
                audit_out.loc[same, col] = str(val)
        else:
            new = pd.DataFrame([row])
            for col in audit_out.columns:
                if col not in new.columns:
                    new[col] = ""
            audit_out = pd.concat([audit_out, new[audit_out.columns]], ignore_index=True)

    if audit_out["event_key"].duplicated().any():
        dupes = audit_out.loc[audit_out["event_key"].duplicated(False), "event_key"].tolist()
        raise SystemExit(f"ABORT: duplicate audit event keys after repair: {dupes[:10]}")

    if (audit_out["needs_rescore"].str.upper() == "YES").any():
        remain = audit_out.loc[audit_out["needs_rescore"].str.upper().eq("YES"), "event_key"].tolist()
        raise SystemExit(f"ABORT: audit still has pending rescore rows: {remain[:10]}")

    # ---------------------------
    # Update queue + resolution report
    # ---------------------------
    queue_out = queue.copy()
    if "resolution_status" not in queue_out.columns:
        queue_out["resolution_status"] = ""
    if "resolved_event_key" not in queue_out.columns:
        queue_out["resolved_event_key"] = ""
    if "resolution_note" not in queue_out.columns:
        queue_out["resolution_note"] = ""

    source_to_canonical = {}
    for ev in REPAIR_EVENTS:
        for k in ev["original_keys"]:
            source_to_canonical[k] = ev["canonical_event_key"]

    for i, qr in queue_out.iterrows():
        key = str(qr["original_event_key"])
        if key not in pending_keys:
            continue
        queue_out.at[i, "needs_rescore"] = "NO"
        if key == KNSA_KEY:
            queue_out.at[i, "resolution_status"] = "CLOSED_EXCLUDED_UNVERIFIED_ACTION_DATE"
            queue_out.at[i, "resolved_event_key"] = ""
            queue_out.at[i, "resolution_note"] = "No exact source-level FDA action date recovered; excluded from audited history."
        elif key in source_to_canonical:
            ckey = source_to_canonical[key]
            queue_out.at[i, "resolution_status"] = "CLOSED_REPAIRED_OR_MERGED"
            queue_out.at[i, "resolved_event_key"] = ckey
            queue_out.at[i, "resolution_note"] = "Canonical event reconstructed with frozen model and decision-safe evidence cutoff."
        else:
            queue_out.at[i, "resolution_status"] = "CLOSED_REMOVE_ONLY"
            queue_out.at[i, "resolved_event_key"] = ""
            queue_out.at[i, "resolution_note"] = "Verified invalid/duplicate/wrong-identity/out-of-period source row removed."

    if (queue_out["needs_rescore"].str.upper() == "YES").any():
        raise SystemExit("ABORT: rescore queue still contains needs_rescore=YES")

    report_rows = []
    audit_prior = pending_audit.set_index("event_key", drop=False)
    for key in sorted(pending_keys):
        prior = audit_prior.loc[key]
        if key == KNSA_KEY:
            report_rows.append({
                "original_event_key": key,
                "prior_audit_status": prior["audit_status"],
                "final_disposition": "EXCLUDED_ACTION_DATE_NOT_SOURCE_VERIFIED",
                "canonical_event_key": "",
                "canonical_pdufa_date": "2026-06-19",
                "action_date": "",
                "actual_outcome": "APPROVED",
                "new_p_approval": "",
                "new_model_class": "",
                "correct": "",
                "historical_market_cap_billions": "",
                "source_url": "https://www.sec.gov/Archives/edgar/data/1730430/000110465926087545/knsa-20260630x10q.htm",
                "note": "Target and eventual approval verified; exact FDA action date not recovered, so no forced cutoff/score.",
            })
        elif key in source_to_canonical:
            ckey = source_to_canonical[key]
            res = event_results[ckey]
            merged = len(res["original_keys"]) > 1 and key != res["original_keys"][0]
            report_rows.append({
                "original_event_key": key,
                "prior_audit_status": prior["audit_status"],
                "final_disposition": "MERGED_DUPLICATE_TO_CANONICAL" if merged else "REPAIRED_CANONICAL",
                "canonical_event_key": ckey,
                "canonical_pdufa_date": res["pdufa_date"],
                "action_date": res["action_date"],
                "actual_outcome": res["actual_outcome"],
                "new_p_approval": res["p_approval"],
                "new_model_class": res["model_class"],
                "correct": bool_text(res["correct"]),
                "historical_market_cap_billions": res["historical_market_cap_billions"],
                "source_url": res["outcome_source"],
                "note": f"Evidence cutoff {res['evidence_cutoff']}; {res['evidence_source_count']} SEC evidence rows.",
            })
        else:
            report_rows.append({
                "original_event_key": key,
                "prior_audit_status": prior["audit_status"],
                "final_disposition": "REMOVED_VERIFIED_INVALID_OR_DUPLICATE",
                "canonical_event_key": "",
                "canonical_pdufa_date": prior.get("canonical_pdufa_date", ""),
                "action_date": "",
                "actual_outcome": "",
                "new_p_approval": "",
                "new_model_class": "",
                "correct": "",
                "historical_market_cap_billions": "",
                "source_url": prior.get("source_url", ""),
                "note": prior.get("failure_reason", ""),
            })

    report = pd.DataFrame(report_rows)
    if len(report) != EXPECTED_PENDING:
        raise SystemExit(f"ABORT: resolution report has {len(report)} rows, expected {EXPECTED_PENDING}")

    # Final audited history sanity.
    merged = hist_out.merge(
        audit_out[["event_key", "count_in_audited_accuracy", "needs_rescore"]],
        on="event_key", how="left", validate="one_to_one"
    )
    pending_hist = merged["needs_rescore"].fillna("").str.upper().eq("YES").sum()
    if pending_hist:
        raise SystemExit(f"ABORT: final history still has {pending_hist} pending rows")

    # Write only after all validation passes.
    hist_out.to_csv(HISTORY_PATH, index=False)
    audit_out.to_csv(AUDIT_PATH, index=False)
    queue_out.to_csv(QUEUE_PATH, index=False)
    report.to_csv(REPORT_PATH, index=False)

    audited_yes = int(
        merged["count_in_audited_accuracy"].fillna("NO").str.upper().eq("YES").sum()
    )
    correct_mask = merged["correct"].astype(str).str.lower().eq("true")
    eligible = merged["count_in_audited_accuracy"].fillna("NO").str.upper().eq("YES")
    correct_n = int((correct_mask & eligible).sum())
    summary = {
        "input_pending_rows": EXPECTED_PENDING,
        "remove_only_rows": len(remove_only_keys),
        "unique_canonical_events_reconstructed": len(REPAIR_EVENTS),
        "knsa_excluded_for_unverified_exact_action_date": 1,
        "final_history_rows": int(len(hist_out)),
        "final_audited_eligible_rows": audited_yes,
        "final_audited_correct_rows": correct_n,
        "final_audited_accuracy_pct": round(correct_n / audited_yes * 100.0, 2) if audited_yes else None,
        "remaining_needs_rescore": 0,
        "note": "Repaired rows are retrospective frozen-model audit reconstructions and are not blind predictions.",
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
