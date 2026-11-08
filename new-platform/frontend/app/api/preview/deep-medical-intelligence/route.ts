import packet from "../../../../data/deepMedicalIntelligencePreview.json";
import {parseDeepMedicalSnapshot} from "../../../../lib/deep-medical-intelligence";

export async function GET(request:Request){
 const params=new URL(request.url).searchParams,applicationId=params.get("applicationId"),nctId=params.get("nctId"),sourceId=params.get("sourceId"),format=params.get("format");
 const headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
 if(nctId&&!/^NCT\d{8}$/.test(nctId))return Response.json({error:"INVALID_EXACT_NCT"},{status:422,headers});
 if(format&&format!=="json")return Response.json({error:"UNSUPPORTED_PREVIEW_FORMAT"},{status:422,headers});
 try{
  const report=parseDeepMedicalSnapshot(packet);
  let applications=report.applications;
  if(applicationId)applications=applications.filter(application=>application.id===applicationId);
  if(nctId)applications=applications.filter(application=>application.nctIds.includes(nctId));
  if((applicationId||nctId)&&applications.length===0)return Response.json({error:"PREVIEW_APPLICATION_NOT_FOUND"},{status:404,headers});
  if(sourceId){
   const sources=applicationId||nctId?applications.flatMap(application=>application.sources):report.sources;
   const source=sources.find(item=>item.id===sourceId);
   if(!source)return Response.json({error:"PREVIEW_SOURCE_NOT_FOUND"},{status:404,headers});
   return Response.json({schemaVersion:1,asOf:report.asOf,source,applicationIds:applications.filter(application=>application.sources.some(item=>item.id===sourceId)).map(application=>application.id)},{headers});
  }
  return Response.json({...report,applications},{headers});
 }catch{
  return Response.json({error:"PREVIEW_SOURCE_VALIDATION_REQUIRED",message:"The isolated preview packet could not be validated. No missing evidence or application outcome was inferred."},{status:503,headers});
 }
}
