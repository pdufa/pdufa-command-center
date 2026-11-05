/** Bounded single-file download for exact trial/program-stage expert review.
 * No uploaded signatures, score promotion or reviewer identity collection.
 */
import {buildRaasExactProgramReviewBundle}
 from "../../../lib/raas-exact-program-review-bundle";

export const dynamic="force-dynamic";
export function GET(request:Request){
 let taskId:string|null=null;
 try{taskId=new URL(request.url).searchParams.get("task");}
 catch{return Response.json({error:"INVALID_REQUEST_URL"},{status:400,
  headers:{"Cache-Control":"no-store"}});}
 if(!taskId||taskId.length>900||/[\u0000-\u001f\u007f]/.test(taskId))
  return Response.json({error:"EXACT_TASK_ID_REQUIRED"},{status:400,
   headers:{"Cache-Control":"no-store"}});
 const bundle=buildRaasExactProgramReviewBundle(taskId);
 if(!bundle)return Response.json({error:"EXACT_PROGRAM_REVIEW_TASK_NOT_FOUND"},{status:404,
  headers:{"Cache-Control":"no-store"}});
 const {ticker,nctId,stage}=bundle.program;
 return new Response(JSON.stringify(bundle,null,2)+"\n",{status:200,headers:{
  "Content-Type":"application/json; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-external-review-'+
   ticker+'-'+nctId+'-'+stage+'-30-metrics.json"',
  "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
 }});
}
