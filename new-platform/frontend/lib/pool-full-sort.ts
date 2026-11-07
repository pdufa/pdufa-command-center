/** Source-backed POOL sorting performed before pagination. No inferred qualification. */
import type {PoolTrialRecord} from "./pool-pipeline-funnel";
import snapshot from "../data/p3PostDataActive.json";
import {sortPoolPage,type PageSortDirection} from "./pool-row-sorting";

export const POOL_SORT_KEYS=[
 "ticker","company","nct","phase","status","drug","intervention","route","indication",
 "start","primary","complete","posted","updated","source","checked","traded","cap","capDate",
 "capQualified","phase3","publicResults","fdaPath","application","focusQualified",
 "reason","evidence","completeness","reviewed"
] as const;
export type PoolSortKey=typeof POOL_SORT_KEYS[number];
export type PoolSortSpec={key:PoolSortKey;direction:PageSortDirection};
type SortableRow=PoolTrialRecord&{
 status?:string;interventionType?:string;route?:string;startDate?:string;
 primaryCompletion?:string;studyCompletion?:string;resultsPosted?:string;
 sourceUpdated?:string;sourceUrl?:string;checkedAt?:string;capChecked?:string;
 capInRange?:boolean;phase3Source?:string;capSource?:string;
};
const roster=new Map(snapshot.records.map(r=>[r.nct+"|"+r.ticker.toUpperCase(),r]));
const nct=(row:SortableRow)=>row.nctId||(row.id.startsWith("TRIAL|")?row.id.slice(6):"");
const focusFor=(row:SortableRow)=>roster.get(nct(row)+"|"+row.ticker.toUpperCase());
const found=(value:unknown)=>typeof value==="string"&&value.trim()?value:null;
const verifiedQuoteDate=(focus:(typeof snapshot.records)[number])=>{
 // A FOCUS spreadsheet snapshot date does NOT establish the quote observation date.
 const value:unknown="marketCapAsOf" in focus?focus.marketCapAsOf:null;
 return found(value);
};
export function poolSortValue(row:PoolTrialRecord,key:PoolSortKey):string|number|null{
 const r=row as SortableRow,focus=focusFor(r),cap=focus?.marketCap??r.marketCap;
 switch(key){
  case "ticker":return found(r.ticker);
  case "company":return found(r.company);
  case "nct":return found(nct(r));
  case "phase":return found(r.stage);
  case "status":return found(r.status);
  case "drug":return found(r.drug);
  case "intervention":return found(r.interventionType);
  case "route":return found(r.route);
  case "indication":return found(r.indication);
  case "start":return found(r.startDate);
  case "primary":return found(r.primaryCompletion);
  case "complete":return found(r.studyCompletion);
  case "posted":return found(r.resultsPosted);
  case "updated":return found(r.sourceUpdated);
  case "source":return found(r.sourceUrl);
  case "checked":return found(r.checkedAt);
  case "traded":return focus?"FOCUS issuer reviewed":null;
  case "cap":return typeof cap==="number"&&Number.isFinite(cap)?cap:null;
  case "capDate":return focus?verifiedQuoteDate(focus):found(r.capChecked);
  case "capQualified":return focus?"Pass (FOCUS snapshot)":r.capInRange===true?"Historical in range — recheck":null;
  case "phase3":return focus||/Phase 3|PHASE3/i.test(r.stage||"")?"Recorded":null;
  case "publicResults":return focus?"Yes — source in FOCUS":found(r.phase3Source)?"Source recorded — review":null;
  case "fdaPath":return focus?"Recorded FOCUS path":null;
  case "application":return focus?found(focus.fdaStatus):null;
  case "focusQualified":return focus?"In FOCUS":null;
  case "reason":return focus?"Exact NCT + ticker matches the saved FOCUS roster":null;
  case "evidence":return focus?found(focus.resultsUrl):found(r.capSource);
  case "completeness":return focus?"FOCUS source links recorded; full evidence not assessed":null;
  case "reviewed":return focus?snapshot.asOf:null;
 }
}
export function sortPoolUniverse<T extends PoolTrialRecord>(rows:readonly T[],spec:PoolSortSpec):T[]{
 return sortPoolPage(rows,row=>poolSortValue(row,spec.key),spec.direction);
}
