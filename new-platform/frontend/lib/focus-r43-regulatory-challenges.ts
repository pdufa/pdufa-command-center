/** MAIN R43: a strictly research-only, immutable-by-import original-source challenge overlay.
 * Does not authorize clinical grades, FDA forecasts, or retrospective outcome labels.
 */
import raw from "../data/focus-r43-priority-regulatory-challenges.json";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";

const EXPECTED = new Map([
  ["capr-deramiocel","NCT05126758"],
  ["svra-molgramostim","NCT04544293"],
  ["cogt-gist","NCT05208047"],
]);

export function validateFocusR43(data:unknown=raw){
  if(!data||typeof data!=="object"||Array.isArray(data))return null;
  const v=data as typeof raw;
  if(v.schema!=="MAIN_R43_PRIORITY_REGULATORY_CHALLENGE_RESEARCH_ONLY"||
    v.asOf!=="2026-11-09"||v.rosterNcts!==29||
    v.provisionalApplicationCycles!==23||
    v.independentClinicalReview!==false||
    v.historicalBacktestingValidated!==false||
    v.numericalApprovalProbability!==null||
    v.officialFdaOutcomeForecast!=="ABSTAIN"||
    v.officialReviewDelayForecast!=="UNKNOWN"||
    FOCUS_PRELIMINARY_R39.trials.length!==29||
    FOCUS_PRELIMINARY_R39.applications.length!==23||
    !Array.isArray(v.records)||v.records.length!==3)return null;
  const cycles=new Map(FOCUS_PRELIMINARY_R39.applications.map(a=>[a.id,a]));
  const seen=new Set<string>();
  for(const item of v.records){
    const expected=EXPECTED.get(item.cycleId), app=cycles.get(item.cycleId);
    if(!expected||seen.has(item.cycleId)||!app||
       item.ticker!==app.ticker||item.ncts.length!==1||item.ncts[0]!==expected||
       !app.ncts.includes(expected)||item.researchOnly!==true||
       item.officialOutcomeForecast!=="ABSTAIN"||item.reviewTimingForecast!=="UNKNOWN"||
       !Array.isArray(item.observations)||item.observations.length<2||
       !Array.isArray(item.sources)||item.sources.length<2||
       item.sources.some(s=>!s.url.startsWith("https://")||!s.date||
         !s.label||!["FDA_STAFF_PRE_AMENDMENT","OFFICIAL_SEC_SPONSOR","SPONSOR"].includes(s.type)))return null;
    seen.add(item.cycleId);
  }
  return seen.size===3?v:null;
}
export const FOCUS_R43_SOURCE_CHALLENGES=validateFocusR43();
