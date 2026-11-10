import {R93_PRIORITY_SCIENTIFIC_GATES} from
 "../../../../../lib/focus-r93-priority-scientific-gates";
import {R94_ACACIA_COHORT_SAFETY_SOURCE} from
 "../../../../../lib/focus-r94-acacia-cross-source-reconciliation";

export const runtime="nodejs";
export const dynamic="force-dynamic";
function safeCell(raw:unknown):string{
 const value=typeof raw==="string"?raw:String(raw??"");
 const normalized=value.replace(/[\r\n\t]/gu," ").slice(0,2500);
 const inert=/^[\s]*[=+\-@]/u.test(normalized)?"'"+normalized:normalized;
 return '"'+inert.replace(/"/gu,'""')+'"';
}
/** Read-only research handoff for original documents, not verified grades. */
export function GET():Response{
 const d=R93_PRIORITY_SCIENTIFIC_GATES;
 const update=R94_ACACIA_COHORT_SAFETY_SOURCE;
 if(!d||!update||update.exactNct!=="NCT06081894"||
    update.originalAcaciaEvidenceGatesUnresolved!==4||
    update.originalLaunchEvidenceGatesUnresolved!==7||
    update.independentSAPProspectivityAuthentication!==false||
    update.qualifiedMedicalScienceReviews!==0||
    update.FDAForecast!=="ABSTAIN"||
    d.priorityOriginalTrialCases!==2||
    d.unresolvedAuthenticatedScienceRequirements!==11||
    d.independentlyVerifiedSignedProspectiveSAPs!==0||
    d.qualifiedIndependentScienceSignoffs!==0||
    d.validatedFDAPredictions!==0)return Response.json({
   error:"ORIGINAL_PRIORITY_GATES_FAILED_SOURCE_VALIDATION",
   FDAForecast:"ABSTAIN"
  },{status:503,headers:{"Cache-Control":"no-store"}});
 const heading=[
  "trial","nct","ticker","evidence_gate_id","research_status",
  "priority","scientific_question","known_source_evidence",
  "source_label","source_url","archived_repository_receipt",
  "original_proof_required","authenticated_final_sap",
  "qualified_science_signoff","FDA_forecast",
  "R94_public_source_clarification_not_adjudicated","R94_original_research_source"
 ];
 const researchUpdate=(nct:string,gateId:string):[string,string]=>{
  if(nct!==update.exactNct)return ["",""];
  if(gateId==="CONSORT_SETS")return [
    "NEJM 517 randomized (258+259); later published appraisal 516 treated. Plausible different cohorts, original CONSORT/first-dose set not independently verified.",
    update.sourceLinks.find(s=>s.id==="S3")?.url??""
  ];
  if(gateId==="HEART_FAILURE_WINDOWS")return [
    "Earlier case figures 11/1; October sponsor reports HF SAE 12/3 with 2 aficamten cases associated with LVEF below 50% plus 10 without. Original cutoffs, exposure and case listings not independently reconciled.",
    update.sourceLinks.find(s=>s.id==="S4")?.url??""
  ];
  if(gateId==="FINAL_LOCKED_SAP")return [
    "Published responder-analysis authors report SAP inclusion before database lock/unblinding. Original controlled signed SAP and first-access audit not independently authenticated.",
    update.sourceLinks.find(s=>s.id==="S5")?.url??""
  ];
  return ["",""];
 };
 const records=d.cases.flatMap(c=>c.gates.map(g=>[
  c.trial,c.nct,c.ticker,g.id,g.sourceStatus,
  g.reviewPriority,g.scientificQuestion,g.existingEvidence,
  g.sourceEvidenceLabel,g.sourceUrl,g.storedResearchReceiptUrl,
  g.originalProofRequired,"NOT_VERIFIED","NOT_SIGNED","ABSTAIN",
  ...researchUpdate(c.nct,g.id)
 ]));
 if(records.length!==11)return Response.json({
  error:"EXPECTED_11_ORIGINAL_SCIENCE_REQUIREMENTS",
  FDAForecast:"ABSTAIN"
 },{status:503,headers:{"Cache-Control":"no-store"}});
 const csv=[heading,...records].map(row=>row.map(safeCell).join(",")).join("\r\n")+"\r\n";
 return new Response(csv,{status:200,headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="main-r94-priority-original-evidence-gates-20261110.csv"',
  "Cache-Control":"private, no-store, max-age=0",
  "X-Content-Type-Options":"nosniff"
 }});
}
