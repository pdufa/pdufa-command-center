/** All primary contrast-to-arm source checks, ungraded. Spreadsheet safe. */
import registry from "../../../public/raas-registry-evidence-index.json";
import {buildPrimaryContrastReconciliationLedger} from "../../../lib/raas-primary-arm-reconciliation";
export const dynamic="force-dynamic";
const fields=[
 "nctId","ticker","outcomeIndex","comparisonIndex","outcomeTitle",
 "outcomeTimeFrame","outcomeUnit","groupIds","groupNames","groupValues",
 "groupMeasurementSeries","armValueMultiplicity","roundingUncertainty",
 "reportedStatisticType","reportedStatisticRaw","reportedCILower",
 "reportedCIUpper","pValueRaw","method","observedFirstMinusSecond",
 "absoluteGapToEitherDirection","gapThreshold","signal",
 "resultsFirstPosted","sourceAsOf","sourceUrl","sourceHash"
] as const;
const clean=(v:unknown)=>{
 const s=Array.isArray(v)?v.map(x=>x??"N/A").join(" | "):String(v??"");
 const safe=/^\s*[=+@-]/.test(s)?"'"+s:s;
 return '"'+safe.replaceAll('"','""')+'"';
};
export function GET(){
 const {records}=buildPrimaryContrastReconciliationLedger(registry);
 const csv="\uFEFF"+[fields.join(","),...records.map(r=>
  fields.map(k=>clean(r[k])).join(","))].join("\r\n")+"\r\n";
 return new Response(csv,{status:200,headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-primary-arm-reconciliation.csv"',
  "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
 }});
}
