#!/usr/bin/env python3
"""Multi-source public research enrichment for the live FOCUS 20x38 survey.

Public research leads only, NOT validated survey answers. Uses the official
ClinicalTrials.gov source packets, issuer-owned company disclosures, openFDA
labels/Drugs@FDA, Europe PMC indexed articles, and SEC filing pointers.
Does not fabricate private pricing, patent rights, patient counts, PDUFA dates,
approval odds, commercial forecasts, or numerical RAAS scores.

Every record is exact-NCT-linked, but external pages may cover an issuer or a
drug rather than that specific trial. 'sourceMatch' preserves that distinction.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,urljoin,urlparse,quote
from urllib.request import Request,urlopen
import time

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
CATALOG=ROOT/"data/phase3_benefit_survey_catalog.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
OUTPUT=ROOT/"reports/focus-survey"
SEC_REGISTRY=ROOT/"data/company_registry.csv"
FDA_LABEL="https://api.fda.gov/drug/label.json"
FDA_DRUGS="https://api.fda.gov/drug/drugsfda.json"
EUROPEPMC="https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA="PDUFACommandCenterPublicResearch/1.1 (+https://github.com/pdufa/pdufa-command-center/issues)"
NCT_RE=re.compile(r"^NCT\d{8}$")
MAX_HTML_BYTES=2_200_000
MAX_JSON_BYTES=3_000_000
PRIMARY_INGREDIENTS={
    "clinicalBenefit":r"\bclinical benefit\b|primary end.?point|\befficacy\b|clinical improvement",
    "magnitude":r"\beffect size\b|mean difference|\bconfidence interval\b|% response|\bprimary endpoint\b",
    "responseRemission":r"\bremission\b|\bresponse rate\b|\bresponder",
    "durability":r"\bdurab|sustained benefit|long.term efficacy",
    "survivalBenefit":r"\boverall survival\b|progression.free survival|mortality",
    "qualityOfLife":r"quality.of.life|patient.reported|\bkccq\b|\bsgrq\b",
    "seriousAes":r"serious adverse event|\bsae\b",
    "safetyAdvantage":r"\bsafety\b|\btolerab|adverse event",
    "discontinuation":r"discontinu|withdrawal due",
    "eligibleUsPatients":r"\bprevalen|\binciden|eligible patient|patient population",
    "unmetNeed":r"unmet medical need|limited treatment options|disease burden",
    "closestCompetitor":r"standard.of.care|approved treatment|competitive therap|head.to.head",
    "competitorCount":r"other approved treatments|competitive landscape|competitors",
    "convenience":r"\boral pill\b|\bonce.daily\b|treatment burden|dose frequency|administration",
    "treatmentSequence":r"first.line|second.line|treatment setting|line.of.therapy",
    "hospitalizationReduction":r"hospitalization|hospital admission|complication reduction",
    "costDifference":r"treatment cost|cost effectiveness",
    "payerAccess":r"\breimburse|\binsurance\b|prior authorization|formulary",
    "treatmentPrice":r"\bwholesale acquisition cost\b|\bnet price\b|drug price|list price",
    "adoption":r"market penetration|commercial uptake|market adoption",
    "switchingPool":r"switching population|switching patients",
    "internationalPatients":r"global prevalence|worldwide patients",
    "additionalIndications":r"additional indication|expanded indication|other indication",
    "peakAnnualSales":r"peak sales|peak annual revenue",
    "revenueGrowth":r"revenue growth|product revenue|net sales",
    "exclusivity":r"patent|exclusivity",
    "licensingValue":r"licens|royalty|milestone payment|partnership agreement",
    "valuationImpact":r"enterprise value|market capitalization|valuation",
    "shareholderRisk":r"cash runway|cash and equivalents|\bdilut|secondary offering|financing",
}
# Official issuer-domain candidates used only if the roster's primary reference is
# hosted on SEC.gov. Never label an inaccessible candidate as a confirmed source.
ISSUER_URLS={
 "ACHV":"https://ir.achievelifesciences.com/",
 "AXSM":"https://www.axsome.com/",
 "COGT":"https://www.cogentbio.com/",
 "CYTK":"https://ir.cytokinetics.com/",
 "MLTX":"https://ir.moonlaketx.com/",
 "PHVS":"https://ir.pharvaris.com/",
 "SVRA":"https://ir.savarapharma.com/",
 "URGN":"https://investors.urogen.com/",
}
NOISE_DRUGS={"placebo","vehicle","behavioral support","saline","usual care",
 "best supportive care","metoprolol succinate","control","sham"}
SOURCE_BUCKETS=("COMPANY","REGISTRY","FDA","LITERATURE","SEC")
STATUS="SOURCE_CAPTURED_NEEDS_REVIEW"

class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[];self.links=[];self.meta={};self.suppress=0;self.title=False;self.title_text=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ("script","style","noscript","svg"):
            self.suppress+=1
        if tag=="title":self.title=True
        if tag=="meta":
            name=(attrs.get("property") or attrs.get("name") or "").lower()
            value=attrs.get("content") or ""
            if name and value:self.meta[name]=value[:500]
        if tag=="a" and attrs.get("href"):
            self.links.append((attrs["href"][:500],attrs.get("title","")[:200]))
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg") and self.suppress:self.suppress-=1
        if tag=="title":self.title=False
    def handle_data(self,data):
        if self.suppress:return
        v=" ".join(data.split())
        if v and len(v)>1:self.parts.append(v)
        if self.title:self.title_text.append(v)

def utcnow():return datetime.now(timezone.utc).isoformat(timespec="seconds")
def safe(v,n=430):return " ".join(str(v or "").split())[:n]
def norm(v):return safe(v,1000).lower()
def digest(o):return hashlib.sha256(json.dumps(o,sort_keys=True,ensure_ascii=False).encode("utf8")).hexdigest()
def atomic(path,o):
    path.parent.mkdir(parents=True,exist_ok=True)
    draft=path.with_suffix(path.suffix+".tmp")
    draft.write_text(json.dumps(o,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    draft.replace(path)
def read(path):return json.loads(path.read_text(encoding="utf8"))
def http(url,json_required=False,maxbytes=MAX_HTML_BYTES):
    parsed=urlparse(url)
    if parsed.scheme!="https" or not parsed.hostname:
        raise ValueError("ONLY_HTTPS_PUBLIC_SOURCES")
    if parsed.hostname in ("localhost","127.0.0.1") or parsed.hostname.endswith(".local"):
        raise ValueError("DISALLOWED_NETWORK_DESTINATION")
    req=Request(url,headers={"User-Agent":UA,
       "Accept":"application/json" if json_required else "text/html,application/xhtml+xml"})
    with urlopen(req,timeout=15) as response:
        if response.status!=200 or response.geturl().split("://")[0]!="https":
            raise ValueError("PUBLIC_SOURCE_UNEXPECTED_RESPONSE")
        body=response.read(maxbytes+1)
        if len(body)>maxbytes:raise ValueError("PUBLIC_SOURCE_TOO_LARGE")
        kind=response.headers.get("Content-Type","")
        if json_required:
            if "json" not in kind.lower():raise ValueError("SOURCE_NOT_JSON")
            return json.loads(body.decode("utf8"))
        if not ("html" in kind.lower() or "text/" in kind.lower()):
            raise ValueError("UNSUPPORTED_WEB_PAGE_FORMAT")
        doc=Reader();doc.feed(body.decode("utf8",errors="replace"))
        return doc
def fetch(url,json_required=False,retries=2,maxbytes=MAX_HTML_BYTES):
    error=""
    for attempt in range(retries):
        try:return http(url,json_required,maxbytes),None
        except HTTPError as exc:
            error="HTTP_"+str(exc.code)
            if exc.code in (400,401,403,404):break
        except (URLError,TimeoutError,OSError,ValueError,UnicodeError) as exc:
            error=type(exc).__name__+":"+safe(str(exc),110)
        if attempt<retries-1:time.sleep(attempt+1)
    return None,error or "UNKNOWN_PUBLIC_SOURCE_ERROR"

def study_drugs(registry):
    drugs=[]
    for v in registry.get("interventions",[]):
        if not isinstance(v,dict) or v.get("type") not in ("DRUG","BIOLOGICAL","COMBINATION_PRODUCT"):
            continue
        raw=safe(v.get("name"),100)
        for x in re.split(r"[,;/]| \+ ",raw):
            label=re.sub(r"\s*\([^)]*\)","",x).strip()
            if len(label)>=4 and norm(label) not in NOISE_DRUGS and label not in drugs:
                drugs.append(label)
    return drugs[:5]

def reg_context(packet):
    registry=packet["registry"]
    return {"nct":packet["nctId"],"ticker":packet["ticker"],"company":packet["company"],
            "drugs":study_drugs(registry),
            "indications":[safe(x,110) for x in registry.get("indications",[])][:10],
            "registryUrl":packet.get("registryUrl","https://clinicaltrials.gov/study/"+packet["nctId"]),
            "registryHash":packet["registrySourceHash"]}

def exact_word(haystack,word):
    target=norm(word)
    if not target or len(target)<4:return False
    return re.search(r"(?<![a-z0-9])"+re.escape(target)+r"(?![a-z0-9])",norm(haystack)) is not None

def matches(context,title,excerpt):
    text=norm(title+" "+excerpt)
    if context["nct"].lower() in text:return "EXACT_NCT"
    if any(exact_word(text,d) for d in context["drugs"]):
        if any(exact_word(text,i) for i in context["indications"]):
            return "DRUG_AND_INDICATION"
        return "DRUG_MENTION_ONLY"
    if any(exact_word(text,i) for i in context["indications"]):
        return "INDICATION_CONTEXT_ONLY"
    return "ISSUER_OR_SOURCE_LEAD_ONLY"

def relevant_ingredient_ids(text):
    corpus=norm(text)
    return [id for id,pattern in PRIMARY_INGREDIENTS.items() if re.search(pattern,corpus,re.I)]

def snippet_near(text,terms,maximum=700):
    raw=" ".join(text.split())
    lower=raw.lower()
    found=[(lower.find(term.lower()),term) for term in terms if len(term)>=4 and term.lower() in lower]
    found=[x for x in found if x[0]>=0]
    if found:
        pos=min(found)[0]
        return safe(raw[max(0,pos-150):pos+maximum],maximum)
    return safe(raw[:maximum],maximum)

def match_level_and_record(context,source_type,url,title,body,date=None,extra=None):
    corpus=title+" "+body
    level=matches(context,title,body)
    ids=relevant_ingredient_ids(corpus)
    return {
        "nctId":context["nct"],"ticker":context["ticker"],"company":context["company"],
        "candidateDrugs":context["drugs"],"registryIndications":context["indications"],
        "sourceType":source_type,"sourceUrl":url,"sourceTitle":safe(title,240),
        "sourceDate":date,"excerpt":snippet_near(body,[context["nct"]]+context["drugs"]+context["indications"]),
        "sourceMatch":level,"ingredientCandidates":ids,
        "status":STATUS,"reviewed":False,"sourceDetails":extra or {},
        "notice":"Candidate evidence for human review; no approval, pricing, sales or RAAS claim is established.",
    }

def company_page(url,context):
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.hostname in ("www.sec.gov","sec.gov","data.sec.gov"):
        return None,[],"SEC_ARCHIVE_UNAVAILABLE_FROM_COMPANY_CRAWL"
    doc,error=fetch(url)
    if not doc:return None,[],error
    plain=" ".join(doc.parts)
    title=" ".join(doc.title_text) or doc.meta.get("og:title","")
    pub=(doc.meta.get("article:published_time") or doc.meta.get("date") or
         doc.meta.get("article:modified_time") or None)
    pub=safe(pub,30) if pub else None
    result=match_level_and_record(context,"COMPANY",url,title,plain,pub,
                                   {"host":parsed.hostname,
                                    "nctMentions":sorted(set(re.findall(r"NCT[0-9]{8}",plain,re.I)))[:100],
                                    "contentSha256":hashlib.sha256(plain.encode("utf8")).hexdigest()})
    links=[]
    base=parsed.hostname.removeprefix("www.")
    for href,caption in doc.links:
        uri=urljoin(url,href)
        target=urlparse(uri)
        if target.scheme!="https" or not target.hostname:continue
        host=target.hostname.removeprefix("www.")
        if host!=base and not host.endswith("."+base):continue
        if re.search(r"\.(pdf|jpg|png|docx|xlsx)(?:$|\?)",target.path,re.I):continue
        label=(caption+" "+uri).lower()
        if re.search(r"phase.?3|topline|top.line|clinical.?result|investor|news.release|financial.result|fda|application|press.release",label):
            links.append(uri.split("#")[0])
    return result,list(dict.fromkeys(links))[:12],None

def issuer_company_sources(rows,contexts):
    # One company crawl per ticker. Keep issuer pages separate from exact NCT
    # identity. Moderate concurrency across different official hosts.
    def one_company(ticker):
        first=next(r for r in rows if r["ticker"]==ticker)
        original=first.get("regulatoryUrl","")
        orig_host=urlparse(original).hostname or ""
        seed=original if orig_host not in ("www.sec.gov","sec.gov","data.sec.gov") else ISSUER_URLS.get(ticker)
        if not seed:
            return ticker,{"pages":[],"errors":["COMPANY_URL_NOT_RESOLVED"],"seed":None}
        ctx=contexts[first["nct"]]
        page,links,error=company_page(seed,ctx)
        pages=[page] if page else []
        errors=[error] if error else []
        # Restrict to issuer's site; avoid unbounded crawling.
        for link in links[:3]:
            if link==seed:continue
            item,_,err=company_page(link,ctx)
            if item:pages.append(item)
            if err:errors.append(safe(err,120))
        return ticker,{"pages":pages,"errors":errors,"seed":seed}
    reports={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one_company,ticker):ticker for ticker in
                 sorted({r["ticker"] for r in rows})}
        for future in as_completed(futures):
            ticker=futures[future]
            try:
                key,report=future.result()
                reports[key]=report
            except Exception as exc:
                reports[ticker]={"pages":[],"errors":[type(exc).__name__+":"+safe(str(exc),140)],"seed":None}
    return reports

def affiliate_records(company_reports,contexts,rows):
    records=[]
    for row in rows:
        context=contexts[row["nct"]]
        for company in company_reports[row["ticker"]]["pages"]:
            # Reclassify each source for the exact NCT and program.
            clone={**company}
            clone["nctId"]=context["nct"]
            clone["candidateDrugs"]=context["drugs"]
            clone["registryIndications"]=context["indications"]
            clone["sourceMatch"]=(
                "EXACT_NCT" if context["nct"] in
                  clone.get("sourceDetails",{}).get("nctMentions",[])
                else matches(context,clone["sourceTitle"],clone["excerpt"]))
            if clone["sourceMatch"]=="ISSUER_OR_SOURCE_LEAD_ONLY":
                # issuer-only lead; keep for audit but never promote to data slot.
                clone["ingredientCandidates"]=[]
            records.append(clone)
    return records

def literature_search(context,mode):
    drug=context["drugs"][0] if context["drugs"] else ""
    indication=context["indications"][0] if context["indications"] else ""
    if mode=="TRIAL":
        query='"'+context["nct"]+'"'
    elif mode=="DRUG_INDICATION" and drug and indication:
        query='TITLE_ABS:"'+drug.replace('"','')+'" AND "'+indication.replace('"','')+'"'
    elif mode=="DISEASE_CONTEXT" and indication:
        query='TITLE_ABS:"'+indication.replace('"','')+'" AND (guideline OR epidemiology OR treatment)'
    else:
        return [],"QUERY_NOT_APPLICABLE"
    url=EUROPEPMC+"?"+urlencode({"query":query,"format":"json","resultType":"core","pageSize":8})
    payload,error=fetch(url,True,maxbytes=MAX_JSON_BYTES)
    if error:return [],error
    result=[]
    for p in (payload.get("resultList",{}).get("result") or [])[:8]:
        source=p.get("source","");id=p.get("id","")
        if not source or not id:continue
        puburl="https://europepmc.org/article/"+quote(str(source))+"/"+quote(str(id))
        title=safe(p.get("title"),300)
        abstract=re.sub(r"<[^>]*>"," ",str(p.get("abstractText") or ""))
        # Label indexed article/abstract content as a lead, not audited clinical data.
        record=match_level_and_record(context,"LITERATURE",puburl,title,abstract,
                           p.get("firstPublicationDate"),
                           {"searchMode":mode,"doi":p.get("doi"),
                            "openAccess":p.get("isOpenAccess")=="Y",
                            "indexedSource":source,"abstractAvailable":bool(abstract)})
        if mode=="DISEASE_CONTEXT" and record["sourceMatch"]=="ISSUER_OR_SOURCE_LEAD_ONLY":
            continue
        if mode=="TRIAL" and context["nct"].lower() in title.lower()+" "+abstract.lower():
            record["sourceMatch"]="EXACT_NCT"
        result.append(record)
    return result,None

def fda_search(context,mode):
    drug=context["drugs"][0] if context["drugs"] else None
    indication=context["indications"][0] if context["indications"] else None
    if mode=="APPROVAL_BY_DRUG" and drug:
        path=FDA_DRUGS
        query='products.brand_name:"'+drug.replace('"','')+'"'
        ingredients=["closestCompetitor","treatmentSequence"]
    elif mode=="APPROVED_LABELS_BY_DISEASE" and indication:
        path=FDA_LABEL
        query='indications_and_usage:"'+indication.replace('"','')+'"'
        ingredients=["closestCompetitor","competitorCount","standardOfCare","safetyAdvantage"]
    else:
        return [],"QUERY_NOT_APPLICABLE"
    url=path+"?"+urlencode({"search":query,"limit":6})
    payload,error=fetch(url,True,maxbytes=MAX_JSON_BYTES)
    if error and error=="HTTP_404":return [],None
    if error:return [],error
    results=[]
    for p in (payload.get("results") or [])[:6]:
        if mode=="APPROVED_LABELS_BY_DISEASE":
            names=p.get("openfda",{}).get("brand_name",[])
            generics=p.get("openfda",{}).get("generic_name",[])
            label=" / ".join(names[:2] or generics[:2]) or "FDA label record"
            indications=" ".join(str(x) for x in p.get("indications_and_usage",[]))
            if indication and not exact_word(indications,indication):
                continue
            body=(indications[:2000]+" "+" ".join(str(x) for x in p.get("dosage_and_administration",[]))[:500])
            if not (p.get("openfda") or {}).get("application_number"):
                continue
            details={"mode":mode,"applicationNumbers":p.get("openfda",{}).get("application_number",[])[:4],
                     "labelEffectiveTime":p.get("effective_time"),
                     "brand":names[:3],"generic":generics[:3]}
            record=match_level_and_record(context,"FDA",
                "https://api.fda.gov/drug/label.json?"+urlencode({"search":query,"limit":6}),
                label,body, p.get("effective_time"),details)
        else:
            brand=" / ".join(str(x.get("brand_name","")) for x in p.get("products",[])[:2])
            details={"mode":mode,"applicationNumber":p.get("application_number"),
                     "sponsorName":p.get("sponsor_name"),
                     "submissions":len(p.get("submissions") or [])}
            record=match_level_and_record(context,"FDA",
                "https://api.fda.gov/drug/drugsfda.json?"+urlencode({"search":query,"limit":6}),
                brand,"FDA Drugs@FDA indexed application name and status",
                None,details)
        record["ingredientCandidates"]=ingredients
        record["sourceMatch"]="FDA_INDEX_SEARCH_MATCH_NEEDS_INDICATION_REVIEW"
        record["notice"]="FDA approved-drug index or label is not evidence of this trial drug's approval or a PDUFA date."
        results.append(record)
    return results,None

def sec_source(row,context,cik=None):
    url=row.get("regulatoryUrl") or ""
    if not url.startswith("https://"):return None
    host=urlparse(url).hostname or ""
    if host in ("www.sec.gov","sec.gov","data.sec.gov"):
        return {
         **match_level_and_record(context,"SEC",url,
            "Issuer-linked SEC primary filing pointer","",None,
            {"cik":cik,"filingAccess":"SEC_PUBLIC_POINTER_UNVERIFIED_CONTENT"}),
          "sourceMatch":"ISSUER_FILING_POINTER_ONLY",
          "ingredientCandidates":["licensingValue","exclusivity","revenueGrowth","shareholderRisk"],
          "notice":"SEC filing pointer only; document content inaccessible here and product rights not verified."
        }
    if "/sec-filings/" in url.lower() or "/sec-filing" in url.lower():
        return {
          **match_level_and_record(context,"SEC",url,
            "Issuer-hosted SEC filing pointer","",None,
            {"cik":cik,"filingAccess":"COMPANY_HOSTED_FILING_CONTENT_NOT_YET_ADJUDICATED"}),
          "sourceMatch":"ISSUER_FILING_POINTER_ONLY",
          "ingredientCandidates":["licensingValue","exclusivity","revenueGrowth","shareholderRisk"]
        }
    return None

def load_ciks():
    result={}
    with SEC_REGISTRY.open(encoding="utf8",newline="") as file:
        for row in csv.DictReader(file):
            if row["status"]=="OK" and re.fullmatch(r"\d{10}",row["cik10"]):
                result[row["ticker"]]=row["cik10"]
    return result

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--dry-run",action="store_true")
    args=cli.parse_args()
    roster=read(ROSTER)["records"]
    catalog=read(CATALOG)["assessments"]
    ids={x["id"] for group in catalog for x in group["ingredients"]}
    if len(catalog)!=20 or len(ids)!=38 or len(roster)!=29 or \
       len({x["nct"] for x in roster})!=29:
        raise ValueError("ACTIVE_FOCUS_SCOPE_CHANGED_REVIEW_BEFORE_WRITE")
    if not set(PRIMARY_INGREDIENTS).issubset(ids):
        raise ValueError("NONCANONICAL_INGREDIENT_ID")
    packet_by_nct={}
    contexts={}
    for row in roster:
        nct=row["nct"]
        if not NCT_RE.fullmatch(nct):raise ValueError("BAD_FOCUS_NCT_ID")
        packet=read(PACKETS/(nct+".json"))
        if packet["nctId"]!=nct or packet["ticker"]!=row["ticker"] or not packet.get("registry"):
            raise ValueError("FOCUS_REGISTRY_IDENTITY_INCONSISTENT:"+nct)
        packet_by_nct[nct]=packet
        contexts[nct]=reg_context(packet)
    if args.dry_run:
        print(json.dumps({"trials":29,"ingredients":38,"companies":len({r["ticker"] for r in roster})}))
        return
    ciks=load_ciks()
    company_reports=issuer_company_sources(roster,contexts)
    output=affiliate_records(company_reports,contexts,roster)
    errors=[]
    for ticker,report in company_reports.items():
        errors += [{"ticker":ticker,"sourceType":"COMPANY","error":error}
                   for error in report["errors"]]
    for row in roster:
        context=contexts[row["nct"]]
        sec=sec_source(row,context,ciks.get(row["ticker"]))
        if sec:output.append(sec)
    # FDA comparisons are queried by disease and individual drug; enforce
    # issuer/trial identity only for the research queue, not the label itself.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={}
        for row in roster:
            c=contexts[row["nct"]]
            for mode in ("TRIAL","DRUG_INDICATION","DISEASE_CONTEXT"):
                futures[pool.submit(literature_search,c,mode)]=(row["nct"],"LITERATURE",mode)
            for mode in ("APPROVAL_BY_DRUG","APPROVED_LABELS_BY_DISEASE"):
                futures[pool.submit(fda_search,c,mode)]=(row["nct"],"FDA",mode)
        for future in as_completed(futures):
            nct,source,mode=futures[future]
            try:
                rec,error=future.result()
                output.extend(rec)
                if error and error!="QUERY_NOT_APPLICABLE":
                    errors.append({"nctId":nct,"sourceType":source,"mode":mode,"error":safe(error,180)})
            except Exception as error:
                errors.append({"nctId":nct,"sourceType":source,"mode":mode,
                               "error":type(error).__name__+":"+safe(str(error),120)})
    # Prevent misleading duplicates from shared company pages. Keep source
    # distinctions, but never count a company document twice for one trial.
    dedup={}
    for row in output:
        if row["nctId"] not in contexts or row["sourceType"] not in SOURCE_BUCKETS:
            raise ValueError("INVALID_ENRICHMENT_SOURCE_ID")
        if any(id not in ids for id in row["ingredientCandidates"]):
            raise ValueError("INVALID_ENRICHMENT_INGREDIENT")
        key=(row["nctId"],row["sourceType"],row["sourceUrl"],
             row["sourceTitle"],row["sourceDetails"].get("applicationNumber"),
             row["sourceDetails"].get("labelEffectiveTime"))
        dedup[key]=row
    output=sorted(dedup.values(),key=lambda r:(r["nctId"],r["sourceType"],r["sourceUrl"],r["sourceTitle"]))
    by_trial=defaultdict(lambda:{"sources":Counter(),"strongContext":0,"candidateIngredients":set()})
    source_counts=Counter()
    for row in output:
        source_counts[row["sourceType"]]+=1
        x=by_trial[row["nctId"]]
        x["sources"][row["sourceType"]]+=1
        if row["sourceMatch"] in ("EXACT_NCT","DRUG_AND_INDICATION"):
            x["strongContext"]+=1
            x["candidateIngredients"].update(row["ingredientCandidates"])
    summary={
        "schemaVersion":1,"generatedAt":utcnow(),"focusTrials":len(roster),
        "companyIssuers":len(company_reports),"surveyGroups":20,"surveyIngredients":38,
        "newSourceLeads":len(output),"sourceCounts":dict(source_counts),
        "errorCount":len(errors),"sourceErrors":errors[:200],
        "sourceStatus":"RESEARCH_LEADS_ONLY_NOT_SURVEY_ANSWERS",
        "verifiedSurveyAnswersCreated":0,
        "perTrial":[{"nctId":r["nct"],"ticker":r["ticker"],
            "sourceCounts":dict(by_trial[r["nct"]]["sources"]),
            "strongSourceContext":by_trial[r["nct"]]["strongContext"],
            "candidateIngredientIds":sorted(by_trial[r["nct"]]["candidateIngredients"])}
                    for r in roster],
        "warning":"A source lead does not resolve any unreviewed survey ingredient; FDA labels and SEC filings are not drug-program proof."
    }
    atomic(OUTPUT/"five-source-leads.json",{"schemaVersion":1,"records":output})
    atomic(OUTPUT/"five-source-summary.json",summary)
    headers=["nctId","ticker","company","sourceType","sourceUrl","sourceTitle",
             "sourceDate","sourceMatch","ingredientCandidates","candidateDrugs",
             "registryIndications","excerpt","sourceDetails","status","reviewed","notice"]
    with (OUTPUT/"five-source-leads.csv").open("w",encoding="utf8",newline="") as file:
        wr=csv.DictWriter(file,fieldnames=headers)
        wr.writeheader()
        for row in output:
            values={key:row.get(key) for key in headers}
            for key in ("ingredientCandidates","candidateDrugs","registryIndications"):
                values[key]="; ".join(values[key])
            values["sourceDetails"]=json.dumps(values["sourceDetails"],sort_keys=True)
            wr.writerow(values)
    print(json.dumps({k:summary[k] for k in ("focusTrials","newSourceLeads","sourceCounts","errorCount")}))
if __name__=="__main__":
    main()
