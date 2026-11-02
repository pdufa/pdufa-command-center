#!/usr/bin/env python3
"""Source-faithful backup for 20 Phase 3 benefit ratings and their survey inputs.

Never manufacture a numeric benefit/risk grade. A count of verified research
inputs is not a clinical efficacy result or an investment ranking.
"""
from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
TRIALS=ROOT/"new-platform/frontend/public/phase3-registry-postings-current.json"
TAXONOMY=ROOT/"data/phase3_benefit_survey_catalog.json"
SAVED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
SHEET_ID="1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
API="https://sheets.googleapis.com/v4/spreadsheets/"+SHEET_ID
SUMMARY="Phase 3 Rating Coverage"
SURVEY="Phase 3 Rating Survey"
INGREDIENTS="Phase 3 Survey Ingredients"
NCT=re.compile(r"^NCT\d{8}$")
SOURCE_KIND="CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT"
COLUMNS_SUMMARY=["Ticker","NCT","Company","Registry Results Posted","Assessment Source"]+[
    "Rating "+str(i) for i in range(1,21)]+[
    "Verified Fields","Modeled Fields","Missing Fields","Verified Rating Scores",
    "Reviewer Finding","Source As Of UTC","Registry Source"
]
COLUMNS_SURVEY=["NCT","Ticker","Company","Rating Number","Rating Heading",
    "Survey / Assessment Objective","Ingredient IDs","Ingredient Questions",
    "Verified Inputs","Modeled Inputs","Missing Inputs","Required Inputs",
    "Rating Score (Evidence Required)","Review / Survey Status","Evidence Summary",
    "Evidence Sources","Evidence Dates","Missing Ingredient IDs",
    "Snapshot Checked UTC","Evidence Record JSON"]
COLUMNS_INGREDIENTS=["Rating Number","Rating Heading","Ingredient ID",
    "Ingredient Label","Survey Question / Purpose","Required Evidence",
    "Assessment Objective","Scoring Guidance"]


def read_json(path):
    with path.open(encoding="utf-8") as file:return json.load(file)


def validate(data,taxonomy,saved):
    if not isinstance(data,dict) or data.get("schemaVersion")!=2 or \
       data.get("measure")!=SOURCE_KIND or \
       data.get("sourceKind")!="OFFICIAL_CLINICALTRIALS_GOV_API_EXACT_NCT":
        raise ValueError("Unverified registry research snapshot")
    records=data.get("records")
    if not isinstance(records,list) or not 700<=len(records)<=20000 or \
       data.get("total")!=len(records) or \
       data.get("noResultsPosted")+data.get("resultsPosted")!=len(records):
        raise ValueError("Partial/invalid trial census")
    if taxonomy.get("schemaVersion")!=1 or taxonomy.get("taxonomy")!="CANONICAL_20_PIPELINE_BENEFIT_ASSESSMENTS":
        raise ValueError("Unsupported rating taxonomy")
    groups=taxonomy.get("assessments")
    if not isinstance(groups,list) or len(groups)!=20 or \
       [g.get("rank") for g in groups]!=list(range(1,21)):
        raise ValueError("Twenty rating headings required")
    ids=[];ings=set()
    for group in groups:
        fields=group.get("ingredients")
        if not isinstance(fields,list) or not fields:raise ValueError("Rating lacks survey ingredients")
        for field in fields:
            fid=field.get("id")
            if not isinstance(fid,str) or not fid or fid in ings:
                raise ValueError("Missing or duplicated ingredient ID")
            ings.add(fid);ids.append(fid)
            if any(not isinstance(field.get(k),str) or not field[k] for k in ("label","question","evidenceRequirement")):
                raise ValueError("Ingredient survey definition incomplete")
    if len(ids)!=38:raise ValueError("Expected 38 distinct supporting survey ingredients")
    ncts=set()
    for record in records:
        id=record.get("nctId")
        if not isinstance(id,str) or not NCT.fullmatch(id) or id in ncts:
            raise ValueError("Duplicate/invalid NCT")
        ncts.add(id)
        posted=record.get("resultsFirstPostedDate")
        count=record.get("resultsCount")
        if type(count) is not int or count not in (0,1) or \
           not isinstance(posted,str) or bool(posted)!=bool(count) or \
           not isinstance(record.get("ticker"),str) or not record.get("ticker"):
            raise ValueError("Registry row mismatch")
    if not isinstance(saved,dict) or saved.get("schemaVersion")!=1 or not isinstance(saved.get("records"),list):
        raise ValueError("Saved review evidence is malformed")
    return groups, ncts


def canonical_source():
    """Consume the same authenticated research export as the other Sheets sync.
    Source errors stop this backup rather than silently erasing old evidence."""
    import requests
    from sync_pipeline_research import read_dataset
    if not os.getenv("DASHBOARD_PASSWORD"):
        raise RuntimeError("DASHBOARD_PASSWORD missing; refusing to replace existing assessment backup")
    (dataset_version,rows),first=read_dataset(requests.Session())
    if not re.fullmatch(r"[a-f0-9]{64}",dataset_version):
        raise ValueError("Canonical research version mismatch")
    return rows, first.get("asOf",""), dataset_version


def prepare(snapshot,taxonomy,saved,canonical):
    groups,ncts=validate(snapshot,taxonomy,saved)
    if not isinstance(canonical,list):raise ValueError("Canonical research feed unavailable")
    exact={}
    for item in canonical:
        if not isinstance(item,dict) or not isinstance(item.get("nctId"),str):
            raise ValueError("Invalid canonical research identity")
        nct=item["nctId"]
        if nct in exact:raise ValueError("Duplicate exact NCT in canonical research")
        if not isinstance(item.get("assessments"),list) or len(item["assessments"])!=20:
            raise ValueError("Invalid 20-rating research mapping")
        exact[nct]=item
    saved_by_id={}
    for record in saved["records"]:
        if not isinstance(record,dict) or not NCT.fullmatch(str(record.get("nctId",""))) or \
           not isinstance(record.get("facts"),dict):
            raise ValueError("Invalid saved reviewed facts")
        key=record["nctId"]
        if key in saved_by_id:raise ValueError("Conflicting saved reviewed research identity")
        saved_by_id[key]=record

    summary=[COLUMNS_SUMMARY]
    survey=[COLUMNS_SURVEY]
    ingredients=[COLUMNS_INGREDIENTS]
    for group in groups:
        for f in group["ingredients"]:
            ingredients.append([group["rank"],group["name"],f["id"],f["label"],
                f["question"],f["evidenceRequirement"],group["objective"],
                "Source-linked input; no numerical rating without independently reviewed scoring rule"])
    matched=0;recorded=0
    for trial in sorted(snapshot["records"],key=lambda t:(t["ticker"],t["nctId"])):
        nct=trial["nctId"];ticker=trial["ticker"];company=trial["company"]
        research=exact.get(nct)
        if research and research.get("ticker")==ticker:
            matched+=1
        else:
            research=None
        reviewed=saved_by_id.get(nct)
        if reviewed and reviewed.get("ticker")!=ticker:
            reviewed=None
        # Reviewed benefits must correspond to exact canonical drug and indication,
        # not just ticker, disease or product name.
        if reviewed and (not research or reviewed.get("drug")!=research.get("drug") or
                         reviewed.get("indication")!=research.get("indication")):
            reviewed=None
        saved_facts=reviewed.get("facts",{}) if reviewed else {}
        ratings=[];verified_total=0;modeled_total=0;missing_total=0;trial_evidence_count=0
        for group in groups:
            rank=group["rank"];questions=group["ingredients"]
            item=research["assessments"][rank-1] if research else None
            if item and (item.get("rank")!=rank or item.get("title")!=group["name"]):
                raise ValueError("Canonical rating taxonomy drift")
            canonical_inputs={i.get("id"):i for i in item.get("inputs",[])} if item else {}
            if item and set(canonical_inputs)!=set(f["id"] for f in questions):
                raise ValueError("Canonical ingredient IDs do not reconcile")
            verified=modeled=0;evidence=[];missing=[];review_notes=[]
            for f in questions:
                fid=f["id"];obs=canonical_inputs.get(fid)
                fact=saved_facts.get(fid)
                status=obs.get("state") if obs else "MISSING"
                url=obs.get("sourceUrl") if obs else None
                dt=obs.get("sourceDate") if obs else None
                val=obs.get("value") if obs else None
                method=obs.get("method") if obs else None
                conf=obs.get("confidence") if obs else None
                if isinstance(fact,dict) and fact.get("status") in ("VERIFIED","MODELED"):
                    status=fact["status"];url=fact.get("sourceUrl");dt=fact.get("sourceDate")
                    val=fact.get("value");method=fact.get("method");conf=fact.get("confidence")
                if status in ("VERIFIED","MODELED") and isinstance(url,str) and url.startswith("https://") and dt:
                    if status=="VERIFIED":verified+=1
                    else:modeled+=1
                    evidence.append({"field":fid,"state":status,"value":val,"sourceUrl":url,
                        "sourceDate":dt,"method":method,"confidence":conf})
                else:
                    missing.append(fid)
                    if status not in ("MISSING",None):review_notes.append(fid+": "+str(status))
            required=len(questions);missing_count=required-verified-modeled
            if missing_count!=len(missing):raise ValueError("Missing field counts mismatch")
            if verified==required:rating="INPUTS_SOURCED_NOT_SCORED"
            elif verified or modeled:rating="PARTIAL_INPUTS_NOT_SCORED"
            else:rating="NOT_ASSESSED"
            ratings.append(rating)
            verified_total+=verified;modeled_total+=modeled;missing_total+=missing_count
            recorded+=len(evidence);trial_evidence_count+=len(evidence)
            reviewed_advantages=[a for a in (reviewed.get("advantages",[]) if reviewed else [])\
                if isinstance(a,dict) and a.get("assessment")==rank]
            review_text=" | ".join(str(a.get("title",""))+": "+str(a.get("comparison","")) for a in reviewed_advantages)
            review_links=[a.get("sourceUrl","") for a in reviewed_advantages if isinstance(a.get("sourceUrl"),str)]
            survey.append([
                nct,ticker,company,rank,group["name"],group["objective"],
                " | ".join(f["id"] for f in questions),
                " | ".join(f["label"]+": "+f["question"] for f in questions),
                verified,modeled,missing_count,required,"",
                "REVIEW_FINDING_RECORDED" if reviewed_advantages else rating,
                (item.get("summary","") if item else "No canonical research record") +
                    (" | "+review_text if review_text else "") +
                    (" | "+ "; ".join(review_notes) if review_notes else ""),
                " | ".join(dict.fromkeys([e["sourceUrl"] for e in evidence]+review_links)),
                " | ".join(dict.fromkeys(str(e["sourceDate"]) for e in evidence)),
                " | ".join(missing),snapshot["sourceAsOf"],
                json.dumps(evidence,ensure_ascii=False,separators=(",",":"))
            ])
        if verified_total+modeled_total+missing_total!=38:
            raise ValueError("Rating and ingredient coverage mismatch")
        summary.append([
            ticker,nct,company,"YES" if trial["resultsCount"] else "NO",
            "EXACT_CANONICAL_NCT" if research else "NO_EXACT_CANONICAL_RESEARCH_MATCH",
            *ratings,verified_total,modeled_total,missing_total,"",
            "SOURCE_INPUTS_NOT_CLINICALLY_ADJUDICATED" if trial_evidence_count else "NO_SCORED_RATINGS",
            snapshot["sourceAsOf"],"https://clinicaltrials.gov/study/"+nct
        ])
    if len(summary)!=len(ncts)+1 or len(survey)!=len(ncts)*20+1 or len(ingredients)!=39:
        raise ValueError("Survey output not complete")
    return {SUMMARY:summary,SURVEY:survey,INGREDIENTS:ingredients}, {
        "trials":len(ncts),"ratings":len(survey)-1,"ingredients":38,
        "exactCanonicalMatched":matched,"sourcedIngredientObservations":recorded
    }


def google_session():
    secret=os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON","")
    if not secret:raise RuntimeError("Google Sheets service account secret not configured")
    import requests,google.auth.transport.requests
    from google.oauth2 import service_account
    creds=service_account.Credentials.from_service_account_info(
        json.loads(secret),scopes=["https://www.googleapis.com/auth/spreadsheets"])
    creds.refresh(google.auth.transport.requests.Request())
    client=requests.Session()
    client.headers["Authorization"]="Bearer "+creds.token
    return client


def request(client,method,path,**kwargs):
    import time
    for attempt in range(4):
        response=client.request(method,API+path,timeout=70,**kwargs)
        if response.status_code not in (429,500,502,503,504) or attempt==3:
            response.raise_for_status()
            return response.json()
        time.sleep(2**attempt)


def publish(values,client):
    meta=request(client,"GET","",params={"fields":"sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))"})
    properties={s["properties"]["title"]:s["properties"] for s in meta.get("sheets",[])}
    for title,rows in values.items():
        p=properties.get(title)
        if p is None or p["gridProperties"]["columnCount"]<len(rows[0]):
            raise RuntimeError("Missing or undersized existing Google backup tab: "+title)
    resize=[]
    for title,rows in values.items():
        p=properties[title]
        if p["gridProperties"]["rowCount"]<len(rows):
            resize.append({"updateSheetProperties":{"properties":{
                "sheetId":p["sheetId"],"gridProperties":{"rowCount":len(rows)+100}},
                "fields":"gridProperties.rowCount"}})
    if resize:request(client,"POST",":batchUpdate",json={"requests":resize})
    # Deterministic chunked overwrite of dedicated, automation-owned tabs only.
    # Other sheets, FS/FA presets and manual reviewers' cells remain untouched.
    for title,rows in values.items():
        last=""
        for index in range(0,len(rows),350):
            chunk=rows[index:index+350]
            end=index+len(chunk)
            start=f"'{title}'!A{index+1}"
            # Batch one contiguous rectangular chunk.
            result=request(client,"PUT","/values/"+quote(start,safe="!':"),
                params={"valueInputOption":"RAW"},
                json={"majorDimension":"ROWS","values":chunk})
            if int(result.get("updatedRows",0))!=len(chunk):
                raise RuntimeError("Google Sheets incomplete rating backup write: "+title)
        # Read back ALL NCT identifiers and exact assessment ranks, not just counts.
        nrows=len(rows);endcol="E" if title==SUMMARY else ("E" if title==SURVEY else "C")
        raw=request(client,"GET","/values/"+quote(f"'{title}'!A1:{endcol}{nrows}",safe="!':"))
        observed=raw.get("values",[])
        expected=[[(str(v) if v is not None else "") for v in row[:5 if title!=INGREDIENTS else 3]] for row in rows]
        normalized=lambda row:[str(v) if v is not None else "" for v in row]+[""]*max(0,len(expected[0])-len(row))
        if len(observed)!=nrows or any(normalized(o)!=e for o,e in zip(observed,expected)):
            raise RuntimeError("Google Drive source-versus-ticker/NCT/rating readback mismatch in "+title)
        # Remove stale tails only after a complete write & readback.
        cap=max(p["gridProperties"]["rowCount"],nrows+100)
        if cap>nrows:
            ending="AF" if title==SUMMARY else ("T" if title==SURVEY else "H")
            request(client,"POST","/values/"+quote(f"'{title}'!A{nrows+1}:{ending}{cap}",safe="!':")+":clear",json={})
    return {key:len(rows)-1 for key,rows in values.items()}


def main():
    data=read_json(TRIALS);taxonomy=read_json(TAXONOMY);saved=read_json(SAVED)
    canonical,asof,version=canonical_source()
    values,counts=prepare(data,taxonomy,saved,canonical)
    published=publish(values,google_session())
    print(json.dumps({"sourceAsOf":data["sourceAsOf"],"canonicalDate":asof,
        "canonicalVersion":version,"counts":counts,"published":published,
        "verification":"ALL NCT/TICKER/RATING IDENTITIES READ BACK"},indent=2))


if __name__=="__main__":main()
