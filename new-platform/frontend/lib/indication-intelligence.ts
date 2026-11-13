/** Evidence-safe joins for the unified POOL → INDICATIONS → FOCUS viewer.
 * Source records are never overwritten, merged across NCTs or scored.
 */
export type IndicationTrial={
  nct:string;ticker:string;company:string;drug:string;indication:string;
  stage:string;focus:boolean;sourceUrl:string;
};
export type DiseaseNodeLite={
  id:string;name:string;parentId:string|null;sourceId?:string;sourceName?:string;aliases?:string[];
};
export type DiseaseLookup={
  byId:Map<string,DiseaseNodeLite>;
  unique:DiseaseNodeLite[];
};
export type LinkedTrial=IndicationTrial&{
  indicationText:string;classificationId:string|null;matchStatus:"EXACT"|"AMBIGUOUS"|"UNMAPPED";
};
export const PHASE_COLUMNS=[
  ["P1","Phase 1"],["P1/2","Phase 1/2"],["P2","Phase 2"],["P2/3","Phase 2/3"],
  ["P3","Phase 3"],["RESULTS","Phase 3 results"],["FDA","FDA / PDUFA"],["OTHER","Other / unknown"]
] as const;
export type PhaseColumn=typeof PHASE_COLUMNS[number][0];
const clean=(s:string)=>s.trim().toLowerCase().replace(/[^a-z0-9]+/g," ").trim();
const trialIdentity=(t:IndicationTrial)=>[t.nct.toUpperCase(),t.ticker.toUpperCase()].join("|");
/** Pipe and semicolon delimiters are explicit separate indications; commas stay inside medical names. */
export function indications(raw:string):string[]{
 const found=[...new Set(raw.split(/\s*[|;]\s*/).map(x=>x.trim()).filter(Boolean))];
 return found.length?found:["Indication not recorded"];
}
export function phaseColumn(stage:string):PhaseColumn{
 const s=stage.toLowerCase().replace(/\s+/g," ");
 if(/post.decision|pdufa|fda|nda|bla|submission|acceptance/.test(s))return "FDA";
 if(/phase 3 results|phase3 results/.test(s))return "RESULTS";
 if(/phase 2\s*\/\s*3|phase2\s*\/\s*3/.test(s))return "P2/3";
 if(/phase 1\s*\/\s*2|phase1\s*\/\s*2/.test(s))return "P1/2";
 if(/phase 3|phase3/.test(s))return "P3";
 if(/phase 2|phase2/.test(s))return "P2";
 if(/phase 1|phase1/.test(s))return "P1";
 return "OTHER";
}
/** Only a unique exact MeSH name/alias is classified. Broader phrases remain review items. */
export function linkToDiseases(rows:readonly IndicationTrial[],index:DiseaseLookup):LinkedTrial[]{
 const names=new Map<string,Set<string>>();
 for(const node of index.unique){
  for(const n of [node.name,node.sourceName,...(node.aliases||[])]){
   if(!n)continue;
   const k=clean(n),set=names.get(k)||new Set<string>();
   set.add(node.sourceId||node.id);names.set(k,set);
  }
 }
 const primary=new Map(index.unique.map(x=>[x.sourceId||x.id,x.id]));
 const result:LinkedTrial[]=[];
 const seen=new Set<string>();
 for(const row of rows){
  if(!/^NCT\d{8}$/.test(row.nct)||!row.ticker.trim())continue;
  for(const indicationText of indications(row.indication||"")){
   const key=trialIdentity(row)+"|"+clean(row.drug||"")+"|"+clean(indicationText);
   if(seen.has(key))continue;seen.add(key);
   const matches=names.get(clean(indicationText));
   const id=matches?.size===1?primary.get([...matches][0])||null:null;
   result.push({...row,indicationText,classificationId:id,
     matchStatus:id?"EXACT":matches&&matches.size>1?"AMBIGUOUS":"UNMAPPED"});
  }
 }
 return result;
}
export function withinBranch(id:string|null,nodeId:string|null,index:DiseaseLookup):boolean{
 if(id===null||nodeId===null)return nodeId===null;
 const visited=new Set<string>();
 let node=index.byId.get(id);
 while(node&&!visited.has(node.id)){
  if(node.id===nodeId)return true;
  visited.add(node.id);
  node=node.parentId?index.byId.get(node.parentId):undefined;
 }
 return false;
}
export function selectedRows(rows:readonly LinkedTrial[],index:DiseaseLookup,
 nodeId:string|null,query:string,focusOnly:boolean,phase:PhaseColumn|null):LinkedTrial[]{
 const q=clean(query);
 return rows.filter(row=>{
  if(focusOnly&&!row.focus)return false;
  if(phase&&phaseColumn(row.stage)!==phase)return false;
  if(nodeId&&!withinBranch(row.classificationId,nodeId,index))return false;
  return !q||[row.nct,row.ticker,row.company,row.drug,row.indicationText,row.stage]
    .some(text=>clean(text).includes(q));
 });
}
/** Deduplicate exact trial IDs inside a branch and phase, while retaining indication-specific rows. */
export function phaseCounts(rows:readonly LinkedTrial[]):Record<PhaseColumn,number>{
 const groups=Object.fromEntries(PHASE_COLUMNS.map(([key])=>[key,new Set<string>()])) as Record<PhaseColumn,Set<string>>;
 for(const row of rows)groups[phaseColumn(row.stage)].add(trialIdentity(row));
 return Object.fromEntries(PHASE_COLUMNS.map(([key])=>[key,groups[key].size])) as Record<PhaseColumn,number>;
}
export function uniqueTrials(rows:readonly LinkedTrial[]):number{
 return new Set(rows.map(trialIdentity)).size;
}
