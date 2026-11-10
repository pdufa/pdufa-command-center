import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE} from "../../../../lib/focus-specialty-assessment";
import {isolatedMedicalBackend} from "../../../../lib/medical-review-matrix";
import {validateSourceRun} from "../../../../lib/medical-source-run";

export const runtime="nodejs";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};

export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  const nct=req.nextUrl.searchParams.get("nct");
  if(!nct||!/^NCT\d{8}$/.test(nct)||!FOCUS_SPECIALTY_ASSESSMENT_QUEUE.some(t=>t.nct===nct))
    return NextResponse.json({error:"Select a verified FOCUS NCT"},{status:422,headers});
  // Do not fall back to the ordinary/production backend, and never use the
  // read-only assessment key against an operational source-worker endpoint.
  const base=isolatedMedicalBackend(process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL);
  const key=process.env.PDUFA_MEDICAL_INTERNAL_API_KEY??process.env.PDUFA_INTERNAL_API_KEY;
  if(!base||!key)return NextResponse.json({error:"Isolated source-worker status access not configured"},{status:503,headers});
  try{
    // GET only. This route cannot start, stop, resume or regrade any run.
    const response=await fetch(base+"/api/medical-continuous/"+nct+"/runs/latest",{
      headers:{"x-pdufa-internal-key":key,Accept:"application/json"},
      redirect:"error",cache:"no-store",signal:AbortSignal.timeout(15000)
    });
    if(response.status===404)
      return NextResponse.json({kind:"NO_RUN",nct,researchOnly:true,prediction:"ABSTAIN"},{headers});
    if(!response.ok||!response.headers.get("content-type")?.includes("json"))
      throw Error("SOURCE_RUN_STATUS_UNAVAILABLE");
    const body=await response.text();
    if(body.length>1_500_000)throw Error("SOURCE_RUN_STATUS_TOO_LARGE");
    const status=validateSourceRun(JSON.parse(body) as unknown,nct);
    return NextResponse.json(status,{headers});
  }catch{
    return NextResponse.json({error:"Isolated source-worker status could not be verified; activity is unknown"},{status:503,headers});
  }
}
