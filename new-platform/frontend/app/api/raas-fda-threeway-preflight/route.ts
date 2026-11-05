/** Public read-only unsigned research checklist; never accepts forecasts. */
import {buildThreeWayFDAFreezePreflightPlan}
 from "../../../lib/raas-fda-three-way-freeze-preflight";

export const dynamic="force-dynamic";
export function GET(request:Request){
 let key:string|null=null;
 try{key=new URL(request.url).searchParams.get("case");}
 catch{return Response.json({error:"INVALID_REQUEST_URL"},{status:400,
  headers:{"Cache-Control":"no-store"}});}
 if(!key||key.length>160||/[\u0000-\u001f\u007f]/.test(key))
  return Response.json({error:"EXACT_CASE_KEY_REQUIRED"},{status:400,
   headers:{"Cache-Control":"no-store"}});
 const plan=buildThreeWayFDAFreezePreflightPlan();
 const record=plan.records.find(x=>x.caseKey===key);
 if(!record)return Response.json({error:"EXACT_FDA_CASE_NOT_FOUND"},{status:404,
  headers:{"Cache-Control":"no-store"}});
 const filename="raas-fda-threeway-preflight-"+record.ticker+"-"+
  record.sourceFingerprint.slice(0,12)+".json";
 return new Response(JSON.stringify(record,null,2)+"\n",{status:200,headers:{
  "Content-Type":"application/json; charset=utf-8",
  "Content-Disposition":'attachment; filename="'+filename+'"',
  "Cache-Control":"no-store",
  "X-Content-Type-Options":"nosniff"
 }});
}
