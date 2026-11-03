/** Consistent read-only RAAS status for NCT spreadsheet rows and CSV exports.
 * Registry results posting is NOT an issuer public-readout classification.
 * Only independently approved, exact-identity ledger ratings become scores.
 */
import type {RaasStage} from "./raas-metric-specs";
import {parseRaasPilotFeed} from "./raas-score-engine";
import {parseProspectiveSourceBaselines} from "./raas-prospective-source-baselines";
import {scanRaasCurrentEvidence} from "./raas-current-evidence-scan";
import {parseRaasCalibrations,parseRaasReviewedLedger,reviewedScoreForTrial}
 from "./raas-reviewed-score-ledger";
import {parseHistoricalFeed,evaluateHistoricalFeed} from "./raas-historical-backtest";
import {parseMetricHistory,evaluateMetricHistory} from "./raas-metric-backtest";
import pilotData from "../data/raas-pilot-observations.json";
import prospectiveData from "../data/raas-prospective-source-baselines.json";
import calibrationsData from "../data/raas-approved-calibrations.json";
import reviewedData from "../data/raas-reviewed-snapshots.json";
import historicalData from "../data/raas-historical-cases.json";
import metricHistoryData from "../data/raas-historical-metric-snapshots.json";

const pilot=parseRaasPilotFeed(pilotData);
const prospective=parseProspectiveSourceBaselines(prospectiveData);
const calibrations=parseRaasCalibrations(calibrationsData);
const reviewed=parseRaasReviewedLedger(reviewedData);
// Do not load unapproved historical research into an approved numerical grade.
// Future approved scores require all the same holdout gates as the detailed view.
const diagnostics=calibrations.entries.length&&reviewed.records.length
 ?evaluateMetricHistory(
   parseHistoricalFeed(historicalData),
   evaluateHistoricalFeed(parseHistoricalFeed(historicalData)),
   parseMetricHistory(metricHistoryData))
 :[];
const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
export type RaasSpreadsheetTrial={
 nctId:string;ticker:string;drug?:string;indication?:string;
 /** Only an independently verified issuer Phase 3 announcement can set this. */
 confirmedPostReadout?:boolean;
 /** Only the separate, issuer-source-classified TOP/BOTTOM sheet can set this. */
 classifiedStage?:RaasStage|null;
};
export type RaasSpreadsheetSummary={
 stage:RaasStage|null;approvedScore:number|null;
 mappedAreas:number|null;missingAreas:number|null;
 sourceAsOf:string;approvedMetrics:number;
 state:"INVALID_IDENTITY"|"STAGE_UNVERIFIED"|"PENDING_VALIDATION"|"APPROVED";
};
export function raasSpreadsheetSummary(trial:RaasSpreadsheetTrial):RaasSpreadsheetSummary{
 const base={
  stage:null,approvedScore:null,mappedAreas:null,missingAreas:null,
  sourceAsOf:pilot.sourceAsOf,approvedMetrics:calibrations.entries.length
 } as const;
 if(!/^NCT\d{8}$/.test(trial.nctId)||!trial.ticker?.trim())
  return {...base,state:"INVALID_IDENTITY"};
 const matches=[...pilot.records,...prospective.records].filter(item=>
  item.nctId===trial.nctId&&same(item.ticker,trial.ticker)&&
  (!trial.drug?.trim()||same(item.drug,trial.drug))&&
  (!trial.indication?.trim()||same(item.indication,trial.indication)));
 const knownStages=[...new Set(matches.map(m=>m.stage))];
 // A ClinicalTrials.gov posted-results flag cannot determine TOP/BOTTOM.
 const stage=trial.classifiedStage||(trial.confirmedPostReadout?"post":
  knownStages.length===1?knownStages[0]:null);
 if(!stage)return {...base,state:"STAGE_UNVERIFIED"};
 // If the row supplies drug and indication, reject cross-therapy associations.
 const matchingStage=matches.some(item=>item.stage===stage);
 const evidence=matchingStage||(!trial.drug?.trim()&&!trial.indication?.trim())
  ?scanRaasCurrentEvidence(pilot,prospective,trial,stage,pilot.sourceAsOf)
  :null;
 const mapped=evidence?.mappedMetrics??0;
 const completeIdentity=!!trial.drug?.trim()&&!!trial.indication?.trim();
 const review=completeIdentity?reviewedScoreForTrial(reviewed,calibrations,{
   nctId:trial.nctId,ticker:trial.ticker,drug:trial.drug!,
   indication:trial.indication!
 },stage,"CURRENT",reviewed.sourceAsOf,diagnostics):null;
 const score=review?.score.score??null;
 return {stage,approvedScore:score,mappedAreas:mapped,
  missingAreas:30-mapped,sourceAsOf:pilot.sourceAsOf,
  approvedMetrics:calibrations.entries.filter(x=>x.stage===stage).length,
  state:score===null?"PENDING_VALIDATION":"APPROVED"};
}
export function raasSpreadsheetExport(trial:RaasSpreadsheetTrial){
 const s=raasSpreadsheetSummary(trial);
 return [s.stage?(s.stage==="pre"?"TOP":"BOTTOM"):"UNCLASSIFIED",
  s.approvedScore===null?"":String(s.approvedScore),
  s.mappedAreas===null?"":String(s.mappedAreas),s.state] as const;
}
