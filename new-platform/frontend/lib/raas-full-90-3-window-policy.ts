/** Pure research configuration shared by the UI; no default entry or exit.
 * These are calendar offsets. Actual exchange sessions and price bars are
 * resolved by the isolated historical research workflow, never inferred here.
 */
export type RaasWindowPair={entryLeadCalendarDays:number;exitLeadCalendarDays:number};
export const ALL_WINDOW_ENTRY_MIN=4;
export const ALL_WINDOW_ENTRY_MAX=90;
export const ALL_WINDOW_EXIT_MIN=3;
export function raasFull903CalendarPairs():RaasWindowPair[]{
 const out:RaasWindowPair[]=[];
 for(let e=ALL_WINDOW_ENTRY_MAX;e>=ALL_WINDOW_ENTRY_MIN;e--)
  for(let x=ALL_WINDOW_EXIT_MIN;x<e;x++)
   out.push({entryLeadCalendarDays:e,exitLeadCalendarDays:x});
 if(out.length!==3828)throw Error("RAAS_90_3_SEARCH_SCOPE_INVALID");
 return out;
}
export const raasFull903Overview=()=>{
 const pairs=raasFull903CalendarPairs();
 return {
  entryRange:"T−90 through T−4",
  exitRange:"T−89 through T−3, strictly after entry",
  availablePairs:pairs.length,
  sampleCaseCount:9,
  historicalGoalVersionCaseSets:11,
  scenarioEvaluations:pairs.length*11,
  explicitBenchmarkWindow:null,
  approvedOptimalWindow:null,
  independentlyVerifiedTrades:0,
  warning:"Research-only selected 2024–2025 sample. Earlier findings including T−79/T−14 are not validated as best."
 };
};
