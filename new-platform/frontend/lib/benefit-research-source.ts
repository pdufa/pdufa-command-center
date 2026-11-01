/** Build the TOOLS benefits feed from the same reconciled, exact-NCT Pipeline
 * research rows used by the canonical PIPELINE views. The feed does not
 * produce clinical conclusions, peer rankings, or unsourced quantities.
 */
import {BENEFIT_GROUPS,parseBenefitFeed,type BenefitFeed,type BenefitRecord,type BenefitFact} from "./benefit-assessments";
import {researchFieldResult,type PipelineResearchRow} from "./pipeline-research-view";

const permitted=new Set(BENEFIT_GROUPS.flatMap(group=>group.fields.map(field=>field.id)));
const confidence=(v:string|null):v is BenefitFact["confidence"]=>v==="HIGH"||v==="MODERATE"||v==="LOW";
const day=(v:string|null,today:string):v is string=>
  typeof v==="string" && /^\d{4}-\d{2}-\d{2}$/.test(v) && v<=today &&
  Number.isFinite(Date.parse(v+"T00:00:00Z")) &&
  new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
const sourceUrl=(v:string|null):v is string=>
  typeof v==="string"&&v.length<=1500&&/^https:\/\/[^\s/]+\/\S*/.test(v);
const identity=(v:{nctId:string;ticker:string;drug:string|null;indication:string|null})=>
  [v.nctId,v.ticker,v.drug||"",v.indication||""].map(s=>s.trim().toLowerCase()).join("|");
const validIdentity=(row:PipelineResearchRow)=> /^NCT\d{8}$/.test(row.nctId)
  &&!!row.ticker?.trim()&&!!row.drug?.trim()&&!!row.indication?.trim()
  &&row.poolStatus==="EXACT_MATCH"&&row.postPhase3Evidence==="REGISTRY_COMPLETED";

export function benefitsFromPipeline(
  rows:readonly PipelineResearchRow[],today:string,saved:BenefitFeed
):BenefitFeed{
  const reviewed=parseBenefitFeed(saved);
  if(!day(today,today))throw Error("BENEFIT_RESEARCH_INVALID_DATE");
  const savedById=new Map(reviewed.records.map(record=>[identity(record),record]));
  const seen=new Set<string>();
  const output:BenefitRecord[]=[];
  for(const row of rows){
    if(!validIdentity(row))continue;
    const key=identity(row);
    if(seen.has(key))throw Error("BENEFIT_PIPELINE_DUPLICATE_IDENTITY");
    seen.add(key);
    const reviewedRecord=savedById.get(key);
    const facts:Record<string,BenefitFact>={};
    for(const id of permitted){
      const result=researchFieldResult(row,id as Parameters<typeof researchFieldResult>[1],today);
      // Source-recorded names, absence, synthetic estimates and uncertain
      // comparators do NOT qualify as independently verified evidence.
      if((result.state!=="VERIFIED"&&result.state!=="MODELED")
        ||!sourceUrl(result.sourceUrl)||!day(result.sourceDate,today)
        ||!result.method?.trim()||result.method.length>2000
        ||!confidence(result.confidence)||!result.value?.trim()
        ||result.value.length>500)continue;
      facts[id]={
        value:result.value,status:result.state,
        sourceUrl:result.sourceUrl,sourceDate:result.sourceDate,
        method:result.method,confidence:result.confidence
      };
    }
    // Reviewed findings are never silently replaced by conflicting automated
    // extraction; record-level source review controls the same field.
    Object.assign(facts,reviewedRecord?.facts||{});
    const record:BenefitRecord={
      nctId:row.nctId,ticker:row.ticker,drug:row.drug!,
      indication:row.indication!,facts,
      advantages:reviewedRecord?.advantages||[],
      overallAdvantages:reviewedRecord?.overallAdvantages||[]
    };
    // Only emit studies with at least one independently sourced assessment
    // field or reviewed advantage. A blank row is still "Not assessed" in UI.
    if(Object.keys(facts).length||record.advantages.length||record.overallAdvantages?.length)
      output.push(record);
  }
  return parseBenefitFeed({schemaVersion:1,sourceAsOf:today,records:output});
}
