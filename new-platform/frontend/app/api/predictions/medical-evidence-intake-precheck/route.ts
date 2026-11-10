import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import pilot from "../../../../data/acacia-pilot-prediction-workup-20261108.json";
import {buildPhase3ReviewQueue} from "../../../../lib/acacia-phase3-review-queue";
import {buildAcaciaAcquisitionHandoff} from "../../../../lib/acacia-evidence-acquisition-handoff";
import {validateAcaciaIntakeCandidate} from "../../../../lib/acacia-evidence-intake-precheck";

/** A stateless SAME-ORIGIN METADATA FORMAT CHECK. No document bytes, retrieval,
 * uploads, persistence, reviewer signatures, patient records or grades.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff","Vary":"Cookie, Origin"};
const json=(data:Record<string,unknown>,status:number)=>NextResponse.json(data,{status,headers});
const MAX_BODY=12_000;

export async function POST(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return json({error:"Dashboard authentication required"},401);
  // State-changing HTTP method even for nonpersistent validation: fail closed
  // on absent, mismatched or opaque Origin. Browser same-origin fetch supplies it.
  if(req.headers.get("origin")!==req.nextUrl.origin||
     req.headers.get("sec-fetch-site")==="cross-site")
    return json({error:"Same-origin browser request required"},403);
  const q=req.nextUrl.searchParams;
  if(q.getAll("nct").length!==1||q.get("nct")!=="NCT06081894"||
     [...q.keys()].some(k=>k!=="nct"))
    return json({error:"Exact NCT06081894 query required"},422);
  if(!/^application\/json(?:\s*;|$)/i.test(req.headers.get("content-type")||""))
    return json({error:"JSON metadata only, never raw files"},415);
  const expectedBytes=Number(req.headers.get("content-length")||"0");
  if(!Number.isFinite(expectedBytes)||expectedBytes>MAX_BODY)
    return json({error:"Metadata payload too large"},413);
  let rawText="";
  try{rawText=await req.text();}
  catch{return json({error:"Failed to read metadata"},400);}
  if(rawText.length>MAX_BODY||new TextEncoder().encode(rawText).length>MAX_BODY)
    return json({error:"Metadata payload too large"},413);
  let candidate:unknown;
  try{candidate=JSON.parse(rawText);}
  catch{return json({error:"Invalid metadata JSON"},400);}
  const packet=buildAcaciaAcquisitionHandoff(buildPhase3ReviewQueue(pilot));
  const report=validateAcaciaIntakeCandidate(candidate,packet);
  if(!report)return json({error:"Evidence intake precheck withheld; source review state not valid"},503);
  return NextResponse.json(report,{status:report.issueCodes.length?422:200,headers});
}
