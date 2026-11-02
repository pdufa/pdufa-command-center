/** Client-side filters for the fully reconciled registry-posting NCT lists.
 * Never mutates source rows or changes clinical results classifications.
 */
import type {RegistryPostingRow} from "./phase3-registry-posting";
export type PostingSortKey="ticker"|"nctId"|"company"|"registryStatus"|"resultsCount"|"resultsFirstPostedDate";
export type PostingSort={key:PostingSortKey;direction:"asc"|"desc"};
export type PostingFilters={
  ticker:string;nctId:string;company:string;registryStatus:string;
  resultsPosted:"all"|"yes"|"no";
  datePresence:"all"|"dated"|"undated";
  from:string;to:string;
};
export const EMPTY_POSTING_FILTERS:PostingFilters={
  ticker:"",nctId:"",company:"",registryStatus:"",resultsPosted:"all",
  datePresence:"all",from:"",to:""
};
export const INITIAL_POSTING_SORT:PostingSort={key:"ticker",direction:"asc"};
export function postingFilterCount(filters:PostingFilters):number{
  return Number(!!filters.ticker)+Number(!!filters.nctId.trim())+
    Number(!!filters.company.trim())+Number(!!filters.registryStatus)+
    Number(filters.resultsPosted!=="all")+Number(filters.datePresence!=="all")+
    Number(!!filters.from)+Number(!!filters.to);
}
export function filterAndSortPostingRows(
  rows:readonly RegistryPostingRow[],query:string,filters:PostingFilters,sort:PostingSort
):RegistryPostingRow[]{
  const q=query.trim().toLocaleLowerCase("en-US");
  const nct=filters.nctId.trim().toLocaleLowerCase("en-US");
  const company=filters.company.trim().toLocaleLowerCase("en-US");
  const filtered=rows.filter(row=>{
    const posted=row.resultsCount>0;
    const date=row.resultsFirstPostedDate||"";
    if(q&&![row.nctId,row.ticker,row.company,row.registryStatus,
             date,row.sourceUrl,posted?"Yes":"No"]
       .some(value=>value.toLocaleLowerCase("en-US").includes(q)))return false;
    if(filters.ticker&&row.ticker!==filters.ticker)return false;
    if(nct&&!row.nctId.toLocaleLowerCase("en-US").includes(nct))return false;
    if(company&&!row.company.toLocaleLowerCase("en-US").includes(company))return false;
    if(filters.registryStatus&&row.registryStatus!==filters.registryStatus)return false;
    if(filters.resultsPosted==="yes"&&!posted || filters.resultsPosted==="no"&&posted)return false;
    if(filters.datePresence==="dated"&&!date || filters.datePresence==="undated"&&!!date)return false;
    if(filters.from&&(!date||date<filters.from))return false;
    if(filters.to&&(!date||date>filters.to))return false;
    return true;
  });
  const cmp=(a:RegistryPostingRow,b:RegistryPostingRow)=>{
    if(sort.key==="resultsCount")return a.resultsCount-b.resultsCount;
    return String(a[sort.key]??"").localeCompare(String(b[sort.key]??""),"en-US",{numeric:true,sensitivity:"base"});
  };
  return filtered.sort((a,b)=>{
    const result=cmp(a,b)*(sort.direction==="asc"?1:-1);
    return result||a.ticker.localeCompare(b.ticker,"en-US")||a.nctId.localeCompare(b.nctId,"en-US");
  });
}
