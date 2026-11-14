import {NextRequest,NextResponse} from "next/server";
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE} from "../../../../lib/focus-specialty-assessment";
import {makeEvidenceRun,type EvidenceRun} from "../../../../lib/prediction-source-tests";

/**
 * Deliberately invoked, read-only ClinicalTrials.gov evidence inspection for
 * all canonical FOCUS trials. This is NOT the full medical/FDA outcome model.
 *
 * Zero background execution on page load. No writes or release of FDA odds.
 * GET requires ?run=source-inspection to prevent accidental crawler execution.
 * POST requires same-origin browser invocation.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=60;
const noStore={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"} as const;
const MAX_RESPONSE_BYTES=5_000_000;
const SOURCE_TIMEOUT_MS=9000;
const CONCURRENCY=8;
type TrialScan={
  ticker:string;nct:string;company:string;applicationCycles:string[];
  registrySourceUrl:string;sourceStatus:"SOURCE_SCANNED"|"SOURCE_UNAVAILABLE";
  sourceError:string|null;registryLastUpdate:string|null;
  reportedPhase:string|null;reportedStatus:string|null;
  sourceFieldPresent:number;missingRegistryFields:number;
  independentReviewRequired:number;notAutomated:number;
  tests:EvidenceRun["tests"];
  scientificAssessment:"INSUFFICIENT_VERIFIED_EVIDENCE";
  prediction:"ABSTAIN";certainty:"NOT_VALIDATED";
};
const object=(x:unknown):Record<string,unknown>=>x&&typeof x==="object"&&!Array.isArray(x)?x as Record<string,unknown>:{};
const text=(x:unknown):string|null=>typeof x==="string"&&x.trim()?x.trim():null;

async function inspect(entry:(typeof FOCUS_SPECIALTY_ASSESSMENT_QUEUE)[number]):Promise<TrialScan>{
  const {nct,ticker,company,applications}=entry;
  const registrySourceUrl="https://clinicaltrials.gov/study/"+nct;
  const base={ticker,nct,company,applicationCycles:applications.map(a=>a.cycleId),
    registrySourceUrl,scientificAssessment:"INSUFFICIENT_VERIFIED_EVIDENCE" as const,
    prediction:"ABSTAIN" as const,certainty:"NOT_VALIDATED" as const};
  try{
    const upstream=await fetch("https://clinicaltrials.gov/api/v2/studies/"+nct+"?format=json",{
      headers:{Accept:"application/json"},cache:"no-store",signal:AbortSignal.timeout(SOURCE_TIMEOUT_MS)
    });
    if(!upstream.ok||!upstream.headers.get("content-type")?.toLowerCase().includes("json"))
      throw Error("REGISTRY_NETWORK_OR_HTTP_ERROR");
    const body=await upstream.text();
    if(body.length>MAX_RESPONSE_BYTES)throw Error("REGISTRY_RESPONSE_LIMIT");
    const study:unknown=JSON.parse(body);
    const report=makeEvidenceRun(study,nct,"FULL");
    const proto=object(object(study).protocolSection);
    const design=object(proto.designModule);
    const status=object(proto.statusModule);
    const phases=Array.isArray(design.phases)?
      design.phases.filter((s:unknown)=>typeof s==="string").join(", "):null;
    return {...base,sourceStatus:"SOURCE_SCANNED" as const,sourceError:null,
      registryLastUpdate:report.registryLastUpdate,reportedPhase:phases||null,
      reportedStatus:text(status.overallStatus),
      sourceFieldPresent:report.tests.filter(t=>t.state==="SOURCE_FIELD_PRESENT").length,
      missingRegistryFields:report.tests.filter(t=>t.state==="SOURCE_FIELD_MISSING").length,
      independentReviewRequired:report.tests.filter(t=>t.state==="INDEPENDENT_REVIEW_REQUIRED").length,
      notAutomated:report.tests.filter(t=>t.state==="NOT_AUTOMATED").length,
      tests:report.tests
    };
  }catch(cause){
    return {...base,sourceStatus:"SOURCE_UNAVAILABLE" as const,sourceError:
      cause instanceof Error&&cause.message==="REGISTRY_NCT_ID_MISMATCH"?
        "Exact NCT record did not match the requested identifier":
        "Official registry source could not be retrieved or verified",
      registryLastUpdate:null,reportedPhase:null,reportedStatus:null,
      sourceFieldPresent:0,missingRegistryFields:0,independentReviewRequired:0,
      notAutomated:0,tests:[]
    };
  }
}
async function performScan(){
  const startedAt=new Date().toISOString();
  const rows:TrialScan[]=[];
  for(let i=0;i<FOCUS_SPECIALTY_ASSESSMENT_QUEUE.length;i+=CONCURRENCY){
    rows.push(...await Promise.all(FOCUS_SPECIALTY_ASSESSMENT_QUEUE.slice(i,i+CONCURRENCY).map(inspect)));
  }
  const scanned=rows.filter(r=>r.sourceStatus==="SOURCE_SCANNED");
  const failed=rows.filter(r=>r.sourceStatus==="SOURCE_UNAVAILABLE");
  return NextResponse.json({
    schemaVersion:1,
    kind:"FOCUS_CURRENT_TRIAL_SOURCE_INSPECTION_NOT_VALIDATED_FDA_ASSESSMENT",
    startedAt,completedAt:new Date().toISOString(),
    rosterAsOf:FOCUS_SPECIALTY_ASSESSMENT_QUEUE[0]?.rosterAsOf??null,
    status:failed.length?"PARTIAL_SOURCE_SCAN":"ALL_REGISTRY_SOURCES_SCANNED",
    summary:{
      targetTrials:FOCUS_SPECIALTY_ASSESSMENT_QUEUE.length,
      sourceScanned:scanned.length,sourceUnavailable:failed.length,
      recordedFieldChecks:scanned.reduce((s,r)=>s+r.sourceFieldPresent,0),
      missingFieldChecks:scanned.reduce((s,r)=>s+r.missingRegistryFields,0),
      reviewRequiredChecks:scanned.reduce((s,r)=>s+r.independentReviewRequired,0),
      nonAutomatedChecks:scanned.reduce((s,r)=>s+r.notAutomated,0),
      independentlyCompletedScientificReviews:0,
      calibratedFDAForecasts:0,
      availableTestDefinitions:12,
      publicSource:"ClinicalTrials.gov API v2",
      savedToDatabase:false
    },
    rows,
    interpretation:{
      sourceCoverageOnly:true,phaseIndependentlyVerified:false,
      specialistAssessmentComplete:false,
      regulatoryAdjudicationComplete:false,
      historicalPredictionValidationComplete:false,
      fdaApproval:"ABSTAIN",completeResponseLetter:"ABSTAIN",
      reviewExtension:"ABSTAIN",certainty:"NOT_VALIDATED",
      warning:"Fresh ClinicalTrials.gov registry source-field inspection only. Not a comprehensive FDA/SEC/CMC or statistical adjudication and not a calibrated FDA prediction."
    }
  },{headers:noStore});
}
export async function GET(req:NextRequest){
  if(req.nextUrl.searchParams.get("run")!=="source-inspection")
    return NextResponse.json({
      status:"READY_ON_DEMAND",rosterSize:FOCUS_SPECIALTY_ASSESSMENT_QUEUE.length,
      instructions:"Open with ?run=source-inspection to perform a fresh, read-only all-FOCUS official registry scan.",
      prediction:"ABSTAIN",certainty:"NOT_VALIDATED"
    },{headers:noStore});
  return performScan();
}
export async function POST(req:NextRequest){
  const origin=req.headers.get("origin");
  if(!origin)return NextResponse.json({error:"Origin header required"},{status:403,headers:noStore});
  try{
    if(new URL(origin).host!==req.nextUrl.host)throw Error("ORIGIN_MISMATCH");
  }catch{
    return NextResponse.json({error:"Cross-origin request denied"},{status:403,headers:noStore});
  }
  return performScan();
}
