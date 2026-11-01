/** Browser-local TOOLS selections. Data is device/browser scoped, not server-side research evidence. */
import {SPECIAL_DESIGNATION_CATEGORIES,type DesignationKey} from "./trial-designations";

export const TOOLS_FILTERS_STORAGE_KEY="pdufa-tools-filter-selections-v1";
export const TOOLS_STEP4_STORAGE_KEY="pdufa-tools-step4-selections-v1";
export const TOOLS_RATINGS_STORAGE_KEY="pdufa-tools-rating-expansions-v1";
export const TOOLS_RANKING_STORAGE_KEY="pdufa-tools-ranking-checklists-v1";
export const TOOLS_CLEAR_EVENT="pdufa-tools-clear-all-selections";

export type ToolsFilterSelections={
  selectedStages:string[];
  selectedDesignations:DesignationKey[];
  activeFilter:"phase"|"designation"|null;
  query:string;
  queryInput:string;
  offset:number;
};

const allowedDesignationKeys=new Set<string>(SPECIAL_DESIGNATION_CATEGORIES.map(x=>x.key));

export function parseToolsFilterSelections(value:unknown,allowedStages:readonly string[]):ToolsFilterSelections|null{
  if(!value||typeof value!=="object"||Array.isArray(value))return null;
  const raw=value as Record<string,unknown>;
  if(!Array.isArray(raw.selectedStages)||!Array.isArray(raw.selectedDesignations))return null;
  const allowed=new Set(allowedStages);
  const stages=[...new Set(raw.selectedStages.filter((s):s is string=>typeof s==="string"&&allowed.has(s)))];
  const designations=[...new Set(raw.selectedDesignations.filter((s):s is DesignationKey=>typeof s==="string"&&allowedDesignationKeys.has(s)))];
  const activeFilter=raw.activeFilter==="phase"||raw.activeFilter==="designation"?raw.activeFilter:null;
  const query=typeof raw.query==="string"?raw.query.slice(0,100):"";
  const queryInput=typeof raw.queryInput==="string"?raw.queryInput.slice(0,100):query;
  const offset=typeof raw.offset==="number"&&Number.isSafeInteger(raw.offset)&&raw.offset>=0
    &&raw.offset<=1000000&&raw.offset%50===0&&stages.length+designations.length>0?raw.offset:0;
  return {selectedStages:stages,selectedDesignations:designations,activeFilter,query,queryInput,offset};
}

export function readToolsPreference(key:string):unknown{
  try{
    if(typeof window==="undefined")return null;
    const raw=window.localStorage.getItem(key);
    return raw===null?null:JSON.parse(raw) as unknown;
  }catch{return null;}
}

export function saveToolsPreference(key:string,value:unknown):void{
  try{if(typeof window!=="undefined")window.localStorage.setItem(key,JSON.stringify(value));}
  catch{/* Browser storage may be disabled; selections still work during this visit. */}
}

export function clearToolsPreferences():void{
  if(typeof window==="undefined")return;
  for(const key of [TOOLS_FILTERS_STORAGE_KEY,TOOLS_STEP4_STORAGE_KEY,
    TOOLS_RATINGS_STORAGE_KEY,TOOLS_RANKING_STORAGE_KEY]){
    try{window.localStorage.removeItem(key);}catch{/* Storage may be disabled. */}
  }
}
