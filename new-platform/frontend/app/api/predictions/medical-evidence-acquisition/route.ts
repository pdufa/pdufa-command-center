import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import pilot from "../../../../data/acacia-pilot-prediction-workup-20261108.json";
import {buildPhase3ReviewQueue} from "../../../../lib/acacia-phase3-review-queue";
import {buildAcaciaAcquisitionHandoff,acquisitionDraftText} from "../../../../lib/acacia-evidence-acquisition-handoff";

/** Signed-in, exact-trial, GET-only document-acquisition handoff; NEVER sends mail. */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  const q=req.nextUrl.searchParams;
  if(q.getAll("nct").length!==1||q.get("nct")!=="NCT06081894"||
     q.getAll("format").length>1||
     [...q.keys()].some(k=>k!=="nct"&&k!=="format")||
     (q.has("format")&&!["json","txt"].includes(q.get("format")||"")))
    return NextResponse.json({error:"Exact NCT and supported format required"},{status:422,headers});
  const packet=buildAcaciaAcquisitionHandoff(buildPhase3ReviewQueue(pilot));
  if(!packet||packet.requests.length!==6||packet.approvedClinicalGrades!==0||
     packet.requestDeliveryStatus!=="DRAFT_ONLY_NOT_SENT"||
     packet.requests.some(x=>x.officialClinicalGrade!==null||
       x.independentReviewerSigned!==false||x.acquisitionState!=="DRAFT_NOT_SENT"))
    return NextResponse.json({error:"Original evidence acquisition packet withheld"},{status:503,headers});
  if(q.get("format")==="txt")
    return new NextResponse(acquisitionDraftText(packet),{status:200,headers:{
      ...headers,"Content-Type":"text/plain; charset=utf-8",
      "Content-Disposition":'attachment; filename="ACACIA-original-evidence-inquiry-DRAFT-NOT-SENT.txt"'
    }});
  return NextResponse.json(packet,{status:200,headers});
}
