/** Stable sorting for the currently loaded POOL page (not the entire census). */
export type PageSortDirection="asc"|"desc";
export function sortPoolPage<T>(
 rows:readonly T[],value:(row:T)=>string|number|null|undefined,
 direction:PageSortDirection
):T[]{
 const asKey=(row:T)=>{
  const raw=value(row);
  if(raw===null||raw===undefined)return null;
  if(typeof raw==="number")return Number.isFinite(raw)?raw:null;
  const s=raw.trim();
  if(!s||/^(not verified|not assessed|unknown|unavailable|non-trial record)$/i.test(s))return null;
  return s;
 };
 return rows.map((row,index)=>({row,index,key:asKey(row)})).sort((a,b)=>{
  if(a.key===null&&b.key===null)return a.index-b.index;
  if(a.key===null)return 1;
  if(b.key===null)return -1;
  let cmp=0;
  if(typeof a.key==="number"&&typeof b.key==="number")cmp=a.key-b.key;
  else cmp=String(a.key).localeCompare(String(b.key),"en",{numeric:true,sensitivity:"base"});
  return cmp===0?a.index-b.index:direction==="asc"?cmp:-cmp;
 }).map(x=>x.row);
}
