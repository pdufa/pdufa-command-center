/** Research-only financial source reconciliation for historical RAAS cases.
 * Independent price/corporate-action and fully diluted-share audits remain
 * REQUIRED even after finance observations pass timestamp validation.
 */
import type {TopRetrospectiveFeed} from "./raas-top-retrospective-intake";
import type {RetrospectiveFeed} from "./raas-retrospective-intake";
export type FinanceFactType=
 "CASH_AND_MARKETABLE"|"CASH_UNRESTRICTED"|"OPERATING_EXPENSES_QTR"|
 "OPERATING_CASH_USED_9M"|"OPERATING_CASH_USED_6M"|"OPERATING_CASH_USED_QTR"|"LOAN_PROCEEDS"|
 "NET_LOSS_QTR"|"NET_LOSS_FY"|"FINANCING_COMMITMENT_NOT_CASH"|
 "EQUITY_OFFERING_NET_PROCEEDS"|"DEBT_PRINCIPAL"|"ATM_CAPACITY_NOT_CASH"|
 "ATM_PROCEEDS_9M"|"ATM_PROCEEDS_6M"|"TOTAL_LIABILITIES"|"EQUITY_FINANCING_NET_PROCEEDS"|
 "NEW_LOAN_NET_PROCEEDS"|"DEBT_REFINANCE_COSTS";
export type FinanceFact={type:FinanceFactType;valueUsdMillions:number;method:string;caveat:string};
export type FinanceRecord={
 id:string;caseId:string;ticker:string;stage:"pre"|"post";
 asOf:string;publishedAt:string;sourceUrl:string;facts:FinanceFact[];
};
export type FinanceFeed={
 schemaVersion:1;scope:"RAAS_HISTORICAL_FINANCE_RESEARCH";
 sourceAsOf:string;note:string;records:FinanceRecord[];
};
export type FinanceReadiness={
 caseId:string;stage:"pre"|"post";financeDataRecorded:boolean;
 financeFactCount:number;cashAmountUsdMillions:number|null;
 cashCategory:string|null;
 securityPriceReconciled:false;fullyDilutedValuationReconciled:false;
 cashRunwayCalculated:false;usableInApprovedRAAS:false;
 issues:string[];
};
const date=(s:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const url=(s:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(s);
const types=new Set<FinanceFactType>([
 "CASH_AND_MARKETABLE","CASH_UNRESTRICTED","OPERATING_EXPENSES_QTR",
 "OPERATING_CASH_USED_9M","OPERATING_CASH_USED_6M","OPERATING_CASH_USED_QTR","LOAN_PROCEEDS",
 "NET_LOSS_QTR","NET_LOSS_FY","FINANCING_COMMITMENT_NOT_CASH",
 "EQUITY_OFFERING_NET_PROCEEDS","DEBT_PRINCIPAL","ATM_CAPACITY_NOT_CASH",
 "ATM_PROCEEDS_9M","ATM_PROCEEDS_6M","TOTAL_LIABILITIES","EQUITY_FINANCING_NET_PROCEEDS",
 "NEW_LOAN_NET_PROCEEDS","DEBT_REFINANCE_COSTS"
]);
export function parseHistoricalFinance(
 input:unknown,top:TopRetrospectiveFeed,bottom:RetrospectiveFeed
):FinanceFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_FINANCE_FEED_INVALID");
 const f=input as FinanceFeed;
 if(f.schemaVersion!==1||f.scope!=="RAAS_HISTORICAL_FINANCE_RESEARCH"||
 !date(f.sourceAsOf)||!Array.isArray(f.records)||f.records.length>10000)
 throw Error("RAAS_FINANCE_FEED_INVALID");
 const lookup=new Map<string,{ticker:string;stage:"pre"|"post";entry:string}>([
  ...top.records.map(r=>[r.id,{ticker:r.ticker,stage:r.stage,entry:r.entry.date}] as const),
  ...bottom.records.map(r=>[r.id,{ticker:r.ticker,stage:r.stage,entry:r.entry.date}] as const)
 ]);
 const seen=new Set<string>();const ids=new Set<string>();
 for(const r of f.records){
  const c=lookup.get(r.caseId);
  if(!c||!r.id?.trim()||seen.has(r.caseId)||ids.has(r.id)||
    r.stage!==c.stage||r.ticker.trim().toLowerCase()!==c.ticker.trim().toLowerCase()||
    !date(r.asOf)||!date(r.publishedAt)||r.asOf>r.publishedAt||
    r.publishedAt>c.entry||r.publishedAt>f.sourceAsOf||!url(r.sourceUrl)||
    !Array.isArray(r.facts)||r.facts.length===0||r.facts.length>30)
    throw Error("RAAS_FINANCE_ROW_INVALID");
  seen.add(r.caseId);ids.add(r.id);
  const factTypes=new Set<string>();
  for(const fact of r.facts){
   if(!types.has(fact.type)||factTypes.has(fact.type)||
     !Number.isFinite(fact.valueUsdMillions)||fact.valueUsdMillions<0||
     !fact.method?.trim()||!fact.caveat?.trim())
     throw Error("RAAS_FINANCE_FACT_INVALID");
   factTypes.add(fact.type);
  }
  if(factTypes.has("CASH_AND_MARKETABLE")&&factTypes.has("CASH_UNRESTRICTED"))
   throw Error("RAAS_FINANCE_CASH_DOUBLE_COUNT");
 }
 return f;
}
export function financeForCase(f:FinanceFeed,id:string):FinanceRecord|null{
 return f.records.find(r=>r.caseId===id)??null;
}
export function financeReadiness(f:FinanceFeed,id:string,stage:"pre"|"post"):FinanceReadiness{
 const r=financeForCase(f,id);
 const cash=r?.facts.find(x=>x.type==="CASH_AND_MARKETABLE"||x.type==="CASH_UNRESTRICTED");
 const issues=["Independent stock closing-price / corporate-action verification outstanding",
  "Contemporaneous common vs ADS share-count and fully diluted valuation reconciliation outstanding",
  "Quarterly financing flow, debt and liabilities do not automatically establish net cash or cash runway",
  "No archived pre-entry RAAS grade or independently validated stock return predictor"];
 if(!r)issues.unshift("Dated pre-entry issuer/SEC financial source missing");
 return {caseId:id,stage,financeDataRecorded:!!r,financeFactCount:r?.facts.length??0,
  cashAmountUsdMillions:cash?.valueUsdMillions??null,cashCategory:cash?.type??null,
  securityPriceReconciled:false,fullyDilutedValuationReconciled:false,
  cashRunwayCalculated:false,usableInApprovedRAAS:false,issues};
}
export type CostReplay={
 observedGrossPercent:number;hypotheticalAfterCostsPercent:number;
 hypotheticalCostPercent:number;hypotheticalPriceShockPercent:number;
 hypotheticalShockExitPrice:number;hypotheticalShockReturnAfterCostsPercent:number;
 hasOriginalPrediction:false;qualifiedForPredictiveAccuracy:false;
};
/** Two separate RESEARCH calculations:
 * 1. vendor-close observation less a user-supplied hypothetical fee/spread
 * 2. independent hypothetical percentage shock from ENTRY, not a forecast
 * and not a probability-weighted valuation target.
 */
export function researchCostReplay(
 entryClose:number,exitClose:number,roundTripBps:number,shockPercent:number
):CostReplay|null{
 if(!Number.isFinite(entryClose)||entryClose<=0||
   !Number.isFinite(exitClose)||exitClose<=0||
   !Number.isFinite(roundTripBps)||roundTripBps<0||roundTripBps>2000||
   !Number.isFinite(shockPercent)||shockPercent< -99||shockPercent>500)
   return null;
 const percentCost=roundTripBps/100;
 const round=(v:number)=>Math.round(v*100)/100;
 const gross=(exitClose/entryClose-1)*100;
 const shockExit=entryClose*(1+shockPercent/100);
 return {observedGrossPercent:round(gross),
  hypotheticalAfterCostsPercent:round(gross-percentCost),
  hypotheticalCostPercent:round(percentCost),
  hypotheticalPriceShockPercent:round(shockPercent),
  hypotheticalShockExitPrice:round(shockExit),
  hypotheticalShockReturnAfterCostsPercent:round(shockPercent-percentCost),
  hasOriginalPrediction:false,qualifiedForPredictiveAccuracy:false};
}
