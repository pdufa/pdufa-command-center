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

VERSION = 2
STATES = ("VERIFIED", "NOT_APPLICABLE", "UNAVAILABLE", "REVIEW_REQUIRED", "CONFLICT", "TECHNICAL_FAILURE")
FIELDS = ["event_key", "ticker", "category", "claim", "verification_status",
          "verification_required",
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


def target_dates(text):
    """Dates explicitly attached to the target, excluding release datelines."""
    date_pattern = (r"(?:20\d{2}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)\s+\d{1,2},?\s+20\d{2})")
    markers = list(re.finditer(r"(?i)\b(?:PDUFA\s*\)?\s*(?:(?:goal|target|action)\s+){0,2}date|target\s+action\s+date|goal\s+date)\b", text))
    observed = set()
    for marker in markers:
        tail = text[marker.end():marker.end()+110]
        match = re.search(date_pattern, tail, re.I)
        if not match:
            continue
        bridge = tail[:match.start()]
        if re.fullmatch(r"(?i)[\s():,;-]*(?:(?:of|is|on|for|set|as|the|has|been|at|to|a|and|in|FDA|target)\b[\s():,;-]*)*", bridge):
            observed |= dates(match.group())
    # Compact primary statements such as "PDUFA November 1, 2026" are valid;
    # an arbitrary date elsewhere after a headline containing PDUFA is not.
    for match in re.finditer(r"(?i)\bPDUFA[\s():,-]+(?:(?:goal|target|action|deadline|date|of|is|on)\s+)*" + date_pattern, text):
        observed |= dates(match.group())
    return observed



def attributed_target_dates(event, passage):
    """Match each PDUFA date to the program text preceding THAT date.

    Investor releases can put multiple drug/date pairs into one sentence or
    HTML table row. The previous program's drug identity must not authorize
    the next program's goal date. We retain preceding program context until
    its own dated target, then reset for the next dated target.
    """
    date_rx = (r"(?:20\d{2}-\d{2}-\d{2}|"
               r"(?:January|February|March|April|May|June|July|August|September|"
               r"October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|"
               r"Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)"
               r"\s+\d{1,2},?\s+20\d{2})")
    markers = list(re.finditer(r"(?i)\b(?:PDUFA|target\s+action\s+date|goal\s+date)\b", passage))
    confirmed = set()
    prior_target_end = 0
    for marker in markers:
        tail = passage[marker.end():marker.end() + 110]
        dated = re.search(date_rx, tail, re.I)
        if not dated:
            continue
        end = marker.end() + dated.end()
        fragment = passage[prior_target_end:end]
        # The program identity and its indication must coexist before the
        # claimed date. The date must be explicitly tied to a target marker.
        if drug_matches(event, fragment) and indication_matches(event, fragment):
            claimed = target_dates(fragment)
            confirmed |= claimed & dates(dated.group())
        prior_target_end = end
    return confirmed


def drug_matches(event, text):
    # Full names/codes and explicitly supplied parenthetical aliases only.
    parts = re.split(r"[()/|;]", event.get("drug", ""))
    parts += re.split(r"[|;]", event.get("drug_aliases", ""))
    # Delivery/dose suffixes are not part of the active drug identity. Keep
    # combination partners intact, and still require the exact indication.
    parts += [re.sub(r"(?i)\s+(?:PDT|HCl|immediate-release|cream\s+[\d.]+%|ophthalmic solution\s+[\d.]+%)$", "", p.strip()) for p in parts]
    for part in parts:
        part = normalized(part)
        if len(part) >= 4 and part not in {"pdt", "injection", "tablets", "oral"}:
            if re.search(r"(?<!\w)" + re.escape(part) + r"(?!\w)", normalized(text)):
                return True
    return False


def indication_matches(event, text):
    stop = {"patients", "adults", "adult", "children", "treatment", "therapy",
            "with", "and", "the", "for", "age", "years", "including"}
    indication = re.sub(r"\bnonadvanced\b", "non advanced", normalized(event.get("indication", "")))
    text = re.sub(r"\bnonadvanced\b", "non advanced", normalized(text))
    tokens = {x for x in indication.split()
              if len(x) >= 4 and x not in stop}
    body = set(normalized(text).split())
    if re.search(r"\bnon\s*advanced\b", indication):
        if not re.search(r"\bnon\s*advanced\b", normalized(text)):
            return False
    qualifiers = tokens & {"advanced", "nonadvanced", "severe", "chronic", "acute"}
    if "advanced" in qualifiers:
        if re.search(r"\bnon\s+advanced\b", indication):
            qualifiers.discard("advanced")
        elif not re.search(r"\badvanced\b", re.sub(r"\bnon\s+advanced\b", "nonadvanced", text)):
            return False
    if not qualifiers <= body:
        return False
    if bool(tokens) and len(tokens & body) >= min(2, len(tokens)):
        return True
    # A program's explicit parenthetical indication abbreviation is a
    # source-provided alias, not an inferred disease match. For example,
    # "autosomal dominant hypocalcemia type 1 (ADH1)" may appear as "ADH1"
    # in a later sentence in the same SEC exhibit. The caller must still
    # independently match the drug, the relevant passage and the dated claim.
    aliases = re.findall(r"\(([A-Za-z][A-Za-z0-9/-]{2,12})\)", str(event.get("indication", "")))
    return any(normalized(alias) in body for alias in aliases
               if len(normalized(alias)) >= 3 and normalized(alias) not in {"fda", "usa"})


def company_matches(event, text):
    stop = {"inc", "incorporated", "corp", "corporation", "co", "company",
            "limited", "ltd", "plc", "holdings", "holding", "group",
            "pharma", "pharmaceutical", "pharmaceuticals", "therapeutics"}
    tokens = [x for x in normalized(event.get("company", "")).split() if x not in stop]
    return bool(tokens) and all(x in normalized(text).split() for x in tokens)


def publication_dates(raw, plain):
    metadata = set(re.findall(r'(?i)"datePublished"\s*:\s*"(20\d{2}-\d{2}-\d{2})', raw))
    metadata |= set(re.findall(r'(?i)<time[^>]*datetime=["\'](20\d{2}-\d{2}-\d{2})', raw))
    metadata |= set(re.findall(r'(?i)<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\'](20\d{2}-\d{2}-\d{2})', raw))
    if metadata:
        return metadata
    # Require a press-release dateline marker rather than any early date;
    # a future PDUFA target in the headline is not a release date.
    marker = re.search(r"(?i)((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)\s+\d{1,2},\s+20\d{2})\s*(?:\(|—|--|/PRNewswire)", plain[:6000])
    if marker:
        return dates(marker.group(1))
    # SEC-filed company press releases often use a conventional dateline
    # such as "SOUTH SAN FRANCISCO, Calif., May 5, 2026 -". A bare
    # "PDUFA November 14, 2026 - ..." is NOT a publication dateline.
    month = (r"(?:January|February|March|April|May|June|July|August|September|"
             r"October|November|December|Jan\.?|Feb\.?|Mar\.?|Apr\.?|"
             r"Jun\.?|Jul\.?|Aug\.?|Sep\.?|Oct\.?|Nov\.?|Dec\.?)")
    dateline = re.search(
        r"(?i)\b[A-Z]{2,}(?:\s+[A-Z]{2,}){0,3},\s*(?:[A-Z][a-z]+\.?,\s*)?"
        + "(" + month + r"\s+\d{1,2},\s+20\d{2})" + r"\s+[-–—]\s",
        plain[:6000])
    return dates(dateline.group(1)) if dateline else set()


def numeric(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


class SourceUnavailable(RuntimeError):
    pass


class IdentityConflict(ValueError):
    pass


FINANCIAL_FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A", "10-QT", "10-KT",
                   "10-QT/A", "10-KT/A", "20-F", "20-F/A", "40-F", "40-F/A", "6-K"}


def financial_snapshot(payload, cik, as_of):
    """One cash definition and aligned reporting periods for collection/review."""
    if not isinstance(payload, dict) or str(payload.get("cik", "")).zfill(10) != cik:
        raise IdentityConflict("Companyfacts CIK mismatch")
    cutoff = as_of.isoformat()
    def values(taxonomy, tag):
        items = payload.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {}).get("USD", [])
        result = []
        for row in items:
            try:
                end, filed = date.fromisoformat(row["end"]), date.fromisoformat(row["filed"])
                if (row.get("form") in FINANCIAL_FORMS and numeric(row.get("val"))
                        and end <= filed <= as_of
                        and re.fullmatch(r"\d{10}-\d{2}-\d{6}", row.get("accn", ""))):
                    result.append(row)
            except (ValueError, KeyError, TypeError):
                continue
        return result
    choices = []
    for taxonomy, tag, basis in (
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue", "CASH_EQUIVALENTS"),
        ("ifrs-full", "CashAndCashEquivalents", "CASH_EQUIVALENTS"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "CASH_INCLUDING_RESTRICTED"),
    ):
        for row in values(taxonomy, tag):
            if row["val"] >= 0 and (as_of - date.fromisoformat(row["end"])).days <= 180:
                choices.append((row, taxonomy, tag, basis))
    if not choices:
        raise ValueError("No current nonnegative USD cash fact with a filing accession")
    # Prefer the newest period, and exact cash equivalents over restricted cash
    # in the SAME period. Never choose the largest balance or a stale exact tag.
    cash, taxonomy, tag, basis = max(choices, key=lambda x: (
        x[0]["end"], x[3] == "CASH_EQUIVALENTS", x[0]["filed"]))
    flows = []
    flow_tag = "NetCashProvidedByUsedInOperatingActivities" if taxonomy == "us-gaap" else "CashFlowsFromUsedInOperatingActivities"
    for row in values(taxonomy, flow_tag):
        try:
            days = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days + 1
            if row["end"] == cash["end"] and row["accn"] == cash["accn"] and 60 <= days <= 380:
                flows.append((days, row))
        except (ValueError, KeyError, TypeError):
            continue
    aligned = min(flows, key=lambda x: x[0]) if flows else None
    return {"cash": cash, "cash_basis": basis, "taxonomy": taxonomy, "cash_tag": tag,
            "flow": aligned[1] if aligned else None, "flow_days": aligned[0] if aligned else None}


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
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            raise ValueError("SEC filing identity is malformed")
        # Legacy EDGAR records legitimately omit primaryDocument. Their dated
        # accession still belongs in an inventory; it cannot be fetched as an
        # empty document or prove a closing. Keep rejecting inconsistent arrays.
        if not isinstance(document, str):
            raise ValueError("SEC primary-document field is malformed")
    return recent


def sec_url_matches(url, cik):
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in {"www.sec.gov", "sec.gov"} or not cik or not cik.isdigit():
        return False
    match = re.match(r"/Archives/edgar/data/(\d+)/\d{18}/[^/]+$", parsed.path, re.I)
    return bool(match and int(match.group(1)) == int(cik))



def documented_preferred_share_purchase(text, closing_date):
    """Strict SEC 8-K fallback for dated, completed preferred-share purchase.

    A purchase agreement, future issuance, closing target, or term sheet does
    not prove funds were received. Require a dated actual Closing Date,
    past-tense Purchasers purchased shares, and an explicit dollar aggregate.
    This only verifies the specific closing, never financing #2 or entry.
    """
    for match in re.finditer(r"(?i)\bclosing\s+date\b", text):
        passage = text[max(0, match.start() - 95):match.end() + 1000]
        if closing_date not in dates(passage):
            continue
        # Look for a real completed acquisition of issued preferred shares,
        # not statements that buyers MAY purchase shares in the future.
        bought = re.search(r"(?i)\bpurchasers?\s+purchased\s+an?\s+aggregate\s+of\s+[\d,]+\s+shares\b", passage)
        price = re.search(r"(?i)\baggregate\s+purchase\s+price\s+of\s*\$\s*[\d,]+(?:\.\d+)?\b", passage)
        if not bought or not price or price.start() < bought.end():
            continue
        if not re.search(r"(?i)\bpreferred\s+stock\b", passage[:price.end()]):
            continue
        # Ensure the purchase follows (rather than precedes) the same dated
        # Closing Date anchor, so an unrelated historical purchase cannot pass.
        if bought.start() < match.end() - max(0, match.start() - 95):
            continue
        return passage[:price.end()]
    return ""


class Verifier:
    def __init__(self, companies, fetch=None, as_of=None, issuer_sources=None):
        self.companies = {r["ticker"].upper(): r for r in companies}
        self.fetcher = fetch or self.fetch
        self.as_of = as_of or datetime.now(timezone.utc).date()
        self.cache = {}
        self.sec_denials = 0
        self.issuer_sources = issuer_sources or {}
        self.issuer_document_cache = {}
        self.unavailable_providers = set()

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

    def result(self, event, category, claim, state, reason, url="", expected="", observed="", evidence="", required=True):
        cached = self.cache.get(url)
        return {"event_key": event.get("event_key", ""), "ticker": event.get("ticker", ""),
                "category": category, "claim": claim, "verification_status": state,
                "verification_required": "YES" if required else "NO",
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
        found = [event.get(k, "") for k in ("pdufa_evidence_url", "trial_evidence_url", "financing_evidence_url", "issuer_evidence_url")]
        for key in ("evidence_summary", "regulatory_summary"):
            found += re.findall(r"https://[^\s<>\"']+", event.get(key, ""))
        return list(dict.fromkeys(u.rstrip(".,;) ") for u in found if u))

    def primary(self, event, url):
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host == "fda.gov" or host.endswith(".fda.gov"):
            return "FDA"
        if sec_url_matches(url, self.cik(event)):
            return "SEC_ISSUER"
        config = self.issuer_sources.get(event.get("ticker", "").upper(), {})
        if host in config.get("hosts", []) and urllib.parse.urlsplit(url).scheme == "https":
            return "ISSUER"
        return ""

    def issuer_documents(self, event):
        """Saved primary references first, then bounded actual SEC exhibits."""
        yielded = set()
        for url in self.references(event):
            if self.primary(event, url) and url not in yielded:
                yielded.add(url)
                yield url
        cik = self.cik(event)
        if not cik:
            return
        if cik not in self.issuer_document_cache:
            _, _, recent = self.submissions(event)
            found = []
            indices = [i for i, form in enumerate(recent["form"])
                       if form in {"8-K", "8-K/A", "6-K"}
                       and recent["filingDate"][i] <= self.as_of.isoformat()][:8]
            for i in indices:
                acc = recent["accessionNumber"][i].replace("-", "")
                base = "https://www.sec.gov/Archives/edgar/data/" + str(int(cik)) + "/" + acc + "/"
                listing = json.loads(self.body(base + "index.json"))
                for item in listing.get("directory", {}).get("item", []):
                    name = item.get("name", "")
                    if (re.search(r"(?i)(?:ex[-_]?99|exhibit[-_]?99)", name)
                            and name.lower().endswith((".htm", ".html"))
                            and re.fullmatch(r"[A-Za-z0-9_.-]+", name)):
                        found.append(base + name)
                if len(found) >= 12:
                    break
            self.issuer_document_cache[cik] = found
        for url in self.issuer_document_cache[cik]:
            if url not in yielded:
                yield url

    def regulatory(self, event):
        expected_outcome = event.get("outcome", "").strip().upper()
        claim = "FDA_DECISION" if expected_outcome in {"APPROVED", "CRL"} else "PDUFA_TARGET"
        expected = event.get("decision_date", "") if claim == "FDA_DECISION" else event.get("pdufa_date", "")
        refs = [u for u in self.references(event) if self.primary(event, u)]
        results = []
        # Empty saved references previously meant an event was never looked up.
        if not refs:
            try:
                refs = list(self.issuer_documents(event))[:12]
            except (ValueError, KeyError, TypeError) as exc:
                return [self.result(event, "FDA", claim, "REVIEW_REQUIRED", "Primary-source discovery requires review: " + str(exc), expected=expected)]
            except Exception as exc:
                return [self.result(event, "FDA", claim, "TECHNICAL_FAILURE", str(exc), expected=expected)]
        for url in refs[:4]:
            try:
                _, plain = self.document(url)
                if not drug_matches(event, plain) or not indication_matches(event, plain):
                    continue
                if self.primary(event, url) in {"FDA", "ISSUER"} and not company_matches(event, plain):
                    continue
                application = event.get("application_number", "").strip()
                if application and not re.search(r"(?<!\d)" + re.escape(application) + r"(?!\d)", plain):
                    continue
                if claim == "PDUFA_TARGET":
                    # Preserve semicolons within a program description,
                    # but assign target dates only to the corresponding program
                    # via attributed_target_dates; never borrow the next drug's date.
                    sections = re.split(r"\s*[•]\s*|(?<=[.!?])\s+(?=[A-Z])", plain)
                    sentences = []
                    for section in sections:
                        if len(section) > 1500:
                            # HTML menus and headings can precede a dateline
                            # without punctuation; limit identity to the claim.
                            sentences.extend(section[max(0, m.start()-650):m.end()+180]
                                for m in re.finditer(r"(?i)\bPDUFA\b|\btarget action date\b", section))
                        else:
                            sentences.append(section)
                    passages = []
                    for i, passage in enumerate(sentences):
                        if not re.search(r"(?i)\bPDUFA\b|\btarget action date\b", passage):
                            continue
                        context = passage
                        # A short continuation may inherit its preceding drug
                        # identity. Never borrow identity from the next program
                        # or from an explicit target for another indication.
                        if (not drug_matches(event, passage) and len(passage) <= 350
                                and re.match(r"(?i)^(?:the\s+)?(?:FDA\b|PDUFA\b)", passage.strip())
                                and not re.search(r"(?i)\bfor\b", passage)):
                            context = " ".join(sentences[max(0, i-1):i+1])
                        if drug_matches(event, context) and indication_matches(event, context):
                            passages.append(context)
                    observed = set().union(*(attributed_target_dates(event, p) for p in passages)) if passages else set()
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
                        if not action_dates:
                            continue
                        state = "VERIFIED" if outcome == expected_outcome and len(action_dates) == 1 and (not expected or action_dates == {expected}) else "CONFLICT"
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
        review = event.get("_financing_review", {})
        if not close and review.get("second_financing_audit_status") == "VERIFIED_SECOND_POST_PHASE3_FINANCING":
            # A matching event ledger supplies a candidate to re-open, not proof.
            # Never borrow another company's or another program's financing.
            url = review.get("second_financing_source", "")
            close = review.get("second_financing_date", "")
        if not sec_url_matches(url, self.cik(event)) or not close:
            return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                "Closing requires a company-matched SEC document and an explicit closing date; index/keywords do not prove second-financing sequence", url, close)
        try:
            _, plain = self.document(url)
            passages = [plain[max(0, m.start()-100):m.end()+350] for m in re.finditer(
                r"(?i)\b(?:closed|completed|consummated)\s+(?:its\s+|the\s+|a\s+)?(?:previously[-\s]+announced\s+)?(?:\$[\d,.]+\s+million\s+)?(?:public\s+|registered\s+direct\s+|private\s+)?(?:offering|financing|placement)\b", plain)]
            if not any(close in dates(p) for p in passages):
                completed_purchase = documented_preferred_share_purchase(plain, close)
                if completed_purchase:
                    return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                        "Company-matched SEC filing confirms completed, dated preferred-share purchases and aggregate price; second post-Phase-3 financing order and dilution risk remain separate",
                        url, close, close, completed_purchase)
                return self.result(event, "SEC", "FINANCING_CLOSURE", "REVIEW_REQUIRED",
                    "No completed transaction clause matches the stored closing date", url, close)
            from sec_financing_closure import candidates as closing_candidates
            clauses = [r["excerpt"] for r in closing_candidates({"text": plain})]
            matched = [p for p in clauses if dates(p) == {close} and re.search(r"\$\s*[\d,.]+\s*(?:million|billion)?", p)]
            if matched:
                return self.result(event, "SEC", "FINANCING_CLOSURE", "VERIFIED",
                    "Company-matched SEC document confirms a dated closing and financing amount; this verifies that closing only, not the post-Phase-3 second-financing sequence",
                    url, close, close, " | ".join(matched))
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
            snapshot = financial_snapshot(json.loads(self.body(url)), cik, self.as_of)
            cash, flow = snapshot["cash"], snapshot["flow"]
            exact = snapshot["cash_basis"] == "CASH_EQUIVALENTS"
            expected = event.get("cash", "") if exact else ""
            state = "CONFLICT" if expected and abs(float(expected) - cash["val"]) > 1 else "VERIFIED"
            result = [self.result(event, "FINANCIAL", "CASH_FACT" if exact else "LIQUIDITY_FACT", state,
                "Current USD fact checked: " + snapshot["cash_basis"] + "; period and filing accession retained",
                url, expected, cash["val"], json.dumps(snapshot, sort_keys=True))]
            if flow is None:
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", "REVIEW_REQUIRED",
                    "No operating cash flow from the same filing and period; no runway certified", url))
            elif flow["val"] >= 0:
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", "NOT_APPLICABLE",
                    "Aligned operating cash flow is nonnegative; finite cash-burn runway does not apply",
                    url, observed="NOT_APPLICABLE", evidence=json.dumps(snapshot, sort_keys=True)))
            elif not exact:
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", "REVIEW_REQUIRED",
                    "Reported cash includes restricted cash; an unrestricted balance is required for spendable-cash runway",
                    url, evidence=json.dumps(snapshot, sort_keys=True)))
            else:
                runway = cash["val"] / (-flow["val"] / (snapshot["flow_days"] / 30.4375))
                expected = event.get("cash_runway_months", "")
                state = "CONFLICT" if expected and abs(float(expected) - runway) > 0.15 else "VERIFIED"
                result.append(self.result(event, "FINANCIAL", "RUNWAY_ESTIMATE", state,
                    "Arithmetic verified using the same cash/operating-flow filing and period; estimate excludes future financings and spending changes",
                    url, expected, round(runway, 4), json.dumps(snapshot, sort_keys=True)))
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
            # Imported event.price_last is undated. Treating a normal price
            # move as a contradiction with today's bar creates false mandatory
            # conflicts. Without a matching quote date, this is not a valid
            # same-session price comparison.
            previous_undated_snapshot = str(event.get("price_last", "")).strip()
            return [self.result(event, "MARKET", "PRICE_VOLUME", "VERIFIED",
                "Provider ticker, bar alignment, values and session verified; "
                "an undated saved price cannot contradict a dated market bar",
                url, "", price, json.dumps({"session": session.isoformat(),
                    "close": price, "volume": volume,
                    "undated_saved_price_last": previous_undated_snapshot}))] + self.market_extras(event)
        except IdentityConflict as exc:
            state, reason = "CONFLICT", str(exc)
        except (ValueError, KeyError, TypeError) as exc:
            state, reason = "REVIEW_REQUIRED", str(exc)
        except Exception as exc:
            state, reason = "TECHNICAL_FAILURE", type(exc).__name__
        return [self.result(event, "MARKET", "PRICE_VOLUME", state, reason, url)] + self.market_extras(event)

    def optional_payload(self, url):
        host = urllib.parse.urlsplit(url).hostname
        if host in self.unavailable_providers:
            raise SourceUnavailable("Provider denied supplemental data earlier in this run")
        try:
            return json.loads(self.body(url))
        except Exception as exc:
            if any(code in str(exc) for code in ("HTTP_401", "HTTP_403", "HTTP_429")):
                self.unavailable_providers.add(host)
            raise

    def market_extras(self, event):
        """Separate dated supplemental observations; never infer float %/borrow."""
        ticker = event["ticker"].upper()
        records = []
        url = "https://api.nasdaq.com/api/quote/" + urllib.parse.quote(ticker) + "/short-interest?assetclass=stocks"
        try:
            data = self.optional_payload(url).get("data") or {}
            if str(data.get("symbol", "")).upper() != ticker:
                raise ValueError("No ticker-matched Nasdaq short-interest response")
            observations = []
            for row in (data.get("shortInterestTable") or {}).get("rows", []):
                settled = datetime.strptime(row["settlementDate"], "%m/%d/%Y").date()
                shares = int(str(row["interest"]).replace(",", ""))
                ratio = float(str(row["daysToCover"]).replace(",", ""))
                if settled <= self.as_of and (self.as_of-settled).days <= 40 and shares >= 0 and math.isfinite(ratio) and ratio >= 0:
                    observations.append((settled, shares, ratio))
            if not observations:
                raise ValueError("No current finite settlement-dated short-interest row")
            settled, shares, ratio = max(observations)
            value = {"settlement_date": settled.isoformat(), "short_shares": shares, "days_to_cover": ratio}
            records.append(self.result(event, "MARKET", "SHORT_INTEREST", "VERIFIED",
                "Nasdaq reported short shares and days to cover; this is not short interest as a percentage of float",
                url, observed=json.dumps(value, sort_keys=True), evidence=json.dumps(value, sort_keys=True), required=False))
        except Exception as exc:
            records.append(self.result(event, "MARKET", "SHORT_INTEREST", "UNAVAILABLE", str(exc), url, required=False))
        url = "https://query1.finance.yahoo.com/v7/finance/options/" + urllib.parse.quote(ticker)
        try:
            result = self.optional_payload(url)["optionChain"]
            if result.get("error") or len(result.get("result") or []) != 1:
                raise ValueError("No unique options chain")
            chain = result["result"][0]
            if chain.get("underlyingSymbol", "").upper() != ticker:
                raise ValueError("Options underlying ticker mismatch")
            expiries = [(abs((datetime.fromtimestamp(t, timezone.utc).date()-self.as_of).days-30), t)
                        for t in chain.get("expirationDates", [])
                        if 21 <= (datetime.fromtimestamp(t, timezone.utc).date()-self.as_of).days <= 45]
            if not expiries:
                raise ValueError("No listed expiration within 21-45 days")
            expiry = min(expiries)[1]
            url += "?date=" + str(expiry)
            chain = self.optional_payload(url)["optionChain"]["result"][0]
            if chain.get("underlyingSymbol", "").upper() != ticker:
                raise ValueError("Dated options underlying mismatch")
            spot = chain.get("quote", {}).get("regularMarketPrice")
            if not numeric(spot) or spot <= 0:
                raise ValueError("No finite underlying quote")
            candidates = []
            for option_set in chain.get("options", []):
                if option_set.get("expirationDate") != expiry:
                    continue
                for contract in option_set.get("calls", []) + option_set.get("puts", []):
                    iv, strike, traded = contract.get("impliedVolatility"), contract.get("strike"), contract.get("lastTradeDate")
                    if not numeric(iv) or not 0 < iv <= 10 or not numeric(strike) or not numeric(traded):
                        continue
                    age = (self.as_of-datetime.fromtimestamp(traded, timezone.utc).date()).days
                    if 0 <= age <= 7 and abs(strike-spot)/spot <= .15:
                        candidates.append((abs(strike-spot), contract))
            if not candidates:
                raise ValueError("No recent near-money option with provider-reported IV")
            contract = min(candidates, key=lambda x:x[0])[1]
            value = {"contract": contract.get("contractSymbol"), "implied_volatility": contract["impliedVolatility"],
                     "expiration": datetime.fromtimestamp(expiry, timezone.utc).date().isoformat(), "strike": contract["strike"]}
            records.append(self.result(event, "MARKET", "OPTIONS_IV", "VERIFIED",
                "Provider IV for a dated near-money option; not an interpolated constant 30-day IV",
                url, observed=json.dumps(value, sort_keys=True), evidence=json.dumps(value, sort_keys=True), required=False))
        except Exception as exc:
            records.append(self.result(event, "MARKET", "OPTIONS_IV", "UNAVAILABLE", str(exc), url, required=False))
        records.append(self.result(event, "MARKET", "BORROW", "UNAVAILABLE",
            "Borrow availability and fees require a broker-specific source; no broker data is configured", required=False))
        return records

    def issuer(self, event):
        failures = []
        try:
            for i, url in enumerate(self.issuer_documents(event)):
                if i >= 16:
                    break
                if self.primary(event, url) == "FDA":
                    continue
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
                        "Primary company-matched source, drug, indication and explicit publication date checked; release claims are not an FDA decision",
                        url, observed=published, evidence=plain[:900])]
                except (ValueError, KeyError, TypeError):
                    continue
                except Exception as exc:
                    failures.append(str(exc)[:120])
        except (ValueError, KeyError, TypeError):
            pass
        except Exception as exc:
            failures.append(str(exc)[:120])
        return [self.result(event, "ISSUER", "PRIMARY_RELEASE", "TECHNICAL_FAILURE" if failures else "REVIEW_REQUIRED",
            "Primary issuer release not confirmed" + (": " + ", ".join(failures[:3]) if failures else " for this event"))]


def summary(rows):
    counts = Counter(row["verification_status"] for row in rows)
    mandatory = [r for r in rows if r.get("verification_required", "YES") == "YES"]
    incomplete = [r for r in mandatory if r["verification_status"] not in {"VERIFIED", "NOT_APPLICABLE"}]
    return {"findings_due": len(rows), "findings_verified": counts["VERIFIED"],
            "findings_not_applicable": counts["NOT_APPLICABLE"], "findings_unavailable": counts["UNAVAILABLE"],
            "required_findings_due": len(mandatory), "required_findings_unresolved": len(incomplete),
            "optional_findings_unavailable": sum(r["verification_status"] == "UNAVAILABLE" and r.get("verification_required") == "NO" for r in rows),
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
    config_path = Path(__file__).resolve().parents[1] / "config/issuer_sources.json"
    issuer_sources = json.loads(config_path.read_text()) if config_path.exists() else {}
    financing_path = data_dir / "second_financing_status.csv"
    financing_reviews = {r["event_key"]: r for r in read_rows(financing_path)} if financing_path.exists() else {}
    verifier = Verifier(companies, fetch=fetch, as_of=as_of, issuer_sources=issuer_sources)
    results = []
    if source == "SEC":
        results += [verifier.registry(company) for company in companies]
    for event in events:
        event = {**event, "_financing_review": financing_reviews.get(event["event_key"], {})}
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
            "scope_coverage_verified": bool(results) and totals["required_findings_unresolved"] == 0,
            "verification_issue_examples": [{k: r[k] for k in ("ticker", "category", "claim", "verification_status", "reason")}
                for r in results if r["verification_status"] not in {"VERIFIED", "NOT_APPLICABLE"}] [:12],
            "issuer_press_releases_verified": sum(r["category"] == "ISSUER" and r["verification_status"] == "VERIFIED" for r in results)}

