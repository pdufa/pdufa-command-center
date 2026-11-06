/** Server-only snapshot of exact-NCT public-source research (Nov 5 2026, US Pacific).
 * Source facts are not efficacy scores, primary-endpoint adjudications or FDA application evidence.
 */
import "server-only";
import {brotliDecompressSync} from "node:zlib";
import {phase3SixSourceCoreBase64} from "../data/phase3SixSourceCore20261105";

export type Phase3OnlineRecord={
 nctId:string; registryStatus:string|null; updated:string|null;
 drugNames:string[];interventionNames:string[];
 primaryOutcome:{measure:string;timeFrame:string}[];
 secondaryOutcomeCount:number;
 enrollment:number|null; enrollmentType:string|null; allocation:string|null;masking:string|null;
 hasResults:boolean;resultsFirstPosted:string|null;
 resultsOutcomeMeasureCount:number;resultsAnalysisCount:number;
 adverseEventsPosted:boolean;hasDocuments:boolean;
 publicationReferences:string[];pubmedPMIDs:string[];
 secFilingMentions:number|null;secondaryIds:string[];
};
export type Phase3OnlineSnapshot={
 schemaVersion:number;generatedAt:string;records:Phase3OnlineRecord[];
};
let cached:Phase3OnlineSnapshot|null=null;
let indexed:Map<string,Phase3OnlineRecord>|null=null;
export function phase3OnlineSnapshot():Phase3OnlineSnapshot{
 if(cached)return cached;
 const uncompressed=brotliDecompressSync(Buffer.from(phase3SixSourceCoreBase64,"base64")).toString("utf8");
 const data=JSON.parse(uncompressed) as Phase3OnlineSnapshot;
 if(data.schemaVersion!==1||data.records?.length!==762||
   new Set(data.records.map(x=>x.nctId)).size!==762||
   data.records.some(x=>!/^NCT\\d{8}$/.test(x.nctId)))throw Error("Online source evidence integrity check failed");
 cached=data;
 indexed=new Map(data.records.map(x=>[x.nctId,x]));
 return cached;
}
export function phase3OnlineRecord(nctId:string):Phase3OnlineRecord|undefined{
 phase3OnlineSnapshot();
 return indexed?.get(nctId);
}
export function phase3OnlineSourceObservation(nctId:string,number:number):{
 description:string;sourceUrl:string;sourceStatus:string
}|null{
 const r=phase3OnlineRecord(nctId);
 if(!r)return null;
 const reg="https://clinicaltrials.gov/study/"+nctId;
 const fact=(description:string,sourceStatus="SOURCE_FACT_ONLY")=>({description,sourceUrl:reg,sourceStatus});
 switch(number){
  case 7:return r.primaryOutcome?.length?
   fact("Public registry primary outcome(s): "+r.primaryOutcome.slice(0,2).map(x=>x.measure).join("; ")):null;
  case 8:return r.primaryOutcome?.some(x=>x.timeFrame)?
   fact("Public registry primary outcome timing: "+r.primaryOutcome.slice(0,2).map(x=>x.timeFrame||"not reported").join("; ")):null;
  case 9:return r.allocation?
   fact("Public registry allocation: "+r.allocation):null;
  case 10:return r.masking?
   fact("Public registry masking: "+r.masking):null;
  case 11:return r.interventionNames?.length?
   fact("Registered interventions: "+r.interventionNames.slice(0,8).join("; ")+
    ". This does NOT adjudicate comparator adequacy"):null;
  case 12:return r.enrollment!==null&&r.enrollment!==undefined?
   fact("Registry enrollment: "+r.enrollment+" ("+(r.enrollmentType||"unspecified type")+")"):null;
  case 17:return r.secondaryOutcomeCount>0?
   fact("The registry documents "+r.secondaryOutcomeCount+
     " secondary outcome measures; this does NOT predict secondary-endpoint success"):null;
  case 25:return r.registryStatus?
   fact("Live-sweep registry status: "+r.registryStatus+" (source snapshot "+r.updated+")"):null;
  case 27:return r.interventionNames?.some(x=>/\\bplacebo\\b/i.test(x))?
   fact("The intervention list names placebo; comparator adequacy is not assessed"):null;
  case 29:return r.hasResults?
   fact("Public ClinicalTrials.gov results posted"+(r.resultsFirstPosted?
    " on "+r.resultsFirstPosted:"")+
    ". This is documented posted-results presence, not an issuer primary-endpoint verdict",
    "REGISTRY_RESULTS_POSTED"):null;
  default:return null;
 }
}
