/**
 * Presentation-only POOL column ordering. Source rows and the three fixed
 * identity columns (Ticker, Company, NCT ID) are never part of this mapping.
 */
export type PoolColumnOrder<K extends string>={
 segmentOrder:string[];
 columnOrder:Record<string,K[]>;
};
export function normalizePoolColumnOrder<K extends string>(
 raw:unknown,defaults:Readonly<Record<string,readonly K[]>>,
 segmentIds:readonly string[]
):PoolColumnOrder<K>{
 const input=raw&&typeof raw==="object"?raw as Partial<PoolColumnOrder<K>>:{};
 const ids=new Set(segmentIds);
 const requested=Array.isArray(input.segmentOrder)?input.segmentOrder:[];
 const segmentOrder=[
  ...new Set([...requested.filter((id):id is string=>typeof id==="string"&&ids.has(id)),...segmentIds])
 ];
 const validKeys=new Set(segmentIds.flatMap(id=>defaults[id]||[]));
 const seen=new Set<K>();
 const columnOrder:Record<string,K[]>={};
 const requestedColumns=input.columnOrder&&typeof input.columnOrder==="object"&&!Array.isArray(input.columnOrder)
  ?input.columnOrder:{};
 for(const id of segmentIds){
  const candidates=requestedColumns[id];
  columnOrder[id]=[];
  if(!Array.isArray(candidates))continue;
  for(const key of candidates){
   if(typeof key==="string"&&validKeys.has(key as K)&&!seen.has(key as K)){
    seen.add(key as K);columnOrder[id].push(key as K);
   }
  }
 }
 // Newly added columns are placed in their original segment, without
 // disturbing existing custom order or reintroducing duplicate fields.
 for(const id of segmentIds)for(const key of defaults[id]||[]){
  if(!seen.has(key)){seen.add(key);columnOrder[id].push(key);}
 }
 return {segmentOrder,columnOrder};
}
export function reorderPoolSegment<K extends string>(
 layout:PoolColumnOrder<K>,source:string,target:string
):PoolColumnOrder<K>{
 if(source===target||!layout.segmentOrder.includes(source)||!layout.segmentOrder.includes(target))return layout;
 const next=layout.segmentOrder.filter(id=>id!==source);
 next.splice(next.indexOf(target),0,source);
 return {...layout,segmentOrder:next};
}
export function stepPoolSegment<K extends string>(
 layout:PoolColumnOrder<K>,id:string,direction:-1|1
):PoolColumnOrder<K>{
 const ix=layout.segmentOrder.indexOf(id),target=ix+direction;
 if(ix<0||target<0||target>=layout.segmentOrder.length)return layout;
 const next=[...layout.segmentOrder];
 [next[ix],next[target]]=[next[target],next[ix]];
 return {...layout,segmentOrder:next};
}
export function movePoolColumn<K extends string>(
 layout:PoolColumnOrder<K>,key:K,targetSegment:string,
 targetKey?:K
):PoolColumnOrder<K>{
 const source=Object.keys(layout.columnOrder).find(id=>layout.columnOrder[id].includes(key));
 if(!source||!(targetSegment in layout.columnOrder)||key===targetKey)return layout;
 const columnOrder:Record<string,K[]>={};
 for(const id of Object.keys(layout.columnOrder))
  columnOrder[id]=layout.columnOrder[id].filter(k=>k!==key);
 const list=columnOrder[targetSegment],targetIndex=targetKey?list.indexOf(targetKey):-1;
 list.splice(targetIndex<0?list.length:targetIndex,0,key);
 return {...layout,columnOrder};
}
export function stepPoolColumn<K extends string>(
 layout:PoolColumnOrder<K>,key:K,direction:-1|1
):PoolColumnOrder<K>{
 const id=Object.keys(layout.columnOrder).find(k=>layout.columnOrder[k].includes(key));
 if(!id)return layout;
 const columns=layout.columnOrder[id],ix=columns.indexOf(key),next=ix+direction;
 if(next<0||next>=columns.length)return layout;
 const updated=[...columns];[updated[ix],updated[next]]=[updated[next],updated[ix]];
 return {...layout,columnOrder:{...layout.columnOrder,[id]:updated}};
}
