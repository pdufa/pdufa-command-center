import part01 from "../data/phase3RegistryDeepResults20261105Part01.json";
import part02 from "../data/phase3RegistryDeepResults20261105Part02.json";
import part03 from "../data/phase3RegistryDeepResults20261105Part03.json";
import part04 from "../data/phase3RegistryDeepResults20261105Part04.json";
import part05 from "../data/phase3RegistryDeepResults20261105Part05.json";
import part06 from "../data/phase3RegistryDeepResults20261105Part06.json";

/** Full public registry primary outcomes and event tables.
 * Documentary observations are not an analysis of success, safety, power or FDA approval.
 */
const parts=[part01,part02,part03,part04,part05,part06] as const;
const records=parts.flatMap(p=>p.records);
export const PHASE3_DEEP_REGISTRY_TRIAL_COUNT=records.length;
const byNct=new Map(records.map(r=>[r.nctId,r] as const));
export const PHASE3_DEEP_REGISTRY_UNIQUE_NCT_COUNT=byNct.size;
export const PHASE3_DEEP_REGISTRY_AS_OF=part01.snapshotAt;
export function phase3DeepRegistryRecord(nctId:string){return byNct.get(nctId);}
type Fact={status:"SOURCE_FACT_ONLY";description:string;sourceUrl:string};
export function phase3DeepRegistrySourceFact(nctId:string,question:number):Fact|null{
 const r=byNct.get(nctId);if(!r)return null;
 const url="https://clinicaltrials.gov/study/"+nctId;
 const fact=(description:string):Fact=>({status:"SOURCE_FACT_ONLY",description,sourceUrl:url});
 const primary=r.primaryResults||[];
 switch(question){
  case 1:
   if(r.hasPostedResults&&primary.length){
    const p=primary[0],ps=(p.analyses||[]).map(a=>a.pValueModifier+a.pValue).filter(Boolean);
    return fact("Posted registry primary outcome: "+p.title+"; "+p.timeFrame+
     (ps.length?"; reported primary test p-value(s): "+ps.slice(0,3).join(", "):"")+
     ". This is a reported measurement and NOT a determination of primary-endpoint PASS/FAIL.");
   }
   return null;
  case 3:
   return r.adverseEventsPosted?fact("Official posted adverse-event tables: serious events "+
    r.seriousAdverseEventsByArm+"; other events "+r.otherAdverseEventsByArm+
    ". No favorable safety grade is inferred."):null;
  case 11:
   return primary.some(p=>(p.measurements||[]).length>1)?
    fact("Posted primary outcome includes multiple reported arm measurements: "+
      primary[0].measurements.slice(0,5).map(m=>m.arm).join("; ")+
      ". Comparison exists, but comparator adequacy has NOT been judged."):null;
  case 22:
   return r.infectionEventTerms?fact("Registry adverse-event terms mentioning infection: "+
    r.infectionEventTerms.slice(0,400)+
    ". Presence of reported events does not establish relative tolerability."):null;
  case 23:
   return r.seriousAdverseEventTerms>0?fact("Posted serious adverse event comparison by arm: "+
    r.seriousAdverseEventsByArm+
    "; "+r.seriousAdverseEventTerms+" serious event terms listed. No safety verdict inferred."):null;
  case 24:
   return r.participantFlowDiscontinuations?fact("Registry lists trial discontinuations and withdrawals: "+
    r.participantFlowDiscontinuations.slice(0,620)+
    ". Completion/retention risk not independently graded."):null;
  default:return null;
 }
}
