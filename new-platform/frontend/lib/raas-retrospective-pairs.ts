/** Paired stage research comparisons, never merged into a training observation.
 * Same issuer and overlapping NCT plus exact normalized drug label required.
 * Every window was selected retrospectively; no pre-entry RAAS score exists.
 */
import type {TopRetrospectiveResult,TopRetrospectiveFeed} from "./raas-top-retrospective-intake";
import type {RetrospectiveResult,RetrospectiveFeed} from "./raas-retrospective-intake";

export type PhasePair={
 ticker:string;drug:string;sharedNctIds:string[];
 pre:{id:string;entryDate:string;exitDate:string;grossPercent:number};
 post:{id:string;entryDate:string;exitDate:string;grossPercent:number};
 status:"RETROSPECTIVE_RESEARCH_ONLY";combinedReturn:null;
};
const canonicalDrug=(name:string):string=>
 name.toLowerCase().replace(/\s*\([^)]*\)\s*$/g,"").trim().replace(/\s+/g," ");
export function pairRetrospectivePrograms(
 topFeed:TopRetrospectiveFeed,topWindows:readonly TopRetrospectiveResult[],
 postFeed:RetrospectiveFeed,postWindows:readonly RetrospectiveResult[]
):PhasePair[]{
 const pairs:PhasePair[]=[];
 const seen=new Set<string>();
 for(const pre of topWindows){
  const t=topFeed.records.find(r=>r.id===pre.id);
  if(!t)continue;
  for(const post of postWindows){
   const p=postFeed.records.find(r=>r.id===post.id);
   if(!p||t.ticker.toUpperCase()!==p.ticker.toUpperCase()||
      canonicalDrug(t.drug)!==canonicalDrug(p.drug)||pre.exitDate>=post.entryDate)continue;
   const shared=t.nctIds.filter(n=>p.nctIds.includes(n));
   if(shared.length===0)continue;
   const key=pre.id+"|"+post.id;
   if(seen.has(key))continue;
   seen.add(key);
   pairs.push({ticker:t.ticker,drug:canonicalDrug(t.drug),
    sharedNctIds:shared,
    pre:{id:pre.id,entryDate:pre.entryDate,exitDate:pre.exitDate,
     grossPercent:pre.observedGrossChangePercent},
    post:{id:post.id,entryDate:post.entryDate,exitDate:post.exitDate,
     grossPercent:post.observedGrossChangePercent},
    combinedReturn:null,status:"RETROSPECTIVE_RESEARCH_ONLY"});
  }
 }
 return pairs.sort((a,b)=>a.ticker.localeCompare(b.ticker));
}
