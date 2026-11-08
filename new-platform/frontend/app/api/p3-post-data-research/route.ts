import focus from "../../../data/p3PostDataActive.json";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};

/** Existing endpoint is retained as a source-only compatibility view.
 * Archived numerical scores and shared research ledgers remain accessible
 * in historical storage, but are never imported or recalculated here.
 */
export function GET(request:Request){
 const params=new URL(request.url).searchParams;
 const nct=params.get("nctId"),format=params.get("format");
 const source=(r:typeof focus.records[number])=>({
  nctId:r.nct,ticker:r.ticker,company:r.company,
  marketCap:r.marketCap,fdaStatus:r.fdaStatus,
  originalClinicalResultsSource:r.resultsUrl,
  originalRegulatorySource:r.regulatoryUrl,
  sourceRosterAsOf:focus.asOf,
  medicalAnalysisHistory:"/analyze-now?nct="+encodeURIComponent(r.nct),
  scientificReviewStatus:"NOT_INDEPENDENTLY_ADJUDICATED",
  approval:"ABSTAIN",crl:"ABSTAIN",delay:"ABSTAIN",certainty:"NOT_VALIDATED"
 });
 if(nct){
  if(!/^NCT\d{8}$/.test(nct))
   return Response.json({error:"Invalid exact NCT"},{status:422,headers});
  const match=focus.records.find(t=>t.nct===nct);
  if(!match)
   return Response.json({error:"NCT not in dated FOCUS evidence roster"},{status:404,headers});
  return Response.json({trial:source(match),historyReadOnlyByNct:true},{headers});
 }
 if(format){
  if(format!=="csv")
   return Response.json({error:"Retired numerical score exports are not available; use original-source CSV."},{status:410,headers});
  const fields=["nctId","ticker","company","originalClinicalResultsSource","originalRegulatorySource","scientificReviewStatus"];
  const csvCell=(v:unknown)=>'"'+String(v??"").replace(/"/g,'""').replace(/^[=+@-]/,"'$&")+'"';
  const rows=focus.records.map(t=>{const x=source(t);return fields.map(k=>csvCell(x[k as keyof typeof x]));});
  const csv=[fields.join(","),...rows.map(r=>r.join(","))].join("\r\n")+"\r\n";
  return new Response("\ufeff"+csv,{headers:{...headers,"Content-Type":"text/csv; charset=utf-8",
    "Content-Disposition":'attachment; filename="focus-original-source-evidence.csv"'}});
 }
 return Response.json({trialCount:focus.records.length,asOf:focus.asOf,
  scope:"DATED_FOCUS_ORIGINAL_SOURCE_ONLY",
  trials:focus.records.map(source),sourceVerifiedByIndependentReview:false,
  note:"Historical research records are preserved read-only, never inputs to active scoring or forecasts."},{headers});
}
