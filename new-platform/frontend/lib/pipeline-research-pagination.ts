import type { PipelineResearchRow } from "./pipeline-research-view";
export type ResearchPage = {view:string;offset:number;limit:number;total:number;rows:PipelineResearchRow[];nextOffset:number|null;datasetVersion:string;caveat:string;overview:Record<string,unknown>};
/** A complete, version-consistent retrieval; never silently keep the first 500. */
export async function loadCompleteResearch(fetchPage:(offset:number,limit:number)=>Promise<unknown>,pageSize=200):Promise<ResearchPage>{
 const rows:PipelineResearchRow[]=[];const seen=new Set<string>();
 let offset=0,total:number|null=null,version:string|null=null,first:ResearchPage|null=null;
 for(;;){
  const raw=await fetchPage(offset,pageSize);
  if(!raw||typeof raw!=="object")throw Error("Invalid research page");
  const p=raw as ResearchPage;
  if(p.view!=="pipeline"||p.offset!==offset||p.limit!==pageSize||!Number.isSafeInteger(p.total)||p.total<0
    ||!Array.isArray(p.rows)||p.rows.length>pageSize||typeof p.datasetVersion!=="string"||!p.datasetVersion
    ||typeof p.caveat!=="string"||!p.overview)throw Error("Invalid research page contract");
  if(total!==null&&(p.total!==total||p.datasetVersion!==version))throw Error("Research dataset changed during pagination; retry");
  if(!first){first=p;total=p.total;version=p.datasetVersion;}
  for(const row of p.rows){
   if(!row||!/^NCT\d{8}$/.test(row.nctId)||typeof row.ticker!=="string"||typeof row.sourceUrl!=="string"
     ||row.poolStatus!=="EXACT_MATCH"||row.postPhase3Evidence!=="REGISTRY_COMPLETED"||!Array.isArray(row.reasons)||seen.has(row.nctId))throw Error("Duplicate or mismatched research trial");
   seen.add(row.nctId);rows.push(row);
  }
  const next=offset+p.rows.length;
  if(next>p.total)throw Error("Research total mismatch");
  if(p.nextOffset===null){if(next!==p.total)throw Error("Incomplete research pagination");break;}
  if(p.rows.length===0||p.nextOffset!==next||next>=p.total)throw Error("Research pagination did not advance");
  offset=next;
 }
 return {...first!,offset:0,total:rows.length,limit:pageSize,nextOffset:null,rows};
}
