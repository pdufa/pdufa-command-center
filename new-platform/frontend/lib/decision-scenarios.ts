/** Research-only scenario comparison. No trade authorization or live market inference. */
export type DecisionState="NOT_READY"|"RESEARCH_ONLY";
export type ScenarioInput={
  asOf:string;currentPrice:number;approvalProbability:number;
  approvalPrice:number;rejectionPrice:number;delayProbability:number;delayPrice:number;
  roundTripCostPct:number;sourceVerified:boolean;calibrated:boolean;
};
export type ScenarioResult={status:DecisionState;reasons:string[];expectedPrice:number|null;expectedReturnPct:number|null;approvalReturnPct:number|null;rejectionReturnPct:number|null};
const finite=(v:number)=>Number.isFinite(v);
/** Deliberately fail closed: illustrative math is never an actionable BUY signal. */
export function evaluateDecisionScenario(x:ScenarioInput, evaluatedAt=new Date()):ScenarioResult{
 const reasons:string[]=[];
 if(!x.sourceVerified)reasons.push("Critical source evidence is unverified");
 if(!x.calibrated)reasons.push("Approval probability is not historically calibrated");
 const asOfMs=Date.parse(x.asOf);
 const evaluatedAtMs=evaluatedAt.getTime();
 if(!Number.isFinite(asOfMs)||!Number.isFinite(evaluatedAtMs))reasons.push("Invalid as-of or evaluation timestamp");
 else if(asOfMs>evaluatedAtMs+5*60*1000||evaluatedAtMs-asOfMs>7*86400000)reasons.push("Scenario evidence is stale or future-dated");
 if(![x.currentPrice,x.approvalPrice,x.rejectionPrice,x.delayPrice].every(v=>finite(v)&&v>0))reasons.push("Invalid or missing positive prices");
 if(!finite(x.approvalProbability)||!finite(x.delayProbability)||x.approvalProbability<0||x.delayProbability<0||x.approvalProbability+x.delayProbability>1)reasons.push("Invalid scenario probabilities");
 if(!finite(x.roundTripCostPct)||x.roundTripCostPct<0||x.roundTripCostPct>=100)reasons.push("Invalid transaction cost");
 if(reasons.length)return {status:"NOT_READY",reasons,expectedPrice:null,expectedReturnPct:null,approvalReturnPct:null,rejectionReturnPct:null};
 const reject=1-x.approvalProbability-x.delayProbability;
 const expectedPrice=x.approvalProbability*x.approvalPrice+x.delayProbability*x.delayPrice+reject*x.rejectionPrice;
 const ret=(price:number)=>(price/x.currentPrice-1)*100-x.roundTripCostPct;
 return {status:"RESEARCH_ONLY",reasons:["Scenario assumptions require independent validation; not an order or recommendation"],expectedPrice,expectedReturnPct:ret(expectedPrice),approvalReturnPct:ret(x.approvalPrice),rejectionReturnPct:ret(x.rejectionPrice)};
}
