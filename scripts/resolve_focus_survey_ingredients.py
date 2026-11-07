#!/usr/bin/env python3
"""100%-enumerated evidence-disposition worklist for all active FOCUS surveys.

This resolves the *research action* for each of 29 x 38 slots; it does not
claim 100% verified medical evidence, nor invent PDUFA, efficacy, pricing,
regulatory, valuation or stock scores. Every source lead is traceable to exact
NCT and exact original ingredient ID, and unknown remains unknown.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/focus-survey"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
CATALOG=ROOT/"data/phase3_benefit_survey_catalog.json"
REGISTRY_PATH=OUT/"source-packets"
NCT=re.compile(r"^NCT\d{8}$")
CLINICAL_URL="https://clinicaltrials.gov/study/"
FDA_URL="https://www.accessdata.fda.gov/scripts/cder/daf/"
SEC_URL="https://www.sec.gov/edgar/search/"
CMS_URL="https://www.cms.gov/medicare/payment/part-b-drugs"
PUBMED_URL="https://pubmed.ncbi.nlm.nih.gov/"
NIH_URL="https://www.cdc.gov/nchs/"
PATENT_URL="https://www.accessdata.fda.gov/scripts/cder/ob/"
NONCLINICAL={ "payerAccess","treatmentPrice","adoption","switchingPool","internationalPatients",
    "additionalIndications","peakAnnualSales","revenueGrowth","exclusivity",
    "licensingValue","valuationImpact","shareholderRisk","costDifference","valuePerOutcome"}
MODEL_DEPENDENT={"treatmentPrice","adoption","switchingPool","internationalPatients",
    "peakAnnualSales","revenueGrowth","valuationImpact","shareholderRisk","costDifference","valuePerOutcome"}
REGISTRY_FACTS={
 "eligibleUsPatients":("eligibilityCriteria","enrollment"),
 "bestSubgroup":("subgroupOutcomes",),
 "standardOfCare":("treatmentArms",),
 "treatmentResistantBenefit":("eligibilityCriteria","subgroupOutcomes"),
 "clinicalBenefit":("reportedOutcomeMeasures",),
 "magnitude":("reportedOutcomeMeasures",),
 "meaningfulBenefit":("reportedOutcomeMeasures",),
 "durability":("durabilityMeasures",),
 "responseRemission":("responseMeasures",),
 "timeToResponse":("timeToResponseMeasures",),
 "survivalBenefit":("survivalMeasures",),
 "qualityOfLife":("qualityOfLifeMeasures",),
 "closestCompetitor":("treatmentArms",),
 "headToHead":("activeComparatorResults",),
 "convenience":("treatmentArms",),
 "treatmentSequence":("eligibilityCriteria","treatmentArms"),
 "safetyAdvantage":("adverseEventGroups",),
 "seriousAes":("seriousEventGroups",),
 "discontinuation":("reportedWithdrawals",),
 "hospitalizationReduction":("reportedOutcomeMeasures",),
}
SOURCES={
 1:"US epidemiology, confirmed indication and eligible treatment-line definition",
 2:"Guidelines and FDA-labeled current standard of care, refractory treatment data",
 3:"Exact trial primary endpoints, aligned comparator, absolute treatment effect, precision",
 4:"Prespecified survival outcomes and risk-set follow-up if relevant",
 5:"Validated patient-reported outcomes, instruments, missingness",
 6:"FDA-labeled indication-matched competitors and same-line pivotal trial evidence",
 7:"Dose/route/frequency, monitoring and same-line current treatment regimen",
 8:"SAE incidence/exposure and discontinuation reasons with comparable denominators",
 9:"Hospitalization results, payer costs, comparator and cost-effectiveness horizon",
 10:"Dated payer formulary/coverage, prior-authorization restrictions",
 11:"Public price or a documented modeled gross/net price, dosing and territory",
 12:"Eligible treated denominator, treatment switching and adoption assumptions",
 13:"Country-specific diagnosis, eligibility and reimbursement evidence",
 14:"Additional verified NCT IDs for same therapy in distinct indication programs",
 15:"Eligible population, price, uptake, rights and low/base/high forecast scenarios",
 16:"Dated issuer revenue baseline, launch ramp, treatment duration and competition",
 17:"FDA Orange/Purple Book, patent claims, regulatory exclusivity, litigation",
 18:"SEC-filed material contracts, partners, royalties and territorial rights",
 19:"Cash/debt, discounting, dilution, territory-specific projected cash flows",
 20:"Share count, liabilities, financing risk and transparent scenario sensitivities",
}
PRIMARY={
 1:NIH_URL,2:FDA_URL,3:CLINICAL_URL,4:CLINICAL_URL,5:CLINICAL_URL,
 6:FDA_URL,7:FDA_URL,8:CLINICAL_URL,9:CMS_URL,10:CMS_URL,
 11:CMS_URL,12:NIH_URL,13:NIH_URL,14:CLINICAL_URL,
 15:SEC_URL,16:SEC_URL,17:PATENT_URL,18:SEC_URL,19:SEC_URL,20:SEC_URL,
}
# A registry observation about a similar endpoint is a research lead, not proof
# of an advantage. Endpoint comparisons are NOT automatically calculated.
def load(path):
 return json.loads(path.read_text(encoding="utf-8"))
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix(path.suffix+".tmp")
 tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 tmp.replace(path)
def slim(s,maxlen=340):
 return " ".join(str(s or "").split())[:maxlen]
def observed(v):
 if v is None:return False
 if isinstance(v,(list,dict)):return bool(v)
 return bool(str(v).strip())
def extract_program(registry):
 indications=list(dict.fromkeys(slim(s,160) for s in registry.get("indications",[]) if slim(s)))
 interventions=[]
 for v in registry.get("interventions",[]):
  name=slim(v.get("name",""),160) if isinstance(v,dict) else ""
  if name and not re.fullmatch("(?i)placebo|saline|behavioral support|vehicle|usual care",name):
   interventions.append(name)
 return indications, list(dict.fromkeys(interventions))
def find_review_context(ingredient,slot,reg,packet,pubs,clinical):
 pointers=[]
 for field in REGISTRY_FACTS.get(ingredient,()):
  value=reg.get(field)
  if not observed(value):continue
  # Registered protocol eligibility and treatment arms can support research;
  # they are not the desired population size, standard of care or convenience comparison.
  pointers.append("registry."+field)
 observations=[o for o in clinical if o.get("relatedIngredient")==ingredient]
 if observations and "registry." + ("reportedOutcomeMeasures" if ingredient in
   ("clinicalBenefit","magnitude","meaningfulBenefit","responseRemission")
   else "adverseEventGroups") not in pointers:
  pointers.append("source-observations:"+str(len(observations)))
 relevant=[]
 for p in pubs:
  nums=str(p.get("suggestedSurveyNumbers","")).split(",")
  if str(slot["surveyNumber"]) in nums and p.get("matchClass") in ("EXACT_NCT_LEAD","DRUG_TITLE_LEAD"):
   relevant.append(p)
 relevant.sort(key=lambda x:0 if x["matchClass"]=="EXACT_NCT_LEAD" else 1)
 return pointers, observations, relevant[:3]

def build(roster,catalog,slots,packets,review_observations,publications,previous_statuses=None,external_sources=None,company_links=None):
 if len(catalog)!=20 or [g.get("rank") for g in catalog]!=list(range(1,21)):
  raise ValueError("CANONICAL_20_SURVEYS_INVALID")
 ingredients=[(g["rank"],g["name"],x["id"],x["label"],x.get("evidenceRequirement",""))
  for g in catalog for x in g["ingredients"]]
 if len(ingredients)!=38 or len({x[2] for x in ingredients})!=38:
  raise ValueError("CANONICAL_38_INGREDIENTS_INVALID")
 by_id={r["nct"]:r for r in roster}
 if len(by_id)!=len(roster) or not 20<=len(roster)<=100 or \
    any(not NCT.fullmatch(nct) for nct in by_id):
  raise ValueError("FOCUS_NCT_IDENTITY_INVALID")
 if len(slots)!=len(roster)*38 or len({(s["nctId"],s["ingredientId"]) for s in slots})!=len(slots):
  raise ValueError("FOCUS_SURVEY_INVENTORY_INCOMPLETE")
 if set(s["nctId"] for s in slots)!=set(by_id):
  raise ValueError("FOCUS_ROSTER_SURVEY_MISMATCH")
 by_slot={(s["nctId"],s["ingredientId"]):s for s in slots}
 for nct in by_id:
  p=packets.get(nct)
  if not p or p.get("nctId")!=nct or not p.get("registrySourceHash") or \
   p.get("ticker")!=by_id[nct]["ticker"] or \
   not isinstance(p.get("registry"),dict):
   raise ValueError("EXACT_REGISTRY_PACKET_REQUIRED:"+nct)
 by_reviews=defaultdict(list)
 for obj in review_observations:
  if obj["nctId"] not in by_id:raise ValueError("OUTSIDE_ROSTER_REVIEW")
  by_reviews[obj["nctId"]].append(obj)
 by_pubs=defaultdict(list)
 for obj in publications:
  if obj["nctId"] not in by_id:raise ValueError("OUTSIDE_ROSTER_PUBLICATION")
  by_pubs[obj["nctId"]].append(obj)
 all_ingredient_ids={item[2] for item in ingredients}
 by_external=defaultdict(list)
 for obj in external_sources or []:
  nct=obj.get("nctId")
  if nct not in by_id or obj.get("ticker")!=by_id[nct]["ticker"]:
   raise ValueError("EXTERNAL_FOCUS_SOURCE_IDENTITY_MISMATCH")
  if obj.get("status")!="SOURCE_CAPTURED_NEEDS_REVIEW" or obj.get("reviewed") is not False or \
     not str(obj.get("sourceUrl","")).startswith("https://"):
   raise ValueError("EXTERNAL_SOURCE_NOT_PRIMARY_RESEARCH_LEAD")
  if any(x not in all_ingredient_ids for x in obj.get("ingredientCandidates",[])):
   raise ValueError("EXTERNAL_SOURCE_NONCANONICAL_INGREDIENT")
  if obj.get("sourceType") not in ("COMPANY","LITERATURE","FDA","SEC"):
   raise ValueError("EXTERNAL_SOURCE_TYPE_UNSUPPORTED")
  if obj.get("sourceMatch") not in ("EXACT_NCT","DRUG_AND_INDICATION"):
   continue
  for ingredient in obj.get("ingredientCandidates",[]):
   by_external[(nct,ingredient)].append(obj)
 by_company_links=defaultdict(list)
 for obj in company_links or []:
  nct=obj.get("nctId")
  if nct not in by_id or obj.get("ticker")!=by_id[nct]["ticker"]:
   raise ValueError("DIRECT_ISSUER_LINK_IDENTITY_MISMATCH")
  if obj.get("url") and str(obj["url"]).startswith("https://"):
   by_company_links[nct].append(obj["url"])
 out=[]
 for row in roster:
  nct=row["nct"]
  packet=packets[nct]
  reg=packet["registry"]
  indications,interventions=extract_program(reg)
  for number,name,id,label,requirement in ingredients:
   slot=by_slot.get((nct,id))
   if not slot or slot["surveyNumber"]!=number or slot["surveyName"]!=name:
    raise ValueError("MISSING_CANONICAL_INGREDIENT:"+nct+":"+id)
   pointers,observations,links=find_review_context(
    id,slot,reg,packet,by_pubs[nct],by_reviews[nct])
   public_candidates=by_external[(nct,id)]
   # The first URL is a citation/research lead, not an accepted score.
   public_candidates=sorted(public_candidates,key=lambda x:
     (0 if x.get("sourceMatch")=="EXACT_NCT" else 1,
      0 if x.get("sourceType")=="COMPANY" else 1,
      str(x.get("sourceUrl",""))))
   already_verified=slot.get("status")=="VERIFIED"
   if already_verified:
    if not slot.get("reviewedSourceUrl") or not slot.get("reviewedSourceDate"):
     raise ValueError("VERIFIED_WITHOUT_PROVENANCE")
    disposition="REVIEWED_ANSWER_PRESENT"
   elif pointers or observations:
    disposition="PRIMARY_SOURCE_INTERPRETATION_REQUIRED"
   elif links:
    disposition="PUBLICATION_CONTENT_REVIEW_REQUIRED"
   elif public_candidates:
    disposition="EXTERNAL_PRIMARY_SOURCE_CONTENT_REVIEW_REQUIRED"
   elif id in MODEL_DEPENDENT:
    disposition="MODELING_INPUTS_UNAVAILABLE"
   else:
    disposition="ADDITIONAL_PRIMARY_RESEARCH_REQUIRED"
   # 100% disposition is not 100% verified evidence.
   official=CLINICAL_URL+nct
   if pointers: next_url=official
   elif links: next_url=links[0].get("url",PRIMARY[number])
   elif public_candidates: next_url=public_candidates[0]["sourceUrl"]
   elif number<=8 and by_company_links.get(nct):
    next_url=by_company_links[nct][0]
   else: next_url=(official if PRIMARY[number]==CLINICAL_URL else PRIMARY[number])
   source_urls=[official] if pointers else []
   source_urls.extend(x.get("url") for x in links if x.get("url"))
   source_urls.extend(x.get("sourceUrl") for x in public_candidates if x.get("sourceUrl"))
   source_urls=list(dict.fromkeys(source_urls))[:4]
   status=slot.get("status","MISSING")
   out.append({
    "nctId":nct,"ticker":row["ticker"],"company":row["company"],
    "drugCandidates":interventions,"registryIndications":indications,
    "drugIndicationIdentityStatus":"CANDIDATE_FROM_REGISTRY_CONFIRM_PRODUCT_RIGHTS",
    "surveyNumber":number,"surveyName":name,"ingredientId":id,"ingredientName":label,
    "priorEvidenceStatus":status,
    "researchDisposition":disposition,
    "reviewedAnswer":slot.get("reviewedValue") if already_verified else None,
    "supportingRegistryPointers":pointers,
    "primaryObservationCount":len(observations),
    "publicationReviewLeads":len(links),
    "externalPublicSourceLeads":len(public_candidates),
    "externalPublicSourceTypes":list(dict.fromkeys(x.get("sourceType") for x in public_candidates)),
    "linkedCompanyDisclosureSources":len(by_company_links.get(nct,[])),
    "sourceUrls":source_urls,
    "recommendedSource":next_url,
    "missingEvidenceRequirement":requirement,
    "nextEvidenceStep":SOURCES[number],
    "requiresModelAssumptions":id in MODEL_DEPENDENT,
    "applicability":"NOT_YET_ADJUDICATED",
    "isSurveyAnswerVerified":already_verified,
    "sourcePacketHash":packet["registrySourceHash"],
    "warning":"This is an auditable research disposition, not an independent survey result.",
   })
 if len(out)!=len(roster)*38:
  raise ValueError("SURVEY_DISPOSITIONS_INCOMPLETE")
 return out

def summary_of(rows,roster):
 dispositions=Counter(x["researchDisposition"] for x in rows)
 by_survey=[]
 by_trial=[]
 for category in range(1,21):
  d=[r for r in rows if r["surveyNumber"]==category]
  by_survey.append({"surveyNumber":category,"survey":d[0]["surveyName"],
    "slots":len(d),"sourceContext":sum(bool(x["supportingRegistryPointers"] or x["publicationReviewLeads"] or x.get("externalPublicSourceLeads")) for x in d),
    "sourceInterpretationRequired":sum(x["researchDisposition"]=="PRIMARY_SOURCE_INTERPRETATION_REQUIRED" for x in d),
    "verified":sum(x["isSurveyAnswerVerified"] for x in d),
    "researchGaps":sum(x["researchDisposition"] in
      ("MODELING_INPUTS_UNAVAILABLE","ADDITIONAL_PRIMARY_RESEARCH_REQUIRED") for x in d)})
 for r in roster:
  group=[x for x in rows if x["nctId"]==r["nct"]]
  by_trial.append({"nctId":r["nct"],"ticker":r["ticker"],"slots":len(group),
    "verified":sum(x["isSurveyAnswerVerified"] for x in group),
    "registryPointers":sum(bool(x["supportingRegistryPointers"]) for x in group),
    "publicationLeads":sum(bool(x["publicationReviewLeads"]) for x in group)})
 verified=sum(x["isSurveyAnswerVerified"] for x in rows)
 return {"schemaVersion":1,"trials":len(roster),"surveys":20,"ingredients":38,
  "slots":len(rows),"dispositionCount":sum(dispositions.values()),
  "researchDispositionCoveragePercent":round(100*sum(dispositions.values())/len(rows),2),
  "verifiedSurveyAnswers":verified,
  "verifiedSurveyPercent":round(100*verified/len(rows),2),
  "sourceContextSlots":sum(bool(x["supportingRegistryPointers"] or x["publicationReviewLeads"] or x.get("externalPublicSourceLeads")) for x in rows),
  "externalSourceMappedSlots":sum(bool(x.get("externalPublicSourceLeads")) for x in rows),
  "dispositions":dict(dispositions),"bySurvey":by_survey,"byTrial":by_trial,
  "warning":"100% research disposition coverage does NOT mean 100% verified evidence, graded surveys, or validated RAAS."}

def run():
 roster_doc=load(ROSTER)
 roster=roster_doc.get("records")
 groups=load(CATALOG)["assessments"]
 slots=load(OUT/"evidence.json")["slots"]
 triage=load(OUT/"review-queue.json")["observations"]
 pubs=load(OUT/"publication-triage.json")["articles"]
 packets={row["nct"]:load(REGISTRY_PATH/(row["nct"]+".json")) for row in roster}
 # Five-source and direct-issuer company research must run BEFORE this audit.
 external=[]
 for filename in ("five-source-leads.json","company-direct-source-candidates.json"):
  source_path=OUT/filename
  # During code-review tests new collection artifacts do not exist yet;
  # the deployment workflow always collects these before calculating gaps.
  if source_path.exists():
   external+=load(source_path).get("records",[])
 index_path=OUT/"company-direct-source-ledger.json"
 company_links=load(index_path).get("rows",[]) if index_path.exists() else []
 items=build(roster,groups,slots,packets,triage,pubs,
   external_sources=external,company_links=company_links)
 summary=summary_of(items,roster)
 save(OUT/"resolution-worklist.json",{"schemaVersion":1,"items":items})
 headers=["nctId","ticker","company","surveyNumber","surveyName","ingredientId",
          "ingredientName","priorEvidenceStatus","researchDisposition",
          "reviewedAnswer","registryIndications","drugCandidates","supportingRegistryPointers",
          "primaryObservationCount","publicationReviewLeads","externalPublicSourceLeads",
          "externalPublicSourceTypes","linkedCompanyDisclosureSources","recommendedSource",
          "missingEvidenceRequirement","nextEvidenceStep","requiresModelAssumptions",
          "applicability","isSurveyAnswerVerified","sourcePacketHash"]
 with (OUT/"resolution-worklist.csv").open("w",encoding="utf-8",newline="") as file:
  writer=csv.DictWriter(file,fieldnames=headers,extrasaction="ignore")
  writer.writeheader()
  for item in items:
   writer.writerow({k:"; ".join(map(str,v)) if isinstance(v,list) else v for k,v in item.items()})
 save(OUT/"resolution-summary.json",summary)
 return summary

if __name__=="__main__":
 print(json.dumps(run(),sort_keys=True))
