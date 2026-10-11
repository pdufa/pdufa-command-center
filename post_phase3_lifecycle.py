"""Read-only Stage 2 position journal and pre-PDUFA exit watch.

Rows are USER-REPORTED holdings, not brokerage-confirmed positions. Entry/exit
dates are never invented and the engine never places or sends orders.
Finance-stage colors and active-position lifecycle colors are separate.
"""
from __future__ import annotations

import csv
import io
import math
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
NCT = re.compile(r"^NCT\d{8}$")
EVENT = re.compile(r"^[A-Z0-9.-]{1,12}\|[A-Z0-9_]+$")
TRADE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
JOURNAL_FIELDS = (
    "trade_id", "event_key", "ticker", "nct_id",
    "entry_date", "entry_price", "shares",
    "pdufa_date_at_entry", "exit_date", "exit_price", "exit_reason",
)
DISPLAY_FIELDS = (
    "Trade ID", "Ticker", "Exact event", "NCT ID", "Trade lifecycle",
    "Monitoring alert", "Next action", "Entry date", "Entry price USD",
    "Shares", "PDUFA date at entry", "Current PDUFA date",
    "Conservative PDUFA date", "Exit deadline (-7d)",
    "Days to exit deadline", "Exit date", "Exit price USD",
    "Last EOD session", "Last EOD close USD", "Marked or realized P/L %",
    "Marked or realized P/L USD", "Market quote source", "Exit reason",
    "As of Pacific",
)


def clean(value):
    return str(value or "").strip()


def day(raw):
    try:
        value = clean(raw)
        return date.fromisoformat(value) if len(value) == 10 else None
    except ValueError:
        return None


def positive_number(raw):
    try:
        v = float(clean(raw))
        return v if math.isfinite(v) and v > 0 else None
    except (ValueError, TypeError):
        return None


def _iso(value):
    return value.isoformat() if value else ""


def parse_journal(upload, max_bytes=250_000):
    """Strict UTF-8 CSV with required headings; never persist user holdings."""
    if not isinstance(upload, bytes) or len(upload) > max_bytes:
        raise ValueError("Journal CSV exceeds the 250 KB limit or is not a file")
    try:
        source = upload.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(source, newline=""))
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Journal header is empty or has duplicate names")
        if not set(JOURNAL_FIELDS).issubset(reader.fieldnames):
            raise ValueError("Journal must include every field in the CSV template")
        data = []
        for line in reader:
            if None in line:
                raise ValueError("CSV row contains more columns than the header")
            if len(data) >= 300:
                raise ValueError("Journal limited to 300 trade rows")
            data.append(line)
        return data
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("Journal must be a valid UTF-8 CSV") from exc


def template_csv():
    output = io.StringIO()
    csv.writer(output).writerow(JOURNAL_FIELDS)
    return output.getvalue().encode("utf-8-sig")


def _quote_index(market_rows, today):
    """No ticker-only financing join: a ticker-only EOD quote is valid
    exclusively for mark-to-market, NEVER a verified company event."""
    index = {}
    duplicates = set()
    for row in market_rows:
        ticker = clean(row.get("ticker")).upper()
        if not ticker:
            continue
        if ticker in index:
            duplicates.add(ticker)
        index[ticker] = row
    for ticker in duplicates:
        index.pop(ticker, None)
    clean_index = {}
    for ticker, row in index.items():
        try:
            checked = datetime.fromisoformat(clean(row.get("checked_at_utc")).replace("Z", "+00:00"))
            if checked.tzinfo is None or checked > datetime.combine(
                today + timedelta(days=1), datetime.min.time(), tzinfo=PACIFIC
            ).astimezone(timezone.utc):
                continue
            checked_day = checked.astimezone(PACIFIC).date()
            session = day(row.get("last_session"))
            close = positive_number(row.get("last_close_usd"))
            if (not session or not close or not 0 <= (today-session).days <= 5 or
                    not 0 <= (today-checked_day).days <= 3 or
                    clean(row.get("market_status")) != "MARKET_UPDATED" or
                    clean(row.get("last_session_freshness")) != "RECENT EOD" or
                    not clean(row.get("market_source")).startswith("https://")):
                continue
            clean_index[ticker] = {"close": close, "session": session,
                                   "source": clean(row.get("market_source"))}
        except (ValueError, TypeError, OverflowError):
            continue
    return clean_index


def monitor_positions(journal, candidates, market_rows, as_of=None):
    """Compute lifecycle from reported positions and exact candidate identity.

    A user-reported entry is not evidence that historical GREEN gates passed.
    RED due means action required, never that the broker sold any shares.
    """
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None:
            raise ValueError("as_of datetime must be timezone aware")
        today = as_of.astimezone(PACIFIC).date()
    else:
        today = as_of if isinstance(as_of, date) else datetime.now(PACIFIC).date()
    event_index = {}
    duplicates = set()
    for c in candidates:
        key = clean(c.get("Exact event"))
        if not key:
            continue
        if key in event_index:
            duplicates.add(key)
        event_index[key] = c
    for key in duplicates:
        event_index.pop(key, None)
    quote_index = _quote_index(market_rows, today)
    id_count = {}
    for row in journal:
        key = clean(row.get("trade_id"))
        id_count[key] = id_count.get(key, 0) + 1

    output = []
    counts = {"open": 0, "due": 0, "recorded_exits": 0, "review": 0, "total": len(journal)}
    for raw in journal:
        trade_id = clean(raw.get("trade_id"))
        key = clean(raw.get("event_key"))
        ticker = clean(raw.get("ticker")).upper()
        nct = clean(raw.get("nct_id")).upper()
        entry = day(raw.get("entry_date"))
        price = positive_number(raw.get("entry_price"))
        shares = positive_number(raw.get("shares"))
        entry_pdufa = day(raw.get("pdufa_date_at_entry"))
        exit_raw = clean(raw.get("exit_date"))
        exit_price_raw = clean(raw.get("exit_price"))
        exit_date = day(exit_raw)
        exit_price = positive_number(exit_price_raw)
        event = event_index.get(key)
        event_nct = clean(event.get("NCT ID")).upper() if event else ""
        current_pdufa = day(event.get("PDUFA date")) if event else None
        pdufa_verified = bool(event and clean(event.get("PDUFA verification")).startswith("VERIFIED"))
        current_verified_date = current_pdufa if pdufa_verified else None
        # A date supplied by the investor remains provisional even when plausible.
        # Use the earlier available date to avoid pushing a planned exit later.
        applicable = min([x for x in (entry_pdufa, current_verified_date) if x],
                         default=None)
        deadline = applicable - timedelta(days=7) if applicable else None
        days_remaining = (deadline - today).days if deadline else None
        quote = quote_index.get(ticker)
        alerts = []
        invalid = []
        if not TRADE_ID.fullmatch(trade_id) or id_count.get(trade_id) != 1:
            invalid.append("Missing/duplicate trade ID")
        if not EVENT.fullmatch(key) or ticker != key.split("|")[0]:
            invalid.append("Invalid exact event/ticker")
        if not NCT.fullmatch(nct):
            invalid.append("Exact NCT ID required")
        if not entry or entry > today or not price or not shares:
            invalid.append("Entry date, price and shares must be valid and nonfuture")
        if exit_raw or exit_price_raw:
            if not exit_date or not exit_price or (entry and exit_date < entry) or (exit_date and exit_date > today):
                invalid.append("Exit date/price must both be valid, chronological and nonfuture")
        if not event:
            alerts.append("Exact program event missing or duplicated in saved candidate queue")
            invalid.append("Missing or ambiguous exact regulatory event")
        elif ticker != clean(event.get("Ticker")).upper() or not event_nct or nct != event_nct:
            alerts.append("Program/NCT identity mismatch or unverified")
            invalid.append("Event-to-NCT mapping is not verified")
        if entry_pdufa is None:
            alerts.append("PDUFA date at entry not recorded")
        if not pdufa_verified:
            alerts.append("Current PDUFA date not independently verified")
        if entry_pdufa and current_verified_date and entry_pdufa != current_verified_date:
            alerts.append("PDUFA DATE CHANGED — earliest date governs provisional deadline")
        if event and clean(event.get("Entry qualification")).startswith("EXCLUDED"):
            alerts.append("FDA outcome / saved regulatory event excluded — urgent assessment")
        if event and not clean(event.get("Entry qualification")).startswith("GREEN"):
            alerts.append("CURRENT ENTRY GATES NOT GREEN; this is not historical entry verification")
        if not quote and not exit_date:
            alerts.append("Current EOD quote absent/stale — no marked P/L")
        if invalid:
            lifecycle = "REVIEW — INVALID OR UNMATCHED JOURNAL"
            action = "Correct journal identity/dates and reconcile exact event"
        elif exit_date:
            lifecycle = "RED — EXIT RECORDED"
            action = "Reconcile reported execution and trading costs"
            if deadline and exit_date > deadline:
                alerts.append("Reported exit occurred AFTER scheduled deadline")
            counts["recorded_exits"] += 1
        elif event and clean(event.get("Entry qualification")).startswith("EXCLUDED"):
            lifecycle = "RED — URGENT REGULATORY REVIEW"
            action = "Assess FDA event immediately; no sale recorded"
            counts["due"] += 1
        elif deadline and today >= deadline:
            lifecycle = "RED — EXIT DUE / NOT RECORDED"
            action = "Planned cutoff reached; confirm actual broker execution"
            counts["due"] += 1
        elif not pdufa_verified or not entry_pdufa or not current_verified_date:
            lifecycle = "REVIEW — EXIT DATE UNVERIFIED"
            action = "Verify PDUFA and entry-date snapshot before trusting cutoff"
        elif quote is None:
            lifecycle = "YELLOW — OPEN / QUOTE RECHECK"
            action = "Recheck EOD price and FDA/financing events; do not infer gain"
            counts["open"] += 1
        elif days_remaining is not None and days_remaining <= 7:
            lifecycle = "YELLOW — EXIT PREPARATION"
            action = "Prepare exit, verify updated FDA and financing disclosures"
            counts["open"] += 1
        else:
            lifecycle = "YELLOW — OPEN / MONITOR"
            action = "Monitor price, filings, regulatory news and exit countdown"
            counts["open"] += 1

        if quote and entry and quote["session"] < entry and not exit_date:
            alerts.append("Latest EOD session predates reported entry; mark unavailable")
            quote = None
            if lifecycle.startswith("YELLOW"):
                lifecycle = "YELLOW — OPEN / QUOTE RECHECK"
                action = "Get a quote dated on or after the actual entry; monitor filings"
        pnl_price = exit_price if exit_date else (quote["close"] if quote else None)
        if invalid or not pnl_price or not price or not shares:
            percent = cash = None
        else:
            percent = round((pnl_price / price - 1)*100, 2)
            cash = round((pnl_price-price)*shares, 2)
        if lifecycle.startswith("REVIEW"):
            counts["review"] += 1
        output.append({
            "Trade ID": trade_id, "Ticker": ticker, "Exact event": key,
            "NCT ID": nct, "Trade lifecycle": lifecycle,
            "Monitoring alert": " | ".join(dict.fromkeys(alerts)),
            "Next action": action,
            "Entry date": _iso(entry), "Entry price USD": price,
            "Shares": shares, "PDUFA date at entry": _iso(entry_pdufa),
            "Current PDUFA date": _iso(current_pdufa),
            "Conservative PDUFA date": _iso(applicable),
            "Exit deadline (-7d)": _iso(deadline),
            "Days to exit deadline": days_remaining,
            "Exit date": _iso(exit_date), "Exit price USD": exit_price,
            "Last EOD session": _iso(quote["session"]) if quote else "",
            "Last EOD close USD": quote["close"] if quote else None,
            "Marked or realized P/L %": percent,
            "Marked or realized P/L USD": cash,
            "Market quote source": quote["source"] if quote else "",
            "Exit reason": clean(raw.get("exit_reason")),
            "As of Pacific": today.isoformat(),
        })
    priority = {
        "RED — EXIT DUE / NOT RECORDED": 0,
        "RED — URGENT REGULATORY REVIEW": 1,
        "REVIEW — INVALID OR UNMATCHED JOURNAL": 2,
        "REVIEW — EXIT DATE UNVERIFIED": 3,
        "YELLOW — EXIT PREPARATION": 4,
        "YELLOW — OPEN / QUOTE RECHECK": 5,
        "YELLOW — OPEN / MONITOR": 6,
        "RED — EXIT RECORDED": 7,
    }
    output.sort(key=lambda item: (priority.get(item["Trade lifecycle"], 8),
                                  item["Days to exit deadline"] if item["Days to exit deadline"] is not None else 9999,
                                  item["Trade ID"]))
    return output, counts
