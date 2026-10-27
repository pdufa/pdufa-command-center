import {evaluateDecisionScenario,type ScenarioInput,type ScenarioResult} from "./decision-scenarios";
/** An evidence record is not a verified fact merely because it was saved. */
export type EvidenceRecord={sourceUrl:string;observedAt:string;status:"VERIFIED"|"UNVERIFIED"|"CONFLICT"|"MISSING";value:number};
export type DecisionEvidence={programId:string;ticker:string;asOf:string;price:EvidenceRecord;approvalProbability:EvidenceRecord;approvalPrice:EvidenceRecord;rejectionPrice:EvidenceRecord;delayProbability:EvidenceRecord;delayPrice:EvidenceRecord;costPct:EvidenceRecord;calibration:{status:"VALIDATED"|"UNVALIDATED";sampleSize:number;asOf:string}};
export type EvidenceDecision={status:"NOT_READY"|"RESEARCH_ONLY";issues:string[];scenario:ScenarioResult|null};
const isDate=(x:string)=>Number.isFinite(Date.parse(x))&&/\d{4}-\d\d-\d\dT/.test(x);
const isUrl=(x:string)=>{try{const u=new URL(x);return u.protocol==="https:"&&!!u.hostname;}catch{return false;}};
/** Strictly checks provenance, timestamps, identity and calibration before allowing illustrative math. */
export function evaluateEvidenceDecision(e:DecisionEvidence,now=new Date()):EvidenceDecision{
 const issues:string[]=[];
 if(!/^PDUFA-\d{6,}$/.test(e.programId)||!/^[A-Z][A-Z0-9.-]{0,9}$/.test(e.ticker))issues.push("Invalid program or ticker identity");
 const at=Date.parse(e.asOf),current=now.getTime();
 if(!isDate(e.asOf)||!Number.isFinite(current)||at>current+300000||current-at>86400000)issues.push("Decision snapshot is not current");
 const fields=["price","approvalProbability","approvalPrice","rejectionPrice","delayProbability","delayPrice","costPct"] as const;
 for(const key of fields){
  const item=e[key],time=Date.parse(item.observedAt);
  if(item.status!=="VERIFIED")issues.push(key+": evidence is "+item.status);
  if(!isUrl(item.sourceUrl))issues.push(key+": HTTPS source required");
  if(!isDate(item.observedAt)||time>at+300000||at-time>86400000)issues.push(key+": evidence timestamp invalid or stale");
 }
 if(e.calibration.status!=="VALIDATED"||!Number.isSafeInteger(e.calibration.sampleSize)||e.calibration.sampleSize<30||!isDate(e.calibration.asOf)||Date.parse(e.calibration.asOf)>at)issues.push("Historical calibration evidence insufficient");
 if(issues.length)return {status:"NOT_READY",issues,scenario:null};
 const input:ScenarioInput={asOf:e.asOf,currentPrice:e.price.value,approvalProbability:e.approvalProbability.value,approvalPrice:e.approvalPrice.value,rejectionPrice:e.rejectionPrice.value,delayProbability:e.delayProbability.value,delayPrice:e.delayPrice.value,roundTripCostPct:e.costPct.value,sourceVerified:true,calibrated:true};
 const scenario=evaluateDecisionScenario(input,now);
 return {status:scenario.status,issues:scenario.status==="NOT_READY"?scenario.reasons:[],scenario:scenario.status==="NOT_READY"?null:scenario};
}
