#!/usr/bin/env python3
"""Fetch direct issuer-owned Phase 3 results releases for the live FOCUS roster.

This supplements company homepages, not a replacement for scientific review.
Blocked issuer pages remain clickable research links with FETCH_BLOCKED status.
A URL or issuer assertion is never promoted into a verified benefit/risk grade.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
import csv,hashlib,json,re
from pathlib import Path
from urllib.parse import urlparse

import collect_focus_five_public_sources as public

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
SEEDS=ROOT/"data/focus_company_phase3_primary_sources.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
OUT=ROOT/"reports/focus-survey"
RESULT=OUT/"company-direct-source-ledger.json"
REPORT=OUT/"company-direct-source-summary.json"
CANDIDATES=OUT/"company-direct-source-candidates.json"
SOURCE_STATUS="SOURCE_CAPTURED_NEEDS_REVIEW"

def validate(roster,seeds):
    by_nct={r["nct"]:r for r in roster}
    if len(roster)!=29 or len(by_nct)!=len(roster):
        raise ValueError("FOCUS_ROSTER_CHANGED_REQUIRES_REVIEW")
    items=seeds.get("sources")
    if seeds.get("schemaVersion")!=1 or not isinstance(items,list) or not items:
        raise ValueError("COMPANY_PRIMARY_SOURCE_SEEDS_INVALID")
    seen=set()
    for item in items:
        nct=item.get("nctId")
        ticker=item.get("ticker")
        url=item.get("url")
        key=(nct,url)
        p=urlparse(url or "")
        if (nct not in by_nct or by_nct[nct]["ticker"]!=ticker or
            not p.scheme=="https" or not p.hostname or
            p.hostname.lower().endswith(".sec.gov") or
            not p.hostname.lower().endswith((".com",".org",".net")) or
            key in seen or
            item.get("reviewStatus")!="PUBLIC_ISSUER_SOURCE_DISCOVERY_ONLY"):
            raise ValueError("INVALID_DIRECT_COMPANY_NCT_ISSUER_LINK")
        seen.add(key)
    return items

def expand_official_candidates(roster,seeds):
    """Try distinct first-party roster sources even when the first issuer URL blocks.

    These are *discovery references* supplied by the canonical FOCUS roster.
    No archive or registry URL is relabelled as a company release; no sources
    beyond three URLs per NCT. A failed direct URL never ends issuer research.
    """
    by_nct=defaultdict(list)
    for item in seeds:by_nct[item["nctId"]].append(item)
    for row in roster:
        nct=row["nct"]
        for field in ("resultsUrl","regulatoryUrl"):
            url=row.get(field,"")
            parsed=urlparse(url)
            host=(parsed.hostname or "").lower()
            if parsed.scheme!="https" or not host or host.endswith(".sec.gov") or                host in ("sec.gov","clinicaltrials.gov","www.clinicaltrials.gov") or                host.endswith(".clinicaltrials.gov") or not host.endswith((".com",".org",".net")):
                continue
            if any(x["url"]==url for x in by_nct[nct]):continue
            if len(by_nct[nct])>=3:break
            by_nct[nct].append({
                "nctId":nct,"ticker":row["ticker"],"url":url,
                "publicationDate":"",
                "programContext":"Canonical FOCUS "+field+" (unverified official-source candidate)",
                "reviewStatus":"PUBLIC_ISSUER_SOURCE_DISCOVERY_ONLY"})
    enriched=[record for row in roster for record in by_nct[row["nct"]]]
    validate(roster,{"schemaVersion":1,"sources":enriched})
    return enriched

def fetch_once(url):
    doc,error=public.fetch(url,json_required=False,retries=1)
    if error:
        return {"error":error,"document":None}
    if not doc:
        return {"error":"PUBLIC_PAGE_NOT_RETRIEVED","document":None}
    plain=" ".join(doc.parts)
    if len(plain)<80:
        return {"error":"SOURCE_HTML_EMPTY_OR_SCRIPT_DEPENDENT","document":None}
    title=" ".join(doc.title_text) or doc.meta.get("og:title","")
    raw_date=(doc.meta.get("article:published_time") or
              doc.meta.get("article:modified_time") or
              doc.meta.get("date") or None)
    return {"error":None,"document":{"title":public.safe(title,350),
      "body":plain,"detectedDate":public.safe(raw_date,30) if raw_date else None,
      "contentSha256":hashlib.sha256(plain.encode("utf8")).hexdigest(),
      "sourceChars":len(plain)}}

def build(roster,seeds,packets,results):
    by_nct={r["nct"]:r for r in roster}
    ledger=[]
    candidates=[]
    observed=Counter()
    seed_by_nct=defaultdict(list)
    for item in seeds:seed_by_nct[item["nctId"]].append(item)
    for row in roster:
        nct=row["nct"]
        packet=packets[nct]
        if packet.get("nctId")!=nct or packet.get("ticker")!=row["ticker"] or \
           not packet.get("registry") or not packet.get("registrySourceHash"):
            raise ValueError("COMPANY_SOURCE_REGISTRY_IDENTITY_MISMATCH:"+nct)
        context=public.reg_context(packet)
        if not seed_by_nct[nct]:
            ledger.append({"nctId":nct,"ticker":row["ticker"],"issuer":row["company"],
                "url":"","sourceTitle":"","expectedPublicationDate":"",
                "status":"NO_DIRECT_ISSUER_RELEASE_INDEXED",
                "sourceMatch":"NOT_ASSESSED","ingredientCandidates":[],
                "sourceHash":"","error":"Research exact Phase 3 release on official company IR site"})
            continue
        for item in seed_by_nct[nct]:
            url=item["url"]
            result=results[url]
            page=result.get("document")
            if not page:
                ledger.append({"nctId":nct,"ticker":row["ticker"],"issuer":row["company"],
                    "url":url,"sourceTitle":item["programContext"],
                    "expectedPublicationDate":item.get("publicationDate",""),
                    "status":"SOURCE_LINK_ONLY_CONTENT_UNAVAILABLE",
                    "sourceMatch":"UNREVIEWED_DOCUMENT_LINK",
                    "ingredientCandidates":[],"sourceHash":"",
                    "error":result.get("error") or "SOURCE_CONTENT_UNAVAILABLE"})
                observed["linkOnly"]+=1
                continue
            title=page["title"]
            body=page["body"]
            record=public.match_level_and_record(context,"COMPANY",url,title,body,
                         page["detectedDate"] or item.get("publicationDate"),
                         {"contentSha256":page["contentSha256"],
                          "sourceChars":page["sourceChars"],
                          "seedContext":item["programContext"],
                          "sourceDiscovery":"CURATED_ISSUER_PUBLIC_PHASE3_RELEASE"})
            if nct.lower() in body.lower() or nct.lower() in title.lower():
                record["sourceMatch"]="EXACT_NCT"
            elif record["sourceMatch"]=="EXACT_NCT":
                # Exact match must originate from actual document, not index.
                record["sourceMatch"]="ISSUER_OR_SOURCE_LEAD_ONLY"
            record["sourceDetails"]["exactNctMentionInFullPage"]=record["sourceMatch"]=="EXACT_NCT"
            record["sourceDetails"]["originalSourceUrl"]=url
            if record["sourceMatch"] not in ("EXACT_NCT","DRUG_AND_INDICATION"):
                record["ingredientCandidates"]=[]
            level=record["sourceMatch"]
            ledger.append({"nctId":nct,"ticker":row["ticker"],"issuer":row["company"],
                "url":url,"sourceTitle":title,
                "expectedPublicationDate":item.get("publicationDate",""),
                "status":SOURCE_STATUS,"sourceMatch":level,
                "ingredientCandidates":record["ingredientCandidates"],
                "sourceHash":page["contentSha256"],"error":""})
            record["reviewed"]=False
            record["status"]=SOURCE_STATUS
            candidates.append(record)
            observed[level]+=1
    if len({r["nctId"] for r in ledger})!=len(roster):
        raise ValueError("COMPANY_SOURCE_LEDGER_INCOMPLETE")
    summary={"schemaVersion":1,"trials":len(roster),"selectedLinks":len(seeds),
             "ledgerRows":len(ledger),"capturedPages":len(candidates),
             "matchedEvidenceCandidates":sum(x["sourceMatch"] in
                 ("EXACT_NCT","DRUG_AND_INDICATION") for x in candidates),
             "blockedOrUnavailable":sum(x["status"]==
                 "SOURCE_LINK_ONLY_CONTENT_UNAVAILABLE" for x in ledger),
             "trialsWithCapturedDirectPage":len({x["nctId"] for x in candidates}),
             "trialsWithDirectLink":len({s["nctId"] for s in seeds}),
             "matchCounts":dict(observed),"verifiedSurveyAnswersCreated":0,
             "notice":"Source leads are unreviewed and link-only sources are NOT evidence."}
    return ledger,candidates,summary

def run():
    roster=public.read(ROSTER)["records"]
    seeds=expand_official_candidates(roster,validate(roster,public.read(SEEDS)))
    packets={r["nct"]:public.read(PACKETS/(r["nct"]+".json")) for r in roster}
    urls=sorted({x["url"] for x in seeds})
    results={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch_once,url):url for url in urls}
        for f in as_completed(futures):
            url=futures[f]
            try:results[url]=f.result()
            except Exception as e:results[url]={"error":type(e).__name__+":"+public.safe(str(e),150),
                                                 "document":None}
    ledger,candidates,summary=build(roster,seeds,packets,results)
    public.atomic(RESULT,{"schemaVersion":1,"rows":ledger})
    public.atomic(CANDIDATES,{"schemaVersion":1,"records":candidates})
    public.atomic(REPORT,summary)
    headers=["nctId","ticker","issuer","url","sourceTitle",
             "expectedPublicationDate","status","sourceMatch",
             "ingredientCandidates","sourceHash","error"]
    with (OUT/"company-direct-source-ledger.csv").open("w",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=headers)
        writer.writeheader()
        for row in ledger:
            writer.writerow({**row,"ingredientCandidates":"; ".join(row["ingredientCandidates"])})
    print(json.dumps(summary,sort_keys=True))
    return summary

if __name__=="__main__":
    run()
