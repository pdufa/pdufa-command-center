import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import pilot from "../../../../data/acacia-pilot-prediction-workup-20261108.json";
import {buildPhase3ReviewQueue,reviewQueueCsv} from "../../../../lib/acacia-phase3-review-queue";

/** Private read-only research queue, not a clinical reviewer write API. */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const baseHeaders={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};

export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers:baseHeaders});
  const query=req.nextUrl.searchParams;
  if(query.getAll("nct").length!==1||query.get("nct")!=="NCT06081894"||
    [...query.keys()].some(x=>x!=="nct"&&x!=="format")||
    query.getAll("format").length>1||
    (query.has("format")&&!["csv","json"].includes(query.get("format")||"")))
    return NextResponse.json({error:"Exact trial and supported output format required"},
      {status:422,headers:baseHeaders});
  const queue=buildPhase3ReviewQueue(pilot);
  if(!queue||queue.summary.officialClinicalGrades!==0||queue.positions.length!==18||
     queue.positions.some(x=>x.clinicalGrade!==null||x.qualifiedReviewerSignoff!==false||
       x.fdaProbability!==null))
    return NextResponse.json({error:"Research source queue is not verified"},
      {status:503,headers:baseHeaders});
  if(query.get("format")==="csv")
    return new NextResponse(reviewQueueCsv(queue),{
      status:200,
      headers:{...baseHeaders,"Content-Type":"text/csv; charset=utf-8",
        "Content-Disposition":'attachment; filename="acacia-phase3-research-queue.csv"'}
    });
  return NextResponse.json(queue,{headers:baseHeaders});
}
