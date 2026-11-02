/** Independent historical RAAS research readiness audit.
 * Records here were selected after their outcomes. This module MUST NOT
 * convert them into original historical forecasts or approved score grades.
 * "RECORDED" denotes a structured dated claim, not external source verification.
 */
import type {RaasStage} from "./raas-metric-specs";
import type {TopRetrospectiveFeed,TopRetrospectiveRecord} from "./raas-top-retrospective-intake";
import type {RetrospectiveFeed,RetrospectiveWindow} from "./raas-retrospective-intake";

export type HistoricalAuditStatus="RECORDED_NOT_INDEPENDENTLY_VERIFIED"|"REQUIRES_RECONCILIATION"|"NOT_AVAILABLE";
export type HistoricalAuditItem={
 id:string;label:string;status:HistoricalAuditStatus;
 detail:string;priority:1|2|3;sourceUrl?:string;
};
export type HistoricalAuditCase={
 id:string;stage:RaasStage;ticker:string;drug:string;indication:string;
 nctCount:number;entryDate:string;exitDate:string;grossPercent:number;
 marketCapUsdMillions:number;eventDate:string;
 items:HistoricalAuditItem[];
 outstandingCount:number;criticalOutstandingCount:number;
 eligibleForHistoricalTraining:false;eligibleForPredictiveValidation:false;
};
const round=(n:number)=>Math.round(n*100)/100;
const dayOffset=(date:string,days:number)=>
 new Date(Date.parse(date+"T00:00:00Z")+days*86400000).toISOString().slice(0,10);
const recorded=(id:string,label:string,detail:string,sourceUrl:string,priority:1|2|3=2):HistoricalAuditItem=>
 ({id,label,detail,sourceUrl,status:"RECORDED_NOT_INDEPENDENTLY_VERIFIED",priority});
const pending=(id:string,label:string,detail:string,priority:1|2|3=1):HistoricalAuditItem=>
 ({id,label,detail,status:"REQUIRES_RECONCILIATION",priority});
const absent=(id:string,label:string,detail:string,priority:1|2|3=1):HistoricalAuditItem=>
 ({id,label,detail,status:"NOT_AVAILABLE",priority});

function sharedItems(row:TopRetrospectiveRecord|RetrospectiveWindow):HistoricalAuditItem[]{
 return [
  recorded("stock-window","Historical price observations",
   `Vendor-reported gross entry ${row.entry.close} and exit ${row.exit.close} USD closing prices. Not split/ADR adjusted or independently reconciled.`,row.entry.sourceUrl),
  recorded("entry-cap","Entry-date company size",
   `Vendor-reported entry-date market capitalization $ ${row.marketCapAtEntry.usdMillions} million; within $300 million–$10 billion research filter. Share counts and corporate actions still need review.`,
   row.marketCapAtEntry.sourceUrl),
  pending("pricing-audit","Reconcile historical prices and market capitalization",
   "Independently establish both trading-session prices, adjusted corporate actions and fully diluted shares; reconcile dated enterprise/equity value and stock class/ADR units."),
  pending("execution","Model an executable investment window",
   "Confirm exchange holidays, bid–ask spread, slippage, opening/closing execution feasibility and realistic round-trip costs."),
  pending("sec-finance","Reconstruct entry-date financial and financing position",
   "Review SEC filings available at entry: cash, burn, debt, shelf/ATM financing, share count, convertible securities and dilution exposure."),
  pending("clinical-peer","Build contemporaneous treatment benefit and peer valuation",
   "Review clinical protocol, complete effect and safety evidence, competing standard of care, pricing and peer comparisons published before the original entry date."),
  absent("original-prediction","Original pre-entry RAAS forecast",
   "No timestamped RAAS prediction or frozen metric ratings existed when the selected historic position would have been opened. Retrospective simulation may be built separately, but it cannot become an authentic historical forecast."),
 ];
}
function auditTop(r:TopRetrospectiveRecord):HistoricalAuditCase{
 const items=[
  recorded("readout-guidance","Sponsor's pre-entry readout guidance",
   `${r.priorGuidanceDate}: ${r.priorGuidance}. Sponsor guidance is not assurance of an exact release date.`,r.priorGuidanceSourceUrl,1),
  recorded("readout-outcome","Observed publication occurred after selected TOP exit",
   `Selected exit ${r.exit.date}, public Phase 3 readout ${r.publicReadoutDate}; later trial results must not enter entry-date inputs.`,r.publicReadoutSourceUrl,1),
  ...sharedItems(r)
 ];
 return summarize(r,r.publicReadoutDate,items);
}
function auditBottom(r:RetrospectiveWindow):HistoricalAuditCase{
 const phase=r.verifiedBeforeEntry.find(e=>e.kind==="PHASE3_PUBLIC_READOUT");
 const target=r.verifiedBeforeEntry.find(e=>e.kind==="PDUFA_CONFIRMED");
 const cut=dayOffset(r.pdufaDate,-3);
 const items=[
  phase?recorded("phase3-public","Phase 3 information available before entry",
   `Source dated ${phase.date}; confirm exact product, trial and indication and access to the full clinical analysis.`,phase.sourceUrl,1):
   absent("phase3-public","Public Phase 3 result before entry","Source not identified; BOTTOM phase eligibility cannot be established.",1),
  target?recorded("pdufa-prior","PDUFA target announced before entry",
   `Source dated ${target.date}; target ${r.pdufaDate} for named application. Reconcile with original FDA application acceptance and later amendments.`,target.sourceUrl,1):
   absent("pdufa-prior","PDUFA target announced before entry","No dated exact-program FDA action target is available.",1),
  recorded("exit-cutoff","PDUFA-minus-three-calendar-day exit limit",
   `Selected exit ${r.exit.date}; three-day calendar cutoff ${cut}. This does not eliminate early FDA-action risk.`,r.exit.sourceUrl,1),
  recorded("observed-action","Actual FDA action used only as later outcome",
   `${r.realizedFDAAction.date}: ${r.realizedFDAAction.status}. ${r.realizedFDAAction.date<r.pdufaDate?"Action occurred before the published target; early-action risk is material.":"Action occurred on/after the target."} This was unknown at entry.`,
   r.realizedFDAAction.sourceUrl,1),
  ...sharedItems(r)
 ];
 return summarize(r,r.pdufaDate,items);
}
function summarize(r:TopRetrospectiveRecord|RetrospectiveWindow,eventDate:string,items:HistoricalAuditItem[]):HistoricalAuditCase{
 const remaining=items.filter(i=>i.status!=="RECORDED_NOT_INDEPENDENTLY_VERIFIED");
 return {id:r.id,stage:r.stage,ticker:r.ticker,drug:r.drug,indication:r.indication,
  nctCount:r.nctIds.length,entryDate:r.entry.date,exitDate:r.exit.date,
  grossPercent:round((r.exit.close/r.entry.close-1)*100),
  marketCapUsdMillions:r.marketCapAtEntry.usdMillions,eventDate,items,
  outstandingCount:remaining.length,criticalOutstandingCount:remaining.filter(i=>i.priority===1).length,
  eligibleForHistoricalTraining:false,eligibleForPredictiveValidation:false};
}
export function buildHistoricalResearchAudit(
 top:TopRetrospectiveFeed,bottom:RetrospectiveFeed
):HistoricalAuditCase[]{
 const cases=[...top.records.map(auditTop),...bottom.records.map(auditBottom)];
 const ids=new Set<string>();
 for(const c of cases){
  if(ids.has(c.id))throw Error("RAAS_HISTORY_DUPLICATE_EXAMPLE_ID");
  ids.add(c.id);
 }
 return cases;
}
export type HistoricalAuditSummary={
 topExamples:number;bottomExamples:number;totalExamples:number;
 openReviews:number;criticalOpenReviews:number;
 eligiblePredictions:0;qualifiedMetricGrades:0;
};
export function summarizeHistoricalResearch(cases:readonly HistoricalAuditCase[]):HistoricalAuditSummary{
 return {topExamples:cases.filter(x=>x.stage==="pre").length,
  bottomExamples:cases.filter(x=>x.stage==="post").length,
  totalExamples:cases.length,
  openReviews:cases.reduce((a,b)=>a+b.outstandingCount,0),
  criticalOpenReviews:cases.reduce((a,b)=>a+b.criticalOutstandingCount,0),
  eligiblePredictions:0,qualifiedMetricGrades:0};
}
