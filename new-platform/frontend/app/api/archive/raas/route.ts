import {HISTORICAL_ARCHIVE_FILES,readHistoricalArchive,type HistoricalArchiveSource} from "../../../../lib/historical-analysis-archive";
export const dynamic="force-dynamic";
/** GET-only historical export. No active analysis or mutation is available. */
export async function GET(request:Request){
 const params=new URL(request.url).searchParams,source=params.get("source"),nctId=params.get("nctId")??undefined;
 const headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
 if(nctId&&!/^NCT\d{8}$/.test(nctId))return Response.json({error:"Invalid exact NCT"},{status:422,headers});
 if(!source)return Response.json({readOnly:true,scope:"HISTORICAL_ARCHIVE_ONLY",sources:Object.keys(HISTORICAL_ARCHIVE_FILES)},{headers});
 if(!(source in HISTORICAL_ARCHIVE_FILES))return Response.json({error:"Unknown historical source"},{status:404,headers});
 try{return Response.json(await readHistoricalArchive(source as HistoricalArchiveSource,nctId),{headers});}
 catch{return Response.json({error:"Historical source unavailable; no record was changed"},{status:503,headers});}
}
