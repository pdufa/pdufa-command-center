#!/usr/bin/env python3
"""Prepare source-grounded FOCUS survey review packets from saved public captures.

Preserves the original 29 x 38 matrix and its statuses. Neither a registry
numeric observation nor a literature search hit is a VERIFIED survey answer.
Literature is only classified as an exact-NCT, drug-title, disease-context or
unlinked research lead; no title-only efficacy or FDA conclusions are permitted.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from collections import Counter, defaultdict

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"reports/focus-survey"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
CATALOG=ROOT/"data/phase3_benefit_survey_catalog.json"
EVIDENCE=OUTPUT/"evidence.json"
PACKETS=OUTPUT/"source-packets"
NCT=re.compile(r"^NCT\d{8}$")
GENERIC_INTERVENTIONS={"placebo","behavioral support","best supportive care",
                       "standard of care","supportive care","saline","vehicle",
                       "sham","usual care","active comparator","control"}
PUBLICATION_CLASSES=("EXACT_NCT_LEAD","DRUG_TITLE_LEAD","INDICATION_CONTEXT_ONLY","UNLINKED_SEARCH_LEAD")
REVIEW_STATUS="SOURCE_OBSERVED_REVIEW_REQUIRED"

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def dump_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    stage=path.with_suffix(path.suffix+".tmp")
    stage.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    stage.replace(path)

def dump_csv(path,headers,rows):
    with path.open("w",encoding="utf-8",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=headers,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def norm(text):
    return " ".join(str(text or "").strip().lower().split())

def short(text,maximum=400):
    return " ".join(str(text or "").split())[:maximum]

def matches_title(title,term):
    value=norm(term)
    if len(value)<4 or value in GENERIC_INTERVENTIONS:
        return False
    return re.search(r"(?<![a-z0-9])"+re.escape(value)+r"(?![a-z0-9])",norm(title)) is not None

def candidate_drugs(registry):
    names=[]
    for item in registry.get("interventions",[]):
        raw=item.get("name","") if isinstance(item,dict) else ""
        if not raw:
            continue
        for name in re.split(r"[,;/]|\s+\+\s+",raw):
            candidate=norm(name)
            if candidate and candidate not in GENERIC_INTERVENTIONS and len(candidate)>=4 and \
               candidate not in names:
                names.append(candidate)
    return names

def classify_article(article,registry):
    title=short(article.get("title",""),500)
    if not title:
        return "UNLINKED_SEARCH_LEAD",[]
    if article.get("exactNctInTitle") or article.get("exactNctInAbstract"):
        return "EXACT_NCT_LEAD",["Exact NCT mention in the indexed citation/abstract; check full text"]
    drug_matches=[drug for drug in candidate_drugs(registry) if matches_title(title,drug)]
    if drug_matches:
        return "DRUG_TITLE_LEAD",drug_matches[:6]
    indications=[x for x in registry.get("indications",[]) if len(norm(x))>=5]
    indication_matches=[term for term in indications if matches_title(title,term)]
    if indication_matches:
        return "INDICATION_CONTEXT_ONLY",indication_matches[:5]
    return "UNLINKED_SEARCH_LEAD",[]

def suggested_surveys(title):
    t=norm(title)
    categories={
        1:r"patient population|prevalence|incidence|epidemiolog|eligibility|patient subgroup",
        2:r"unmet need|standard of care|treatment resistant|refractory",
        3:r"efficacy|clinical outcome|benefit|response|remission|randomized trial",
        4:r"survival|mortality",
        5:r"quality.of.life|patient.reported|health.related quality",
        6:r"comparative|versus|competition|competing|head.to.head",
        7:r"convenien|administration|adherence|route",
        8:r"safety|tolerability|adverse.event|discontinuation",
        9:r"cost.effectiveness|hospitali|economic burden",
        10:r"insurance|coverage|reimbursement|payer",
        11:r"price|pricing",
        12:r"uptake|adoption|market penetration",
        13:r"international population|global prevalence",
        14:r"additional indication",
        17:r"patent|exclusivity",
    }
    return [str(num) for num,pattern in categories.items() if re.search(pattern,t)]

def as_text(value):
    if value is None:
        return ""
    return short(value,600)

def collect_packets(roster,slots):
    if len(roster)!=len({r["nct"] for r in roster}):
        raise ValueError("DUPLICATE_FOCUS_NCT")
    if len(slots)!=38*len(roster) or \
       len({(s.get("nctId"),s.get("ingredientId")) for s in slots})!=len(slots):
        raise ValueError("INCOMPLETE_SURVEY_SLOT_INVENTORY")
    allowed={r["nct"]:r for r in roster}
    if set(s["nctId"] for s in slots)!=set(allowed):
        raise ValueError("FOCUS_SOURCE_MATRIX_MISMATCH")
    packets=[]
    for nct,row in allowed.items():
        if not NCT.fullmatch(nct):
            raise ValueError("INVALID_FOCUS_NCT")
        path=PACKETS/(nct+".json")
        if not path.exists():
            raise ValueError("SOURCE_PACKET_NOT_CAPTURED: "+nct)
        packet=read_json(path)
        if packet.get("nctId")!=nct or packet.get("ticker")!=row["ticker"] or \
           packet.get("company")!=row["company"]:
            raise ValueError("SOURCE_PACKET_IDENTITY_CONFLICT: "+nct)
        if not isinstance(packet.get("registry"),dict) or \
           not isinstance(packet.get("literatureLeads"),list):
            raise ValueError("SOURCE_PACKET_UNAVAILABLE: "+nct)
        if not packet.get("registrySourceHash"):
            raise ValueError("SOURCE_REGISTRY_PROVENANCE_MISSING: "+nct)
        packets.append(packet)
    return packets

def observed_record(packet,kind,ingredient,group,measure,value,unit="",timeframe="",description=""):
    return {
        "nctId":packet["nctId"],"ticker":packet["ticker"],"company":packet["company"],
        "sourceType":"CLINICALTRIALS_GOV_REGISTRY","observationKind":kind,
        "relatedIngredient":ingredient,
        "treatmentGroup":short(group,140),"measure":short(measure,220),
        "observedValue":as_text(value),"unit":as_text(unit),
        "timeFrame":short(timeframe,180),"context":short(description,550),
        "sourceUrl":packet["registryUrl"],
        "retrievedAt":packet["retrievedAt"],
        "sourceHash":packet["registrySourceHash"],
        "status":REVIEW_STATUS,
        "reviewNote":"Exact-NCT registry observation only; verify endpoint, cohort, denominators, statistical methods and applicable drug/indication before survey acceptance.",
    }

def extract_observations(packet):
    registry=packet["registry"]
    result=[]
    for outcome in registry.get("reportedOutcomeMeasures",[])[:60]:
        group_names={str(g.get("id")):short(g.get("title"),140)
                     for g in outcome.get("groups",[]) if isinstance(g,dict)}
        for item in outcome.get("measurements",[])[:80]:
            value=item.get("value","")
            if value in ("",None):
                continue
            title=short(outcome.get("title",""),220)
            ingredient=("survivalBenefit" if re.search(r"surviv|mortality",title,re.I)
                      else "qualityOfLife" if re.search(r"quality.of.life|patient.reported",title,re.I)
                      else "clinicalBenefit")
            g=str(item.get("groupId",""))
            result.append(observed_record(packet,"REGISTERED_NUMERIC_OUTCOME",
                ingredient,group_names.get(g,g),title,value,
                outcome.get("unit",""),outcome.get("timeFrame",""),
                "Spread: "+as_text(item.get("spread","")) if item.get("spread") not in ("",None) else "No spread recorded in capture"))
    for group in registry.get("adverseEventGroups",[])[:50]:
        title=group.get("title") or group.get("id","")
        for event,label,numerator,denominator in (
            ("SERIOUS_ADVERSE_EVENTS","Serious adverse events","seriousAffected","seriousAtRisk"),
            ("OTHER_ADVERSE_EVENTS","Other adverse events","otherAffected","otherAtRisk")):
            n,d=group.get(numerator),group.get(denominator)
            if not isinstance(n,int) or isinstance(n,bool) or \
               not isinstance(d,int) or isinstance(d,bool) or d<=0 or n<0 or n>d:
                continue
            result.append(observed_record(packet,event,"seriousAes" if event=="SERIOUS_ADVERSE_EVENTS"
                else "safetyAdvantage",title,label,str(n)+"/"+str(d),"patients",
                description="Observed count/at-risk denominator; not exposure adjusted or a safety superiority conclusion"))
    for index,arm in enumerate(registry.get("treatmentArms",[])[:24]):
        if not isinstance(arm,dict) or not arm.get("label"):
            continue
        result.append(observed_record(packet,"REGISTERED_TREATMENT_ARM",
            "convenience",arm.get("label"),"Arm "+str(index+1)+" · "+str(arm.get("type","")),
            "; ".join(arm.get("interventionNames",[])) or arm.get("description",""),
            description="Arm registration only; no inferred convenience advantage or treatment sequence"))
    return result

def triage_all(roster,slots,packets):
    observations=[]
    publications=[]
    categories=Counter()
    for packet in packets:
        registry=packet["registry"]
        observations+=extract_observations(packet)
        seen_urls=set()
        for item in packet["literatureLeads"]:
            url=item.get("url","")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            category,matched=classify_article(item,registry)
            categories[category]+=1
            publications.append({
                "nctId":packet["nctId"],"ticker":packet["ticker"],"company":packet["company"],
                "articleTitle":short(item.get("title"),500),
                "url":url,
                "doi":as_text(item.get("doi")),
                "publicationDate":as_text(item.get("publicationDate")),
                "openAccess":bool(item.get("isOpenAccess")),
                "matchClass":category,
                "matchedTerms":"; ".join(matched),
                "suggestedSurveyNumbers":",".join(suggested_surveys(item.get("title",""))),
                "status":"PUBLICATION_RESEARCH_LEAD_NOT_VALIDATED",
                "reviewNote":"Verify actual article content, exact drug, indication, endpoints and source date; avoid treating search hits as pivotal trial evidence.",
            })
    # Sort strongest source links first, preserving all weak leads for audit.
    priority={"EXACT_NCT_LEAD":0,"DRUG_TITLE_LEAD":1,
              "INDICATION_CONTEXT_ONLY":2,"UNLINKED_SEARCH_LEAD":3}
    publications.sort(key=lambda p:(priority[p["matchClass"]],p["nctId"],p["articleTitle"]))
    observations.sort(key=lambda p:(p["nctId"],p["observationKind"],
                                    p["measure"],p["treatmentGroup"]))
    per_nct=defaultdict(lambda:{"numericOutcomes":0,"seriousEventGroups":0,
                                "otherEventGroups":0,"registeredArms":0,"publications":0,
                                "exactNctPublications":0,"drugTitleLeads":0})
    for o in observations:
        x=per_nct[o["nctId"]]
        if o["observationKind"]=="REGISTERED_NUMERIC_OUTCOME":x["numericOutcomes"]+=1
        elif o["observationKind"]=="SERIOUS_ADVERSE_EVENTS":x["seriousEventGroups"]+=1
        elif o["observationKind"]=="OTHER_ADVERSE_EVENTS":x["otherEventGroups"]+=1
        elif o["observationKind"]=="REGISTERED_TREATMENT_ARM":x["registeredArms"]+=1
    for p in publications:
        x=per_nct[p["nctId"]]
        x["publications"]+=1
        if p["matchClass"]=="EXACT_NCT_LEAD":x["exactNctPublications"]+=1
        if p["matchClass"]=="DRUG_TITLE_LEAD":x["drugTitleLeads"]+=1
    summary={
        "schemaVersion":1,"trials":len(roster),"surveyCategories":20,
        "surveyIngredients":38,"ingredientSlots":len(slots),
        "registryTrials":len(packets),"registryFactObservations":len(observations),
        "numericOutcomeMeasurements":sum(o["observationKind"]=="REGISTERED_NUMERIC_OUTCOME" for o in observations),
        "seriousEventGroupObservations":sum(o["observationKind"]=="SERIOUS_ADVERSE_EVENTS" for o in observations),
        "otherEventGroupObservations":sum(o["observationKind"]=="OTHER_ADVERSE_EVENTS" for o in observations),
        "registeredTreatmentArms":sum(o["observationKind"]=="REGISTERED_TREATMENT_ARM" for o in observations),
        "distinctTrialPublicationLeads":len(publications),
        "publicationCategories":dict(categories),
        "perTrial":[{"nctId":r["nct"],"ticker":r["ticker"],**per_nct[r["nct"]]} for r in roster],
        "verifiedSurveyAnswersFromTriage":0,
        "note":"Source facts and literature relevance candidates do not validate the 38 survey ingredients; existing evidence statuses unchanged.",
    }
    return observations,publications,summary

def run():
    roster_data=read_json(ROSTER)
    catalog=read_json(CATALOG)
    roster=roster_data.get("records",[])
    groups=catalog.get("assessments",[])
    slots=read_json(EVIDENCE).get("slots",[])
    if len(groups)!=20 or sum(len(g.get("ingredients",[])) for g in groups)!=38:
        raise ValueError("SURVEY_TAXONOMY_INTEGRITY_FAILED")
    packets=collect_packets(roster,slots)
    observations,publications,summary=triage_all(roster,slots,packets)
    observation_headers=["nctId","ticker","company","sourceType","observationKind",
                         "relatedIngredient","treatmentGroup","measure","observedValue",
                         "unit","timeFrame","context","sourceUrl","retrievedAt","sourceHash",
                         "status","reviewNote"]
    literature_headers=["nctId","ticker","company","articleTitle","url","doi",
                        "publicationDate","openAccess","matchClass","matchedTerms",
                        "suggestedSurveyNumbers","status","reviewNote"]
    dump_json(OUTPUT/"review-queue.json",
              {"schemaVersion":1,"observations":observations})
    dump_csv(OUTPUT/"review-queue.csv",observation_headers,observations)
    dump_json(OUTPUT/"publication-triage.json",
              {"schemaVersion":1,"articles":publications})
    dump_csv(OUTPUT/"publication-triage.csv",literature_headers,publications)
    dump_json(OUTPUT/"triage-summary.json",summary)
    return summary

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",action="store_true")
    args=parser.parse_args()
    if args.report:
        print(json.dumps(read_json(OUTPUT/"triage-summary.json"),indent=2))
        return
    report=run()
    print(json.dumps({k:report[k] for k in
          ("trials","ingredientSlots","registryFactObservations",
           "numericOutcomeMeasurements","distinctTrialPublicationLeads",
           "publicationCategories","verifiedSurveyAnswersFromTriage")}))
if __name__=="__main__":
    main()
