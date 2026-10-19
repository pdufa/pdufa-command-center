import { NextRequest, NextResponse } from "next/server";
import { backupDecision, SCAN_WORKFLOW, SCAN_REPO } from "../../../../lib/nightly-backup";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

function response(payload:object,status=200){
  return NextResponse.json(payload,{status,headers:{"Cache-Control":"no-store"}});
}
async function github(path:string,token:string,options:RequestInit={}){
  return fetch("https://api.github.com/repos/"+SCAN_REPO+path,{
    ...options,cache:"no-store",signal:AbortSignal.timeout(15000),
    headers:{"Accept":"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28",
      "User-Agent":"pdufa-independent-vercel-backup",
      "Authorization":"Bearer "+token,
      ...(options.headers||{})}
  });
}

/** Independent missed-start fallback; no public or password-session invocation. */
export async function GET(request:NextRequest){
  const secret=process.env.CRON_SECRET?.trim();
  if(!secret||secret.length<16||request.headers.get("authorization")!=="Bearer "+secret)
    return response({ok:false,reason:"Unauthorized cron request"},401);
  const token=process.env.PDUFA_GITHUB_TOKEN?.trim();
  if(!token)return response({ok:false,reason:"GitHub dispatch token not configured"},503);
  try {
    const historyResponse=await github("/actions/workflows/"+SCAN_WORKFLOW+
      "/runs?branch=main&per_page=100",token);
    if(!historyResponse.ok){
      console.error("PDUFA backup history HTTP",historyResponse.status);
      return response({ok:false,reason:"GitHub status verification failed; no dispatch"},503);
    }
    const body:unknown=await historyResponse.json();
    const history=body&&typeof body==="object"&&"workflow_runs" in body
      ?(body as {workflow_runs:unknown}).workflow_runs:null;
    const decision=backupDecision(history,new Date());
    if(decision.action==="error"){
      console.error("PDUFA backup safety gate",decision.reason);
      return response({ok:false,...decision},503);
    }
    if(decision.action==="skip"){
      console.info("PDUFA backup skipped",decision.night,decision.reason);
      return response({ok:true,...decision});
    }
    const dispatched=await github("/actions/workflows/"+SCAN_WORKFLOW+"/dispatches",token,{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({ref:"main",inputs:{
        scan_mode:decision.scanMode,gem_action:decision.gemAction,validate_only:false
      }})
    });
    if(dispatched.status!==204){
      console.error("PDUFA backup dispatch HTTP",dispatched.status);
      return response({ok:false,action:"error",night:decision.night,
        reason:"GitHub rejected backup dispatch; check Actions write permission"},502);
    }
    console.info("PDUFA backup requested sequence",decision.night,decision.scanMode);
    return response({ok:true,action:"dispatched",night:decision.night,
      scanMode:decision.scanMode,gemAction:decision.gemAction,
      workflowUrl:"https://github.com/"+SCAN_REPO+"/actions/workflows/"+SCAN_WORKFLOW},202);
  } catch {
    return response({ok:false,reason:"GitHub check or dispatch unavailable; no confirmed launch"},503);
  }
}
