#!/usr/bin/env python3
"""FOCUS-only Telegram news leads using the existing bot GitHub secrets.

This is a headline/filing discovery alert, NOT scientific adjudication,
approval-probability calculation, or verification of a linked FDA cycle.
The first run records an old-news baseline; later checks alert for new
or materially amended title/description fingerprints only.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse
import urllib.request
import xml.etree.ElementTree as ET

try:
    from scripts.telegram_scan_alert import main as telegram_send
except ModuleNotFoundError:
    from telegram_scan_alert import main as telegram_send

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
FDA_API = "https://pdufa-new-dashboard.vercel.app/api/news"
MAX_AGE = timedelta(days=3)
MAX_BYTES = 700_000
GOOD_TERMS = re.compile(
    r"\b(fda|pdufa|phase[\s-]*[123]|clinical|trial|study|efficacy|safety|"
    r"approval|approved|review|readout|results?|data|complete response|crl|"
    r"filings?|financ\w*|offering|dilut\w*|earnings|revenue|sec|"
    r"8-k|10-q|6-k|partnership|acquisition|manufacturing|hold|halt)\b",
    re.I,
)
HIGH_TERMS = re.compile(
    r"\b(fda|pdufa|clinical hold|trial halted|phase[\s-]*3|"
    r"crl|complete response letter|rejection|approved|approval|"
    r"secondary offering|public offering|safety|adverse event|"
    r"deadline|review extension)\b", re.I,
)


def get_json(url):
    if url != FDA_API:
        raise ValueError("Unsupported FDA API endpoint")
    req = urllib.request.Request(url, headers={
        "User-Agent": "PDUFA-FOCUS-TelegramNews/1.0 (research)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=18) as response:
        if urlparse(response.url).hostname != "pdufa-new-dashboard.vercel.app":
            raise ValueError("FDA API redirect offsite")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("FDA API response too large")
    return json.loads(data)


def get_xml(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "news.google.com" or parsed.path != "/rss/search":
        raise ValueError("Unknown news source")
    req = urllib.request.Request(url, headers={
        "User-Agent": "PDUFA-FOCUS-TelegramNews/1.0 (research)",
        "Accept": "application/rss+xml, application/xml",
    })
    with urllib.request.urlopen(req, timeout=12) as response:
        if urlparse(response.url).hostname != "news.google.com":
            raise ValueError("News source redirected")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("News RSS response too large")
    return data


def roster():
    data = json.loads(ROSTER.read_text(encoding="utf-8"))
    records = data.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Canonical FOCUS roster unavailable")
    tickers = {}
    for r in records:
        if not isinstance(r, dict):
            continue
        ticker, nct, company = r.get("ticker"), r.get("nct"), r.get("company")
        if not (isinstance(ticker, str) and re.fullmatch(r"[A-Z]{2,6}", ticker)
                and isinstance(nct, str) and re.fullmatch(r"NCT\d{8}", nct)
                and isinstance(company, str) and len(company.strip()) >= 4):
            raise ValueError("Untrusted FOCUS identity; refusing partial run")
        item = tickers.setdefault(ticker, {"company": company, "ncts": set()})
        # Legal suffix variants in the same ticker are safe (e.g. Cytokinetics
        # versus Cytokinetics, Inc.); unrelated issuer names are not.
        if issuer_alias(item["company"]).casefold() != issuer_alias(company).casefold():
            raise ValueError("Conflicting FOCUS ticker identity")
        item["ncts"].add(nct)
    if not tickers:
        raise ValueError("No FOCUS tickers")
    return tickers


def issuer_alias(name):
    name = re.sub(r",?\s+(?:Inc\.?|Ltd\.?|S\.A\.?|N\.V\.?|AG)\s*$", "", name, flags=re.I)
    return name.strip()


def text_clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value or ""))).strip()


def as_utc(value):
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, IndexError):
        return None


def recent(published, now):
    return bool(published and now - MAX_AGE <= published <= now + timedelta(minutes=15))


def google_rss_candidates(ticker, company, raw, now):
    """Google News coverage is an unverified LEAD; never a primary FDA action."""
    root = ET.fromstring(raw)
    if root.tag != "rss":
        raise ValueError("Expected RSS")
    alias = issuer_alias(company)
    alias_norm = re.sub(r"[^a-z0-9]+", " ", alias.lower()).strip()
    entries = []
    for node in root.findall("./channel/item")[:40]:
        title = text_clean(node.findtext("title"))
        description = text_clean(node.findtext("description"))
        link = (node.findtext("link") or "").strip()
        date = as_utc((node.findtext("pubDate") or "").strip())
        url = urlparse(link)
        if not title or len(title) > 350 or not link.startswith("https://") or url.hostname != "news.google.com":
            continue
        if not recent(date, now):
            continue
        norm = " " + re.sub(r"[^a-z0-9]+", " ", (title + " " + description).lower()) + " "
        match_issuer = bool(alias_norm and (" " + alias_norm + " ") in norm)
        match_ticker = bool(re.search(r"(?<![A-Z])" + re.escape(ticker) + r"(?![A-Z])", title))
        if not (match_issuer or match_ticker) or not GOOD_TERMS.search(title):
            continue
        entries.append({
            "key": "media:" + ticker + ":" + link,
            "ticker": ticker, "kind": "UNVERIFIED_MEDIA_HEADLINE",
            "title": title, "description": description[:350], "url": link,
            "published": date.isoformat(), "drug": "", "ncts": [],
            "priority": "HIGH — verify source" if HIGH_TERMS.search(title) else "MEDIUM — verify source",
        })
    return entries


def fda_candidates(payload, current, now):
    if payload.get("feedStatus") != "LIVE_FDA_RSS":
        raise ValueError("Live FDA RSS unavailable")
    events = []
    for a in payload.get("articles", []):
        if not isinstance(a, dict):
            continue
        ticker = a.get("ticker")
        link = a.get("sourceUrl", "")
        if (ticker not in current or a.get("kind") != "FDA_ARTICLE"
            or a.get("verification") != "OFFICIAL_FDA_PUBLICATION"
            or a.get("matchStatus") != "UNREVIEWED_EXACT_DRUG_MENTION"
            or not isinstance(link, str) or urlparse(link).hostname not in ("fda.gov", "www.fda.gov")
            or not link.startswith("https://")):
            continue
        associated = set(a.get("ncts") or []) & current[ticker]["ncts"]
        if not associated:
            continue
        try:
            date = datetime.fromisoformat(str(a.get("publishedAt")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if not recent(date, now):
            continue
        events.append({
            "key": "fda:" + ticker + ":" + link,
            "ticker": ticker, "kind": "OFFICIAL_FDA_DRUG_MENTION_UNREVIEWED",
            "title": text_clean(a.get("title", ""))[:350],
            "description": text_clean(a.get("description", ""))[:350],
            "url": link, "published": date.isoformat(),
            "drug": str(a.get("drug") or "")[:120], "ncts": sorted(associated),
            "priority": "HIGH — official FDA publication; application identity unverified",
        })
    return events


def fingerprint(item):
    stable = "\n".join([item["title"], item["description"], item["kind"]])
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def gather(current, now, *, fda_fetch=get_json, xml_fetch=get_xml):
    events = []
    failures = []
    try:
        events.extend(fda_candidates(fda_fetch(FDA_API), current, now))
    except Exception as exc:
        failures.append("FDA feed: " + type(exc).__name__)
    for ticker, info in sorted(current.items()):
        query = '"' + issuer_alias(info["company"]) + '" when:2d'
        feed = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-US&gl=US&ceid=US:en"
        try:
            events.extend(google_rss_candidates(ticker, info["company"], xml_fetch(feed), now))
        except Exception as exc:
            failures.append("News " + ticker + ": " + type(exc).__name__)
    bykey = {e["key"]: e for e in events}
    return bykey, failures


def alert_details(item, amended):
    changed = "MATERIALLY AMENDED HEADLINE / SUMMARY" if amended else "NEW PUBLICATION"
    msg = [
        item["ticker"] + " | " + item["priority"],
        changed + " | " + item["published"][:19] + " UTC",
        item["title"][:185],
        "Source: " + item["url"][:280],
    ]
    if item["kind"] == "UNVERIFIED_MEDIA_HEADLINE":
        msg.append("Third-party news lead; verify original company/FDA/SEC source before reassessment.")
    else:
        msg.append("Official FDA article, UNREVIEWED drug-name match; not proof of application-specific action.")
        msg.append("Drug: " + item["drug"][:65] + " | NCT: " + ",".join(item["ncts"])[:85])
    msg.append("No prediction/approval probability changed by this alert.")
    return "\n".join(msg)[:700]


def check_and_send(path, now=None, *, load=gather, sender=telegram_send):
    now = now or datetime.now(timezone.utc)
    current = roster()
    incoming, failures = load(current, now)
    if len(failures) >= len(current) + 1:
        raise RuntimeError("All news sources unavailable; state not advanced")
    has_state = Path(path).exists()
    if has_state:
        try:
            saved = json.loads(Path(path).read_text(encoding="utf-8"))
            if saved.get("schemaVersion") != 1 or not isinstance(saved.get("seen"), dict):
                raise ValueError("Invalid news baseline")
            seen = saved["seen"]
        except (ValueError, OSError, AttributeError) as exc:
            raise RuntimeError("News history corrupted; refusing to flood chat") from exc
    else:
        seen = {}
    sent = 0
    if not has_state:
        for key, item in incoming.items():
            seen[key] = {"fingerprint": fingerprint(item), "observedAt": now.isoformat()}
        print("Initial FOCUS news baseline saved; no historical alert flood.")
    else:
        for key, item in sorted(incoming.items()):
            old = seen.get(key)
            fp = fingerprint(item)
            if isinstance(old, dict) and old.get("fingerprint") == fp:
                continue
            details = alert_details(item, amended=old is not None)
            success = sender(["--event", "focus-news", "--details", details])
            if success == 0:
                sent += 1
                seen[key] = {"fingerprint": fp, "observedAt": now.isoformat()}
            else:
                print("::warning::FOCUS news Telegram notification failed; will retry.")
    # Bound state; old material changes outside the lookback window are irrelevant.
    cutoff = now - timedelta(days=35)
    seen = {
        k: v for k, v in seen.items()
        if isinstance(v, dict) and isinstance(v.get("observedAt"), str)
        and v["observedAt"] >= cutoff.isoformat()
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "schemaVersion": 1, "updatedAt": now.isoformat(), "tickerCount": len(current),
        "seen": seen,
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("FOCUS Telegram news check: tickers=%d; candidates=%d; notified=%d; failed_sources=%d."
          % (len(current), len(incoming), sent, len(failures)))
    for failure in failures:
        print("::warning::" + failure)
    return 0


if __name__ == "__main__":
    try:
        if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
            raise RuntimeError("Telegram bot secrets unavailable; delivery not configured")
        sys.exit(check_and_send(os.environ.get("FOCUS_TELEGRAM_NEWS_STATE", ".cache/focus-telegram-news.json")))
    except Exception as exc:
        print("::error::FOCUS Telegram news check failed: " + type(exc).__name__ + " (no success claimed)")
        sys.exit(1)
