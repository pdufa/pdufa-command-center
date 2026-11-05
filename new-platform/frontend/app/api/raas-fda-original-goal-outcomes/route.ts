/** Public read-only original-goal FDA outcome review queue. No uploads,
 * model training, outcome certification, or automated trading decisions.
 */
import {currentRaasFdaOriginalGoalOutcomeAudit}
 from "../../../lib/raas-fda-original-goal-outcome-audit";
import {buildThreeWayFDAFreezePreflightPlan}
 from "../../../lib/raas-fda-three-way-freeze-preflight";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
export function GET(request:Request){
 let caseKey:string|null;
 try{caseKey=new URL(request.url).searchParams.get("case");}
 catch{return Response.json({error:"INVALID_URL"},{status:400,headers});}
 const audit=currentRaasFdaOriginalGoalOutcomeAudit();
 if(caseKey===null)return Response.json(audit,{headers});
 if(!caseKey||caseKey.length>160||/[\u0000-\u001f\u007f]/.test(caseKey))
  return Response.json({error:"EXACT_FDA_CASE_REQUIRED"},{status:400,headers});
 const selected=audit.cases.find(r=>r.caseKey===caseKey);
 const plan=buildThreeWayFDAFreezePreflightPlan().records.find(r=>r.caseKey===caseKey);
 if(!selected||!plan)
  return Response.json({error:"EXACT_FDA_CASE_NOT_FOUND"},{status:404,headers});
 const handoff={
  schemaVersion:1,
  scope:"RAAS_FDA_ORIGINAL_GOAL_OUTCOME_EVIDENCE_HANDOFF_UNADJUDICATED",
  caseKey:selected.caseKey,ticker:selected.ticker,drug:selected.drug,
  indication:selected.indication,trialNctId:plan.trialNctId,
  researchSourceAsOf:audit.snapshotAsOf,
  sourceFingerprint:plan.sourceFingerprint,
  originalFirstGoalDate:selected.originalFirstGoalDate,
  listedTargetDate:selected.listedTargetDate,
  formalRevisionOfOriginalDate:plan.goalHasFormalRevision,
  issuerGoalSourceUrl:plan.primaryIssuerSourceUrl,
  stageEligibility:selected.stageEligibility,
  sourceCandidateStatus:selected.status,
  sourceCandidateBlockers:selected.blockers,
  independentlyVerifiedOutcome:null,
  approvedForecast:null,
  approvedRaasScore:null,
  requiredEvidence:[
   "Confirm exact FDA NDA/BLA/supplement application number, sponsor, indication, and review cycle independently.",
   "Identify the FIRST publicly announced original PDUFA goal and separately record later formal date revisions.",
   "Acquire matching official FDA action letter or independently verifiable original-goal amendment, with regulator-effective date and source publication date.",
   "Determine whether PASS, CRL or a formally approved EXTENSION actually occurred by the original goal; do not use an eventual later approval as an original-goal PASS.",
   "Record source fingerprint, publication chronology, archived source document digest, and dissenting or conflicting evidence; authenticate any private independent review externally.",
   "Keep this outcome evidence strictly separate from prediction-time source inputs and from later training/validation cohorts.",
   "Only pair an independently adjudicated label with an independently witnessed, genuinely predecision three-way forecast of the SAME application and cycle; then evaluate a prespecified eligible cohort including abstentions."
  ],
  note:audit.warning
 };
 const safeTicker=selected.ticker.replace(/[^A-Z0-9.-]/g,"");
 return new Response(JSON.stringify(handoff,null,2)+"\n",{status:200,headers:{
  ...headers,"Content-Type":"application/json; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-fda-original-goal-review-'+
   safeTicker+'-'+plan.sourceFingerprint.slice(0,12)+'.json"'
 }});
}
