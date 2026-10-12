"""Fresh, conservative verification of nightly source claims.

This module never changes candidate data, scores, financing sequence, or trade
eligibility. A reachable URL, an index, and a closing keyword are different
claims. Each result carries its scope, evidence, fetch time, and content hash.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

VERSION = 1
STATES = ("VERIFIED", "REVIEW_REQUIRED", "CONFLICT", "TECHNICAL_FAILURE")
FIELDS = ["event_key", "ticker", "category", "claim", "verification_status",
          "expected", "observed", "reason", "source_url", "source_sha256",
          "checked_at", "evidence"]
MAX_BODY = 8_000_000
AGENT = "PDUFACommandCenter/1.0 source-verification"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def scope_hash(events, companies):
    # Include evidence identity, not prices changed by the collectors.
    items = sorted((r.get("event_key", ""), r.get("ticker", ""),
                    r.get("drug", ""), r.get("indication", ""),
                    r.get("pdufa_date", "")) for r in events)
    registry = sorted((r.get("ticker", ""), r.get("cik10", "")) for r in companies)
    return digest(json.dumps([items, registry], separators=(",", ":")).encode())


def run_identity():
    return ":".join(os.environ.get(k, "local") for k in
                    ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"))


def normalized(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def visible(raw):
    raw = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", raw))).strip()


def dates(text):
    found = set()
    for token in re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", text):
        try:
            found.add(date.fromisoformat(token).isoformat())
        except ValueError:
            pass
    pattern = (r"\b(?:January|February|March|April|May|June|July|August|September|"
               r"October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|"
               r"Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)"
               r"\s+\d{1,2},?\s+20\d{2}\b")
    for token in re.findall(pattern, text, re.I):
        token = re.sub(r"(?i)\bSept\.?", "Sep", token).replace(".", "")
        for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                found.add(datetime.strptime(token, fmt).date().isoformat())
                break
            except ValueError:
                pass
    return found


def drug_matches(event, text):
    # Full names/codes and explicitly supplied parenthetical aliases only.
    parts = re.split(r"[()/|;]", event.get("drug", ""))
    for part in parts:
        part = normalized(part)
        if len(part) >= 4 and part not in {"pdt", "injection", "tablets", "oral"}:
            if re.search(r"(?<!\w)" + re.escape(part) + r"(?!\w)", normalized(text)):
                return True
    return False


def indication_matches(event, text):
    stop = {"patients", "adults", "adult", "children", "treatment", "therapy",
            "with", "and", "the", "for", "age", "years", "including"}
    tokens = {x for x in normalized(event.get("indication", "")).split()
              if len(x) >= 4 and x not in stop}
    body = set(normalized(text).split())
    return bool(tokens) and len(tokens & body) >= min(2, len(tokens))


def company_matches(event, text):
    stop = {"inc", "incorporated", "corp", "corporation", "co", "company",
            "limited", "ltd", "plc", "holdings", "holding", "group",
            "pharma", "pharmaceutical", "pharmaceuticals", "therapeutics"}
    tokens = [x for x in normalized(event.get("company", "")).split() if x not in stop]
    return bool(tokens) and all(x in normalized(text).split() for x in tokens)


def publication_dates(raw, plain):
    metadata = set(re.findall(r'(?i)"datePublished"\s*:\s*"(20\d{2}-\d{2}-\d{2})', raw))
    metadata |= set(re.findall(r'(?i)<time[^>]*datetime=["\'](20\d{2}-\d{2}-\d{2})', raw))
    if metadata:
        return metadata
    # Require a press-release dateline marker rather than any early date;
    # a future PDUFA target in the headline is not a release date.
    marker = re.search(r"(?i)((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2})\s*(?:\(|—|--|/PRNewswire)", plain[:400])
    return dates(marker.group(1)) if marker else set()


def numeric(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


class SourceUnavailable(RuntimeError):
    pass


class IdentityConflict(ValueError):
    pass


def validate_submissions(payload, cik, ticker):
    if not isinstance(payload, dict) or str(payload.get("cik", "")).zfill(10) != cik:
        raise IdentityConflict("SEC response CIK does not match registry CIK")
    tickers = payload.get("tickers")
    if not isinstance(tickers, list) or ticker.upper() not in [str(t).upper() for t in tickers]:
        raise IdentityConflict("SEC response does not identify the requested ticker")
    recent = payload.get("filings", {}).get("recent")
    required = ("form", "filingDate", "accessionNumber", "primaryDocument")
    if not isinstance(recent, dict) or any(not isinstance(recent.get(k), list) for k in required):
        raise ValueError("SEC recent-filings schema is incomplete")
    lengths = {len(recent[k]) for k in required}
    if len(lengths) != 1 or not recent["form"]:
        raise ValueError("SEC recent-filings arrays are empty or inconsistent")
    for filed, accession, document in zip(recent["filingDate"], recent["accessionNumber"], recent["primaryDocument"]):
        date.fromisoformat(filed)
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession) or not document:
            raise ValueError("SEC filing identity is malformed")
    return recent


def sec_url_matches(url, cik):
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in {"www.sec.gov", "sec.gov"} or not cik or not cik.isdigit():
        return False
    match = re.match(r"/Archives/edgar/data/(\d+)/\d{18}/[^/]+$", parsed.path, re.I)
    return bool(match and int(match.group(1)) == int(cik))


class Verifier:
    def __init__(self, companies, fetch=None, as_of=None):
        self.companies = {r["ticker"].upper(): r for r in companies}
        self.fetcher = fetch or self.fetch
        self.as_of = as_of or datetime.now(timezone.utc).date()
        self.cache = {}
        self.sec_denials = 0

    def fetch(self, url):
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        is_sec = host == "sec.gov" or host.endswith(".sec.gov")
        if is_sec and self.sec_denials >= 3:
            raise SourceUnavailable("SEC circuit breaker after three HTTP 403 responses")
        agent = os.environ.get("SEC_USER_AGENT", "").strip() if is_sec else AGENT
        if is_sec and not re.fullmatch(r".{3,120}\s+[^\s@]+@[^\s@]+\.[^\s@]+", agent):
            raise SourceUnavailable("An identifying SEC_USER_AGENT is required")
        request = urllib.request.Request(url, headers={"User-Agent": agent, "Accept": "*/*"})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(request, timeout=18) as response:
                    final_host = (urllib.parse.urlsplit(response.geturl()).hostname or "").lower()
                    same_family = (final_host == host or
                                   is_sec and (final_host == "sec.gov" or final_host.endswith(".sec.gov")) or
                                   host.endswith("fda.gov") and (final_host == "fda.gov" or final_host.endswith(".fda.gov")))
                    if response.status != 200 or not same_family:
                        raise SourceUnavailable("HTTP response or redirect failed verification")
                    body = response.read(MAX_BODY + 1)
                    if not body.strip() or len(body) > MAX_BODY:
                        raise SourceUnavailable("Empty or oversized primary response")
                    if is_sec:
                        self.sec_denials = 0
                    return body
            except urllib.error.HTTPError as exc:
                if is_sec and exc.code == 403:
                    self.sec_denials += 1
                if attempt == 0 and exc.code in {429, 500, 502, 503, 504}:
                    time.sleep(1)
                    continue
                raise SourceUnavailable("HTTP_" + str(exc.code)) from exc
            except (TimeoutError, urllib.error.URLError) as exc:
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise SourceUnavailable(type(exc).__name__) from exc
            finally:
                if is_sec:
                    time.sleep(0.15)

    def body(self, url):
        if url not in self.cache:
            try:
                body = self.fetcher(url)
                if not isinstance(body, bytes) or not body.strip() or len(body) > MAX_BODY:
                    raise SourceUnavailable("Empty, malformed, or oversized response")
                self.cache[url] = (body, utcnow())
            except Exception as exc:
                self.cache[url] = exc
        result = self.cache[url]
        if isinstance(result, Exception):
            raise result
        return result[0]

    def document(self, url):
        body = self.body(url)
        if body.startswith(b"%PDF"):
            from pypdf import PdfReader
            text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(body)).pages)
            return text, text
        raw = body.decode("utf-8", "replace")
        return raw, visible(raw)

    def result(self, event, category, claim, state, reason, url="", expected="", observed="", evidence=""):
        cached = self.cache.get(url)
        return {"event_key": event.get("event_key", ""), "ticker": event.get("ticker", ""),
                "category": category, "claim": claim, "verification_status": state,
                "expected": str(expected), "observed": str(observed), "reason": reason,
                "source_url": url, "source_sha256": digest(cached[0]) if isinstance(cached, tuple) else "",
                "checked_at": cached[1] if isinstance(cached, tuple) else utcnow(),
                "evidence": re.sub(r"\s+", " ", evidence)[:900]}

    def company(self, event):
        return self.companies.get(event.get("ticker", "").upper(), {})

    def cik(self, event):
        value = self.company(event).get("cik10", "").strip()
        return value.zfill(10) if value.isdigit() and int(value) else ""

    def submissions(self, event):
        cik = self.cik(event)
        if not cik:
            raise ValueError("Missing valid registry CIK")
        url = "https://data.sec.gov/submissions/CIK" + cik + ".json"
        payload = json.loads(self.body(url))
        return url, payload, validate_submissions(payload, cik, event["ticker"])

    def references(self, event):
        found = [event.get(k, "") for k in ("pdufa_evidence_url", "trial_evidence_url", "financing_evidence_url")]
        for key in ("evidence_summary", "regulatory_summary"):
            found += re.findall(r"https://[^\s<>\"']+", event.get(key, ""))
        return list(dict.fromkeys(u.rstrip(".,;) ") for u in found if u))

    def primary(self, event, url):
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host == "fda.gov" or host.endswith(".fda.gov"):
            return "FDA"
        if sec_url_matches(url, self.cik(event)):
            return "SEC_ISSUER"
        return ""

    def regulatory(self, event):
        expected_outcome = event.get("outcome", "").strip().upper()
        claim = "FDA_DECISION" if expected_outcome in {"APPROVED", "CRL"} else "PDUFA_TARGET"
        expected = event.get("decision_date", "") if claim == "FDA_DECISION" else event.get("pdufa_date", "")
        refs = [u for u in self.references(event) if self.primary(event, u)]
        results = []
        for url in refs[:4]:
            try:
                _, plain = self.document(url)
                if not drug_matches(event, plain) or not indication_matches(event, plain):
                    continue
                if self.primary(event, url) == "FDA" and not company_matches(event, plain):
                    continue
                application = event.get("application_number", "").strip()
                if application and not re.search(r"(?<!\d)" + re.escape(application) + r"(?!\d)", plain):
                    continue
                if claim == "PDUFA_TARGET":
                    passages = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z])", plain)
                                if re.search(r"(?i)\bPDUFA\b|\btarget action date\b", p)]
                    observed = set().union(*(dates(p) for p in passages)) if passages else set()
                    if not expected or not observed:
                        continue
                    state = "VERIFIED" if observed == {expected} else "CONFLICT"
                    reason = "Drug, indication and reported target date match primary evidence" if state == "VERIFIED" else "Primary target date disagrees or multiple dates need reconciliation"
                    if state == "VERIFIED" and expected < self.as_of.isoformat():
                        state, reason = "REVIEW_REQUIRED", "Original target date confirmed, but target has passed and the final outcome remains unresolved"
                    results.append(self.result(event, "FDA", claim, state, reason, url, expected, " | ".join(sorted(observed)), " | ".join(passages)))
                else:
                    # Action wording, identity and date must coexist locally;
                    # publication/modified dates never become decision dates.
                    passages = [plain[max(0, m.start()-120):m.end()+450]
                                for m in re.finditer(r"(?i)\bFDA\s+(?:has\s+)?approv(?:ed|es)\b|\bcomplete response letter\b", plain)]
                    for passage in passages:
                        if not drug_matches(event, passage) or "fda" not in passage.lower():
                            continue
                        outcome = "CRL" if re.search(r"(?i)complete response letter", passage) else "APPROVED"
                        if re.search(r"(?i)\b(?:previously|historically|could|might|may|expects?|anticipated|not approved)\b", passage):
                            continue
                        if outcome == "CRL" and not re.search(r"(?i)\b(?:received|issued|delivered)\b", passage):
                            continue
                        action_dates = dates(passage)
                        if not expected or not action_dates:
                            continue
                        state = "VERIFIED" if outcome == expected_outcome and action_dates == {expected} else "CONFLICT"
                        results.append(self.result(event, "FDA", claim, state,
                            "Event outcome and explicit action date match" if state == "VERIFIED" else "Outcome/action date conflict requires review",
                            url, expected_outcome + " " + expected, outcome + " " + " | ".join(sorted(action_dates)), passage))
            except (SourceUnavailable, urllib.error.URLError, TimeoutError) as exc:
                results.append(self.result(event, "FDA", claim, "TECHNICAL_FAILURE", str(exc), url, expected))
            except Exception as exc:
                results.append(self.result(event, "FDA", claim, "REVIEW_REQUIRED", "Unusable source: " + type(exc).__name__, url, expected))
        conflicts = [r for r in results if r["verification_status"] == "CONFLICT"]
        verified = [r for r in results if r["verification_status"] == "VERIFIED"]
        if conflicts:
            return conflicts[:1]
        if verified:
            return verified[:1]
        return results[:1] or [self.result(event, "FDA", claim, "REVIEW_REQUIRED",
            "No primary source safely matches drug, indication, claim and explicit date", expected=expected)]

    def registry(self, company):
        event = {"ticker": company["ticker"], "event_key": "REGISTRY:" + company["ticker"]}
        url = "https://data.sec.gov/submissions/CIK" + self.cik(event) + ".json" if self.cik(event) else ""
        try:
            url, payload, recent = self.submissions(event)
            return self.result(event, "SEC", "FILINGS_INVENTORY", "VERIFIED",
                "CIK, ticker and nonempty filing arrays match; this verifies inventory only", url,
                self.cik(event), str(payload["cik"]).zfill(10), "Recent filings: " + str(len(recent["form"])))
        except IdentityConflict as exc:
            return self.result(event, "SEC", "FILINGS_INVENTORY", "CONFLICT", str(exc), url)
        except (ValueError, KeyError, TypeError) as exc:
            return self.result(event, "SEC", "FILINGS_INVENTORY", "REVIEW_REQUIRED", str(exc), url)
        except Exception as exc:
            return self.result(event, "SEC", "FILINGS_INVENTORY", "TECHNICAL_FAILURE", str(exc), url)

    def financing(self, event):
        url = event.get("financing_evidence_url", "")
        close = event.get("financing_close_date", "")
        if not sec_url_matches(url, self.cik(event)) or not close:
            return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                "Closing requires a company-matched SEC document and an explicit closing date; index/keywords do not prove second-financing sequence", url, close)
        try:
            _, plain = self.document(url)
            passages = [plain[max(0, m.start()-100):m.end()+350] for m in re.finditer(
                r"(?i)\b(?:closed|completed|consummated)\s+(?:its\s+|the\s+|a\s+)?(?:\$[\d,.]+\s+million\s+)?(?:public\s+|registered\s+direct\s+|private\s+)?(?:offering|financing|placement)\b", plain)]
            if not any(close in dates(p) for p in passages):
                return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                    "No completed transaction clause matches the stored closing date", url, close)
            # A closing can be real without being financing #2 after Phase 3.
            return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                "Dated closing clause found; exact deal, proceeds and post-Phase-3 second-financing sequence still require adjudication",
                url, close, close, " | ".join(passages))
        except Exception as exc:
            return self.result(event, "SEC", "FINANCING_CLOSURE", "TECHNICAL_FAILURE", type(exc).__name__, url, close)

    def financial(self, event):
        cik = self.cik(event)
        url = "https://data.sec.gov/api/xbrl/companyfacts/CIK" + cik + ".json" if cik else ""
        if not cik:
            return [self.result(event, "FINANCIAL", "CASH_AND_RUNWAY", "REVIEW_REQUIRED", "Missing CIK")]
        try:
            payload = json.loads(self.body(url))
            if str(payload.get("cik", "")).zfill(10) != cik:
                raise IdentityConflict("Companyfacts CIK mismatch")
            facts = payload.get("facts", {}).get("us-gaap", {})
            def values(name):
                items = facts.get(name, {}).get("units", {}).get("USD", [])
                return [r for r in items if r.get("form") in {"10-Q", "10-K"}
                        and numeric(r.get("val")) and r.get("end", "") <= self.as_of.isoformat()
                        and r.get("end", "") <= r.get("filed", "") <= self.as_of.isoformat()
                        and re.fullmatch(r"\d{10}-\d{2}-\d{6}", r.get("accn", ""))]
            # Cash equivalents, restricted cash and investments are different
            # measures; never pick the largest total and relabel it cash.
            cash_rows = values("CashAndCashEquivalentsAtCarryingValue")
            if not cash_rows:
                raise ValueError("No cash-equivalents USD fact with filing accession")
            cash = max(cash_rows, key=lambda r: (r["end"], r.get("filed", "")))
            age = (self.as_of - date.fromisoformat(cash["end"])).days
            if age > 180 or cash["val"] < 0:
                raise ValueError("Cash fact is stale or negative")
            expected_cash = event.get("cash", "")
            state = "VERIFIED"
            if expected_cash and abs(float(expected_cash) - cash["val"]) > 1:
                state = "CONFLICT"
            result = [self.result(event, "FINANCIAL", "CASH_FACT", state,
                "Exact cash-equivalents fact, period and filing accession checked", url,
                expected_cash, cash["val"], json.dumps(cash, sort_keys=True))]
            flows = []
            for fact in values("NetCashProvidedByUsedInOperatingActivities"):
                if fact["end"] != cash["end"] or not fact.get("start"):
                    continue
                days = (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days + 1
                if 60 <= days <= 380:
                    flows.append((days, fact))
            if not flows:
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", "REVIEW_REQUIRED",
                    "No operating-cash-flow duration aligned to cash period; no runway certified", url))
                return result
            days, flow = min(flows, key=lambda r: (r[0], -date.fromisoformat(r[1].get("filed", r[1]["end"])).toordinal()))
            if flow["val"] >= 0:
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", "REVIEW_REQUIRED",
                    "Operating cash flow is nonnegative; finite cash-burn runway is not applicable", url))
                return result
            runway = cash["val"] / (-flow["val"] / (days / 30.4375))
            expected = event.get("cash_runway_months", "")
            state = "CONFLICT" if expected and abs(float(expected)-runway) > 0.15 else "VERIFIED"
            result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", state,
                "Arithmetic verified using aligned cash/operating-flow periods; estimate excludes future financings and spending changes",
                url, expected, round(runway, 4), json.dumps({"cash": cash, "operating_flow": flow, "days": days}, sort_keys=True)))
            return result
        except IdentityConflict as exc:
            state, reason = "CONFLICT", str(exc)
        except (ValueError, KeyError, TypeError) as exc:
            state, reason = "REVIEW_REQUIRED", str(exc)
        except Exception as exc:
            state, reason = "TECHNICAL_FAILURE", type(exc).__name__
        return [self.result(event, "FINANCIAL", "CASH_AND_RUNWAY", state, reason, url)]

    def market(self, event):
        ticker = event["ticker"].upper()
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(ticker) + "?range=3mo&interval=1d&events=history"
        try:
            payload = json.loads(self.body(url))
            chart = payload["chart"]
            if chart.get("error") or len(chart.get("result") or []) != 1:
                raise ValueError("Market provider returned an error or no unique symbol")
            data = chart["result"][0]
            if data.get("meta", {}).get("symbol", "").upper() != ticker:
                raise IdentityConflict("Market response ticker mismatch")
            times = data["timestamp"]
            quote = data["indicators"]["quote"][0]
            closes, volumes = quote["close"], quote["volume"]
            if not times or len(times) != len(closes) or len(times) != len(volumes) or times != sorted(set(times)):
                raise ValueError("Market bars are empty, duplicated or misaligned")
            valid = [(t, c, v) for t, c, v in zip(times, closes, volumes)
                     if numeric(t) and numeric(c) and c > 0 and numeric(v) and v >= 0]
            if not valid:
                raise ValueError("No finite price/volume bar")
            stamp, price, volume = valid[-1]
            session = datetime.fromtimestamp(stamp, timezone.utc).date()
            if session > self.as_of or (self.as_of-session).days > 7:
                raise ValueError("Market session is future-dated or over seven calendar days old")
            expected = event.get("price_last", "")
            state = "CONFLICT" if expected and abs(float(expected)-price) > max(0.02, price*0.005) else "VERIFIED"
            return [self.result(event, "MARKET", "PRICE_VOLUME", state,
                "Direct provider response ticker, bar alignment, numbers and session checked; no exchange-level corroboration claimed",
                url, expected, price, json.dumps({"session": session.isoformat(), "close": price, "volume": volume})),
                self.result(event, "MARKET", "SHORT_IV_BORROW", "REVIEW_REQUIRED",
                    "Price feed does not verify short interest, IV or borrow availability/fees")]
        except IdentityConflict as exc:
            state, reason = "CONFLICT", str(exc)
        except (ValueError, KeyError, TypeError) as exc:
            state, reason = "REVIEW_REQUIRED", str(exc)
        except Exception as exc:
            state, reason = "TECHNICAL_FAILURE", type(exc).__name__
        return [self.result(event, "MARKET", "PRICE_VOLUME", state, reason, url),
                self.result(event, "MARKET", "SHORT_IV_BORROW", "REVIEW_REQUIRED", "Separate sources required")]

    def issuer(self, event):
        refs = [u for u in self.references(event) if sec_url_matches(u, self.cik(event))
                and re.search(r"(?i)(?:ex[-_]?99|exhibit[-_]?99)", u)]
        failures = []
        if not refs:
            try:
                _, _, recent = self.submissions(event)
                # Discover actual issuer exhibits, not Google News redirects.
                indices = [i for i, form in enumerate(recent["form"]) if form == "8-K"][:3]
                for i in indices:
                    acc = recent["accessionNumber"][i].replace("-", "")
                    base = "https://www.sec.gov/Archives/edgar/data/" + str(int(self.cik(event))) + "/" + acc + "/"
                    listing = json.loads(self.body(base + "index.json"))
                    for item in listing.get("directory", {}).get("item", []):
                        name = item.get("name", "")
                        if re.search(r"(?i)(?:ex[-_]?99|exhibit[-_]?99)", name) and name.lower().endswith((".htm", ".html")):
                            refs.append(base + urllib.parse.quote(name))
            except Exception as exc:
                failures.append(type(exc).__name__)
        for url in refs[:6]:
            try:
                raw, plain = self.document(url)
                if not drug_matches(event, plain) or not indication_matches(event, plain) or not company_matches(event, plain):
                    continue
                if not re.search(r"(?i)\b(?:press release|announced|announces|reported|reports)\b", plain):
                    continue
                posted = publication_dates(raw, plain)
                if len(posted) != 1:
                    continue
                published = next(iter(posted))
                if published > self.as_of.isoformat():
                    return [self.result(event, "ISSUER", "PRIMARY_RELEASE", "CONFLICT", "Release date is in the future", url, observed=published)]
                return [self.result(event, "ISSUER", "PRIMARY_RELEASE", "VERIFIED",
                    "Company CIK, SEC exhibit, drug, indication and explicit release date checked; release claims are not an FDA decision",
                    url, observed=published, evidence=plain[:900])]
            except Exception as exc:
                failures.append(type(exc).__name__)
        return [self.result(event, "ISSUER", "PRIMARY_RELEASE", "TECHNICAL_FAILURE" if failures else "REVIEW_REQUIRED",
            "Primary issuer release not confirmed" + (": " + ", ".join(failures[:3]) if failures else " for this event"))]


def summary(rows):
    counts = Counter(row["verification_status"] for row in rows)
    return {"findings_due": len(rows), "findings_verified": counts["VERIFIED"],
            "findings_unresolved": counts["REVIEW_REQUIRED"], "findings_conflicted": counts["CONFLICT"],
            "verification_technical_failure_count": counts["TECHNICAL_FAILURE"],
            "verification_status_counts": dict(counts)}


def verify_source(source, data_dir, out, fetch=None, as_of=None):
    events = read_rows(data_dir / "pdufa_candidates.csv")
    companies = read_rows(data_dir / "company_registry.csv")
    if not events or any(not r.get("event_key") or not r.get("ticker") for r in events):
        raise ValueError("Candidate scope is empty or lacks event identities")
    if len({r["event_key"] for r in events}) != len(events):
        raise ValueError("Duplicate candidate event identities")
    if not companies or len({r["ticker"].upper() for r in companies}) != len(companies):
        raise ValueError("Company registry is empty or contains duplicate tickers")
    verifier = Verifier(companies, fetch=fetch, as_of=as_of)
    results = []
    if source == "SEC":
        results += [verifier.registry(company) for company in companies]
    for event in events:
        if source == "FDA":
            results += verifier.regulatory(event)
        elif source == "SEC":
            results.append(verifier.financing(event))
        elif source == "FINANCIAL":
            results += verifier.financial(event)
        elif source == "MARKET":
            results += verifier.market(event)
        elif source == "ISSUER":
            results += verifier.issuer(event)
        else:
            raise ValueError("Unsupported verification source")
    out.mkdir(parents=True, exist_ok=True)
    path = out / (source.lower() + "_verification.csv")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    totals = summary(results)
    registry_rows = [r for r in results if r["claim"] == "FILINGS_INVENTORY"]
    registry_counts = Counter(r["verification_status"] for r in registry_rows)
    inventory = ({"registry_companies": len(companies), "companies_due": len(companies),
                  "companies_checked": registry_counts["VERIFIED"],
                  "sec_registry_status_counts": dict(registry_counts),
                  "sec_registry_output": path.name} if source == "SEC" else {})
    return {**totals, **inventory, "verification_version": VERSION, "verification_run_id": run_identity(),
            "verification_scope_sha256": scope_hash(events, companies),
            "verification_ledger": path.name, "verification_ledger_sha256": digest(path.read_bytes()),
            "verification_events_due": len(events), "verification_events_checked": len({r["event_key"] for r in results if not r["event_key"].startswith("REGISTRY:")}),
            "scope_coverage_verified": bool(results) and totals["findings_verified"] == len(results),
            "verification_issue_examples": [{k: r[k] for k in ("ticker", "category", "claim", "verification_status", "reason")}
                for r in results if r["verification_status"] != "VERIFIED"][:12],
            "issuer_press_releases_verified": sum(r["category"] == "ISSUER" and r["verification_status"] == "VERIFIED" for r in results)}
