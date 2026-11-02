/** FDA-primary action cross-checks for retrospectively selected BOTTOM cases.
 * These are AFTER-EXIT historical outcomes, never entry-time evidence or
 * qualifying RAAS investment forecasts / scientific approval probabilities.
 * The FDA source confirms a drug/indication action, NOT every linked NCT.
 */
import type {RetrospectiveFeed} from "./raas-retrospective-intake";
export type FdaPrimaryOutcome={
 caseId:string;ticker:string;drug:string;indication:string;
 product:string;decision:"APPROVED";decisionDate:string;
 fdaUrl:string;sourceTitle:string;sourceType:"FDA_PRIMARY_PAGE";
 scope:"HISTORICAL_POST_EXIT_OUTCOME_ONLY";reviewedAt:string;
};
export type FdaPrimaryFeed={
 schemaVersion:1;scope:"RAAS_FDA_PRIMARY_HISTORICAL_OUTCOME_CROSSCHECKS";
 sourceAsOf:string;note:string;records:FdaPrimaryOutcome[];
};
const day=(s:unknown):s is string=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const official=(s:unknown):s is string=>typeof s==="string"&&
 /^https:\/\/www\.fda\.gov\/[a-z0-9/-]+$/i.test(s);
const textField=(s:unknown):s is string=>typeof s==="string"&&s.trim().length>0&&s.length<=300;
const exact=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();

/** Fail closed rather than attaching a later, different product's FDA action
 * to an earlier trade, confusing two NCTs, or counting duplicate programs.
 */
export function parseFdaPrimaryOutcomes(raw:unknown,post:RetrospectiveFeed):FdaPrimaryFeed{
 if(!raw||typeof raw!=="object"||Array.isArray(raw))throw Error("RAAS_FDA_SOURCE_LEDGER_INVALID");
 const feed=raw as FdaPrimaryFeed;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_FDA_PRIMARY_HISTORICAL_OUTCOME_CROSSCHECKS"||
    !day(feed.sourceAsOf)||feed.sourceAsOf>post.sourceAsOf||
    typeof feed.note!=="string"||!feed.note.trim()||feed.note.length>1500||
    !Array.isArray(feed.records)||feed.records.length>100)
   throw Error("RAAS_FDA_SOURCE_LEDGER_INVALID");
 const original=new Map(post.records.map(r=>[r.id,r]));
 const seen=new Set<string>();
 for(const r of feed.records){
  const matching=r&&original.get(r.caseId);
  if(!r||!matching||seen.has(r.caseId)||!textField(r.ticker)||
     !textField(r.drug)||!textField(r.indication)||!textField(r.product)||
     !textField(r.sourceTitle)||r.decision!=="APPROVED"||
     r.sourceType!=="FDA_PRIMARY_PAGE"||
     r.scope!=="HISTORICAL_POST_EXIT_OUTCOME_ONLY"||
     !day(r.decisionDate)||!day(r.reviewedAt)||r.reviewedAt>feed.sourceAsOf||
     r.reviewedAt<r.decisionDate||!official(r.fdaUrl)||
     !exact(r.ticker,matching.ticker)||!exact(r.drug,matching.drug)||
     !exact(r.indication,matching.indication)||
     r.decisionDate!==matching.realizedFDAAction.date||
     matching.realizedFDAAction.status!=="FDA_APPROVED"||
     r.decisionDate<=matching.exit.date)
    throw Error("RAAS_FDA_ACTION_CROSSCHECK_MISMATCH");
  seen.add(r.caseId);
 }
 return feed;
}
export function fdaPrimaryOutcomeForCase(feed:FdaPrimaryFeed,caseId:string):FdaPrimaryOutcome|null{
 return feed.records.find(r=>r.caseId===caseId)||null;
}
export function fdaPrimaryOutcomeSummary(feed:FdaPrimaryFeed,post:RetrospectiveFeed):{
 crosschecked:number;total:number;notCrosschecked:number
}{
 const total=post.records.length;
 const crosschecked=feed.records.length;
 return {crosschecked,total,notCrosschecked:total-crosschecked};
}
