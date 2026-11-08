import {NextRequest,NextResponse} from "next/server";
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE} from "../../../../lib/focus-specialty-assessment";
import {makeEvidenceRun,TEST_NAMES} from "../../../../lib/prediction-source-tests";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;
const noStore={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"} as const;

/**
 * User-triggered read-only scientific source evidence inspection.
 * No run is silently started by visiting a page. No numerical probability is
 * generated, saved or released. No backend state or legacy scan is mutated.
 */
export async function POST(req:NextRequest){
  const origin=req.headers.get("origin");
  if(origin){
    try {
      if(new URL(origin).host!==req.nextUrl.host)
        return NextResponse.json({error:"Cross-origin analysis request denied"},{status:403,headers:noStore});
    }catch{
      return NextResponse.json({error:"Invalid request origin"},{status:403,headers:noStore});
    }
  }
  if(!(req.headers.get("content-type")||"").toLowerCase().includes("application/json"))
    return NextResponse.json({error:"JSON input required"},{status:415,headers:noStore});
  if(Number(req.headers.get("content-length")||0)>2000)
    return NextResponse.json({error:"Request too large"},{status:413,headers:noStore});
  let input:unknown;
  try{input=await req.json();}catch{
    return NextResponse.json({error:"Invalid JSON body"},{status:400,headers:noStore});
  }
  const body=input&&typeof input==="object"&&!Array.isArray(input)?input as Record<string,unknown>:{};
  const nct=body.nct;
  const mode=body.mode;
  const index=body.testIndex;
  if(typeof nct!=="string"||!/^NCT\d{8}$/.test(nct)||
     !FOCUS_SPECIALTY_ASSESSMENT_QUEUE.some(row=>row.nct===nct)||
     (mode!=="FULL"&&mode!=="SINGLE")||
     (mode==="SINGLE"&&(!Number.isInteger(index)||typeof index!=="number"||index<0||index>=TEST_NAMES.length))){
    return NextResponse.json({error:"Select an exact current FOCUS NCT and a valid analysis mode/test"},{status:422,headers:noStore});
  }
  // Exact-path official source only; never accept arbitrary client URLs.
  const url="https://clinicaltrials.gov/api/v2/studies/"+nct+"?format=json";
  try{
    const response=await fetch(url,{
      headers:{Accept:"application/json"},cache:"no-store",signal:AbortSignal.timeout(16000)
    });
    if(!response.ok||!response.headers.get("content-type")?.toLowerCase().includes("json"))
      throw Error("OFFICIAL_REGISTRY_UNAVAILABLE");
    const raw=await response.text();
    if(raw.length>5_000_000)throw Error("REGISTRY_SOURCE_TOO_LARGE");
    const study:unknown=JSON.parse(raw);
    const result=makeEvidenceRun(study,nct,mode,mode==="SINGLE"?index as number:undefined);
    return NextResponse.json(result,{headers:noStore});
  }catch(error){
    return NextResponse.json({
      error:error instanceof Error&&error.message==="REGISTRY_NCT_ID_MISMATCH"?
        "Registry returned a different NCT identity; no analysis released.":
        "Official ClinicalTrials.gov source could not be inspected. No test or prediction was completed.",
      nct,source:"https://clinicaltrials.gov/study/"+nct,
      prediction:"ABSTAIN",certainty:"NOT_VALIDATED"
    },{status:503,headers:noStore});
  }
}
