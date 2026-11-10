import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE} from "../../../../lib/focus-specialty-assessment";
import {isolatedMedicalBackend} from "../../../../lib/medical-review-matrix";

export const runtime="nodejs";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};
const REGISTRY="https://clinicaltrials.gov/study/";
const CATEGORIES=new Set([
  "PHASE_RECONCILIATION_REQUIRED",
  "POSTED_PRIMARY_RESULTS_NEED_ADJUDICATION",
  "NO_POSTED_PRIMARY_RESULTS_FIND_ORIGINAL_READOUT",
]);
const STATES=new Set([
  "MATCHED_SINGLE_PHASE","SOURCE_PHASE_DRIFT_REVIEW",
  "MULTIPHASE_REVIEW_REQUIRED","NO_REGISTRY_PHASE_REVIEW",
]);
const allowed=new Set(FOCUS_SPECIALTY_ASSESSMENT_QUEUE.map(t=>t.nct));
type Row=Record<string,unknown>;
function obj(x:unknown):Row {
  if (!x || typeof x!=="object" || Array.isArray(x)) throw Error("INVALID_RECORD");
  return x as Row;
}
function count(x:unknown):x is number {
  return typeof x==="number"&&Number.isSafeInteger(x)&&x>=0;
}
function text(x:unknown,max=500):x is string {
  return typeof x==="string"&&x.length<=max;
}
function abstain(x:unknown):boolean{
  const r=obj(x);
  return Object.keys(r).length===3 && ["APPROVAL","CRL","REVIEW_DELAY"].every(k=>r[k]==="ABSTAIN");
}
function checkedSourceUrl(x:unknown,nct:string){
  if(x!==REGISTRY+nct) throw Error("INVALID_SOURCE_IDENTITY");
  return x as string;
}
export function validatedPhaseHandoff(q:unknown,detail:unknown,nct:string){
  const root=obj(q),e=obj(detail);
  if(root.schema!=="EXACT_NCT_EVIDENCE_REVIEW_QUEUE_V1"||
     root.status!=="READY_FOR_INDEPENDENT_EVIDENCE_REVIEW"||
     root.canonicalTrials!==29 || root.clinicalSignoff!==false||
     root.certainty!=="NOT_VALIDATED"||!abstain(root.fdaPredictions)||
     !Array.isArray(root.reviewItems)||root.reviewItems.length!==29||allowed.size!==29)
    throw Error("INVALID_REVIEW_QUEUE");
  const seen=new Set<string>(),ranks=new Set<number>();
  const queue=root.reviewItems.map((raw:unknown)=>{
    const v=obj(raw);
    if(typeof v.nct!=="string"||!allowed.has(v.nct)||seen.has(v.nct)||
       !count(v.reviewQueuePosition)||v.reviewQueuePosition<1||v.reviewQueuePosition>29||
       ranks.has(v.reviewQueuePosition)||!count(v.reviewPriority)||v.reviewPriority<1||v.reviewPriority>3||
       !CATEGORIES.has(String(v.category))||!STATES.has(String(v.phaseAgreement))||
       !Array.isArray(v.phase)||v.phase.some((p:unknown)=>typeof p!=="string"||!/^PHASE[1-4]$|^EARLY_PHASE1$/.test(p))||
       v.phaseReviewerStatus!=="NOT_INDEPENDENTLY_ADJUDICATED"||
       !text(v.registryLastUpdate,40)||!count(v.primaryOutcomeResultsPosted)||
       !count(v.primaryOutcomeDefinitions)||!text(v.registrySnapshotId,200)||
       !text(v.sourceRunId,200)||!text(v.nextEvidenceAction,1800))
      throw Error("INVALID_REVIEW_ITEM");
    checkedSourceUrl(v.officialRegistryUrl,v.nct);
    seen.add(v.nct);ranks.add(v.reviewQueuePosition);
    return {
      nct:v.nct as string,
      rank:v.reviewQueuePosition as number,
      category:v.category as string,
      reviewPriority:v.reviewPriority as number,
      phase:v.phase as string[],
      phaseAgreement:v.phaseAgreement as string,
      registryLastUpdate:v.registryLastUpdate as string,
      registeredPrimaryOutcomes:v.primaryOutcomeDefinitions as number,
      postedPrimaryResults:v.primaryOutcomeResultsPosted as number,
      officialUrl:v.officialRegistryUrl as string,
      nextAction:v.nextEvidenceAction as string,
      snapshotId:v.registrySnapshotId as string,
      sourceRunId:v.sourceRunId as string,
      reviewerStatus:v.phaseReviewerStatus as string,
    };
  });
  if([...allowed].some(id=>!seen.has(id))||ranks.size!==29)throw Error("INCOMPLETE_FOCUS_QUEUE");
  const phase=queue.filter(v=>v.category==="PHASE_RECONCILIATION_REQUIRED").length;
  const posted=queue.filter(v=>v.category==="POSTED_PRIMARY_RESULTS_NEED_ADJUDICATION").length;
  const missing=queue.filter(v=>v.category==="NO_POSTED_PRIMARY_RESULTS_FIND_ORIGINAL_READOUT").length;
  if(root.phaseReconciliationRequired!==phase||root.postedPrimaryResultsNeedReview!==posted||
     root.noPostedPrimaryResults!==missing||phase+posted+missing!==29)
    throw Error("INCONSISTENT_QUEUE_COUNTS");
  const selected=queue.find(v=>v.nct===nct);
  if(!selected||e.nct!==nct||e.snapshotId!==selected.snapshotId||
     e.sourceRunId!==selected.sourceRunId||e.phaseAgreement!==selected.phaseAgreement||
     JSON.stringify(e.currentRegistryPhases)!==JSON.stringify(selected.phase)||
     e.machineSourceIdentityVerified!==true||e.reviewerVerifiedCurrentPhase!==false||
     e.lastCompletedPhaseIndependentlyVerified!==false||e.scientificSignoff!==false||
     e.scientificGradesWritten!==0||e.certainty!=="NOT_VALIDATED"||
     !abstain(e.fdaPredictions)||e.sourceType!=="OFFICIAL_REGISTRY_SPONSOR_SUBMITTED"||
     !text(e.sponsor,240)||!text(e.title,500)||!text(e.overallStatus,90)||
     !text(e.latestRecordUpdatePosted,40)||!text(e.savedAt,80)||
     !Array.isArray(e.savedRegistryPhases)||!text(e.phaseAgreementExplanation,900)||
     !/^[a-f0-9]{64}$/.test(String(e.sourceHashSha256))||
     !/^[a-f0-9]{64}$/.test(String(e.savedStageHashSha256)))
    throw Error("INCONSISTENT_REGISTRY_SNAPSHOT");
  checkedSourceUrl(e.registryUrl,nct);
  return {
    schema:"ISOLATED_READ_ONLY_PHASE_HANDOFF_V1",
    nct, canonicalTrials:29,
    buckets:{phaseReconciliationRequired:phase,postedPrimaryResultsNeedReview:posted,noPostedPrimaryResults:missing},
    selected:{
      ...selected,title:e.title as string,sponsor:e.sponsor as string,
      overallStatus:e.overallStatus as string,
      savedRegistryPhases:e.savedRegistryPhases as string[],
      latestRecordUpdatePosted:e.latestRecordUpdatePosted as string,
      snapshotSavedAt:e.savedAt as string,
      rationale:e.phaseAgreementExplanation as string,
      registrySha256:e.sourceHashSha256 as string,
      savedStageSha256:e.savedStageHashSha256 as string,
      priorCompletedPhaseVerified:false,currentPhaseReviewerVerified:false,
    },
    queue:queue.sort((a,b)=>a.rank-b.rank),
    reviewerSignoff:false, scientificGradesWritten:0,
    fdaPredictions:{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"},
    certainty:"NOT_VALIDATED",
    note:"Sponsor registry facts and source triage are not independent clinical adjudication. Review requires a named authorized reviewer.",
  };
}
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  const nct=req.nextUrl.searchParams.get("nct");
  if(!nct||!allowed.has(nct)||req.nextUrl.searchParams.has("assessmentIndex"))
    return NextResponse.json({error:"Select one exact FOCUS trial"},{status:422,headers});
  const base=isolatedMedicalBackend(process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL);
  const key=process.env.PDUFA_MEDICAL_REVIEW_READ_KEY;
  if(!base||!key)return NextResponse.json({error:"Isolated read-only review service not configured"},{status:503,headers});
  try{
    const init:RequestInit={headers:{"x-pdufa-internal-key":key},redirect:"error",cache:"no-store",signal:AbortSignal.timeout(20000)};
    const paths=[
      "/api/internal/medical-primary-evidence-review/queue",
      "/api/internal/medical-registry-reconciliation/"+nct+"/latest",
    ];
    const responses=await Promise.all(paths.map(path=>fetch(base+path,init)));
    if(responses.some(r=>!r.ok||!r.headers.get("content-type")?.includes("json")))throw Error("SOURCE_UNAVAILABLE");
    const docs=await Promise.all(responses.map(async r=>{
      const body=await r.text();if(body.length>2_000_000)throw Error("SOURCE_TOO_LARGE");
      return JSON.parse(body) as unknown;
    }));
    return NextResponse.json(validatedPhaseHandoff(docs[0],docs[1],nct),{headers});
  }catch{
    return NextResponse.json({error:"Verified registry evidence handoff is unavailable; no phase signoff was inferred."},{status:503,headers});
  }
}
