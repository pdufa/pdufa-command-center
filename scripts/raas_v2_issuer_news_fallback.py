#!/usr/bin/env python3
"""Independent public issuer-news availability check when SEC EDGAR blocks CI.

Not a replacement for comprehensive SEC filings or for signed FDA action
records. A link is a review candidate, not evidence of a specific regulatory
deadline or a numbered pending application. Empty dynamic pages are UNKNOWN.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")

import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"new-platform/frontend/data/raas-v2-nov14-issuer-goal-continuity.json"
SCOPE="RAAS_V2_OFFICIAL_ISSUER_NEWS_FALLBACK_SOURCE_LEADS_NOT_FDA_OR_SEC_CENSUS"
URLS={
    "CYTK":"https://ir.cytokinetics.com/press-releases/",
    "SMMT":"https://smmttx.com/investor-information/",
}
LATEST_GOAL_SOURCE_DATE={"CYTK":"2026-08-06","SMMT":"2026-10-21"}
MAX_BYTES=2_000_000
MAX_RESULTS=25


def require(ok,code):
    if not ok: raise ValueError("RAAS_ISSUER_NEWS_"+code)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchor=None
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=="a":
            d=dict(attrs)
            self.anchor={"href":d.get("href"),"text":[]}
    def handle_data(self,data):
        if self.anchor is not None:
            self.anchor["text"].append(data)
    def handle_endtag(self,tag):
        if tag.lower()=="a" and self.anchor is not None:
            self.links.append({"href":self.anchor["href"],
                               "text":" ".join(" ".join(
                                   self.anchor["text"]).split())[:200]})
            self.anchor=None


def is_release_url(ticker,url):
    p=urlparse(url)
    if p.scheme!="https" or p.username or p.password or p.port not in (None,443):
        return False
    host=(p.hostname or "").lower()
    if ticker=="CYTK":
        return host=="ir.cytokinetics.com" and (
            "/press-release-details/" in p.path and "/2026/" in p.path)
    return host in {"smmttx.com","www.smmttx.com"} and (
        "/news/press-releases/news-details/2026/" in p.path)


def inspect_page(ticker,source_status,body,detail):
    require(ticker in URLS,"UNKNOWN_TICKER")
    require(source_status in {"AVAILABLE","SOURCE_UNAVAILABLE",
        "HTTP_404_NO_PUBLIC_RECORD","MALFORMED_RESPONSE"},
        "SOURCE_STATUS_INVALID")
    require(source_status=="AVAILABLE" or body is None,
            "BODY_WITH_UNAVAILABLE_SOURCE")
    links=[]
    if source_status=="AVAILABLE":
        require(isinstance(body,str) and 0<len(body)<=MAX_BYTES
                and "<" in body,"HTML_SOURCE_INVALID")
        parser=LinkParser()
        parser.feed(body)
        seen=set()
        for x in parser.links:
            href=x["href"]
            if not isinstance(href,str) or not href.strip():
                continue
            link=urljoin(URLS[ticker],href.strip())
            if not is_release_url(ticker,link):
                continue
            # Query strings are not needed and can contain tracking or
            # cache-busting parameters. Only keep canonical issuer links.
            parsed=urlparse(link)
            clean=parsed._replace(query="",fragment="").geturl()
            if clean in seen:
                continue
            seen.add(clean)
            links.append({
                "issuerArticleUrl":clean,
                "displayTitleFromAnchorNotRegulatoryEvidence":x["text"],
                "verifiedPublishedAfterLastReviewedGoalSource":False,
                "articleContentReviewedForPdufaChange":False,
                "pendingFdaApplicationNumberVerified":False,
                "officialFdaActionOrExtensionVerified":False,
            })
    links.sort(key=lambda x:x["issuerArticleUrl"])
    return {
        "ticker":ticker,
        "issuerOfficialNewsPage":URLS[ticker],
        "lastReviewedIssuerGoalSourceDate":LATEST_GOAL_SOURCE_DATE[ticker],
        "sourceStatus":source_status,
        "sourceDetail":(detail or "")[:260],
        "pageAccessible":source_status=="AVAILABLE",
        "issuerArticleLinksFound":len(links),
        "listedResearchLinkCandidates":links[:MAX_RESULTS],
        "additionalArticleLinksNotDisplayed":max(0,len(links)-MAX_RESULTS),
        "issuerNewsPageAccessibleButNoArticlesParsedIsNoNews":False,
        "issuerNewsIsComprehensiveSECDisclosureFeed":False,
        "issuerArticleLinkCertifiesFdaDeadlineOrApplicationNumber":False,
        "sec403FixedByThisIssuerNewsSource":False,
        "pageParseStatus":(
            "NEWS_LINK_LEADS_FOUND_NOT_DATE_OR_CONTENT_VERIFIED" if links
            else "PAGE_FETCHED_NO_PARSEABLE_ARTICLES_NOT_A_NEGATIVE_RESULT"
            if source_status=="AVAILABLE" else
            "PUBLIC_ISSUER_NEWS_SOURCE_UNAVAILABLE"),
    }


def inspect_report(payloads,statuses,details,checked_at,source=None):
    require(isinstance(checked_at,str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",checked_at),
        "CLOCK_FORMAT")
    dt.datetime.strptime(checked_at,"%Y-%m-%dT%H:%M:%SZ")
    require(set(payloads)==set(statuses)==set(details)==set(URLS),
            "MISSING_ISSUER_SOURCE")
    data=source or json.loads(SOURCE.read_text("utf-8"))
    require(data.get("scope")==
        "RAAS_V2_NOV14_DATED_ISSUER_GOAL_CONTINUITY_NOT_INDEPENDENT_FDA_CYCLE_VERIFICATION"
        and data.get("independentlyVerifiedCurrentFdaReviewCycleCount")==0,
        "ISSUER_GOAL_SOURCE_NOT_RESEARCH_ONLY")
    by={x.get("ticker"):x for x in data.get("records",[])}
    require(set(by)==set(URLS) and all(
        by[t].get("issuerPublicSourceDate")==LATEST_GOAL_SOURCE_DATE[t]
        and by[t].get("absenceOfLaterGoalChangeIndependentlyEstablished") is False
        and by[t].get("fullDatedFDAActionCycleIndependentlyEstablished") is False
        for t in URLS),"ISSUER_GOAL_SOURCE_IDENTITY_WRONG")
    rows=[inspect_page(t,statuses[t],payloads[t],details[t])
          for t in ("CYTK","SMMT")]
    return {
        "schemaVersion":1,"scope":SCOPE,
        "status":"ISSUER_NEWS_FALLBACK_RESEARCH_ONLY_NOT_SEC_OR_FDA_COVERAGE",
        "checkedAtUTC":checked_at,
        "officialIssuerNewsPagesChecked":2,
        "officialIssuerNewsPagesAccessible":sum(x["pageAccessible"] for x in rows),
        "issuerNewsResearchLinkCandidatesFound":sum(
            x["issuerArticleLinksFound"] for x in rows),
        "rows":rows,
        "secOfficialFilingsAccessRestoredByFallback":False,
        "newCurrentPendingApplicationNumbersIndependentlyVerified":0,
        "independentlyVerifiedFdaDeadlineRevisions":0,
        "newThreeWayPredictionsFromIssuerNews":0,
        "approvedRAASMetricCalibrations":0,
        "warning":"Issuer news is a supplemental public source, not a replacement "
            "for SEC EDGAR. Investor websites may be dynamic or omit articles. "
            "A URL, missing article or access denial does not prove anything "
            "about an FDA outcome, application number, or deadline revision.",
    }


def fetch_page(ticker):
    require(ticker in URLS,"FETCH_UNKNOWN_ISSUER")
    request=urllib.request.Request(URLS[ticker],headers={
        "User-Agent":"PDUFA-Research-Public-Source-Checker/1.0",
        "Accept":"text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(request,timeout=12) as response:
            raw=response.read(MAX_BYTES+1)
            require(len(raw)<=MAX_BYTES,"HTML_SOURCE_TOO_LARGE")
        try:
            return raw.decode("utf-8"),"AVAILABLE",None
        except UnicodeError:
            return None,"MALFORMED_RESPONSE","non-UTF8 issuer page"
    except urllib.error.HTTPError as exc:
        if exc.code==404:
            return None,"HTTP_404_NO_PUBLIC_RECORD","issuer site HTTP 404"
        return None,"SOURCE_UNAVAILABLE","issuer site HTTP "+str(exc.code)
    except (OSError,TimeoutError) as exc:
        return None,"SOURCE_UNAVAILABLE",type(exc).__name__


def main():
    now=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results={t:fetch_page(t) for t in ("CYTK","SMMT")}
    report=inspect_report(
        {t:results[t][0] for t in results},
        {t:results[t][1] for t in results},
        {t:results[t][2] for t in results},now)
    out=Path(os.getenv("RAAS_ISSUER_NEWS_FALLBACK_JSON",
        "raas-v2-issuer-news-fallback-research-leads.json"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                   encoding="utf-8")
    print(json.dumps({key:report[key] for key in (
        "checkedAtUTC","officialIssuerNewsPagesAccessible",
        "issuerNewsResearchLinkCandidatesFound",
        "secOfficialFilingsAccessRestoredByFallback",
        "newCurrentPendingApplicationNumbersIndependentlyVerified")},sort_keys=True))


if __name__=="__main__":
    main()
