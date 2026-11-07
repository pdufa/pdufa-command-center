#!/usr/bin/env python3
"""Public ClinicalTrials.gov same-drug *additional indication discovery* for FOCUS.

Each result is an unverified research lead, NOT proof of a distinct approved
indication, commercial rights, active Phase 3, FDA filing or drug equivalence.
A zero match is not "no other indications" if the search failed or truncated.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import json,re,time
from pathlib import Path
from urllib.parse import urlencode
from collect_focus_survey_evidence import load,atomic_json,request_json,utcnow

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
OUTPUT=ROOT/"reports/focus-survey"
STUDIES_API="https://clinicaltrials.gov/api/v2/studies"
REJECT={"placebo","vehicle","sham","saline","control","behavioral support","standard of care",
        "best supportive care","usual care","matching placebo","active comparator"}
NCT=re.compile(r"^NCT\d{8}$")
STATUS="SAME_DRUG_DIFFERENT_CONDITION_RESEARCH_LEAD_RIGHTS_UNCONFIRMED"

def norm(s):
    return " ".join(re.findall(r"[a-z0-9]+",str(s or "").lower()))

def canonical_condition(s):
    """Collapse obvious disease acronyms without equating disease subtypes."""
    key=norm(s)
    return {
        "osa":"obstructive sleep apnea",
        "sleep apnea obstructive":"obstructive sleep apnea",
        "obstructive sleep apnoea":"obstructive sleep apnea",
        "ohcm":"obstructive hypertrophic cardiomyopathy",
        "hae":"hereditary angioedema",
        "uc":"ulcerative colitis",
    }.get(key,key)

def population_only_condition(s):
    """Healthy-volunteer pharmacology is not an additional therapeutic indication."""
    key=norm(s)
    if not key:return True
    return bool(re.fullmatch(
        r"(?:normal )?healthy(?: human)?(?: adult| subject| participant| volunteer| person| men| women| male| female| population| control| individual| individual subjects| adult subjects| adult volunteers| male volunteers| female volunteers| adult participants| volunteers| subjects| participants| people| individuals| males| females)*s?",
        key)) or key in ("health volunteers","healthy volunteers","healthy subject",
                        "healthy subjects","healthy controls","healthy population",
                        "normal volunteers","normal healthy volunteers",
                        "healthy participants","healthy adult volunteers"))

def short(s,maxlen=230):
    return " ".join(str(s or "").split())[:maxlen]

def primary_drug(registry):
    """Use the named active intervention, not placebo/behavioral comparator."""
    for item in registry.get("interventions",[]):
        if not isinstance(item,dict) or item.get("type") not in ("DRUG","BIOLOGICAL","GENETIC","OTHER"):
            continue
        raw=short(item.get("name",""),150)
        if not raw:
            continue
        first=re.split(r"\s*[,;/]\s*|\s+\+\s+",raw)[0]
        first=re.sub(r"\s*\(.*$","",first).strip()
        candidate=norm(first)
        if len(candidate)<4 or candidate in REJECT or not re.search(r"[a-z]",candidate):
            continue
        return first
    return None

def intervention_matches(candidate,name):
    # No ticker-only, substring or simple company name matches.
    a,b=norm(candidate),norm(name)
    if a in REJECT or b in REJECT or len(a)<4:
        return False
    if a==b:
        return True
    return b.startswith(a+" ") and (
        bool(re.search(r"\d",b[len(a):])) or
        any(word in b[len(a):].split() for word in ("tablet","capsule","solution","mg","dose","subcutaneous"))
    )

def study_match(candidate,study):
    protocol=study.get("protocolSection",{})
    identity=protocol.get("identificationModule",{})
    arms=protocol.get("armsInterventionsModule",{})
    status=protocol.get("statusModule",{})
    design=protocol.get("designModule",{})
    nct=identity.get("nctId","")
    if not NCT.fullmatch(str(nct)):
        return None
    matched_intervention=None
    for i in arms.get("interventions",[]):
        if not isinstance(i,dict) or i.get("type") not in ("DRUG","BIOLOGICAL","GENETIC","OTHER"):
            continue
        if intervention_matches(candidate,i.get("name","")):
            matched_intervention=i.get("name")
            break
        if any(intervention_matches(candidate,other) for other in i.get("otherNames",[])):
            matched_intervention=i.get("name")
            break
    if not matched_intervention:return None
    return {
        "nctId":nct,"intervention":short(matched_intervention),
        "conditions":[short(x,170) for x in protocol.get("conditionsModule",{}).get("conditions",[])
                      if isinstance(x,str) and x.strip()][:35],
        "phase":",".join(design.get("phases",[])),
        "overallStatus":short(status.get("overallStatus")),
        "leadSponsor":short(protocol.get("sponsorCollaboratorsModule",{}).get("leadSponsor",{}).get("name")),
        "lastUpdate":short(status.get("studyLastUpdatePostDateStruct",{}).get("date")
                           or status.get("lastUpdatePostDateStruct",{}).get("date"),30),
        "sourceUrl":"https://clinicaltrials.gov/study/"+nct
    }

def search_drug(drug,page_size=150,max_pages=2):
    """Bounded paged search. Record truncation explicitly; never claim exhausted."""
    entries=[]
    token=None
    for page in range(max_pages):
        params={"query.intr":drug,"pageSize":page_size,"format":"json","countTotal":"true"}
        if token:params["pageToken"]=token
        url=STUDIES_API+"?"+urlencode(params)
        data=request_json(url,retries=3,maximum=8_000_000)
        if not isinstance(data,dict) or not isinstance(data.get("studies"),list):
            raise RuntimeError("CLINICALTRIALS_SEARCH_SCHEMA_INVALID")
        entries+=data["studies"]
        token=data.get("nextPageToken")
        if not token:break
        time.sleep(0.4)
    return {
        "drug":drug,"studies":entries,
        "scanTruncated":bool(token),"queryCount":len(entries),
        "searchUrl":"https://clinicaltrials.gov/search?intr="+drug.replace(" ","%20")
    }

def build_index(roster,packets,search_results):
    by_drug=defaultdict(list)
    for row in roster:
        packet=packets[row["nct"]]
        drug=primary_drug(packet["registry"])
        if drug:
            by_drug[norm(drug)].append((row,packet,drug))
    rows=[]
    coverage=[]
    for row in roster:
        packet=packets[row["nct"]]
        drug=primary_drug(packet["registry"])
        current_conditions=set(filter(None,(canonical_condition(x) for x in packet["registry"].get("indications",[])
                                                   if not population_only_condition(x))))
        if not drug:
            coverage.append({"nctId":row["nct"],"ticker":row["ticker"],
               "drugCandidate":"","searchStatus":"DRUG_IDENTITY_UNRESOLVED",
               "candidateOtherIndicationTrials":0,"searchTruncated":False,
               "searchResultCount":0,"sourceNote":"Trial has no unambiguous active drug field"})
            continue
        response=search_results.get(norm(drug))
        if not response or response.get("error"):
            coverage.append({"nctId":row["nct"],"ticker":row["ticker"],
               "drugCandidate":drug,"searchStatus":"SEARCH_UNAVAILABLE",
               "candidateOtherIndicationTrials":0,"searchTruncated":False,
               "searchResultCount":0,"sourceNote":response.get("error","No query result") if response else "No query"})
            continue
        found_ncts=set()
        for raw in response.get("studies",[]):
            candidate=study_match(drug,raw)
            if not candidate or candidate["nctId"]==row["nct"]:
                continue
            diff=[c for c in candidate["conditions"]
                  if not population_only_condition(c) and canonical_condition(c) not in current_conditions]
            if not diff or candidate["nctId"] in found_ncts:
                continue
            found_ncts.add(candidate["nctId"])
            rows.append({"sourceFocusNct":row["nct"],"ticker":row["ticker"],
                "company":row["company"],"drugCandidate":drug,
                "registeredSourceConditions":sorted(packet["registry"].get("indications",[])),
                "otherNct":candidate["nctId"],"otherConditions":diff,
                "otherPhases":candidate["phase"],
                "otherTrialStatus":candidate["overallStatus"],
                "otherTrialSponsor":candidate["leadSponsor"],
                "registeredIntervention":candidate["intervention"],
                "sourceUrl":candidate["sourceUrl"],"sourceLastUpdated":candidate["lastUpdate"],
                "searchTruncated":bool(response["scanTruncated"]),
                "evidenceStatus":STATUS,
                "nextStep":"Independently reconcile same drug/formulation, different indication, sponsor, territorial rights, and program phase before survey validation.",
                "warning":"Different registry condition strings may still be synonyms, subtypes, or alternative eligibility labels; healthy-volunteer studies are excluded."})
        coverage.append({"nctId":row["nct"],"ticker":row["ticker"],
            "drugCandidate":drug,"searchStatus":"PARTIAL_SEARCH" if response["scanTruncated"] else "SEARCHED",
            "candidateOtherIndicationTrials":len(found_ncts),
            "searchTruncated":bool(response["scanTruncated"]),
            "searchResultCount":response["queryCount"],
            "sourceNote":"Candidate links, not confirmed marketable other indications"})
    if len(coverage)!=len(roster):raise ValueError("FOCUS_OTHER_INDICATION_COVERAGE_INCOMPLETE")
    return rows,coverage

def run():
    roster=load(ROSTER)["records"]
    if not 20<=len(roster)<=100 or len({r["nct"] for r in roster})!=len(roster):
        raise ValueError("INVALID_FOCUS_ROSTER")
    packets={}
    for row in roster:
        p=load(PACKETS/(row["nct"]+".json"))
        if p.get("nctId")!=row["nct"] or p.get("ticker")!=row["ticker"] or not p.get("registry"):
            raise ValueError("EXACT_NCT_PACKET_INVALID")
        packets[row["nct"]]=p
    drugs={norm(primary_drug(p["registry"])):primary_drug(p["registry"])
           for p in packets.values() if primary_drug(p["registry"])}
    searches={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending={pool.submit(search_drug,drug):key for key,drug in drugs.items()}
        for future in as_completed(pending):
            key=pending[future]
            try:searches[key]=future.result()
            except Exception as exc:searches[key]={"error":type(exc).__name__+":"+short(str(exc),170)}
    rows,coverage=build_index(roster,packets,searches)
    summary={"schemaVersion":1,"generatedAt":utcnow(),"focusTrials":len(roster),
       "uniqueDrugQueries":len(drugs),
       "searchesSuccessful":sum("error" not in x for x in searches.values()),
       "searchesUnavailable":sum("error" in x for x in searches.values()),
       "candidateOtherIndicationLinks":len(rows),
       "focusTrialsWithCandidates":sum(bool(x["candidateOtherIndicationTrials"]) for x in coverage),
       "searchTruncatedDrugs":[x["drug"] for x in searches.values() if x.get("scanTruncated")],
       "verifiedAdditionalIndicationSurveyAnswers":0,
       "warning":"Candidate trial links only. Different registry conditions can be synonyms. Product rights and true additional indications remain unverified."}
    atomic_json(OUTPUT/"additional-indication-research.json",
        {"schemaVersion":1,"candidates":rows,"byTrial":coverage})
    atomic_json(OUTPUT/"additional-indication-coverage.json",summary)
    print(json.dumps(summary,sort_keys=True))
    return summary

if __name__=="__main__":
    run()
