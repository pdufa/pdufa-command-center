#!/usr/bin/env python3
import os, re, json, time, html
from pathlib import Path
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REGISTRY = DATA / "company_registry.csv"
CANDIDATES = DATA / "pdufa_candidates.csv"
EVENTS = DATA / "discovery_events.csv"
QUEUE = DATA / "discovery_backfill_queue.csv"
STATE = DATA / "discovery_run_state.json"

SEC_HEADERS = {
    "User-Agent": os.getenv(
        "SEC_USER_AGENT",
        "PDUFA Command Center pdufa-command-center@users.noreply.github.com"
    ),
    "Accept-Encoding": "gzip, deflate",
}
LOOKBACK_DAYS = max(1, int(os.getenv("DISCOVERY_LOOKBACK_DAYS", "10")))
CT_LIMIT = max(25, min(500, int(os.getenv("DISCOVERY_CT_LIMIT", "200"))))
SEC_DOCS_PER_COMPANY = max(1, min(10, int(os.getenv("DISCOVERY_SEC_DOCS_PER_COMPANY", "3"))))
PAUSE = max(0.05, float(os.getenv("DISCOVERY_SEC_PAUSE_SECONDS", "0.12")))

ELIGIBLE_SIC = {"2833","2834","2835","2836","8731","8734"}
SEC_FORMS = {"8-K","6-K","10-Q","10-K"}
EVENT_COLUMNS = [
    "discovery_key","discovered_at_utc","source_type","event_type","ticker","company","cik10",
    "drug","indication","nct_id","application_type","pdufa_date","source_date","source_url",
    "evidence","company_status","match_confidence","pipeline_status"
]
QUEUE_COLUMNS = [
    "discovery_key","ticker","company","cik10","event_type","drug","indication","nct_id",
    "application_type","pdufa_date","source_url","evidence","company_status",
    "match_confidence","backfill_status","first_seen_utc","last_seen_utc"
]

def now():
    return datetime.now(timezone.utc).isoformat()

def clean(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return re.sub(r"\s+", " ", str(v)).strip()

def norm_name(v):
    s = clean(v).lower()
    s = re.sub(r"[/\\]", " ", s)
    s = re.sub(r"\b(incorporated|inc|corp|corporation|company|co|plc|ltd|limited|holdings|holding|group|sa|se|nv|ag|de|llc)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def req(url, *, params=None, headers=None, timeout=30):
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(1 + attempt)
    raise RuntimeError(f"GET failed {url}: {last}")

def load_csv(path, cols=None):
    if path.exists():
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    return pd.DataFrame(columns=cols or [])

def write_csv(path, df):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def sec_ticker_map():
    data = req("https://www.sec.gov/files/company_tickers_exchange.json", headers=SEC_HEADERS).json()
    fields = data.get("fields", [])
    rows = data.get("data", [])
    frame = pd.DataFrame(rows, columns=fields)
    ren = {}
    for c in frame.columns:
        lc = c.lower()
        if lc == "cik":
            ren[c] = "cik10"
        elif lc == "name":
            ren[c] = "company"
        elif lc == "ticker":
            ren[c] = "ticker"
        elif lc == "exchange":
            ren[c] = "exchange"
    frame = frame.rename(columns=ren)
    for c in ["ticker","company","cik10","exchange"]:
        if c not in frame:
            frame[c] = ""
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["cik10"] = frame["cik10"].astype(str).str.replace(r"\D","",regex=True).str.zfill(10)
    frame["name_norm"] = frame["company"].map(norm_name)
    return frame[["ticker","company","cik10","exchange","name_norm"]].drop_duplicates("ticker")

def get_submission(cik10):
    cik10 = re.sub(r"\D","", clean(cik10)).zfill(10)
    if not cik10.strip("0"):
        return {}
    return req(f"https://data.sec.gov/submissions/CIK{cik10}.json", headers=SEC_HEADERS).json()

def qualify_sec_company(row, submission_cache):
    cik = clean(row.get("cik10"))
    if not cik:
        return None
    if cik not in submission_cache:
        try:
            submission_cache[cik] = get_submission(cik)
            time.sleep(PAUSE)
        except Exception:
            submission_cache[cik] = {}
    sub = submission_cache[cik]
    sic = clean(sub.get("sic"))
    if sic not in ELIGIBLE_SIC:
        return None
    return {
        "ticker": clean(row.get("ticker")).upper(),
        "company": clean(sub.get("name")) or clean(row.get("company")),
        "cik10": cik.zfill(10),
        "exchange": clean(row.get("exchange")),
        "sic": sic,
        "sic_description": clean(sub.get("sicDescription")),
        "status": "AUTO_ADDED_DISCOVERY",
    }

def match_sponsor(sponsor, registry, secmap):
    target = norm_name(sponsor)
    if not target:
        return None, 0.0
    # Existing registry exact / fuzzy.
    exact = registry[registry["name_norm"] == target]
    if not exact.empty:
        return exact.iloc[0].to_dict(), 1.0
    # SEC exact.
    exact = secmap[secmap["name_norm"] == target]
    if not exact.empty:
        return exact.iloc[0].to_dict(), 0.99
    # Fuzzy across SEC names; require a high threshold to auto-add.
    best = None
    score = 0.0
    target_tokens = set(target.split())
    for _, r in secmap.iterrows():
        candidate = clean(r.get("name_norm"))
        if not candidate:
            continue
        cand_tokens = set(candidate.split())
        if target_tokens and cand_tokens and not (target_tokens & cand_tokens):
            continue
        s = SequenceMatcher(None, target, candidate).ratio()
        if s > score:
            score = s
            best = r.to_dict()
    return best, score

def application_type(text):
    low = text.lower()
    if re.search(r"\bsbla\b|supplemental biologics license application", low):
        return "sBLA"
    if re.search(r"\bbla\b|biologics license application|biologic license application", low):
        return "BLA"
    if re.search(r"\bsnda\b|supplemental new drug application", low):
        return "sNDA"
    if re.search(r"\bnda\b|new drug application", low):
        return "NDA"
    return ""

def event_type(text):
    low = text.lower()
    if "pdufa" in low:
        return "PDUFA"
    if application_type(text):
        return "APPLICATION"
    if re.search(r"\bphase\s*3\b|\bphase iii\b|\bpivotal\b", low) and re.search(r"result|readout|topline|met (?:the )?primary|endpoint", low):
        return "PHASE3_RESULT"
    return ""

def extract_pdufa_date(text):
    # Conservative: date must appear close to the literal PDUFA phrase.
    m = re.search(
        r"(?is)pdufa.{0,180}?\b("
        r"January|February|March|April|May|June|July|August|September|October|November|December"
        r")\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(20\d{2})",
        text
    )
    if not m:
        return ""
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date().isoformat()
    except Exception:
        return ""

def strip_html(raw):
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()

def evidence_snippet(text):
    low = text.lower()
    positions = [p for p in [
        low.find("pdufa"), low.find("phase 3"), low.find("phase iii"),
        low.find("new drug application"), low.find("biologics license application")
    ] if p >= 0]
    if not positions:
        return clean(text[:500])
    p = min(positions)
    return clean(text[max(0,p-180):p+420])[:600]

registry = load_csv(REGISTRY)
for c in ["ticker","company","cik10","exchange","sic","sic_description","status"]:
    if c not in registry:
        registry[c] = ""
registry["ticker"] = registry["ticker"].astype(str).str.upper().str.strip()
registry["cik10"] = registry["cik10"].astype(str).str.replace(r"\D","",regex=True).str.zfill(10)
registry["name_norm"] = registry["company"].map(norm_name)
initial_registry_n = len(registry)
candidate_df = load_csv(CANDIDATES)
tracked_tickers = set(candidate_df.get("ticker", pd.Series(dtype=str)).astype(str).str.upper().str.strip())

old_events = load_csv(EVENTS, EVENT_COLUMNS)
old_queue = load_csv(QUEUE, QUEUE_COLUMNS)
secmap = sec_ticker_map()
submission_cache = {}
new_events = []
added_companies = []

def add_event(rec):
    key_basis = "|".join([
        clean(rec.get("source_type")), clean(rec.get("event_type")),
        clean(rec.get("ticker")).upper(), clean(rec.get("nct_id")),
        clean(rec.get("pdufa_date")), clean(rec.get("source_url"))
    ])
    rec["discovery_key"] = re.sub(r"[^A-Za-z0-9._|:/-]+", "_", key_basis)[:500]
    rec["discovered_at_utc"] = now()
    rec["pipeline_status"] = "ALREADY_TRACKED" if clean(rec.get("ticker")).upper() in tracked_tickers else "BACKFILL_REQUIRED"
    for c in EVENT_COLUMNS:
        rec.setdefault(c, "")
    new_events.append({c: clean(rec.get(c)) for c in EVENT_COLUMNS})

# 1) EVENT-FIRST: globally scan recent Phase 3 ClinicalTrials.gov records.
try:
    params = {
        "query.term": "AREA[Phase]PHASE3",
        "format": "json",
        "pageSize": min(100, CT_LIMIT),
        "sort": "LastUpdatePostDate:desc",
    }
    token = ""
    seen = 0
    while seen < CT_LIMIT:
        if token:
            params["pageToken"] = token
        payload = req("https://clinicaltrials.gov/api/v2/studies", params=params).json()
        studies = payload.get("studies", [])
        if not studies:
            break
        for st in studies:
            if seen >= CT_LIMIT:
                break
            seen += 1
            proto = st.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            sponsors = proto.get("sponsorCollaboratorsModule", {})
            design = proto.get("designModule", {})
            status = proto.get("statusModule", {})
            cond = proto.get("conditionsModule", {})
            arms = proto.get("armsInterventionsModule", {})
            phases = design.get("phases", []) or []
            if "PHASE3" not in phases:
                continue
            sponsor = clean((sponsors.get("leadSponsor") or {}).get("name"))
            sponsor_class = clean((sponsors.get("leadSponsor") or {}).get("class"))
            if sponsor_class.upper() != "INDUSTRY":
                continue
            match, score = match_sponsor(sponsor, registry, secmap)
            ticker = clean((match or {}).get("ticker")).upper()
            company = clean((match or {}).get("company")) or sponsor
            cik = clean((match or {}).get("cik10"))
            company_status = "IN_DB" if ticker and ticker in set(registry["ticker"]) else "REVIEW"
            if ticker and company_status != "IN_DB" and score >= 0.90:
                qualified = qualify_sec_company(match, submission_cache)
                if qualified:
                    registry = pd.concat([registry, pd.DataFrame([{**qualified, "name_norm": norm_name(qualified["company"])}])], ignore_index=True)
                    registry = registry.drop_duplicates("ticker", keep="first")
                    added_companies.append(qualified)
                    company_status = "AUTO_ADDED"
                    company = qualified["company"]
                    cik = qualified["cik10"]
            nct = clean(ident.get("nctId"))
            interventions = []
            for it in arms.get("interventions", []) or []:
                name = clean(it.get("name"))
                if name and name not in interventions:
                    interventions.append(name)
            conditions = [clean(x) for x in (cond.get("conditions", []) or []) if clean(x)]
            last_update = clean(((status.get("lastUpdatePostDateStruct") or {}).get("date")))
            source = f"https://clinicaltrials.gov/study/{nct}" if nct else "https://clinicaltrials.gov/"
            add_event({
                "source_type":"CLINICALTRIALS_GLOBAL",
                "event_type":"PHASE3_REGISTRY_UPDATE",
                "ticker":ticker,
                "company":company,
                "cik10":cik,
                "drug":" | ".join(interventions[:4]),
                "indication":" | ".join(conditions[:4]),
                "nct_id":nct,
                "source_date":last_update,
                "source_url":source,
                "evidence":f"Phase 3 industry-sponsored study; lead sponsor={sponsor}",
                "company_status":company_status,
                "match_confidence":f"{score:.3f}" if score else "",
            })
        token = clean(payload.get("nextPageToken"))
        if not token:
            break
except Exception as e:
    ct_error = f"{type(e).__name__}: {e}"
else:
    ct_error = ""

# 2) COMPANY EVENT SCAN: scan recent SEC filings for Phase 3 / NDA / BLA / PDUFA.
cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date()
for idx, r in registry.drop_duplicates("ticker").iterrows():
    ticker = clean(r.get("ticker")).upper()
    cik = clean(r.get("cik10")).zfill(10)
    if not ticker or not cik.strip("0"):
        continue
    try:
        sub = submission_cache.get(cik) or get_submission(cik)
        submission_cache[cik] = sub
        recent = pd.DataFrame((sub.get("filings", {}) or {}).get("recent", {}))
        if recent.empty:
            time.sleep(PAUSE)
            continue
        recent["filingDate_dt"] = pd.to_datetime(recent.get("filingDate"), errors="coerce")
        recent = recent[
            recent["form"].astype(str).isin(SEC_FORMS) &
            (recent["filingDate_dt"].dt.date >= cutoff)
        ].sort_values("filingDate_dt", ascending=False).head(SEC_DOCS_PER_COMPANY)
        for _, fr in recent.iterrows():
            acc = clean(fr.get("accessionNumber"))
            doc = clean(fr.get("primaryDocument"))
            if not acc or not doc:
                continue
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{doc}"
            try:
                raw = req(url, headers=SEC_HEADERS).text
                text = strip_html(raw)
            except Exception:
                continue
            et = event_type(text)
            if not et:
                continue
            pdate = extract_pdufa_date(text)
            add_event({
                "source_type":"SEC_COMPANY_SCAN",
                "event_type":et,
                "ticker":ticker,
                "company":clean(r.get("company")),
                "cik10":cik,
                "application_type":application_type(text),
                "pdufa_date":pdate,
                "source_date":clean(fr.get("filingDate")),
                "source_url":url,
                "evidence":evidence_snippet(text),
                "company_status":"IN_DB",
                "match_confidence":"1.000",
            })
        time.sleep(PAUSE)
    except Exception:
        continue

# Persist registry additions.
registry = registry.drop(columns=["name_norm"], errors="ignore")
registry = registry.drop_duplicates("ticker", keep="first").sort_values("ticker")
write_csv(REGISTRY, registry)

# Merge/dedupe events.
events = pd.concat([old_events, pd.DataFrame(new_events, columns=EVENT_COLUMNS)], ignore_index=True)
if not events.empty:
    events = events.drop_duplicates("discovery_key", keep="last")
    events = events.sort_values(["source_date","ticker","event_type"], ascending=[False,True,True])
write_csv(EVENTS, events[EVENT_COLUMNS] if not events.empty else pd.DataFrame(columns=EVENT_COLUMNS))

# Build/update backfill queue for anything not already in active PDUFA tracking.
queue_updates = []
for _, r in events.iterrows():
    if clean(r.get("pipeline_status")) != "BACKFILL_REQUIRED":
        continue
    queue_updates.append({
        "discovery_key":clean(r.get("discovery_key")),
        "ticker":clean(r.get("ticker")),
        "company":clean(r.get("company")),
        "cik10":clean(r.get("cik10")),
        "event_type":clean(r.get("event_type")),
        "drug":clean(r.get("drug")),
        "indication":clean(r.get("indication")),
        "nct_id":clean(r.get("nct_id")),
        "application_type":clean(r.get("application_type")),
        "pdufa_date":clean(r.get("pdufa_date")),
        "source_url":clean(r.get("source_url")),
        "evidence":clean(r.get("evidence")),
        "company_status":clean(r.get("company_status")),
        "match_confidence":clean(r.get("match_confidence")),
        "backfill_status":"NEEDS_FULL_BACKFILL",
        "first_seen_utc":clean(r.get("discovered_at_utc")),
        "last_seen_utc":now(),
    })
queue = pd.concat([old_queue, pd.DataFrame(queue_updates, columns=QUEUE_COLUMNS)], ignore_index=True)
if not queue.empty:
    queue = queue.sort_values("last_seen_utc").drop_duplicates("discovery_key", keep="last")
write_csv(QUEUE, queue[QUEUE_COLUMNS] if not queue.empty else pd.DataFrame(columns=QUEUE_COLUMNS))

state = {
    "status":"COMPLETE",
    "completed_at_utc":now(),
    "registry_before":int(initial_registry_n),
    "registry_after":int(len(registry)),
    "companies_auto_added":int(len(added_companies)),
    "events_total":int(len(events)),
    "backfill_queue_total":int(len(queue)),
    "ctgov_error":ct_error,
}
STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
print(json.dumps(state, indent=2))
