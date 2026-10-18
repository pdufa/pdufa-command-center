#!/usr/bin/env python3
"""Assess every census trial with source-grounded evidence, no fabricated GEM approvals."""
import csv,json,re
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
D=Path(__file__).resolve().parents[1]/"data"
def read(n):
 p=D/n
 if not p.exists():return []
 with p.open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
trials=read("phase3_all_years_300m_10b_trials.csv")
ann=read("phase3_announcements.csv")
membership=json.loads((D/"gem_stage_membership.json").read_text(encoding="utf-8"))
old={}
for tier in ("GEM","GEM_JR"):
 for e in membership["stages"][tier]["entries"].values():
  if e.get("status")=="ACTIVE" and e.get("ticker") and e.get("nct_id"):
   old[(e["ticker"].upper(),e["nct_id"])]=tier
by_nct={}
for e in ann:
 k=(e.get("ticker","").upper(),e.get("nct_id",""))
 if k[0] and re.fullmatch(r"NCT\d{8}",k[1]):by_nct.setdefault(k,[]).append(e)
rows=[]
for t in trials:
 key=(t["ticker"].upper(),t["nct_id"])
 sources=by_nct.get(key,[])
 issuer=[r for r in sources if r.get("source_type")=="ISSUER_TOPLINE_RELEASE" and r.get("phase3_results_source","").startswith("https://")]
 positive=[]
 for r in issuer:
  label=" ".join(str(r.get(k,"")) for k in ("phase3_result","phase3_status","verification_status")).upper()
  if any(x in label for x in ("FAILED","NEGATIVE","NOT MET","MISSED","INCONCLUSIVE")):continue
  if any(x in label for x in ("PRIMARY_MET_VERIFIED","VERIFIED_SUCCESS","RESULTS_VERIFIED")):positive.append(r)
 if positive:stage="GEM_EVIDENCE_CANDIDATE";reason="Issuer positive-result label and source present; still requires endpoint and regulatory review"
 elif t.get("status") in ("RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION","COMPLETED"):
  stage="GEM_JR_RESEARCH";reason="Active/completed Phase 3; successful endpoint not verified"
 else:stage="PIPELINE_REVIEW";reason="Trial inactive or status not sufficient to infer success"
 rows.append({**t,"assessment":stage,"existing_membership":old.get(key,"NONE"),"issuer_positive_source":positive[0]["phase3_results_source"] if positive else "","registry_result_record_count":len(sources),"assessment_reason":reason})
counts=Counter(r["assessment"] for r in rows)
out=D/"phase3_730_full_assessment.csv"
with out.open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={"generated_at":datetime.now(timezone.utc).isoformat(),"assessed_trials":len(rows),"gem_evidence_candidates":counts["GEM_EVIDENCE_CANDIDATE"],"gem_jr_research":counts["GEM_JR_RESEARCH"],"pipeline_review":counts["PIPELINE_REVIEW"],"reconciled":sum(counts.values())==len(trials),"existing_gem_overlap":sum(r["existing_membership"]=="GEM" for r in rows),"existing_gem_jr_overlap":sum(r["existing_membership"]=="GEM_JR" for r in rows),"warning":"Every trial assessed with available saved evidence. GEM_EVIDENCE_CANDIDATE is NOT verified full GEM qualification. GEM_JR_RESEARCH is a broad research bucket, not proof of successful Phase 3. Clinical endpoint/FDA/financing checks still missing for many trials."}
(D/"phase3_730_full_assessment_status.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2))
