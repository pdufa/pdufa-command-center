/** Download one exact-trial evidence packet. Read-only, unsigned and never approved. */
import {frozenReviewPacket} from "../../../lib/raas-external-review-intake";
export const dynamic="force-dynamic";
export function GET(request:Request){
 let taskId:string|null=null;
 try{taskId=new URL(request.url).searchParams.get("task");}
 catch{return Response.json({error:"INVALID_REQUEST_URL"},{status:400});}
 if(!taskId||taskId.length>700||/[\u0000-\u001f\u007f]/.test(taskId))
  return Response.json({error:"EXACT_TASK_ID_REQUIRED"},{status:400,
   headers:{"Cache-Control":"no-store"}});
 const packet=frozenReviewPacket(taskId);
 if(!packet)return Response.json({error:"EXACT_METRIC_NOT_FOUND"},{status:404,
  headers:{"Cache-Control":"no-store"}});
 const t=packet.task;
 return new Response(JSON.stringify(packet,null,2)+"\n",{status:200,headers:{
  "Content-Type":"application/json; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-review-'+t.ticker+'-'+
   t.nctId+'-'+t.metricId+'.json"',
  "Cache-Control":"no-store",
  "X-Content-Type-Options":"nosniff"
 }});
}
