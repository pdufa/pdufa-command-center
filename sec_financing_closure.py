"""Step 4 upgrade: evidence-traceable, conservative SEC financing closing review.

No completed financing is inferred from SEC form metadata, offering registration,
future-tense projections, an ATM program, or gross proceeds alone. A reviewed
SEC 8-K (or its exhibit) with dated, explicit closing text is required; results
are researcher-attested source reviews and NOT independent auditor conclusions.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from sec_step4 import DEFAULT_DB, cik10, clean_ticker, utc_now

SEC_BASE = "https://www.sec.gov/Archives/edgar/data/"
TYPES = ("PUBLIC_OFFERING", "REGISTERED_DIRECT", "PRIVATE_PLACEMENT", "OTHER_EQUITY")
AMOUNT_RX = re.compile(
    r"\b(gross|net)\s+proceeds\s+(?:of|were|was|totaled|totaling)\s+"
    r"(?:(?:approximately|about|an?\s+estimated)\s+)?"
    r"\$\s*([\d,]+(?:\.\d+)?)\s*(billion|million|thousand|bn|mm|m)?\b",
    re.I)
FINANCING_RX = re.compile(
    r"\b(?:public offering|underwritten offering|registered direct offering|"
    r"private placement|firm commitment offering|equity financing|"
    r"offering of (?:its |the )?(?:common stock|securities|shares)|"
    r"offering of \d[\d,]* (?:shares|units)|financing transaction)\b", re.I)
CLOSED_RX = re.compile(
    r"\b(?:closed|completed|consummated|has closed|has completed|has consummated)\b", re.I)
PROSPECTIVE_RX = re.compile(
    r"\b(?:expects? to|expected to|will|would|may|might|planned to|"
    r"anticipates? to|subject to|not yet|has not|had not|did not|"
    r"upon completion|if completed|prior to closing|scheduled to)\b", re.I)
ATM_RX = re.compile(r"\b(?:at[- ]the[- ]market|ATM program|sales agreement)\b", re.I)
DATE_RX = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b")
MONTH_RX = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
    r"\.?\s+\d{1,2},?\s+\d{4}\b", re.I)


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "svg", "head"}:
            self.ignore += 1
        if tag in {"p", "br", "div", "li", "tr", "table", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg", "head"} and self.ignore:
            self.ignore -= 1
        if tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignore:
            self.parts.append(data + " ")


def visible_text(payload):
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    parser = _VisibleText()
    if "<html" in payload[:3000].lower() or re.search(r"<(?:div|p|body|table)\b", payload[:3000], re.I):
        parser.feed(payload)
        s = "".join(parser.parts)
    else:
        s = html.unescape(payload)
        s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _filing_info(row, cik, as_of):
    """Allow retrieval only from a registered issuer's indexed recent 8-K."""
    cik = cik10(cik)
    cutoff = _date(as_of)
    if not cutoff:
        raise ValueError("Invalid research as-of date")
    if row.get("form") not in {"8-K", "8-K/A"}:
        raise ValueError("Only indexed 8-K and 8-K/A documents are accepted as closure evidence")
    filed = _date(row.get("filed"))
    if not filed or filed > cutoff:
        raise ValueError("Filing was not available on the selected analysis date")
    accn = str(row.get("accession") or "")
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accn) or accn[:10] != cik:
        raise ValueError("8-K accession does not belong to the selected issuer CIK")
    prefix = f"{SEC_BASE}{int(cik)}/{accn.replace('-', '')}/"
    primary = str(row.get("source_url") or "")
    path = urlsplit(primary)
    if not primary.startswith(prefix) or path.query or path.fragment:
        raise ValueError("Indexed filing URL does not match issuer CIK and accession")
    return {"cik": cik, "accession": accn, "filed": filed, "prefix": prefix}


def _date(raw):
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except ValueError:
        return None


def _document_url(row, cik, as_of, document_name=None):
    filing = _filing_info(row, cik, as_of)
    if document_name:
        name = str(document_name).strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name) or not re.search(r"\.(?:htm|html|txt)$", name, re.I):
            raise ValueError("SEC exhibit document must be a safe .htm/.html/.txt filename from this filing")
        return filing, filing["prefix"] + name
    return filing, row["source_url"]


def fetch_sec_document(row, cik, as_of, user_agent, document_name=None,
                       opener=urlopen, attempts=2):
    """Fetch only exact SEC EDGAR archive path for the selected CIK/accession."""
    filing, url = _document_url(row, cik, as_of, document_name)
    if not (str(user_agent or "").strip() and "@" in user_agent and len(user_agent.strip()) >= 12):
        raise ValueError("Set SEC_USER_AGENT to app name and genuine contact email.")
    req = Request(url, headers={"User-Agent": user_agent,
                                "Accept": "text/html,text/plain",
                                "Accept-Encoding": "identity"})
    for attempt in range(attempts):
        try:
            with opener(req, timeout=18) as response:
                payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                raise RuntimeError("SEC filing document over 2 MB; inspect manually")
            txt = visible_text(payload)
            if len(txt) < 50:
                raise RuntimeError("SEC filing contained no usable text")
            digest = hashlib.sha256(payload).hexdigest()
            return {"source_url": url, "filed": filing["filed"].isoformat(),
                    "accession": filing["accession"], "cik": filing["cik"],
                    "form": row["form"], "document_sha256": digest,
                    "text": txt, "source_kind": "SEC EDGAR 8-K DOCUMENT"}
        except HTTPError as exc:
            if exc.code in (403, 401):
                raise RuntimeError(f"SEC access HTTP {exc.code}. Confirm SEC_USER_AGENT and network.") from exc
            if exc.code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"SEC document retrieval HTTP {exc.code}. Nothing verified.") from exc
        except (URLError, OSError, TimeoutError) as exc:
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"SEC filing network unavailable: {exc}") from exc
    raise RuntimeError("SEC filing could not be fetched")


def _sentence_blocks(text):
    """Compact text into clause-sized segments; no heading-only verification."""
    for paragraph in re.split(r"(?<=[.!?;])\s+(?=[A-Z0-9$])", text):
        paragraph = paragraph.strip()
        if paragraph:
            yield paragraph


def _closing_date_in_text(segment, closing_date):
    """Require exact real date printed near the assertion, never inferred from filing date."""
    d = _date(closing_date)
    if d is None:
        return False
    for raw in DATE_RX.findall(segment):
        try:
            observed = date.fromisoformat(raw) if "-" in raw else datetime.strptime(raw, "%m/%d/%Y").date()
        except ValueError:
            continue
        if observed == d:
            return True
    for token in MONTH_RX.findall(segment):
        cleaned = re.sub(r"\bSept\.?\b", "Sep", token, flags=re.I).replace(".", "")
        for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                if datetime.strptime(cleaned, fmt).date() == d:
                    return True
            except ValueError:
                continue
    return False


def candidates(document):
    """Offer only *possible* closing statements; human must verify transaction match."""
    text = document["text"]
    findings = []
    for part in _sentence_blocks(text):
        if len(part) > 900:
            # Do not treat giant SEC boilerplate blocks as a discrete completion statement.
            continue
        if not CLOSED_RX.search(part) or not FINANCING_RX.search(part):
            continue
        if PROSPECTIVE_RX.search(part):
            continue
        if ATM_RX.search(part):
            continue
        if not (DATE_RX.search(part) or MONTH_RX.search(part)):
            continue
        # Prevent a report containing unrelated closing and offering statements
        # from becoming a positive merely because both words appear.
        close = CLOSED_RX.search(part)
        offer = FINANCING_RX.search(part)
        if abs(close.start() - offer.start()) > 260:
            continue
        finding = re.sub(r"\s+", " ", part).strip()
        findings.append({"id": hashlib.sha256(finding.encode("utf-8")).hexdigest()[:20],
                         "excerpt": finding[:900],
                         "date_hint_required": True})
        if len(findings) >= 30:
            break
    return findings


def _amounts(clause):
    values = {"gross_proceeds_usd": None, "net_proceeds_usd": None}
    multiplier = {None: 1, "thousand": 1_000, "million": 1_000_000,
                  "mm": 1_000_000, "m": 1_000_000, "billion": 1_000_000_000,
                  "bn": 1_000_000_000}
    for kind, amount, unit in AMOUNT_RX.findall(clause):
        try:
            val = float(amount.replace(",", "")) * multiplier[unit.lower() if unit else None]
        except (ValueError, KeyError):
            continue
        if not math_is_valid_usd(val):
            continue
        key = f"{kind.lower()}_proceeds_usd"
        values[key] = val
    return values


def math_is_valid_usd(v):
    return 0 < v < 500_000_000_000 and v == v and v not in (float("inf"), float("-inf"))


def _type_of(clause):
    lower = clause.lower()
    if "at-the-market" in lower or "at the market" in lower:
        return None
    if "registered direct" in lower:
        return "REGISTERED_DIRECT"
    if "private placement" in lower:
        return "PRIVATE_PLACEMENT"
    if "offering" in lower:
        return "PUBLIC_OFFERING"
    return "OTHER_EQUITY"


def review_closure(document, finding_id, closing_date, deal_label,
                   reviewer_confirmed=False, as_of=None):
    """Creates a reviewable evidence assertion; never verifies from filing index."""
    cutoff = _date(as_of) if as_of is not None else datetime.now(timezone.utc).date()
    filed = _date(document.get("filed"))
    closed = _date(closing_date)
    if not reviewer_confirmed:
        raise ValueError("Reviewer must explicitly confirm reading the SEC filing and matched transaction.")
    if not (cutoff and filed and closed and closed <= filed <= cutoff
            and 0 <= (filed - closed).days <= 120):
        raise ValueError("Closure date must be real, within 120 days before SEC filing and not after research date")
    label = str(deal_label or "").strip()
    if not (4 <= len(label) <= 120 and not re.search(r"[\x00-\x1f]", label)):
        raise ValueError("Enter a specific transaction/deal label (4–120 characters)")
    choices = {c["id"]: c for c in candidates(document)}
    claim = choices.get(str(finding_id))
    if not claim:
        raise ValueError("Closing claim is not present in fetched SEC document")
    if not _closing_date_in_text(claim["excerpt"], closed):
        raise ValueError("Declared closing date is not explicitly stated in selected SEC clause")
    if document.get("source_kind") != "SEC EDGAR 8-K DOCUMENT" or not re.fullmatch(
            r"[a-f0-9]{64}", str(document.get("document_sha256") or "")):
        raise ValueError("Missing SEC retrieval proof; manually copied text cannot verify closing")
    dtype = _type_of(claim["excerpt"])
    if dtype is None:
        raise ValueError("ATM program is not a completed offering event")
    cash = _amounts(claim["excerpt"])
    return {
        "ticker": clean_ticker(document["ticker"]), "cik": cik10(document["cik"]),
        "company": document.get("company", ""), "as_of": cutoff.isoformat(),
        "deal_label": label, "closing_date": closed.isoformat(), "financing_type": dtype,
        "status": "VERIFIED CLOSED — REVIEWER CONFIRMED SEC 8-K CLAIM",
        "reviewed_by_user": True, "reviewed_at_utc": utc_now(),
        "source_url": document["source_url"], "source_form": document["form"],
        "source_filed": document["filed"], "source_accession": document["accession"],
        "document_sha256": document["document_sha256"],
        "evidence_excerpt": claim["excerpt"], "claim_id": claim["id"],
        **cash,
        "amount_note": "Gross/net proceeds are quoted only if specifically disclosed in evidence clause.",
        "atm_status": "NOT VERIFIED — closed transaction does not rule out active ATM or future dilution",
        "ordinal_status": "NOT VERIFIED — multiple post-Phase 3 financings require separate evidence and staging",
        "attestation": "Human reviewed SEC 8-K excerpt, not independent auditor validation",
        "eligible_for_automatic_entry": False,
        "entry_blockers": [
            "Link this event to the required post-Phase 3 financing stage",
            "Confirm no material unresolved active ATM/near-term issuance",
            "Verify Phase 3 readout, regulatory readiness and trading setup separately",
        ],
    }


def _db(db_path=DEFAULT_DB):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=25)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=25000")
    con.execute("""CREATE TABLE IF NOT EXISTS sec_financing_closure_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL, cik TEXT NOT NULL, deal_label TEXT NOT NULL,
        closing_date TEXT NOT NULL, event_sha TEXT NOT NULL,
        created_utc TEXT NOT NULL, payload_json TEXT NOT NULL,
        UNIQUE(ticker,cik,deal_label,closing_date,event_sha)
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS financing_by_ticker ON sec_financing_closure_history(ticker,id)")
    return con


def save_review(event, db_path=DEFAULT_DB):
    if event.get("status") != "VERIFIED CLOSED — REVIEWER CONFIRMED SEC 8-K CLAIM":
        raise ValueError("Only source-reconciled closing events can be stored as reviewed")
    if not event.get("reviewed_by_user") or not event.get("document_sha256"):
        raise ValueError("Evidence/reviewer confirmation is missing")
    payload = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    with _db(db_path) as db:
        db.execute("""INSERT OR IGNORE INTO sec_financing_closure_history
            (ticker,cik,deal_label,closing_date,event_sha,created_utc,payload_json)
            VALUES(?,?,?,?,?,?,?)""",
            (event["ticker"], event["cik"], event["deal_label"], event["closing_date"],
             digest, utc_now(), payload))
        row = db.execute("""SELECT id FROM sec_financing_closure_history
             WHERE ticker=? AND cik=? AND deal_label=? AND closing_date=? AND event_sha=?""",
             (event["ticker"], event["cik"], event["deal_label"],
              event["closing_date"], digest)).fetchone()
        return int(row["id"])


def read_reviews(ticker=None, db_path=DEFAULT_DB):
    path = Path(db_path)
    if not path.exists():
        return []
    with _db(db_path) as db:
        if ticker is None:
            rows = db.execute("SELECT * FROM sec_financing_closure_history ORDER BY id DESC").fetchall()
        else:
            rows = db.execute("SELECT * FROM sec_financing_closure_history WHERE ticker=? ORDER BY id DESC",
                              (clean_ticker(ticker),)).fetchall()
        return [{**dict(r), "event": json.loads(r["payload_json"])} for r in rows]


def financing_gate(ticker, required_deal_label=None, as_of=None, db_path=DEFAULT_DB, cik=None):
    """Step 6-ready conservative gate. Only named matching deal closes qualify."""
    cutoff = _date(as_of) if as_of is not None else datetime.now(timezone.utc).date()
    if cutoff is None:
        raise ValueError("Invalid as-of date")
    if cik is None:
        return {"status": "REVIEW — CURRENT ISSUER CIK REQUIRED",
                "closure_verified": False, "entry_ready": False,
                "reviewed_events": 0}
    verified_cik = cik10(cik)
    rows = read_reviews(ticker, db_path)
    eligible = [r["event"] for r in rows if
                r["event"].get("cik") == verified_cik and
                _date(r["event"].get("source_filed")) and
                _date(r["event"]["source_filed"]) <= cutoff and
                _date(r["event"].get("closing_date")) and
                _date(r["event"]["closing_date"]) <= cutoff]
    # A named event can only pass once the *specific deal* is matched.
    if not str(required_deal_label or "").strip():
        return {"status": "REVIEW — REQUIRED FINANCING NOT IDENTIFIED",
                "closure_verified": False, "entry_ready": False,
                "reviewed_events": len(eligible)}
    matches = [e for e in eligible if e["deal_label"].casefold() ==
               str(required_deal_label).strip().casefold()]
    if not matches:
        return {"status": "PENDING — NO REVIEWED SEC CLOSING FOR NAMED FINANCING",
                "closure_verified": False, "entry_ready": False,
                "reviewed_events": len(eligible)}
    event = sorted(matches, key=lambda e: (e["source_filed"], e["reviewed_at_utc"]))[-1]
    return {"status": "CLOSED EVIDENCE VERIFIED — ENTRY RISK REVIEW STILL REQUIRED",
            "closure_verified": True, "entry_ready": False,
            "closing_date": event["closing_date"], "source_url": event["source_url"],
            "deal_label": event["deal_label"], "gross_proceeds_usd": event["gross_proceeds_usd"],
            "net_proceeds_usd": event["net_proceeds_usd"],
            "unresolved_risks": event["entry_blockers"], "reviewed_events": len(eligible)}
