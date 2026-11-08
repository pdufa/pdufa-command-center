import history from "../../../../data/phaseFirstRatingHistory20261106.json";
export const dynamic="force-dynamic";
export function GET(request:Request){
 const id=new URL(request.url).searchParams.get("trialId");
 if(!id||!/^(NCT|ISRCTN)\d{8}$/.test(id))return Response.json({error:"Exact trial identifier required"},{status:400});
 const records=history.records.filter(r=>r.continuityKey===id);
 if(!records.length)return Response.json({error:"No phase-first history for this trial"},{status:404});
 return Response.json({trialId:id,scope:"HISTORICAL_ARCHIVE_ONLY",readOnly:true,records,
  note:"Read-only historical snapshots as originally recorded. Retired ratings do not contribute to current source analysis or FDA predictions."},{headers:{"Cache-Control":"no-store"}});
}
