/** Unsigned exact-NCT clinical registry evidence packet for review, not scores.
 * Each request loads the saved source snapshot; no live FDA or trial claims.
 */
import registry from "../../../public/raas-registry-evidence-index.json";
import {parseRegistryEvidenceIndex} from "../../../lib/raas-registry-evidence";
import {registryEvidenceReviewerPacket} from "../../../lib/raas-registry-source-integrity";
export const dynamic="force-dynamic";
const index=parseRegistryEvidenceIndex(registry);
export function GET(request:Request){
 let nctId="",ticker="";
 try{
  const url=new URL(request.url);
  nctId=url.searchParams.get("nctId")??"";
  ticker=url.searchParams.get("ticker")??"";
 }catch{return Response.json({error:"INVALID_REQUEST_URL"},{status:400});}
 if(!/^NCT\d{8}$/.test(nctId)||!/^[A-Z]{1,7}(?:[.-][A-Z]{1,3})?$/.test(ticker))
  return Response.json({error:"EXACT_NCT_AND_ISSUER_REQUIRED"},{status:400,
   headers:{"Cache-Control":"no-store"}});
 const record=index.records.find(r=>r.nctId===nctId&&r.ticker===ticker);
 if(!record)return Response.json({error:"SOURCE_TRIAL_NOT_FOUND"},{status:404,
  headers:{"Cache-Control":"no-store"}});
 const packet=registryEvidenceReviewerPacket(record,index.sourceAsOf);
 return new Response(JSON.stringify(packet,null,2)+"\n",{status:200,headers:{
  "Content-Type":"application/json; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-registry-'+ticker+'-'+nctId+'-review.json"',
  "Cache-Control":"no-store",
  "X-Content-Type-Options":"nosniff"
 }});
}
