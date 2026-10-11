"""Fail-closed Phase 2 PRIMARY statistical evidence for PRE PHASE 3.

Exact registered Phase 2 NCT, ticker and timestamp only. A linked p-value is
not a Phase 3 success prediction, an efficacy verdict, or issuer readout.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, date

NCT_PATTERN = re.compile(r"NCT\d{8}")
NCT_FULL = re.compile(r"^NCT\d{8}$")


def _observed(raw):
    try:
        value = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
        return value.astimezone(timezone.utc) if value.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def _published(raw):
    try:
        return date.fromisoformat(str(raw or ""))
    except (ValueError, TypeError):
        return None


def primary_evidence_index(records, as_of):
    """Index only timestamp-qualified registry PRIMARY p-value observations."""
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError("as_of must be a timezone-aware datetime")
    as_of = as_of.astimezone(timezone.utc)
    matched = {}
    used_ids = set()
    for record in records or []:
        ticker = str(record.get("ticker") or "").strip().upper()
        nct = str(record.get("nct_id") or "").strip().upper()
        pvalue = str(record.get("p_value") or "").strip()
        modifier = str(record.get("p_value_modifier") or "=").strip()
        try:
            numeric_p = float(pvalue)
        except (ValueError, TypeError):
            numeric_p = float("nan")
        observed = _observed(record.get("observed_at_utc"))
        posted = _published(record.get("results_first_posted"))
        link = str(record.get("source_url") or "").strip()
        endpoint = str(record.get("primary_endpoint") or "").strip()
        comparison = str(record.get("comparison") or "").strip()
        oid = str(record.get("observation_id") or "").strip()
        if not (re.fullmatch(r"[A-Z0-9.-]{1,15}", ticker)
                and NCT_FULL.fullmatch(nct)
                and link == f"https://clinicaltrials.gov/study/{nct}"
                and observed and observed <= as_of and posted and posted <= observed.date()
                and posted <= as_of.date()
                and 0 <= numeric_p <= 1 and modifier in {"=", "<", "<=", ">", ">="}
                and endpoint and comparison and oid):
            continue
        # The collector records PRIMARY analyses only; treat the documented
        # field as a source claim, NOT an automatically verified endpoint label.
        unique = (ticker, nct, oid)
        if unique in used_ids:
            continue
        used_ids.add(unique)
        matched.setdefault((ticker, nct), []).append({
            "nct_id": nct, "p_value": pvalue, "modifier": modifier, "endpoint": endpoint,
            "comparison": comparison, "first_observed_at_utc": observed.isoformat(),
            "source_url": link, "registry_results_first_posted": posted.isoformat(),
        })
    for values in matched.values():
        values.sort(key=lambda row: (row["nct_id"], row["endpoint"], row["comparison"]))
    return matched


def phase2_linked_summary(index, ticker, phase2_links):
    """No ticker-only evidence transfer; link must contain the Phase 2 NCT."""
    ticker = str(ticker or "").strip().upper()
    linked = sorted(set(NCT_PATTERN.findall(str(phase2_links or "").upper())))
    evidence = [item for nct in linked for item in index.get((ticker, nct), ())]
    if not evidence:
        return {
            "Linked Phase 2 PRIMARY p": "NOT VERIFIED — NO ELIGIBLE LINKED PRIMARY ANALYSIS",
            "Phase 2 PRIMARY evidence count": 0,
            "Phase 2 PRIMARY first observed UTC": "",
            "Phase 2 PRIMARY registry sources": "",
        }
    summaries = []
    for value in evidence:
        p_text = f"p{value['modifier']}{value['p_value']}"
        if value["modifier"] == "=" and float(value["p_value"]) == 0:
            # Preserve the source's displayed precision without asserting an
            # exact zero or inventing a bound that the registry did not report.
            p_text = f"p reported as {value['p_value']} (exact p unavailable)"
        summaries.append(f"{value['nct_id']} {p_text} ({value['comparison']})")
    return {
        "Linked Phase 2 PRIMARY p": " | ".join(summaries[:6]) +
            (f" | +{len(evidence)-6} more" if len(evidence)>6 else ""),
        "Phase 2 PRIMARY evidence count": len(evidence),
        "Phase 2 PRIMARY first observed UTC": min(v["first_observed_at_utc"] for v in evidence),
        "Phase 2 PRIMARY registry sources": " | ".join(sorted(set(v["source_url"] for v in evidence))),
    }
