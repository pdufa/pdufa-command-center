/** Export the entire saved 762-trial gap queue; no scores or trading signals.
 * CSV formula-escaping prevents source text from executing spreadsheet formulas.
 */
import registry from "../../../public/raas-registry-evidence-index.json";
import {buildTrialEvidenceBacklog} from "../../../lib/raas-trial-evidence-backlog";
export const dynamic="force-dynamic";
const fields=[
 "nctId","ticker","priority","stage","trialName","registeredStatus",
 "postedResults","postedPrimaryOutcomeCount","hasPrimaryComparisons",
 "hasConfidenceIntervals","hasSeriousEventDenominators",
 "primaryContrastCount","primaryNumericCICount","saeDenominatorGroupCount",
 "sourceIntegrityIssueCount","sourceIntegrityIssueCodes","reviewedTop",
 "reviewedBottom","stageEvidenceDate","acceptedPdufaGoal",
 "applicationKey","sourceDate","sourceUrl","nextEvidenceAction"
] as const;
function cell(v:unknown){
 const s=String(v??"");
 const safe=/^\s*[=+@-]/.test(s)?"'"+s:s;
 return '"'+safe.replaceAll('"','""')+'"';
}
export function GET(){
 const backlog=buildTrialEvidenceBacklog(registry);
 const lines=[fields.join(","),...backlog.items.map(row=>
  fields.map(k=>cell(row[k])).join(","))];
 return new Response("\uFEFF"+lines.join("\r\n")+"\r\n",{
  status:200,headers:{
   "Content-Type":"text/csv; charset=utf-8",
   "Content-Disposition":'attachment; filename="raas-762-trial-evidence-gaps.csv"',
   "Cache-Control":"no-store",
   "X-Content-Type-Options":"nosniff"
  }
 });
}
