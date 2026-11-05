/** Read-only all-trial ClinicalTrials.gov source-fact export.
 * These are source-reported, unadjusted observations. NO scored RAAS metrics
 * or calibrated FDA outcomes are present in this export.
 */
import registry from "../../../public/raas-registry-evidence-index.json";
import {buildRaasRegistryClinicalFactLedger} from "../../../lib/raas-registry-clinical-fact-ledger";
export const dynamic="force-dynamic";
const fields=["nctId","ticker","candidateStage","metricIds","kind",
 "sourceDate","resultsFirstPosted","sourceAsOf","sourceUrl","sourceHash",
 "measurementLabel","measurementValue","measurementUnit","description"] as const;
function cell(value:unknown):string{
 const s=Array.isArray(value)?value.join("; "):String(value??"");
 const safe=/^\s*[=+@-]/.test(s)?"'"+s:s;
 return '"'+safe.replaceAll('"','""')+'"';
}
export function GET(){
 const ledger=buildRaasRegistryClinicalFactLedger(registry);
 const lines=[fields.join(","),...ledger.facts.map(f=>
  fields.map(k=>cell(f[k])).join(","))];
 return new Response("\uFEFF"+lines.join("\r\n")+"\r\n",{
  status:200,headers:{
   "Content-Type":"text/csv; charset=utf-8",
   "Content-Disposition":'attachment; filename="raas-registry-clinical-source-facts.csv"',
   "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
  }
 });
}
