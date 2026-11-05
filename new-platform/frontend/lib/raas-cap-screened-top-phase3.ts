/** Partition the CAP-screened, source-recorded Phase 3 subset into the TOP
 * intake without making an unverified issuer-readout claim.
 * All exact issuer-classified POST trials are excluded, even if their
 * development-stage string has not been updated by the registry.
 * Source-classified TOP-as-of-check rows remain in the established TOP sheet.
 */
import type {ReadoutClassification,ReadoutRow} from "./phase3-public-readout";
import type {RaasScreenedTrialRoster} from "./raas-full-universe-roster";
export type CapScreenedTopPhase3={
 sourceAsOf:string;
 candidates:ReadoutRow[];
 alreadyTop:ReadoutRow[];
 excludedKnownPost:number;
 totalCurrentTopPhase3:number;
};
export function splitCapScreenedTopPhase3(
 roster:RaasScreenedTrialRoster,
 classification:ReadoutClassification
):CapScreenedTopPhase3{
 if(roster?.source!=="MARKET_CAP_RESTRICTED_PHASE3_POOL"||
  !roster.details||roster.details.size!==roster.rows.length||
  !roster.sourceAsOf||!classification||classification.total!==741)
  throw Error("TOP_CAP_SCREENED_PHASE3_INPUT_INVALID");
 const knownPost=new Set(classification.post.map(x=>x.nctId));
 const pre=new Map(classification.pre.map(x=>[x.nctId,x.ticker]));
 const candidates:ReadoutRow[]=[],alreadyTop:ReadoutRow[]=[];
 let excludedKnownPost=0;
 const seen=new Set<string>();
 for(const row of roster.rows){
  const details=roster.details.get(row.nctId);
  if(!details||details.recordedStage!=="Phase 3"||seen.has(row.nctId))
   throw Error("TOP_CAP_SCREENED_PHASE3_STAGE_OR_ID_INVALID");
  seen.add(row.nctId);
  if(knownPost.has(row.nctId)){excludedKnownPost++;continue;}
  if(pre.get(row.nctId)===row.ticker){
   if(row.evidence?.kind!=="PRE_AS_OF_CHECK")
    throw Error("TOP_CAP_SCREENED_PHASE3_ISSUER_PRE_MISMATCH");
   alreadyTop.push(row);continue;
  }
  if(row.evidence!==null)throw Error("TOP_CAP_SCREENED_PHASE3_UNVERIFIED_HAS_STAGE");
  candidates.push(row);
 }
 const alpha=(a:ReadoutRow,b:ReadoutRow)=>
  a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId);
 candidates.sort(alpha);alreadyTop.sort(alpha);
 return {sourceAsOf:roster.sourceAsOf,candidates,alreadyTop,excludedKnownPost,
  totalCurrentTopPhase3:candidates.length+alreadyTop.length};
}
export function capScreenedTopPhase3Csv(
 roster:RaasScreenedTrialRoster,split:CapScreenedTopPhase3
):string{
 const quote=(value:string)=>'"'+(/^[=+@-]/.test(value)?"'"+value:value)
  .replace(/"/g,'""')+'"';
 const headers=["NCT","Ticker","Company","Drug / therapy","Indication",
  "Recorded development stage","Readout status","Cap-screen source as of",
  "Market-cap range","Research score status","Registry source"];
 const present=[...split.alreadyTop,...split.candidates]
  .sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId));
 const verified=new Set(split.alreadyTop.map(x=>x.nctId));
 const out=[headers.map(quote).join(",")];
 for(const row of present){
  const d=roster.details.get(row.nctId);
  if(!d||d.recordedStage!=="Phase 3")throw Error("TOP_CAP_EXPORT_SOURCE_MISMATCH");
  const vals=[row.nctId,row.ticker,row.company,d.drug,d.indication,
   d.recordedStage,verified.has(row.nctId)?"TOP_AS_OF_SAVED_ISSUER_CHECK":"READOUT_UNVERIFIED",
   split.sourceAsOf,"$300M–$10B (dated verified issuer screen)",
   verified.has(row.nctId)?"Existing stage-specific source reviews only":"N/A — five research fields available, not a verified TOP score",
   row.sourceUrl];
  out.push(vals.map(quote).join(","));
 }
 return "\uFEFF"+out.join("\r\n")+"\r\n";
}
