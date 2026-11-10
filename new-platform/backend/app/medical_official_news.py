"""Fail-closed, source-first FDA news watcher for exact FOCUS application cycles.

Only official FDA RSS publications are candidates. A unique *literal drug name*
in an FDA-hosted headline establishes a research lead, not a verified FDA
application identity, decision, PDUFA-date change or calibrated prediction.
This schedules the existing source-only Analyze Now worker, which preserves
immutable revisions and abstentions. Other media/sponsor articles never cause
automatic runs. The first scan establishes a baseline without back-firing.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

LOG = logging.getLogger(__name__)
OFFICIAL_FEED = "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml"
WATCH_ID = "official-fda-rss-v1"
_MAX_XML = 800_000


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def official_link(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in ("www.fda.gov", "fda.gov") and not (
            parsed.username or parsed.password or parsed.port or parsed.fragment)
    except ValueError:
        return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def canonical_fda_article(url: str):
    """FDA's own RSS XML uses http links; upgrade exact FDA hosts to HTTPS."""
    try:
        parsed = urlparse(url)
        if (parsed.scheme not in ("http", "https") or
            parsed.hostname not in ("www.fda.gov", "fda.gov") or
            parsed.username or parsed.password or parsed.port):
            return None
        return "https://www.fda.gov" + (parsed.path or "/") + (("?" + parsed.query) if parsed.query else "")
    except ValueError:
        return None


def download_official_feed():
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(OFFICIAL_FEED, headers={
        "Accept": "application/rss+xml, application/xml, text/xml",
        "User-Agent": "PDUFACommandCenter-NewsMonitor/1.0 (research-only)"
    })
    with opener.open(request, timeout=12) as response:
        if response.status != 200 or not official_link(response.url):
            raise ValueError("FDA official feed unavailable")
        data = response.read(_MAX_XML + 1)
    if len(data) > _MAX_XML:
        raise ValueError("FDA feed too large")
    return data


def parse_fda_feed(content: bytes):
    """Authenticated by fixed FDA HTTPS endpoint + explicit final-host check upstream.

    No article text is interpreted as execution instructions. A recorded
    article is NOT a verified FDA outcome or independently assessed evidence.
    """
    if not content or len(content) > _MAX_XML:
        raise ValueError("FDA feed missing or oversized")
    root = ET.fromstring(content)
    if root.tag.lower() != "rss":
        raise ValueError("Expected FDA RSS")
    items = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        raw_date = (item.findtext("pubDate") or "").strip()
        canonical = canonical_fda_article(link)
        if not title or len(title) > 320 or not canonical or not raw_date:
            continue
        try:
            published = parsedate_to_datetime(raw_date)
            if published.tzinfo is None:
                continue
            published = published.astimezone(timezone.utc)
            if published > datetime.now(timezone.utc) + timedelta(days=2):
                continue
        except (ValueError, TypeError):
            continue
        items.append({"title": title, "url": canonical, "publishedAt": published.isoformat()})
    if not items:
        raise ValueError("FDA RSS contains no valid official articles")
    return items[:150]


def exact_drug_alias(drug):
    if not isinstance(drug, str):
        return None
    alias = re.split(r"\s*[\(+/]", drug, maxsplit=1)[0].strip().casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", alias).strip()
    if len(normalized) < 6:
        return None
    return normalized


def unique_cycle_match(title, snapshot):
    """Require one and only one distinct application cycle for a full drug alias."""
    norm = " " + re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip() + " "
    cycles = {}
    for row in snapshot.get("records", []):
        nct = row.get("nct")
        if not isinstance(nct, str) or not re.fullmatch(r"NCT\d{8}", nct):
            continue
        for cycle in row.get("candidateApplications", []):
            if not isinstance(cycle, dict):
                continue
            alias = exact_drug_alias(cycle.get("drug"))
            cycle_id = cycle.get("cycleId")
            if alias and isinstance(cycle_id, str) and (" " + alias + " ") in norm:
                entry = cycles.setdefault(cycle_id, {"cycleId":cycle_id,"drug":cycle["drug"],
                    "ticker":cycle.get("ticker"),"ncts":set()})
                entry["ncts"].add(nct)
    if len(cycles) != 1:
        return None
    only = next(iter(cycles.values()))
    return {**only, "ncts":sorted(only["ncts"])}


def initialize(engine):
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_official_news_watch (
            watch_id TEXT PRIMARY KEY, baselined_at TEXT NOT NULL,
            last_checked_at TEXT NOT NULL, last_error TEXT)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_official_news_events (
            event_key TEXT PRIMARY KEY, article_url TEXT NOT NULL,
            cycle_id TEXT NOT NULL, nct_id TEXT NOT NULL,
            headline TEXT NOT NULL, published_at TEXT NOT NULL,
            observed_at TEXT NOT NULL, status TEXT NOT NULL,
            research_run_id TEXT, last_attempt_at TEXT)"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_official_news_by_nct
            ON medical_official_news_events(nct_id,observed_at)"""))


def check_once(engine, *, fetch=None):
    """Append exactly one event per (FDA article, exact cycle, exact NCT).

    On durable post-baseline events, automatically request a NEW existing
    source-only research run if that NCT is eligible and no run is active.
    A change never overwrites earlier revisions or releases probabilities.
    """
    from . import medical_continuous as core
    from .medical_on_demand import eligible_for_analysis, start_now

    if engine.dialect.name != "postgresql":
        raise RuntimeError("Official news automation requires durable PostgreSQL")
    content = fetch() if fetch else download_official_feed()
    items = parse_fda_feed(content)
    path = core.APPLICATIONS
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("schemaVersion") != 1 or not isinstance(snapshot.get("records"), list):
        raise ValueError("Exact application crosswalk unavailable")
    tally = {"articlesChecked":len(items),"matchedCycles":0,"baselined":0,
             "queued":0,"deferred":0,"ambiguousOrUnmatched":0}
    at = utcnow()
    with engine.begin() as c:
        start = c.execute(text("SELECT baselined_at FROM medical_official_news_watch WHERE watch_id=:id"),
                          {"id":WATCH_ID}).scalar()
        if start is None:
            c.execute(text("""INSERT INTO medical_official_news_watch
                (watch_id,baselined_at,last_checked_at,last_error)
                VALUES(:id,:now,:now,NULL) ON CONFLICT(watch_id) DO NOTHING"""),
                {"id":WATCH_ID,"now":at})
            start = None
        else:
            c.execute(text("""UPDATE medical_official_news_watch
                SET last_checked_at=:now,last_error=NULL WHERE watch_id=:id"""),
                {"now":at,"id":WATCH_ID})
    for item in items:
        cycle = unique_cycle_match(item["title"],snapshot)
        if not cycle:
            tally["ambiguousOrUnmatched"]+=1
            continue
        tally["matchedCycles"]+=1
        for nct in cycle["ncts"]:
            if nct not in core.roster():
                tally["deferred"]+=1
                continue
            published = datetime.fromisoformat(item["publishedAt"])
            # On first observation, do not replay old articles as new triggers.
            state = ("BASELINED" if start is None or published <= datetime.fromisoformat(start)
                     else "AWAITING_REASSESSMENT")
            key = hashlib.sha256((item["url"]+"|"+cycle["cycleId"]+"|"+nct).encode()).hexdigest()
            with engine.begin() as c:
                c.execute(text("""INSERT INTO medical_official_news_events
                    (event_key,article_url,cycle_id,nct_id,headline,published_at,observed_at,status)
                    VALUES(:key,:url,:cycle,:nct,:headline,:pub,:now,:state)
                    ON CONFLICT(event_key) DO NOTHING"""),
                    {"key":key,"url":item["url"],"cycle":cycle["cycleId"],"nct":nct,
                     "headline":item["title"],"pub":item["publishedAt"],"now":at,"state":state})
                prior = c.execute(text("SELECT status,last_attempt_at FROM medical_official_news_events WHERE event_key=:key"),
                                  {"key":key}).mappings().first()
            if not prior or prior["status"] == "BASELINED":
                tally["baselined"]+=1
                continue
            if prior["status"] == "REASSESSMENT_REQUESTED":
                continue
            if not eligible_for_analysis(nct):
                tally["deferred"]+=1
                continue
            with engine.begin() as c:
                active = c.execute(text("""SELECT run_id FROM medical_continuous_runs
                    WHERE nct_id=:nct AND status IN ('PENDING','RUNNING') LIMIT 1"""),
                    {"nct":nct}).scalar()
            if active:
                tally["deferred"]+=1
                continue
            # Avoid simultaneous servers scheduling the same event. Expired
            # leases permit crash recovery; idempotent UUID prevents duplicate runs.
            with engine.begin() as c:
                claimed = c.execute(text("""UPDATE medical_official_news_events
                    SET status='CLAIMED',last_attempt_at=:now
                    WHERE event_key=:key AND (
                        status='AWAITING_REASSESSMENT'
                        OR (status='CLAIMED' AND last_attempt_at<:expiry))
                    RETURNING event_key"""),
                    {"key":key,"now":at,
                     "expiry":(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()}).first()
            if not claimed:
                tally["deferred"]+=1
                continue
            try:
                request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "fda-news|"+key))
                started = start_now(engine,nct,request_id,trigger="OFFICIAL_FDA_NEWS_CHANGE")
                with engine.begin() as c:
                    c.execute(text("""UPDATE medical_official_news_events
                        SET status='REASSESSMENT_REQUESTED',research_run_id=:run
                        WHERE event_key=:key AND status='CLAIMED'"""),
                        {"run":started["runId"],"key":key})
                tally["queued"]+=1
            except Exception as exc:
                with engine.begin() as c:
                    c.execute(text("""UPDATE medical_official_news_events
                        SET status='AWAITING_REASSESSMENT'
                        WHERE event_key=:key AND status='CLAIMED'"""),{"key":key})
                tally["deferred"]+=1
                LOG.warning("Official FDA source evidence research deferred nct=%s error_type=%s",
                            nct,type(exc).__name__)
    return tally


def status(engine):
    with engine.connect() as c:
        watch=c.execute(text("""SELECT baselined_at,last_checked_at,last_error
            FROM medical_official_news_watch WHERE watch_id=:id"""),{"id":WATCH_ID}).mappings().first()
        rows=c.execute(text("""SELECT status,COUNT(*) AS total FROM medical_official_news_events
            GROUP BY status""")).mappings().all()
    return {"source":"OFFICIAL_FDA_RSS","watchEnabled":os.getenv("PDUFA_MEDICAL_AUTO_WATCH","").lower() in ("1","true","yes"),
        "baselineAt":watch["baselined_at"] if watch else None,
        "lastCheckedAt":watch["last_checked_at"] if watch else None,
        "statuses":{row["status"]:row["total"] for row in rows},
        "reassessmentType":"SOURCE_COLLECTION_ONLY",
        "modelDecision":"ABSTAIN","calibration":"NOT_VALIDATED",
        "note":"Official FDA article and unique exact drug-name match triggers source-only reevaluation. No FDA review-cycle adjudication or prediction probability is implied."}


def install_routes(app, engine_provider, require_key, require_storage):
    router=APIRouter(prefix="/api/news-automation", dependencies=[Depends(require_key),Depends(require_storage)])
    @router.get("/status")
    def read_status():
        try:
            return status(engine_provider())
        except Exception as exc:
            LOG.warning("Official FDA news automation status unavailable type=%s",type(exc).__name__)
            raise HTTPException(503,"Durable news automation status unavailable")
    app.include_router(router)
