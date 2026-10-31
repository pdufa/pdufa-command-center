"""Conservative FDA-source reconciliation for the separate Phase 3 library.

An approval notification must explicitly name the NCT, drug and indication;
Drugs@FDA separately corroborates the application and sponsor. Unresolved or
ambiguous matches remain PENDING. Clinical endpoints never establish an FDA
decision. Only new library source/checkpoint tables are written here.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from sqlalchemy import text

LOG = logging.getLogger(__name__)
INDEX = "https://www.fda.gov/drugs/resources-information-approved-drugs/oncology-cancerhematologic-malignancies-approval-notifications"
FDA_API = "https://api.fda.gov/drug/drugsfda.json"
MAX_BYTES = 4 * 1024 * 1024
LOCK_KEY = 72403507132
_lock = threading.Lock()
_started = set()
_startup_lock = threading.Lock()
_NCTS = re.compile(r"\bNCT[0-9]{8}\b")
_MONTHS = {name.lower(): i for i, name in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}
_STOP = {"inc", "incorporated", "ltd", "limited", "llc", "corporation", "corp", "company", "co", "pharmaceuticals", "pharmaceutical", "research", "laboratories", "laboratory", "the", "and", "of", "for", "patients", "with", "adult", "adults", "disease", "study", "therapy", "treatment", "advanced", "metastatic", "recurrent"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def initialize(engine):
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS phase3_regulatory_sources (
            url TEXT PRIMARY KEY,kind TEXT NOT NULL,state TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
            document TEXT,sha256 TEXT,retrieved_at TEXT,published_at TEXT,last_error_code TEXT,
            reconciled INTEGER NOT NULL DEFAULT 0,next_retry_at TEXT,last_checked_at TEXT)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS phase3_regulatory_history (
            event_id TEXT PRIMARY KEY,occurred_at TEXT NOT NULL,kind TEXT NOT NULL,document TEXT NOT NULL)"""))
        c.execute(text("CREATE INDEX IF NOT EXISTS phase3_regulatory_pending ON phase3_regulatory_sources(state,next_retry_at)"))
        c.execute(text("""INSERT INTO phase3_regulatory_sources(url,kind,state) VALUES(:url,'INDEX','PENDING')
            ON CONFLICT(url) DO NOTHING"""), {"url": INDEX})


def _history(engine, kind, document):
    with engine.begin() as c:
        c.execute(text("INSERT INTO phase3_regulatory_history(event_id,occurred_at,kind,document) VALUES(:id,:at,:kind,:doc)"),
                  {"id": str(uuid.uuid4()), "at": stamp(), "kind": kind, "doc": canonical(document)})


class _HTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.parts, self.paragraphs = [], [], []
        self._skip = 0
        self._paragraph = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        if tag == "p":
            self._paragraph = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = max(0, self._skip - 1)
        if tag == "p" and self._paragraph is not None:
            self.paragraphs.append(" ".join(" ".join(self._paragraph).split()))
            self._paragraph = None

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)
            if self._paragraph is not None:
                self._paragraph.append(data)


def _document(raw, url):
    parser = _HTML()
    parser.feed(raw)
    links = sorted(set(urljoin(url, value).split("#", 1)[0] for value in parser.links))
    body = " ".join(" ".join(parser.parts).split())
    # Literal link destinations are retained as source evidence, not inferred text.
    return {"body": body, "paragraphs": parser.paragraphs, "links": links,
            "raw_sha256": digest(raw), "retrieved_at": stamp()}


def _allowed_index(url):
    parsed = urlsplit(url)
    original = urlsplit(INDEX)
    return parsed.scheme == "https" and parsed.hostname == "www.fda.gov" and parsed.path == original.path


def _allowed_article(url):
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.hostname == "www.fda.gov" and parsed.path.startswith("/drugs/resources-information-approved-drugs/") and not _allowed_index(url)


def fetch(url, *, json_response=False):
    host = urlsplit(url).hostname or ""
    if not url.startswith("https://") or host not in ("www.fda.gov", "api.fda.gov", "www.accessdata.fda.gov"):
        raise ValueError("REGULATORY_SOURCE_HOST_NOT_ALLOWED")
    last = "SOURCE_UNAVAILABLE"
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "PDUFA-Phase3-Library/1.0", "Accept": "application/json" if json_response else "text/html"})
            with urlopen(request, timeout=20) as response:
                final_host = urlsplit(response.geturl()).hostname or ""
                if final_host not in ("www.fda.gov", "api.fda.gov", "www.accessdata.fda.gov"):
                    raise ValueError("REGULATORY_REDIRECT_HOST_NOT_ALLOWED")
                if response.status != 200:
                    raise ValueError("SOURCE_HTTP_STATUS")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("REGULATORY_SOURCE_TOO_LARGE")
            body = raw.decode("utf-8")
            if json_response:
                document = json.loads(body, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("SOURCE_INVALID_JSON")))
                if not isinstance(document, dict) or not isinstance(document.get("results"), list):
                    raise ValueError("SOURCE_INVALID_JSON")
                return body, document
            if "<html" not in body.lower() and "<body" not in body.lower():
                raise ValueError("SOURCE_NOT_HTML")
            return body, _document(body, url)
        except HTTPError as exc:
            last = "HTTP_" + str(exc.code)
            if exc.code in (400, 401, 403, 404):
                break
        except (URLError, TimeoutError, OSError, UnicodeError):
            last = "SOURCE_UNAVAILABLE"
        if attempt < 2:
            time.sleep(0.3 * (attempt + 1))
    raise ValueError(last)


def _tokens(value):
    mapped = re.sub(r"\b(?:neoplasms?|carcinomas?|malignanc(?:y|ies))\b", "cancer", value.lower())
    return {part for part in re.findall(r"[a-z0-9]+", mapped) if len(part) >= 3 and part not in _STOP}


def _literal(value, body):
    return bool(value and re.search(r"(?<![a-z0-9])" + re.escape(value.lower()) + r"(?![a-z0-9])", body.lower()))


def _announcement(document):
    # Only an explicit affirmative FDA approval statement can enter this adapter.
    for paragraph in document.get("paragraphs", []):
        if not re.search(r"(?:Food and Drug Administration|\bFDA\b).{0,160}\b(?:approved|granted accelerated approval)\b", paragraph, re.I):
            continue
        if re.search(r"\b(?:not approved|not yet approved|did not approve|has not approved)\b", paragraph, re.I):
            continue
        date = re.search(r"\bOn\s+(" + "|".join(_MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})", paragraph, re.I)
        indication = re.search(r"\b(?:approved|granted accelerated approval)\b.{0,700}?\bfor\s+(.+?)(?:\.\s|\.$|$)", paragraph, re.I)
        if not date or not indication:
            continue
        try:
            day = datetime(int(date[3]), _MONTHS[date[1].lower()], int(date[2]), tzinfo=timezone.utc)
        except ValueError:
            continue
        # The announcement's decision date is explicit. When publication metadata
        # is unavailable, retrieval is the conservative evidence-availability
        # upper bound; never backdate evidence availability to an inferred date.
        return {"decision_date": day.date().isoformat(), "published_at": document["retrieved_at"],
                "indication": indication[1].strip(), "paragraph": paragraph}
    return None


def _catalog_trial(engine, nct):
    with engine.connect() as c:
        row = c.execute(text("SELECT nct_id,company,drug,indication FROM phase3_trials WHERE nct_id=:nct"), {"nct": nct}).mappings().first()
        if row is None:
            return None
        drugs = list(c.execute(text("SELECT d.name FROM phase3_drugs d JOIN phase3_trial_drugs t ON t.drug_id=d.drug_id WHERE t.nct_id=:nct"), {"nct": nct}).scalars())
    return {**dict(row), "drugs": drugs}


def _lookup_application(drug, article, trial):
    # Product-name equality alone is insufficient: the article must independently
    # name this exact trial, and the company/indication checks below must pass.
    query = 'products.active_ingredients.name:"' + drug.replace('"', '') + '"'
    url = FDA_API + "?" + urlencode({"search": query, "limit": 100})
    try:
        body, response = fetch(url, json_response=True)
    except ValueError as exc:
        if str(exc) != "HTTP_404":
            raise
        # openFDA returns HTTP 404 for a query with zero matching applications.
        # No response is evidence of a verified FDA application or decision;
        # do not discard the entire article or retry it indefinitely for this.
        return None, None
    candidates = []
    for application in response["results"]:
        number, sponsor = application.get("application_number"), application.get("sponsor_name")
        if not isinstance(number, str) or not re.fullmatch(r"(?:NDA|ANDA|BLA)\d{6}", number) or not isinstance(sponsor, str):
            continue
        if not (_tokens(sponsor) & _tokens(trial["company"])):
            continue
        products = application.get("products", [])
        matches = [p for p in products if any(str(a.get("name", "")).casefold() == drug.casefold() for a in p.get("active_ingredients", []))]
        if not matches:
            continue
        brand_explicit = any(_literal(str(p.get("brand_name", "")), article["body"]) for p in matches)
        numbered = number.lower() in article["body"].lower() or number[-6:] in " ".join(article.get("links", []))
        if not brand_explicit and not numbered:
            continue
        candidates.append((application, numbered))
    explicit = [entry for entry in candidates if entry[1]]
    candidates = explicit or candidates
    unique = {entry[0]["application_number"]: entry[0] for entry in candidates}
    if len(unique) != 1:
        return None, None
    selected = next(iter(unique.values()))
    source = {"url": url, "sha256": digest(body), "retrieved_at": stamp(), "verification_status": "VERIFIED", "document": body}
    return selected, source


def reconcile_document(engine, url, document):
    """Return actual counts; never manufacture a decision for an unmatched trial."""
    announcement = _announcement(document)
    ncts = sorted(set(_NCTS.findall(document["body"])))
    if not announcement or not ncts:
        return {"reconciled": 0, "deferred": 0, "reason": "NO_EXPLICIT_TRIAL_APPROVAL_SCOPE"}
    from .phase3_catalog import record_regulatory_evidence
    reconciled, deferred, reasons = 0, 0, set()
    for nct in ncts:
        trial = _catalog_trial(engine, nct)
        if trial is None:
            deferred += 1
            continue
        drugs = [drug for drug in trial["drugs"] if _literal(drug, document["body"])]
        if not drugs or not (_tokens(trial["indication"]) & _tokens(announcement["indication"])):
            reasons.add("DRUG_OR_INDICATION_NOT_RECONCILED")
            continue
        applications = []
        for drug in drugs:
            application, app_source = _lookup_application(drug, document, trial)
            if application:
                applications.append((drug, application, app_source))
        # A combination regimen can have multiple drugs; each relationship gets
        # its own explicit scoped application record, never a one-to-one guess.
        if not applications:
            reasons.add("APPLICATION_NOT_INDEPENDENTLY_RECONCILED")
            continue
        for drug, application, app_source in applications:
            scope = {"application": application["application_number"], "drug": drug, "indication": announcement["indication"]}
            scoped = {"application_id": application["application_number"] + ":" + digest(canonical(scope))[:20],
                      "application_number": application["application_number"], "sponsor": application["sponsor_name"],
                      "drug": drug, "indication": announcement["indication"]}
            body = document["body"]
            source = {"url": url, "sha256": digest(body), "retrieved_at": document["retrieved_at"],
                      "verification_status": "VERIFIED", "publisher_kind": "FDA", "document": body}
            record_regulatory_evidence(engine, application=scoped, decision="APPROVED", nct_ids=[nct],
                                       source=source, application_source=app_source,
                                       published_at=announcement["published_at"], decision_date=announcement["decision_date"], submission_status="APPROVED")
            reconciled += 1
    return {"reconciled": reconciled, "deferred": deferred, "reason": ",".join(sorted(reasons)) or None}


@contextmanager
def _exclusive(engine):
    if not _lock.acquire(blocking=False):
        yield False
        return
    connection = None
    locked = False
    try:
        if engine.dialect.name == "postgresql":
            connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
            locked = bool(connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}).scalar())
            if not locked:
                yield False
                return
        yield True
    finally:
        if connection is not None:
            if locked:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
            connection.close()
        _lock.release()


def sync(engine, max_pages=3):
    if not isinstance(max_pages, int) or not 1 <= max_pages <= 10:
        raise ValueError("Invalid regulatory batch size")
    initialize(engine)
    with _exclusive(engine) as acquired:
        if not acquired:
            return status(engine)
        now = stamp()
        old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with engine.begin() as c:
            # Revisit the official index daily to discover new announcements.
            c.execute(text("UPDATE phase3_regulatory_sources SET state='PENDING' WHERE kind='INDEX' AND state='COMPLETE' AND last_checked_at<:old"), {"old": old})
            rows = c.execute(text("""SELECT * FROM phase3_regulatory_sources
                WHERE state IN ('PENDING','RETRY','DEFERRED') AND (next_retry_at IS NULL OR next_retry_at<=:now)
                ORDER BY CASE kind WHEN 'INDEX' THEN 0 ELSE 1 END,last_checked_at,url LIMIT :limit"""), {"now": now, "limit": max_pages}).mappings().all()
        for source in rows:
            try:
                document = json.loads(source["document"]) if source["document"] else None
                if document is None or source["kind"] == "INDEX":
                    _, document = fetch(source["url"])
                if source["kind"] == "INDEX":
                    with engine.begin() as c:
                        for link in document["links"]:
                            if not (_allowed_article(link) or _allowed_index(link)) or link == source["url"]:
                                continue
                            c.execute(text("INSERT INTO phase3_regulatory_sources(url,kind,state) VALUES(:url,:kind,'PENDING') ON CONFLICT(url) DO NOTHING"),
                                      {"url": link, "kind": "INDEX" if _allowed_index(link) else "ARTICLE"})
                    observed = {"reconciled": 0, "deferred": 0, "reason": None}
                else:
                    observed = reconcile_document(engine, source["url"], document)
                state = "DEFERRED" if observed["deferred"] else "COMPLETE"
                next_retry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat() if state == "DEFERRED" else None
                with engine.begin() as c:
                    c.execute(text("""UPDATE phase3_regulatory_sources SET state=:state,attempts=attempts+1,document=:doc,
                        sha256=:sha,retrieved_at=:retrieved,last_checked_at=:now,last_error_code=:reason,reconciled=:count,next_retry_at=:retry WHERE url=:url"""),
                              {"state": state, "doc": canonical(document), "sha": document["raw_sha256"], "retrieved": document["retrieved_at"],
                               "now": stamp(), "reason": observed["reason"], "count": observed["reconciled"], "retry": next_retry, "url": source["url"]})
                _history(engine, "SOURCE_CHECKED", {"url": source["url"], "raw_sha256": document["raw_sha256"], **observed})
            except Exception as exc:
                # Keep failure logs visible without source bodies or credentials.
                code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[A-Z0-9_,]{1,120}", str(exc)) else type(exc).__name__
                # Log a stable public-source fingerprint, not raw URLs or query
                # strings. The persisted source registry retains the full URL.
                kind = source["kind"] if source["kind"] in {"INDEX", "ARTICLE"} else "UNKNOWN"
                LOG.warning(
                    "PDUFA_PHASE3_REGULATORY_SOURCE_FAILED code=%s source_kind=%s source_sha256=%s",
                    code, kind, digest(source["url"]),
                )
                with engine.begin() as c:
                    c.execute(text("""UPDATE phase3_regulatory_sources SET state='RETRY',attempts=attempts+1,
                        last_error_code=:error,next_retry_at=:retry,last_checked_at=:at WHERE url=:url"""),
                              {"error": code, "retry": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(), "at": stamp(), "url": source["url"]})
                _history(engine, "SOURCE_FAILED", {"url": source["url"], "error_code": code})
        result = status(engine)
        LOG.info("PDUFA_PHASE3_REGULATORY_PROGRESS %s", canonical(result))
        return result


def status(engine):
    with engine.connect() as c:
        totals = dict(c.execute(text("SELECT state,COUNT(*) FROM phase3_regulatory_sources GROUP BY state")).all())
        checked = c.execute(text("SELECT MAX(last_checked_at) FROM phase3_regulatory_sources WHERE retrieved_at IS NOT NULL")).scalar()
        latest_error = c.execute(text("SELECT last_error_code FROM phase3_regulatory_sources WHERE state='RETRY' ORDER BY last_checked_at DESC LIMIT 1")).scalar()
        reconciled = c.execute(text("SELECT COALESCE(SUM(reconciled),0) FROM phase3_regulatory_sources")).scalar_one()
        pending = c.execute(text("SELECT COUNT(*) FROM phase3_regulatory_sources WHERE state IN ('PENDING','RETRY','DEFERRED') AND (next_retry_at IS NULL OR next_retry_at<=:now)"), {"now": stamp()}).scalar_one()
        automatic = c.execute(text("SELECT MAX(occurred_at) FROM phase3_regulatory_history WHERE kind='AUTOMATIC_EXECUTION_STARTED'")).scalar()
    return {"source": "FDA approval notifications + Drugs@FDA", "status": "ERROR" if latest_error else "VERIFIED" if checked else "PENDING",
            "last_checked_at": checked, "last_error_code": latest_error, "sources": totals,
            "ready_sources": pending, "reconciled_trial_application_links": reconciled,
            "scheduling": {"mechanism": "independent_in_process_worker_with_daily_index_discovery", "last_automatic_execution_at": automatic,
                           "automatic_start_observed": bool(automatic), "daily_recurrence_verified": False},
            "coverage": "Official FDA oncology approval notifications corroborated with Drugs@FDA; other biologic records require explicit source reconciliation",
            "sec": {"status": "CONFIGURED_NOT_EXECUTED" if os.environ.get("PDUFA_SEC_USER_AGENT") else "USER_AGENT_CONFIGURATION_REQUIRED"},
            "official_sponsor": {"status": "EXPLICIT_PRIMARY_EVIDENCE_REQUIRED"},
            "unresolved_decision_policy": "PENDING; no clinical-result or elapsed-date inference"}


def start(engine):
    """Separate daily worker; an index failure cannot stop CT.gov ingestion."""
    if engine.dialect.name != "postgresql":
        return
    initialize(engine)
    key = id(engine)
    with _startup_lock:
        if key in _started:
            return
        _started.add(key)
    def work():
        _history(engine, "AUTOMATIC_EXECUTION_STARTED", {"mechanism": "independent_in_process_worker_with_daily_index_discovery"})
        while True:
            try:
                result = sync(engine, max_pages=3)
                if result["ready_sources"]:
                    time.sleep(1)
                    continue
            except Exception as exc:
                LOG.error("PDUFA_PHASE3_REGULATORY_WORKER_FAILED type=%s", type(exc).__name__)
            time.sleep(60)
    threading.Thread(target=work, name="phase3-regulatory", daemon=True).start()
