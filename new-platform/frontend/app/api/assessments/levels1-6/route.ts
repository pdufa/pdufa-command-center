import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import {assessmentOptions,parseRunRequest,runAssessment} from "../../../../lib/level16-assessment-runner";

export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=30;
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};
const json=(body:unknown,status=200)=>NextResponse.json(body,{status,headers});
const authorized=(req:NextRequest)=>authConfigured()&&hasSession(req.cookies.get(COOKIE_NAME)?.value);

/** Loading options never executes an assessment. */
export async function GET(req:NextRequest){
 if(!authorized(req))return json({error:"Sign in to run your assessments"},401);
 try{return json(assessmentOptions());}
 catch{return json({error:"Collected assessment evidence is unavailable or inconsistent"},503);}
}
/** Explicit owner click only. Server-selected evidence, no review/role/source claims accepted. */
export async function POST(req:NextRequest){
 if(!authorized(req))return json({error:"Sign in to run your assessments"},401);
 if(req.headers.get("origin")!==req.nextUrl.origin)return json({error:"Same-origin action required"},403);
 if(!req.headers.get("content-type")?.toLowerCase().startsWith("application/json"))return json({error:"JSON body required"},415);
 if(Number(req.headers.get("content-length")||0)>1024)return json({error:"Request too large"},413);
 let raw="";
 if(!req.body)return json({error:"Choose a trial or all FOCUS trials"},422);
 const reader=req.body.getReader();const chunks:Uint8Array[]=[];let size=0;
 try{
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>1024){await reader.cancel();return json({error:"Request too large"},413);}chunks.push(value);}
  raw=Buffer.concat(chunks).toString("utf8");
 }catch{return json({error:"Unable to read request"},422);}
 let request;
 try{request=parseRunRequest(JSON.parse(raw));}
 catch{return json({error:"Choose one exact FOCUS NCT or all FOCUS trials; no extra fields allowed"},422);}
 try{return json(runAssessment(request));}
 catch{return json({error:"Assessment could not run because the collected source package failed validation. No completion was recorded."},503);}
}
