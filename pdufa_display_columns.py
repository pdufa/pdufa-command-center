"""Shared, source-preserving PDUFA grid presentation for the four research tabs.

This module formats saved evidence. It does not infer clinical success, financing
closure, cash runway or FDA approval probabilities from ticker alone.
"""
from datetime import date
import pandas as pd

POST_SCORES = (
    "Clinical evidence /30", "Financing evidence /20", "Trading setup /20",
    "PDUFA evidence /15", "Market activity /10", "Company track record /5",
)
PRE_SCORES = (
    "Phase 2 Efficacy /25", "Phase 3 Design /30", "Safety /15",
    "Regulatory Alignment /15", "Execution /10", "Evidence Quality /5",
)
PRE_PRIORITY_SCORES = (
    "Priority stage /30", "Priority identity /15", "Priority registry /10",
    "Priority protocol /15", "Priority Phase 2 evidence /15",
    "Priority timing /10", "Priority market cap /5",
)
POST_PRIORITY_SCORES = (
    "Review timing /30", "Review clinical follow-up /20",
    "Review financing follow-up /15", "Review regulatory follow-up /15",
    "Review market follow-up /15", "Review identity /5",
)
FRONT = (
    "Ticker", "Score /100", "PDUFA Date", "Days to PDUFA",
    "Score type", *POST_SCORES, *PRE_SCORES,
    *PRE_PRIORITY_SCORES, *POST_PRIORITY_SCORES,
    "Date Classification", "Primary p",
    "F", "Cash Runway (months)", "Cash Runway As Of",
)
DISPLAY_ORDER_OPTIONS = ("Top Score", "Ticker A–Z")
FINANCING_LABELS = ("F START", "F RUN", "F CLOSED", "F UNKNOWN")


def _present(value):
    if value is None:
        return False
    try:
        if bool(pd.isna(value)):
            return False
    except (ValueError, TypeError):
        return False
    return str(value).strip().lower() not in ("", "nan", "nat", "none", "<na>")


def _pick(row, *names):
    for name in names:
        if name in row and _present(row[name]):
            return row[name]
    return None


def _identity(row):
    ticker = _pick(row, "Ticker", "ticker")
    nct = _pick(row, "NCT ID", "nct_id")
    return (str(ticker).strip().upper() if ticker is not None else "",
            str(nct).strip().upper() if nct is not None else "")


def _index_unique(records):
    unique, duplicated = {}, set()
    for row in records:
        key = _identity(row)
        if not all(key):
            continue
        if key in unique:
            duplicated.add(key)
        else:
            unique[key] = row
    for key in duplicated:
        unique.pop(key, None)
    return unique


def enrich_exact_trials(frame, pre=(), post=()):
    """Attach only a unique same-ticker/same-NCT, drug-consistent match.

    Pre/post inputs must already have passed their own snapshot freshness tests.
    The original Pipeline or Pre-Phase-3 columns remain untouched.
    """
    result = frame.copy()
    pre_index, post_index = _index_unique(pre), _index_unique(post)
    allowed = (
        *POST_SCORES, *PRE_SCORES, *PRE_PRIORITY_SCORES, *POST_PRIORITY_SCORES,
        "Evidence score /100", "Research priority /100",
        "Research priority status", "Review priority /100",
        "Review priority status", "Review priority rubric",
        "Pre-readout research score /100", "Preliminary clinical score /100",
        "Financing cycle (separate)", "PDUFA date", "Phase 3 PRIMARY p",
        "Primary endpoint p values observed", "Cash Runway (months)",
        "Cash Runway As Of",
    )
    collected = []
    for row in result.to_dict("records"):
        key = _identity(row)
        drug = str(_pick(row, "Drug", "drug") or "").strip().casefold()
        joined = {}
        for index in (pre_index, post_index):
            candidate = index.get(key)
            if not candidate:
                continue
            other = str(_pick(candidate, "Drug", "drug") or "").strip().casefold()
            if drug and other and drug != other:
                continue
            for col in allowed:
                if not _present(row.get(col)) and _present(candidate.get(col)):
                    joined[col] = candidate[col]
        collected.append(joined)
    for col in allowed:
        if col not in result.columns:
            result[col] = None
        values = [item.get(col) for item in collected]
        original = result[col].tolist()
        result[col] = [a if _present(a) else b for a, b in zip(original, values)]
    return result


def _financing_block(value):
    if not _present(value):
        return "F UNKNOWN"
    text = str(value).strip().upper()
    if text in FINANCING_LABELS:
        return text
    if text.startswith("GREEN — FINANCING STARTED"):
        return "F START"
    if text.startswith("YELLOW — FINANCING RUNNING"):
        return "F RUN"
    if text.startswith("RED — FINANCING CLOSED"):
        return "F CLOSED"
    # REVIEW/UNKNOWN or an unsourced 'closed' field cannot prove event closure.
    return "F UNKNOWN"


def _classify(days, dated):
    if pd.isna(days):
        return "NO PDUFA VERIFIED" if not dated else "DATE REVIEW"
    d = int(days)
    if d < 0:
        return "PAST / RECHECK"
    if d == 0:
        return "DECISION DAY"
    if d <= 13:
        return "13–1 DAYS"
    if d <= 30:
        return "30–14 DAYS"
    if d <= 60:
        return "60–31 DAYS"
    if d <= 90:
        return "90–61 DAYS"
    return "90+ DAYS"


def prepare_pdufa_grid(frame, *, view="UNIFIED", as_of=None):
    """Reorder columns consistently, retaining every original research field."""
    out = frame.copy()
    if "Ticker" not in out:
        out["Ticker"] = out["ticker"] if "ticker" in out else ""
    date_columns = ("PDUFA Date", "PDUFA Target", "PDUFA date (pipeline)",
                    "PDUFA date", "Saved PDUFA target", "pdufa_date")
    dates = pd.Series([_pick(r, *date_columns) for r in out.to_dict("records")],
                      index=out.index, dtype="object")
    raw_dates = pd.to_datetime(dates, errors="coerce", format="mixed")
    out["PDUFA Date"] = raw_dates.dt.strftime("%Y-%m-%d").fillna("")
    today = as_of if as_of is not None else date.today()
    if isinstance(today, pd.Timestamp):
        today = today.date()
    computed_days = (raw_dates - pd.Timestamp(today)).dt.days.astype("Int64")
    # Always derive countdown from displayed date to prevent mismatched dates/days.
    out["Days to PDUFA"] = computed_days
    out["Date Classification"] = [
        _classify(d, bool(day)) for d, day in zip(computed_days, out["PDUFA Date"])
    ]
    existing_primary = ("Phase 3 PRIMARY p", "Phase 3 primary p",
                        "Primary endpoint p values observed")
    out["Primary p"] = [_pick(row, *existing_primary)
                        for row in out.to_dict("records")]
    status = "Financing cycle (separate)"
    out["F"] = [_financing_block(_pick(row, "F", status))
                for row in out.to_dict("records")]
    out["Cash Runway (months)"] = [
        _pick(row, "Cash Runway (months)", "cash_runway_months",
              "Cash runway months", "Cash Runway")
        for row in out.to_dict("records")
    ]
    out["Cash Runway As Of"] = [
        _pick(row, "Cash Runway As Of", "Cash runway verified date",
              "cash_runway_verified_at")
        for row in out.to_dict("records")
    ]
    # All four tabs expose a score, but the models are intentionally NOT
    # interchangeable. Clinical review and research-triage scores do not become
    # estimates of approval probability or permission to trade.
    scores, types = [], []
    for row in out.to_dict("records"):
        post = _pick(row, "Evidence score /100")
        reviewed = _pick(row, "Pre-readout research score /100")
        provisional = _pick(row, "Preliminary clinical score /100")
        pre_priority = _pick(row, "Review priority /100")
        post_priority = _pick(row, "Research priority /100")
        if str(row.get("Review priority status") or "").startswith("EXCLUDED"):
            pre_priority = None

        if view == "POST PHASE 3":
            candidates = (
                (post, "POST: evidence"),
                (post_priority, "POST: research triage"),
            )
        elif view == "PRE PHASE 3":
            candidates = (
                (reviewed, "PRE: reviewed clinical"),
                (provisional, "PRE: provisional clinical"),
                (pre_priority, "PRE: review priority"),
            )
        elif view == "PIPELINE":
            candidates = (
                (reviewed, "PRE: reviewed clinical"),
                (provisional, "PRE: provisional clinical"),
                (post, "POST: evidence"),
                (pre_priority, "PRE: review priority"),
                (post_priority, "POST: research triage"),
            )
        else:
            candidates = (
                (post, "POST: evidence"),
                (reviewed, "PRE: reviewed clinical"),
                (provisional, "PRE: provisional clinical"),
                (pre_priority, "PRE: review priority"),
                (post_priority, "POST: research triage"),
            )
        value, label = None, "NOT SCORED"
        for candidate, kind in candidates:
            try:
                numeric = float(candidate)
            except (TypeError, ValueError, OverflowError):
                continue
            if pd.notna(numeric) and 0 <= numeric <= 100:
                value, label = numeric, kind
                break
        scores.append(value)
        types.append(label)
    out["Score /100"] = pd.Series(scores, index=out.index, dtype="Float64")
    out["Score type"] = types
    for col in POST_SCORES + PRE_SCORES + PRE_PRIORITY_SCORES + POST_PRIORITY_SCORES:
        if col not in out:
            out[col] = None
    return out[list(FRONT) + [col for col in out.columns if col not in FRONT]]


def sort_pdufa_grid(frame, order=DISPLAY_ORDER_OPTIONS[0]):
    """Sort the already-scored display rows, without inventing scores.

    TOP SCORE is a *display sort only*: scores from different research models
    are not scientifically equivalent; the adjacent Score type stays visible.
    Scores descend, then numeric days to PDUFA ascend within each score.
    Missing scores/days go last within their respective sort level, followed
    by ticker/NCT/drug tie-breakers.
    """
    if order not in DISPLAY_ORDER_OPTIONS:
        raise ValueError("Unsupported PDUFA display order")
    out = frame.copy()
    for name in ("Ticker", "NCT ID", "Drug"):
        if name not in out:
            out[name] = ""
    if "Score /100" not in out:
        out["Score /100"] = pd.Series([pd.NA] * len(out), index=out.index, dtype="Float64")
    if order == "Ticker A–Z":
        return out.sort_values(["Ticker", "NCT ID", "Drug"],
                               ascending=True, na_position="last", kind="stable")
    out["_score_sort"] = pd.to_numeric(out["Score /100"], errors="coerce")
    out["_days_sort"] = pd.to_numeric(
        out.get("Days to PDUFA", pd.Series(pd.NA, index=out.index, dtype="Float64")),
        errors="coerce",
    )
    result = out.sort_values(
        ["_score_sort", "_days_sort", "Ticker", "NCT ID", "Drug"],
        ascending=[False, True, True, True, True],
        na_position="last", kind="stable",
    )
    return result.drop(columns=["_score_sort", "_days_sort"])


def finance_style(frame):
    """Small single-cell blocks with black bold text and a black border."""
    css = {
        "F START": "background-color:#bbf7d0; color:#000000;",
        "F RUN": "background-color:#fef08a; color:#000000;",
        "F CLOSED": "background-color:#fecaca; color:#000000;",
        "F UNKNOWN": "background-color:#e5e7eb; color:#000000;",
    }
    return frame.style.map(
        lambda value: css.get(value, css["F UNKNOWN"])
                      + "font-weight:bold; text-align:center; border:1px solid #111111;",
        subset=["F"],
    )
