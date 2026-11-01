/** Shared, ordered benefit-assessment catalog. Each numbered heading owns its subcolumns.
 * Research fields and advantages are separate source-backed records; missing is NOT zero.
 */
import {RANKED_BENEFIT_ASSESSMENTS} from "./pipeline-benefit-assessments";
import {ALL_RESEARCH_FIELD_DEFINITIONS} from "./pipeline-research-view";
export type BenefitField = {id:string;label:string};
export type BenefitGroup = {number:number;name:string;fields:readonly BenefitField[]};
/** Reuse the canonical 20 original assessment groups and the mapped 38+ research fields.
 * Never fork the assessment taxonomy between PIPELINE and TOOLS.
 */
export const BENEFIT_GROUPS:readonly BenefitGroup[]=RANKED_BENEFIT_ASSESSMENTS.map(spec=>({
  number:spec.rank,
  name:spec.title,
  fields:spec.fields.map(id=>({id,label:ALL_RESEARCH_FIELD_DEFINITIONS.find(f=>f.id===id)?.label||id}))
}));
export type BenefitFact={
  value:string|number;
  status:"VERIFIED"|"MODELED";
  sourceUrl:string;
  sourceDate:string;
  method:string;
  confidence:"HIGH"|"MODERATE"|"LOW";
};
export type BenefitAdvantage={
  id:string;assessment:number;rank:number;title:string;comparator:string;
  comparison:string;sourceUrl:string;sourceDate:string;method:string;
  confidence:"HIGH"|"MODERATE"|"LOW";status:"VERIFIED"|"MODELED";
};
export type BenefitRecord={
  nctId:string;ticker:string;drug:string;indication:string;
  facts:Record<string,BenefitFact>;
  advantages:BenefitAdvantage[];
  overallAdvantages?:BenefitAdvantage[];
};
export type BenefitFeed={schemaVersion:1;sourceAsOf:string|null;records:BenefitRecord[]};
const validDate=(v:unknown):v is string=>typeof v==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v)
  &&new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v
  &&Date.parse(v+"T00:00:00Z")<=Date.now();
const validUrl=(v:unknown):v is string=>typeof v==="string"&&v.length<=1500&&/^https:\/\/[^\s/]+\/\S*/.test(v);
const validText=(v:unknown,max=1000):v is string=>typeof v==="string"&&v.trim().length>0&&v.length<=max;
const confidence=(v:unknown)=>v==="HIGH"||v==="MODERATE"||v==="LOW";
const status=(v:unknown)=>v==="VERIFIED"||v==="MODELED";
function validFact(v:unknown):v is BenefitFact{
  if(!v||typeof v!=="object")return false;
  const f=v as Partial<BenefitFact>;
  return (typeof f.value==="string"?validText(f.value,500):typeof f.value==="number"&&Number.isFinite(f.value))
    &&status(f.status)&&validUrl(f.sourceUrl)&&validDate(f.sourceDate)
    &&validText(f.method,2000)&&confidence(f.confidence);
}
function validAdvantage(v:unknown):v is BenefitAdvantage{
  if(!v||typeof v!=="object")return false;
  const a=v as Partial<BenefitAdvantage>;
  return validText(a.id,120)&&Number.isInteger(a.assessment)&&a.assessment!>=1&&a.assessment!<=20
    &&Number.isInteger(a.rank)&&a.rank!>=1&&a.rank!<=100
    &&validText(a.title,250)&&validText(a.comparator,250)
    &&validText(a.comparison,1000)&&validText(a.method,2000)
    &&validUrl(a.sourceUrl)&&validDate(a.sourceDate)&&confidence(a.confidence)&&status(a.status);
}
/** Strictly validate at the authenticated read boundary; no partial trusted feed. */
export function parseBenefitFeed(raw:unknown):BenefitFeed{
  if(!raw||typeof raw!=="object")throw Error("BENEFIT_FEED_INVALID");
  const feed=raw as Partial<BenefitFeed>;
  if(feed.schemaVersion!==1||!Array.isArray(feed.records)||feed.records.length>20000
    ||(feed.sourceAsOf!==null&&!validDate(feed.sourceAsOf)))throw Error("BENEFIT_FEED_INVALID");
  const ids=new Set<string>();
  for(const record of feed.records){
    if(!record||!/^NCT\d{8}$/.test(record.nctId)||!validText(record.ticker,24)
      ||!validText(record.drug,250)||!validText(record.indication,250)
      ||!record.facts||typeof record.facts!=="object"||Array.isArray(record.facts)
      ||!Array.isArray(record.advantages)||record.advantages.length>200
      ||(record.overallAdvantages!==undefined&&(!Array.isArray(record.overallAdvantages)||record.overallAdvantages.length>30)))throw Error("BENEFIT_RECORD_INVALID");
    const identity=[record.nctId,record.ticker,record.drug,record.indication].join("|").toLowerCase();
    if(ids.has(identity))throw Error("BENEFIT_RECORD_DUPLICATED");
    ids.add(identity);
    const allowed=new Set(BENEFIT_GROUPS.flatMap(g=>g.fields.map(f=>f.id)));
    if(Object.entries(record.facts).some(([key,value])=>!allowed.has(key)||!validFact(value)))
      throw Error("BENEFIT_FACT_INVALID");
    const ranks=new Set<string>(),unique=new Set<string>();
    for(const item of record.advantages){
      if(!validAdvantage(item))throw Error("BENEFIT_ADVANTAGE_INVALID");
      const rankKey=item.assessment+":"+item.rank;
      if(ranks.has(rankKey)||unique.has(item.id))throw Error("BENEFIT_RANK_DUPLICATED");
      ranks.add(rankKey);unique.add(item.id);
    }
    const overallRanks=new Set<number>();
    for(const item of record.overallAdvantages||[]){
      if(!validAdvantage(item)||overallRanks.has(item.rank)||!record.advantages.some(a=>a.id===item.id))
        throw Error("BENEFIT_OVERALL_RANK_INVALID");
      overallRanks.add(item.rank);
    }
  }
  return feed as BenefitFeed;
}
/** No ticker-only matching. Drug and indication must be present and identical. */
export function benefitForTrial(
  feed:BenefitFeed|null,
  trial:{nctId:string;ticker:string;drug:string;indication:string}
):BenefitRecord|null{
  if(!feed||!trial.drug?.trim()||!trial.indication?.trim())return null;
  const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
  return feed.records.find(r=>r.nctId===trial.nctId&&same(r.ticker,trial.ticker)
    &&same(r.drug,trial.drug)&&same(r.indication,trial.indication))||null;
}
export function rankAdvantages(record:BenefitRecord|null,assessment?:number):BenefitAdvantage[]{
  return (assessment===undefined?(record?.overallAdvantages||[]):record?.advantages.filter(x=>x.assessment===assessment)||[])
    .sort((a,b)=>a.rank-b.rank||a.id.localeCompare(b.id));
}
