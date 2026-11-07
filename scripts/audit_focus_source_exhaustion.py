#!/usr/bin/env python3
"""Audit real source attempts for EVERY active FOCUS survey question.

Never infer 'no more evidence' from one 403, missing ClinicalTrials.gov results,
a saved link, or an issuer-level document. Every applicable source family needs
a real search or an explicit blocker. Public sources, exact match, review, and
applicability remain separate. The audit creates a continuation queue, NOT
survey results or an FDA/RAAS rating.
"""
from __future__ import annotations
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/focus-survey"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
CATALOG=ROOT/"data/phase3_benefit_survey_catalog.json"

SOURCES={
 1:("REGISTRY","COMPANY","LITERATURE","NIH_EPIDEMIOLOGY"),
 2:("COMPANY","FDA","LITERATURE","CLINICAL_GUIDELINES"),
 3:("REGISTRY","COMPANY","LITERATURE"),
 4:("REGISTRY","COMPANY","LITERATURE"),
 5:("REGISTRY","COMPANY","LITERATURE"),
 6:("REGISTRY","COMPANY","FDA","LITERATURE"),
 7:("REGISTRY","COMPANY","FDA","CLINICAL_GUIDELINES"),
 8:("REGISTRY","COMPANY","FDA","LITERATURE"),
 9:("REGISTRY","COMPANY","LITERATURE","CMS_PAYER"),
 10:("FDA","COMPANY","CMS_PAYER"),
 11:("COMPANY","SEC","CMS_PAYER"),
 12:("COMPANY","SEC","NIH_EPIDEMIOLOGY","CLINICAL_GUIDELINES"),
 13:("COMPANY","LITERATURE","NIH_EPIDEMIOLOGY"),
 14:("REGISTRY","COMPANY","LITERATURE"),
 15:("COMPANY","SEC","NIH_EPIDEMIOLOGY","CMS_PAYER"),
 16:("COMPANY","SEC"),
 17:("COMPANY","FDA","PATENT_EXCLUSIVITY"),
 18:("COMPANY","SEC"),
 19:("COMPANY","SEC"),
 20:("COMPANY","SEC"),
}
ALL=("COMPANY","REGISTRY","FDA","LITERATURE","SEC",
     "NIH_EPIDEMIOLOGY","CLINICAL_GUIDELINES","CMS_PAYER","PATENT_EXCLUSIVITY")
UNSEARCHED="NOT_YET_SEARCHED"
BLOCKED="ACCESS_BLOCKED_RETRY_ANOTHER_AVENUE"
NO_MATCH="SEARCHED_NO_INGREDIENT_MATCH"
SOURCE_LEAD="EVIDENCE_LEAD_REQUIRES_REVIEW"
GENERIC_LEAD="BACKGROUND_OR_ISSUER_LINK_NOT_ANSWER"
ACCEPTED="SOURCE_REVIEWED_INPUT_EXISTS"
NON_EXHAUSTED=frozenset((UNSEARCHED,BLOCKED,SOURCE_LEAD,GENERIC_LEAD))
NEXT_ACTION={
 "COMPANY":"Search official product pipeline, full investor-relations archive, alternate company domain, distributed release and original presentation; check exact drug, indication, trial",
 "REGISTRY":"Inspect exact NCT protocol, posted results, adverse events, analysis denominator and submission history",
 "FDA":"Search Drugs@FDA, approved labels, product/application archives and the actual application-stage evidence without inferring approval from competitor labels",
 "LITERATURE":"Search exact NCT, drug aliases, indication, conference abstracts and peer-reviewed original trials, then open and read candidate results",
 "SEC":"Read issuer-hosted SEC filings, 10-K/10-Q/20-F/8-K/6-K and exhibits; if SEC 403 persists, use company IR originals rather than mark absent",
 "NIH_EPIDEMIOLOGY":"Search CDC/NIH/SEER and disease registries for dated diagnosed and treatment-eligible populations by jurisdiction",
 "CLINICAL_GUIDELINES":"Search disease-society clinical practice guidelines and current standard-of-care recommendations",
 "CMS_PAYER":"Search CMS public payment files, original formularies, reimbursement policies, published pricing and payer criteria; unknown net prices require modeled scenarios",
 "PATENT_EXCLUSIVITY":"Search FDA Orange Book, Purple Book, USPTO patents and official exclusivity records; do not infer unverified commercial rights",
}
def load(path):
 return json.loads(path.read_text(encoding="utf-8"))
def optional(path,fallback):
 return load(path) if path.exists() else fallback
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 temporary=path.with_suffix(path.suffix+".tmp")
 temporary.write_text(json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 temporary.replace(path)
def normalize_url(url):
 try:
  p=urlparse(str(url))
  return str(url) if p.scheme=="https" and p.hostname else None
 except (ValueError,TypeError):return None

def assess_source(name,trial,ingredient,number,context):
 nct,ticker=trial["nct"],trial["ticker"]
 registry=context["packets"].get(nct,{})
 issuer=context["issuer"].get(ticker,{})
 direct=context["direct"].get(nct,[])
 five=context["five"].get((nct,name),[])
 errors=context["errors"].get((nct,name),[])
 slot=context["slots"][(nct,ingredient)]
 ptrs=slot.get("registryLeads",[])
 url=None
 detail=""
 if name=="REGISTRY":
  if not registry.get("registry") or registry.get("nctId")!=nct:
   return {"status":BLOCKED,"reason":"Official exact-NCT study not retrieved",
           "url":"https://clinicaltrials.gov/study/"+nct}
  url="https://clinicaltrials.gov/study/"+nct
  status=SOURCE_LEAD if ptrs else NO_MATCH
  detail="Registry captured; absence of posted results is not proof no company result exists"
 elif name=="COMPANY":
  related=[x for x in direct if ingredient in x.get("ingredientCandidates",[]) and
           x.get("sourceMatch") in ("EXACT_NCT","DRUG_AND_INDICATION") and
           x.get("status")=="SOURCE_CAPTURED_NEEDS_REVIEW"]
  linked=[x for x in direct if x.get("status")=="SOURCE_CAPTURED_NEEDS_REVIEW"]
  failures=[x for x in direct if x.get("status")=="SOURCE_LINK_ONLY_CONTENT_UNAVAILABLE"]
  url=normalize_url((related or linked or failures or direct or [{}])[0].get("url"))
  if related:
   status=SOURCE_LEAD
   detail="Full official issuer document indexed for this survey; still requires ingredient interpretation"
  elif linked:
   status=GENERIC_LEAD
   detail="Issuer page accessed but ingredient-specific clinical/commercial claim not independently reviewed"
  elif failures or errors:
   status=BLOCKED
   detail="Issuer document retrieval blocked or unavailable; company domain, syndication, presentations and regulatory exhibits remain alternatives"
  else:
   status=UNSEARCHED
   detail="No company issuer document search receipt"
 elif name=="LITERATURE":
  relevant=[x for x in five if ingredient in x.get("ingredientCandidates",[]) and
      x.get("sourceMatch") in ("EXACT_NCT","DRUG_AND_INDICATION") ]
  indexed=[x for x in context["publications"].get(nct,[]) if
      str(number) in str(x.get("suggestedSurveyNumbers","")).split(",") and
      x.get("matchClass") in ("EXACT_NCT_LEAD","DRUG_TITLE_LEAD")]
  url=normalize_url((relevant or indexed or five or [{}])[0].get(
      "sourceUrl" if relevant or five else "url"))
  if relevant or indexed:
   status=SOURCE_LEAD
   detail="Candidate indexed trial/drug publication found; read original full text before survey conclusion"
  elif errors:
   status=BLOCKED;detail="Scientific literature query returned an error; retry alternative index"
  elif five or context["publications"].get(nct):
   status=GENERIC_LEAD;detail="Only general or loosely linked articles; repeat exact drug/trial search"
  else:
   status=NO_MATCH;detail="Europe PMC queries performed with no usable trial-specific hit; try PubMed, journals and conference proceedings"
 elif name=="FDA":
  url=normalize_url((five or [{}])[0].get("sourceUrl"))
  if errors:
   status=BLOCKED;detail="FDA search was blocked; open Drugs@FDA and FDA-label sources independently"
  elif five:
   status=GENERIC_LEAD
   detail="FDA index/label discovery is not proof of exact trial product approval or relevant comparator"
  elif context["source_five"].get(nct) is not None:
   status=NO_MATCH;detail="openFDA drug and label queries returned no matching lead; not an FDA application adjudication"
  else:
   status=UNSEARCHED;detail="FDA query receipt unavailable"
 elif name=="SEC":
  links=[x for x in five if x.get("sourceType")=="SEC"]
  url=normalize_url((links or [{}])[0].get("sourceUrl"))
  status_=issuer.get("status","")
  if status_=="SEC_ISSUER_IDENTITY_CONFIRMED_RIGHTS_NOT_ESTABLISHED":
   status=GENERIC_LEAD if issuer.get("facts") or links else NO_MATCH
   detail="Issuer facts/filings do not establish indication rights, product-specific licensing or forecast"
  elif status_=="SEC_SOURCE_UNAVAILABLE":
   status=BLOCKED
   detail=str(issuer.get("sourceError","SEC access failed"))+"; issuer-hosted filings and exhibits still need review"
  elif links:
   status=GENERIC_LEAD;detail="Issuer SEC filing URL exists but filing content not verified"
  else:
   status=UNSEARCHED;detail="No SEC issuer research receipt"
 else:
  status=UNSEARCHED
  detail="Dedicated source family not yet searched under ingredient-specific criteria"
 if name=="COMPANY" and errors and status not in (SOURCE_LEAD,GENERIC_LEAD):
  detail+=(("; "+str(errors[0])) if errors else "")
 return {"status":status,"reason":detail,"url":url}

def make_context(roster):
 by={r["nct"]:r for r in roster}
 slots=load(OUT/"evidence.json").get("slots",[])
 if len(slots)!=38*len(by) or len({(x.get("nctId"),x.get("ingredientId")) for x in slots})!=len(slots):
  raise ValueError("INVALID_FOCUS_SURVEY_EVIDENCE_MATRIX")
 slotmap={(x["nctId"],x["ingredientId"]):x for x in slots}
 packets={r["nct"]:optional(OUT/"source-packets"/(r["nct"]+".json"),{}) for r in roster}
 lead_doc=optional(OUT/"five-source-leads.json",{"records":[]})
 five=defaultdict(list)
 for x in lead_doc.get("records",[]):
  if x.get("nctId") not in by:raise ValueError("EXTERNAL_SOURCE_OUTSIDE_FOCUS")
  five[(x["nctId"],x["sourceType"])].append(x)
 summary=optional(OUT/"five-source-summary.json",{})
 errors=defaultdict(list)
 for x in summary.get("sourceErrors",[]):
  key=(x.get("nctId"),x.get("sourceType"))
  if key[0] in by:errors[key].append(x.get("error"))
  if key[0] is None and x.get("ticker"):
   for trial in roster:
    if trial["ticker"]==x["ticker"]:
     errors[(trial["nct"],x.get("sourceType"))].append(x.get("error"))
 direct=defaultdict(list)
 doc=optional(OUT/"company-direct-source-ledger.json",{"rows":[]})
 for x in doc.get("rows",[]):
  if x.get("nctId") not in by:raise ValueError("DIRECT_SOURCE_OUTSIDE_FOCUS")
  direct[x["nctId"]].append(x)
 publications=defaultdict(list)
 for x in optional(OUT/"publication-triage.json",{"articles":[]}).get("articles",[]):
  if x.get("nctId") not in by:raise ValueError("PUBLICATION_OUTSIDE_FOCUS")
  publications[x["nctId"]].append(x)
 sec_doc=optional(OUT/"sec-companyfacts.json",{"issuers":[]})
 issuer={x["ticker"]:x for x in sec_doc.get("issuers",[])}
 return {"slots":slotmap,"packets":packets,"five":five,
  "source_five":{x["nctId"]:x for x in summary.get("perTrial",[])},
  "errors":errors,"direct":direct,"publications":publications,"issuer":issuer}

def audit(roster,catalog,context):
 canonical=[(g["rank"],g["name"],x["id"],x["label"]) for g in catalog for x in g["ingredients"]]
 if len(canonical)!=38 or len({x[2] for x in canonical})!=38 or \
    len(catalog)!=20 or [g["rank"] for g in catalog]!=list(range(1,21)):
  raise ValueError("INVALID_CANONICAL_SURVEY_TAXONOMY")
 if len(roster)!=29 or len({r["nct"] for r in roster})!=29:
  raise ValueError("CURRENT_FOCUS_ROSTER_IDENTITY_CHANGED")
 rows=[]
 counts=Counter()
 family_counts=Counter()
 for trial in roster:
  for number,survey,ingredient,label in canonical:
   slot=context["slots"].get((trial["nct"],ingredient))
   if not slot:
    raise ValueError("MISSING_EXACT_FOCUS_INGREDIENT")
   required=SOURCES[number]
   attempts={kind:assess_source(kind,trial,ingredient,number,context) for kind in required}
   for kind,item in attempts.items():
    family_counts[(kind,item["status"])]+=1
   statuses=[x["status"] for x in attempts.values()]
   if slot["status"]=="VERIFIED":
    action="REVIEWED_FACT_PRESENT_ADDITIONAL_CONTEXT_MAY_BE_MISSING"
   elif SOURCE_LEAD in statuses:
    action="READ_AND_ADJUDICATE_CAPTURED_PRIMARY_EVIDENCE"
   elif BLOCKED in statuses:
    action="UNBLOCK_WITH_INDEPENDENT_PRIMARY_SOURCE"
   elif UNSEARCHED in statuses:
    action="SEARCH_UNVISITED_SOURCE_FAMILY"
   else:
    action="VERIFY_EXTERNAL_PRIMARY_SOURCES_OR_MODEL_WITH_ASSUMPTIONS"
   blocked=[k for k,x in attempts.items() if x["status"]==BLOCKED]
   unsearched=[k for k,x in attempts.items() if x["status"]==UNSEARCHED]
   leads=[k for k,x in attempts.items() if x["status"]==SOURCE_LEAD]
   # Distinguish source-access, research worklist and genuinely completed answers.
   attempted=sum(x["status"]!=UNSEARCHED for x in attempts.values())
   row={"nctId":trial["nct"],"ticker":trial["ticker"],
    "surveyNumber":number,"surveyName":survey,"ingredientId":ingredient,
    "ingredientName":label,"evidenceStatus":slot["status"],
    "requiredSourceFamilies":list(required),
    "sourcesAttempted":attempted,"sourcesRequired":len(required),
    "unsearchedFamilies":unsearched,"blockedFamilies":blocked,
    "evidenceLeadFamilies":leads,
    "sourceReceipts":attempts,"nextAction":action,
    "suggestedFallbacks":[NEXT_ACTION[k] for k in blocked+unsearched],
    "isResearchExhausted":False,
    "isVerifiedIngredient":slot["status"]=="VERIFIED",
    "warning":"Do not say 'no more evidence' when a primary source is blocked, unsearched, or unreviewed."}
   counts[action]+=1
   rows.append(row)
 if len(rows)!=len(roster)*38:raise ValueError("INVALID_AUDIT_POPULATION")
 summary={"schemaVersion":1,"trials":len(roster),"surveys":20,"ingredients":38,
  "surveySlots":len(rows),"sourceReceipts":sum(x["sourcesRequired"] for x in rows),
  "sourceAttempts":sum(x["sourcesAttempted"] for x in rows),
  "blockedSourceSlots":sum(bool(x["blockedFamilies"]) for x in rows),
  "unsearchedSourceSlots":sum(bool(x["unsearchedFamilies"]) for x in rows),
  "slotsWithEvidenceLeads":sum(bool(x["evidenceLeadFamilies"]) for x in rows),
  "verifiedIngredientInputs":sum(x["isVerifiedIngredient"] for x in rows),
  "researchExhausted":sum(x["isResearchExhausted"] for x in rows),
  "nextActions":dict(counts),"familyStatuses":[
     {"family":k[0],"status":k[1],"count":v} for k,v in sorted(family_counts.items())],
  "meaning":"This measures which source avenues were tried, which failed, and which still require review. Not a verified survey score."}
 return rows,summary

def run():
 roster=load(ROSTER)["records"]
 catalog=load(CATALOG)["assessments"]
 context=make_context(roster)
 items,summary=audit(roster,catalog,context)
 save(OUT/"source-exhaustion-audit.json",{"schemaVersion":1,"records":items})
 save(OUT/"source-exhaustion-summary.json",summary)
 columns=["nctId","ticker","surveyNumber","surveyName","ingredientId","ingredientName",
  "evidenceStatus","requiredSourceFamilies","sourcesAttempted","sourcesRequired",
  "unsearchedFamilies","blockedFamilies","evidenceLeadFamilies",
  "nextAction","isResearchExhausted","isVerifiedIngredient","suggestedFallbacks"]
 with (OUT/"source-exhaustion-audit.csv").open("w",encoding="utf-8",newline="") as handle:
  writer=csv.DictWriter(handle,fieldnames=columns,extrasaction="ignore")
  writer.writeheader()
  for row in items:
   flat={**row}
   for key in ("requiredSourceFamilies","unsearchedFamilies","blockedFamilies",
               "evidenceLeadFamilies","suggestedFallbacks"):
    flat[key]=" | ".join(row[key])
   writer.writerow(flat)
 print(json.dumps(summary,sort_keys=True))
 return summary
if __name__=="__main__":
 run()
