import history from "../../../../data/phaseFirstRatingHistory20261106.json";
export const dynamic="force-dynamic";
export function GET(request:Request){
 const id=new URL(request.url).searchParams.get("trialId");
 if(!id||!/^(NCT|ISRCTN)\d{8}$/.test(id))return Response.json({error:"Exact trial identifier required"},{status:400});
 const records=history.records.filter(r=>r.continuityKey===id);
 if(!records.length)return Response.json({error:"No phase-first history for this trial"},{status:404});
 return Response.json({trialId:id,scope:history.scope,records,
  note:"Append-only Git-persisted research snapshots. Existing RAAS, clinical-grade and calibration ledgers are unchanged; no source-only fact is promoted to a prediction."},{headers:{"Cache-Control":"no-store"}});
}
