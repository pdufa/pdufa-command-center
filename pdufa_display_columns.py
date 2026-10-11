"""Shared, source-preserving PDUFA grid presentation for the four research tabs.

This module formats saved evidence. It does not infer clinical success, financing
closure, cash runway or FDA approval probabilities from ticker alone.
"""
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
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
    "2nd Financing Completed", "Cash Runway (months)",
    "Score type", *POST_SCORES, *PRE_SCORES,
    *PRE_PRIORITY_SCORES, *POST_PRIORITY_SCORES,
    "Date Classification", "Primary p",
    "F", "Cash Runway As Of",
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
        "Primary endpoint p values observed", "2nd Financing Completed",
        "Cash Runway (months)", "Cash Runway As Of",
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


def _second_financing_completed(row):
    """Only the separately audited second close can mark this field verified.

    A closed financing cycle alone must NOT prove the second post-Phase-3
    offering, and the absence of a record must NOT be interpreted as NO.
    """
    audit = str(_pick(row, "second_financing_audit_status") or "").strip().upper()
    closed = str(_pick(row, "second_financing_closed") or "").strip().upper()
    source = str(_pick(row, "second_financing_source") or "").strip()
    event = _pick(row, "event_key", "Exact event")
    if (audit == "VERIFIED_SECOND_POST_PHASE3_FINANCING" and
            closed == "YES" and event and source.startswith("https://")):
        return "YES — VERIFIED (HISTORICAL)"
    if str(_pick(row, "2nd Financing Completed") or "").strip().upper() == "YES — VERIFIED (HISTORICAL)":
        # Only sourced, audited POST3 queue rows create this exact display label.
        return "YES — VERIFIED (HISTORICAL)"
    return "NOT VERIFIED"


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
    out["2nd Financing Completed"] = [
        _second_financing_completed(row) for row in out.to_dict("records")
    ]
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



PDUFA_DAY_COLUMNS = ("Days to PDUFA", "DAYS TO PDUFA", "days_to_pdufa", "Days Left")
FINANCE_NEIGHBORS = ("2nd Financing Completed", "Cash Runway (months)")


@lru_cache(maxsize=16)
def _audited_second_financing_keys(path, mtime_ns, size):
    """Read a source-dated exact-event ledger; never infer second-close from F."""
    try:
        audit = pd.read_csv(path, dtype=str, keep_default_na=False)
    except (OSError, ValueError, pd.errors.ParserError, UnicodeError):
        return frozenset()
    required = {
        "event_key", "second_financing_status", "second_financing_audit_status",
        "second_financing_closed", "second_financing_source",
    }
    if not required.issubset(audit.columns):
        return frozenset()
    keys = audit["event_key"].astype(str).str.strip()
    unique = keys.ne("") & ~keys.duplicated(keep=False)
    def valid_url(value):
        try:
            link = urlparse(str(value))
            return (link.scheme == "https" and bool(link.hostname) and
                    not link.username and not link.password)
        except ValueError:
            return False
    allowed = (
        unique
        & audit["second_financing_status"].str.strip().str.upper().isin(("CLOSED", "FINISHED"))
        & audit["second_financing_audit_status"].str.strip().eq("VERIFIED_SECOND_POST_PHASE3_FINANCING")
        & audit["second_financing_closed"].str.strip().str.upper().eq("YES")
        & audit["second_financing_source"].map(valid_url)
    )
    return frozenset(keys.loc[allowed])


def align_pdufa_finance_columns(frame, *, audit_path="data/second_financing_status.csv",
                                add_countdown=False):
    """Place both finance measures after the countdown in every PDUFA event grid.

    This works for modern and legacy countdown labels. Missing cash runway is
    blank and second-finance is NOT VERIFIED. An event-key-only, duplicate-free,
    SEC/source-linked audit can upgrade a completion label; ticker-only and
    generic F CLOSED matches are never sufficient.
    """
    if not isinstance(frame, pd.DataFrame):
        return frame
    days = next((col for col in PDUFA_DAY_COLUMNS if col in frame), None)
    if days is None and not (add_countdown and "PDUFA Date" in frame):
        return frame
    out = frame.copy()
    if days is None:
        date_values = pd.to_datetime(out["PDUFA Date"], errors="coerce")
        from zoneinfo import ZoneInfo
        today = pd.Timestamp.now(tz=ZoneInfo("America/Los_Angeles")).date()
        out["Days to PDUFA"] = (date_values - pd.Timestamp(today)).dt.days.astype("Int64")
        days = "Days to PDUFA"

    if "Cash Runway (months)" not in out:
        runway = next((c for c in ("cash_runway_months", "Cash runway months", "Cash Runway")
                       if c in out), None)
        out["Cash Runway (months)"] = out[runway] if runway else None
    if "2nd Financing Completed" not in out:
        out["2nd Financing Completed"] = "NOT VERIFIED"
    else:
        out["2nd Financing Completed"] = out["2nd Financing Completed"].fillna(
            "NOT VERIFIED").replace("", "NOT VERIFIED")

    if "event_key" in out or "Exact event" in out:
        event_col = "event_key" if "event_key" in out else "Exact event"
        path = Path(audit_path)
        try:
            stat = path.stat()
            verified = _audited_second_financing_keys(str(path), stat.st_mtime_ns, stat.st_size)
        except OSError:
            verified = frozenset()
        if verified:
            events = out[event_col].fillna("").astype(str).str.strip()
            valid = events.isin(verified)
            if "Ticker" in out:
                tickers = out["Ticker"].fillna("").astype(str).str.strip().str.upper()
                valid &= events.str.split("|", regex=False).str[0].str.upper().eq(tickers)
            elif "ticker" in out:
                tickers = out["ticker"].fillna("").astype(str).str.strip().str.upper()
                valid &= events.str.split("|", regex=False).str[0].str.upper().eq(tickers)
            out.loc[valid, "2nd Financing Completed"] = "YES — VERIFIED (HISTORICAL)"

    # Do not let a stored review-stage flag stand in for the verified second close.
    old = list(out.columns)
    cols = [c for c in old if c not in FINANCE_NEIGHBORS]
    offset = cols.index(days) + 1
    cols[offset:offset] = list(FINANCE_NEIGHBORS)
    result = out.loc[:, cols].copy()
    result.attrs.update(frame.attrs)
    return result


def sort_pdufa_grid(frame, order=DISPLAY_ORDER_OPTIONS[0]):
    """Sort the already-scored display rows, without inventing scores.

    TOP SCORE is a *display sort only*: scores from different research models
    are not scientifically equivalent; the adjacent Score type stays visible.
    Scores descend, then numeric days to PDUFA descend within each score.
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
        ascending=[False, False, True, True, True],
        na_position="last", kind="stable",
    )
    return result.drop(columns=["_score_sort", "_days_sort"])


def sort_pdufa_rows(frame):
    """Sort legacy PDUFA tables by existing score and countdown, both descending.

    Preserve all source columns and values. Without a score, sort only the
    countdown. Missing scores and countdowns remain last at each sort level.
    """
    aliases = {
        "Days to PDUFA": ("Days to PDUFA", "DAYS TO PDUFA", "days_to_pdufa", "Days Left"),
        "Score /100": ("Score /100", "Our Trade/PDUFA Score", "Trade Score", "trade_score",
                       "Evidence score /100", "Pre-readout research score /100",
                       "Preliminary clinical score /100", "Review priority /100",
                       "Research priority /100"),
        "Ticker": ("Ticker", "ticker"),
        "NCT ID": ("NCT ID", "NCT", "nct_id"),
        "Drug": ("Drug", "drug"),
    }
    if frame.empty or not any(c in frame for c in aliases["Days to PDUFA"]):
        return frame.copy()
    keys = pd.DataFrame(index=range(len(frame)))
    for name, choices in aliases.items():
        column = next((c for c in choices if c in frame), None)
        if column is not None:
            keys[name] = frame[column].to_numpy()
    keys["_position"] = range(len(frame))
    positions = sort_pdufa_grid(keys)["_position"].tolist()
    return frame.iloc[positions].copy()


def finance_style(frame):
    """Color financial evidence without altering underlying values or freshness.

    Traffic-light bands are used only for interpretable measurements:
    cash runway (>=12 / 6–<12 / <6 months), financing rubric points,
    and the *age* of dated runway evidence (<=90 / 91–120 / >120 days).
    Raw dollar amounts are neutral blue: a large balance or market cap
    alone does not imply a strong financial position. Missing/unverified is gray.
    """
    palette = {
        "green": "#bbf7d0",
        "yellow": "#fef08a",
        "red": "#fecaca",
        "neutral": "#dbeafe",
        "unknown": "#e5e7eb",
    }
    def paint(level):
        return (
            f"background-color:{palette[level]}; color:#000000;"
            "font-weight:bold; text-align:center; border:1px solid #111111;"
        )

    def band_number(value, *, high, middle, inverse=False):
        try:
            numeric = float(str(value).strip().replace(",", "").replace("%", ""))
            if not pd.notna(numeric):
                return "unknown"
        except (TypeError, ValueError, OverflowError):
            return "unknown"
        if inverse:
            return "green" if numeric <= high else "yellow" if numeric <= middle else "red"
        return "green" if numeric >= high else "yellow" if numeric >= middle else "red"

    def source_age(value):
        if not _present(value):
            return "unknown"
        parsed = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(parsed):
            return "unknown"
        today = pd.Timestamp.now(tz="America/Los_Angeles").date()
        age = (today - parsed.date()).days
        if age < 0:
            return "unknown"  # Future-dated evidence cannot be called current.
        return "green" if age <= 90 else "yellow" if age <= 120 else "red"

    def financing_color(value):
        return {
            "F START": "green", "F RUN": "yellow",
            "F CLOSED": "red", "F UNKNOWN": "unknown",
        }.get(_financing_block(value), "unknown")

    styled = frame.style
    if "F" in frame.columns:
        styled = styled.map(lambda v: paint(financing_color(v)), subset=["F"])

    for col in frame.columns:
        if col == "F":
            continue
        name = str(col).replace("_", " ").casefold()
        # Mutually exclusive semantic cases are chosen before broad labels.
        if name == "2nd financing completed":
            selector = lambda v: ("green" if str(v).upper().startswith("YES — VERIFIED")
                                  else "unknown")
        elif "cash runway as of" in name or "cash runway verified date" in name:
            selector = source_age
        elif "runway" in name and ("month" in name or name == "cash runway"):
            selector = lambda v: band_number(v, high=12, middle=6)
        elif "financing evidence /20" in name:
            selector = lambda v: band_number(v, high=15, middle=10)
        elif "runway risk index" in name:
            selector = lambda v: band_number(v, high=33, middle=66, inverse=True)
        elif "financing cycle" in name:
            selector = financing_color
        elif any(label in name for label in (
            "financing", "offering", "proceeds", "dilution", "atm",
            "cash", "debt", "revenue", "market cap", "short interest",
            "shares outstanding", "financial", "runway",
        )):
            selector = lambda v: "neutral" if _present(v) and str(v).strip().casefold() not in (
                "unknown", "not verified", "not available", "not scored",
                "review", "pending", "unverified", "n/a",
            ) else "unknown"
        else:
            continue
        styled = styled.map(lambda v, fn=selector: paint(fn(v)), subset=[col])
    return styled
