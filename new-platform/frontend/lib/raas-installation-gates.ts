/** RAAS installation acceptance gates. This is an independent, fail-closed
 * completion check: passing unit tests does not imply validated clinical
 * predictions, investment returns, or permission to assign a numeric score.
 */
import type {RaasReadinessReport} from "./raas-readiness-scan";

export type InstallationGate={
 id:string;name:string;completed:boolean;
 achieved:number;required:number;unit:string;
 blocker:string;
};
export type RaasInstallationStatus={
 state:"COMPLETE"|"INCOMPLETE";
 technicalBlueprintReady:boolean;
 totalGates:number;completedGates:number;remainingGates:number;
 eligibleSourceYears:number;
 sourceYears:readonly {year:number;verified:boolean;status:string}[];
 gates:readonly InstallationGate[];
 note:string;
};
type YearAudit={year:number;status:string;sourceUrl?:string|null};
type HistoricalIntake={
 scope?:string;yearAudits?:YearAudit[];
 records?:unknown[];
};
const firstYear=2024,lastYear=2025;
const validSource=(url:unknown):url is string=>
 typeof url==="string" && /^https:\/\/[^\s/]+\.[^\s/]+/i.test(url);
const gate=(id:string,name:string,achieved:number,required:number,
 unit:string,blocker:string):InstallationGate=>({
  id,name,achieved,required,unit,completed:achieved>=required&&required>0,blocker
});
/** Non-empty approved records can count ONLY if the audited metric scan
 * already verified all chronological, issuer-disjoint holdout rules.
 */
export function evaluateRaasInstallation(
 report:RaasReadinessReport,
 intake:HistoricalIntake
):RaasInstallationStatus {
 const metrics=report.metrics;
 if(report.summary.metricsInspected!==60||metrics.length!==60||
  new Set(metrics.map(m=>m.stage+"|"+m.id)).size!==60||
  report.categories.length!==12||
  !intake || intake.scope!=="RAAS_2024_2025_PDUFA_POINT_IN_TIME_INTAKE"||
  !Array.isArray(intake.yearAudits)||intake.yearAudits.length!==2||
  !Array.isArray(intake.records))
  throw Error("RAAS_INSTALLATION_INPUT_INVALID");
 const entries=Array.from({length:lastYear-firstYear+1},(_,i)=>{
  const year=firstYear+i;
  const matching=intake.yearAudits!.filter(a=>a.year===year);
  if(matching.length!==1)throw Error("RAAS_INSTALLATION_YEAR_CENSUS_INVALID");
  const a=matching[0];
  const verified=a.status==="FULL_EVENT_CENSUS_AUDITED"&&validSource(a.sourceUrl);
  return {year,verified,status:verified?"SOURCE_CENSUS_AUDITED":
   "MISSING_VERIFIED_EVENT_CENSUS"};
 });
 const pre=metrics.filter(m=>m.stage==="pre"&&m.approvedCalibration).length;
 const post=metrics.filter(m=>m.stage==="post"&&m.approvedCalibration).length;
 const completeYears=entries.filter(y=>y.verified).length;
 const approvedTotal=pre+post;
 // A prospective metric-score source is NOT a full historical trade case.
 const gates:InstallationGate[]=[
  gate("catalog","60 metric definitions (30 TOP, 30 BOTTOM)",
   report.summary.metricsInspected,60,"metrics",
   "Complete the agreed 60 metric specification and stage mapping."),
  gate("historical-census","2024–2025 fully audited PDUFA event census (active two-year study)",
   completeYears,2,"years",
   "Original event target publications, withdrawals, CRLs, extensions and exceptions must be independently audited for 2024 and 2025; retrospective candidate dates are not evidence of complete years."),
  gate("historical-trades","Independent eligible historical trade records",
   report.summary.historicalAcceptedCases,60,"accepted trades",
   "At least 30 independent training issuers and 30 nonoverlapping holdout issuers are required per metric; even 60 trades alone cannot certify every metric."),
  gate("top-calibration","TOP historically calibrated 0–100 metric rules",
   pre,30,"TOP metrics",
   "Use source-dated original facts and issuer-disjoint walk-forward returns; no retrospectively invented grades."),
  gate("bottom-calibration","BOTTOM historically calibrated 0–100 metric rules",
   post,30,"BOTTOM metrics",
   "Verify disease-specific benchmarks, earlier FDA actions, independent return windows and validation protocols."),
  gate("reviewed-trials","Reviewed trial ENTRY/CURRENT/EXIT rating snapshots",
   report.summary.reviewedTrialSnapshots,1,"trial snapshots",
   "Approved dated metric grades and passed critical-risk gates must be recorded per trial; one snapshot is only a minimal smoke test.")
 ];
 // No false-positive complete state: a source-readiness report currently
 // explicitly declares finalScoring NOT_VALIDATED, so no condition can
 // override that declaration.
 const passed=gates.filter(g=>g.completed).length;
 const state=passed===gates.length&&
  approvedTotal===60&&report.finalScoring!=="NOT_VALIDATED"?"COMPLETE":"INCOMPLETE";
 return {state,technicalBlueprintReady:gates[0].completed,
  totalGates:gates.length,completedGates:passed,
  remainingGates:gates.length-passed,eligibleSourceYears:completeYears,
  sourceYears:entries,gates,
  note:"The active 2024–2025 two-year study replaces the ten-year completion requirement. Earlier 2016–2025 research remains archived and cannot enter the active cohort; original public event timing, $300M–$10B entry capitalization and issuer-disjoint holdouts still require independent proof. No missing score is assigned zero."};
}
