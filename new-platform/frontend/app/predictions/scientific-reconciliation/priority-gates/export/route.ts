import {R93_PRIORITY_SCIENTIFIC_GATES} from
 "../../../../../lib/focus-r93-priority-scientific-gates";

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
 if(!d||d.priorityOriginalTrialCases!==2||
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
  "qualified_science_signoff","FDA_forecast"
 ];
 const records=d.cases.flatMap(c=>c.gates.map(g=>[
  c.trial,c.nct,c.ticker,g.id,g.sourceStatus,
  g.reviewPriority,g.scientificQuestion,g.existingEvidence,
  g.sourceEvidenceLabel,g.sourceUrl,g.storedResearchReceiptUrl,
  g.originalProofRequired,"NOT_VERIFIED","NOT_SIGNED","ABSTAIN"
 ]));
 if(records.length!==11)return Response.json({
  error:"EXPECTED_11_ORIGINAL_SCIENCE_REQUIREMENTS",
  FDAForecast:"ABSTAIN"
 },{status:503,headers:{"Cache-Control":"no-store"}});
 const csv=[heading,...records].map(row=>row.map(safeCell).join(",")).join("\r\n")+"\r\n";
 return new Response(csv,{status:200,headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="main-r93-priority-original-evidence-gates-20261110.csv"',
  "Cache-Control":"private, no-store, max-age=0",
  "X-Content-Type-Options":"nosniff"
 }});
}
