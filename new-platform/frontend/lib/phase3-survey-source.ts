/** Independent readout-only SURVEY feed: never combine issuer topline claims with the
 * verified Pipeline population, and never treat published results as FDA approval.
 * Every field must originate in the dated, exact-NCT issuer readout manifest.
 */
import {parseBenefitFeed,type BenefitFeed} from "./benefit-assessments";

type ManifestEntry={
 nctId:string;ticker:string;drug:string;indication:string;
 kind:string;evidenceDate:string;evidenceUrl:string;
};
type Manifest={sourceAsOf:string;entries:ManifestEntry[]};
const canonical=(s:string)=>s.trim().toLowerCase();

export function verifiedReadoutSurveyFeed(raw:unknown,manifest:Manifest):BenefitFeed{
 const feed=parseBenefitFeed(raw);
 if(feed.sourceAsOf!==manifest.sourceAsOf||!Array.isArray(manifest.entries))
  throw Error("SURVEY_READOUT_MANIFEST_DATE_MISMATCH");
 const evidence=new Map<string,ManifestEntry>();
 for(const entry of manifest.entries){
  if(!/^NCT\d{8}$/.test(entry.nctId)||evidence.has(entry.nctId))
   throw Error("SURVEY_READOUT_MANIFEST_INVALID");
  evidence.set(entry.nctId,entry);
 }
 const seen=new Set<string>();
 for(const record of feed.records){
  const item=evidence.get(record.nctId);
  // Registry-posted, unverified, stale or ticker-only programs cannot qualify.
  if(!item||item.kind!=="POST_PUBLIC_READOUT"||
    item.ticker!==record.ticker||
    canonical(item.drug)!==canonical(record.drug)||
    canonical(item.indication)!==canonical(record.indication)||
    seen.has(record.nctId))
   throw Error("SURVEY_READOUT_EXACT_IDENTITY_REQUIRED");
  seen.add(record.nctId);
  if(Object.keys(record.facts).length===0||record.advantages.length||
    (record.overallAdvantages||[]).length)
   throw Error("SURVEY_READOUT_SOURCE_EVIDENCE_REQUIRED");
  for(const fact of Object.values(record.facts)){
   if(fact.status!=="VERIFIED"||fact.sourceUrl!==item.evidenceUrl||
      fact.sourceDate!==item.evidenceDate||
      !fact.method.startsWith("Sponsor-reported")||
      !fact.method.includes("not independent")&&!fact.method.includes("Not an independent"))
    throw Error("SURVEY_READOUT_SPONSOR_PROVENANCE_REQUIRED");
  }
 }
 return feed;
}
