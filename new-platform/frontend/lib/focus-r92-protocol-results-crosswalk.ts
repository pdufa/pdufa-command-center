/** MAIN R92: compare CURRENT public registry protocol primary outcomes to
 * CURRENT posted primary outcome records. Current protocol data may have been
 * retrospectively edited and DOES NOT prove original prespecification.
 * This is textual/source reconciliation only; NO clinical score.
 */
import {R91_POSTED_RESULTS_ROSTER,inspectR91CurrentPostedResults} from "./focus-r91-posted-results-reconciliation";
import {R91_DATED_SOURCE_AUDIT} from "./focus-r91-source-audit-readiness";
type Roster=NonNullable<typeof R91_POSTED_RESULTS_ROSTER>;
type RosterRow=Roster["rows"][number];
type RecordValue=Record<string,unknown>;
function obj(x:unknown):RecordValue|null{
 return x!==null&&typeof x==="object"&&!Array.isArray(x)?x as RecordValue:null;
}
function list(x:unknown,max:number):unknown[]|null{
 return Array.isArray(x)&&x.length<=max?x:null;
}
function str(x:unknown,max=1000):string|null{
 return typeof x==="string"&&x.length>0&&x.length<=max&&
 !/[\u0000-\u001f\u007f]/u.test(x)?x:null;
}
function normalize(x:string|null):string{
 return (x??"").toLowerCase().normalize("NFKC")
  .replace(/[%]/gu," percent ")
  .replace(/[^a-z0-9]+/gu," ")
  .replace(/\s+/gu," ").trim();
}
const STOP_WORDS=new Set([
 "the","a","an","of","in","on","from","at","to","by","for","and","with",
 "who","as","is","was","were","during","through","between","after","before",
 "treatment","subjects","subject","participants","participant","patients",
 "patient","change","baseline","proportion","percentage","percent","week",
 "time","number","rate","mean","average","inclusion","clinical"
]);
function tokenSet(x:string|null):Set<string>{
 return new Set(normalize(x).split(" ").filter(v=>v.length>=3&&!STOP_WORDS.has(v)));
}
function overlap(a:string|null,b:string|null):number{
 const x=tokenSet(a),y=tokenSet(b);
 if(x.size===0||y.size===0)return 0;
 const intersection=[...x].filter(t=>y.has(t)).length;
 return intersection/Math.max(x.size,y.size);
}
export const R92_SCIENTIFIC_LIMIT=
 "This is a lexical crosswalk of CURRENT registry protocol design and posted aggregate results. A match is not evidence of the ORIGINAL final signed SAP or prospectively approved endpoint. A mismatch is a research question, not evidence of misconduct, statistical failure, or a negative FDA decision.";

export function buildR92CurrentProtocolResultsRoster(){
 const r=R91_POSTED_RESULTS_ROSTER,a=R91_DATED_SOURCE_AUDIT;
 if(!r||!a||r.exactTrials!==29||r.provisionalCycles!==23||
    r.withPostedResultsAtSnapshot!==12||r.rows.length!==29||
    a.originalResultsSourceNcts!==12||a.reportedPrimaryOutcomeEntries!==16||
    a.qualifiedIndependentScientificSignoffs!==0||
    a.finalProspectivelySignedSAPsIndependentlyAuthenticated!==0||
    r.qualifiedScienceSignoffs!==0||r.validatedFDAPredictions!==0)return null;
 const by=new Map(a.rows.map(x=>[x.nct,x]));
 if(by.size!==12)return null;
 const rows=[];
 for(const row of r.rows){
  if(row.FDAForecast!=="ABSTAIN"||row.signedProspectiveSAPAuthenticated!==false||
     row.independentQualifiedClinicalReview!==false)return null;
  const dated=by.get(row.nct);
  if(row.resultsPostedInDatedRegistrySnapshot!==Boolean(dated))return null;
  if(!dated)continue;
  rows.push({
   nct:row.nct,ticker:row.ticker,phase:row.phase,cycleIds:[...row.cycleIds],
   sourceUrl:"https://clinicaltrials.gov/study/"+row.nct,
   datedOriginalResultsSHA256:dated.rawOriginalSourceSHA256,
   archivedPrimaryOutcomeCount:dated.primaryOutcomeCount,
   originalSignedSAPAuthenticated:false as const,
   independentlyAdjudicated:false as const,
   FDAForecast:"ABSTAIN" as const
  });
 }
 if(rows.length!==12||new Set(rows.map(x=>x.nct)).size!==12)return null;
 rows.sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R92_12_CASE_CURRENT_PROTOCOL_AND_RESULTS_SOURCE_CROSSWALK" as const,
  censusDate:"2026-11-10" as const,
  exactFocusTrials:29 as const,
  provisionalFDACycles:23 as const,
  registeredResultNcts:12 as const,
  priorObservedPrimaryOutcomes:16 as const,
  originalSignedSAPsAuthenticated:0 as const,
  independentScientificSignoffs:0 as const,
  validatedFDAForecasts:0 as const,
  notice:R92_SCIENTIFIC_LIMIT,rows
 };
}
export const R92_CURRENT_PROTOCOL_RESULTS_ROSTER=buildR92CurrentProtocolResultsRoster();
type Row=NonNullable<typeof R92_CURRENT_PROTOCOL_RESULTS_ROSTER>["rows"][number];

export function inspectR92CurrentProtocolResults(row:Row,body:unknown){
 const root=obj(body);
 const protocol=obj(root?.protocolSection);
 const ident=obj(protocol?.identificationModule);
 if(str(ident?.nctId,30)!==row.nct)return null;
 const currentOutcomes=obj(protocol?.outcomesModule);
 const plannedRaw=list(currentOutcomes?.primaryOutcomes,80);
 if(!currentOutcomes||!plannedRaw)return null;
 const sourceResult=inspectR91CurrentPostedResults({
  nct:row.nct,ticker:row.ticker,phase:row.phase,
  cycleIds:row.cycleIds,resultsPostedInDatedRegistrySnapshot:true,
  originalRegistryUrl:row.sourceUrl,sourceArchiveDate:"2026-11-10",
  independentQualifiedClinicalReview:false,
  signedProspectiveSAPAuthenticated:false,FDAForecast:"ABSTAIN"
 },body);
 if(!sourceResult||sourceResult.sourceStatus!=="ORIGINAL_PUBLIC_AGGREGATE_RESULTS_POSTED_NOT_ADJUDICATED")
  return null;
 const planned=[];
 for(let i=0;i<plannedRaw.length;i++){
  const p=obj(plannedRaw[i]);
  const title=str(p?.measure,900);
  const timeFrame=p?.timeFrame===undefined?null:str(p.timeFrame,500);
  const description=p?.description===undefined?null:str(p.description,1000);
  if(!p||!title||
     p.timeFrame!==undefined&&timeFrame===null||
     p.description!==undefined&&description===null)return null;
  planned.push({
   key:"protocol-primary-"+i,
   title,timeFrame,description,
   normalizedTitle:normalize(title),
   normalizedTimeFrame:normalize(timeFrame)
  });
 }
 const posted=sourceResult.registeredOutcomes.map((r,i)=>({
   key:"results-primary-"+i,
   title:r.title,timeFrame:r.timeFrame,
   populationDescription:r.populationDescription,
   sourceReportedAnalysisGroups:r.groups.length,
   sourceReportedDenominatorEntries:r.denominators.reduce(
    (s,d)=>s+d.counts.length,0),
   sourceReportedPValueEntries:r.analyses.filter(x=>x.pValue!==null).length,
   normalizedTitle:normalize(r.title),
   normalizedTimeFrame:normalize(r.timeFrame)
 }));
 const links=posted.map(result=>{
  const exact=planned.filter(x=>x.normalizedTitle===result.normalizedTitle);
  const strongest=exact.filter(x=>x.normalizedTimeFrame===result.normalizedTimeFrame);
  let state:
   "EXACT_TITLE_AND_TIME_FRAME"|
   "EXACT_TITLE_TIME_FRAME_DIFFERS"|
   "MULTIPLE_POSSIBLE_PROTOCOL_ENTRIES"|
   "LEXICAL_CANDIDATE_REQUIRES_REVIEW"|
   "NO_LEXICAL_CANDIDATE_REQUIRES_REVIEW";
  let candidates:typeof planned=[];
  if(strongest.length===1){
   state="EXACT_TITLE_AND_TIME_FRAME";candidates=strongest;
  }else if(strongest.length>1){
   state="MULTIPLE_POSSIBLE_PROTOCOL_ENTRIES";candidates=strongest;
  }else if(exact.length===1){
   state="EXACT_TITLE_TIME_FRAME_DIFFERS";candidates=exact;
  }else if(exact.length>1){
   state="MULTIPLE_POSSIBLE_PROTOCOL_ENTRIES";candidates=exact;
  }else{
   const ranked=planned.map(p=>({p,score:overlap(p.title,result.title)}))
    .filter(x=>x.score>=0.5)
    .sort((a,b)=>b.score-a.score||a.p.key.localeCompare(b.p.key));
   if(ranked.length>0){
    state="LEXICAL_CANDIDATE_REQUIRES_REVIEW";
    candidates=ranked.slice(0,3).map(x=>x.p);
   }else{
    state="NO_LEXICAL_CANDIDATE_REQUIRES_REVIEW";
   }
  }
  return {
   postedOutcomeKey:result.key,postedTitle:result.title,
   postedTimeFrame:result.timeFrame,
   state,possibleProtocolKeys:candidates.map(x=>x.key),
   interpretation:"TEXTUAL_REGISTRY_LEAD_ONLY_NO_PRESPECIFICATION_OR_SAP_CLAIM" as const
  };
 });
 const exactKeys=new Set(links.filter(x=>x.state==="EXACT_TITLE_AND_TIME_FRAME")
  .flatMap(x=>x.possibleProtocolKeys));
 const titleOnlyKeys=new Set(links.filter(x=>x.state==="EXACT_TITLE_TIME_FRAME_DIFFERS")
  .flatMap(x=>x.possibleProtocolKeys));
 return {
  schema:"MAIN_R92_LIVE_CURRENT_PROTOCOL_VS_POSTED_PRIMARY_OUTCOMES" as const,
  nct:row.nct,ticker:row.ticker,originalSourceUrl:row.sourceUrl,
  currentProtocolPrimaryCount:planned.length,
  postedRegistryPrimaryCount:posted.length,
  originalCensusPrimaryCount:row.archivedPrimaryOutcomeCount,
  priorSourceCountChanged:posted.length!==row.archivedPrimaryOutcomeCount,
  plannedPrimaryOutcomes:planned,
  postedPrimaryOutcomes:posted,
  textualCrosswalk:links,
  exactTitleAndTimeframeCount:links.filter(x=>x.state==="EXACT_TITLE_AND_TIME_FRAME").length,
  exactTitleDifferentTimeframeCount:links.filter(x=>x.state==="EXACT_TITLE_TIME_FRAME_DIFFERS").length,
  needsIndependentEndpointReviewCount:links.filter(x=>![
   "EXACT_TITLE_AND_TIME_FRAME","EXACT_TITLE_TIME_FRAME_DIFFERS"
  ].includes(x.state)).length,
  protocolPrimaryWithoutExactMatch:planned.filter(x=>
   !exactKeys.has(x.key)&&!titleOnlyKeys.has(x.key)).map(x=>x.key),
  originalProspectiveSAPAuthenticated:false as const,
  sourceVersionEffectiveBeforeUnblindingVerified:false as const,
  clinicalEndpointConsistencyIndependentlySigned:false as const,
  safetyInterpretationIndependentlySigned:false as const,
  scienceGrade:null,
  FDAForecast:"ABSTAIN" as const,
  notice:R92_SCIENTIFIC_LIMIT
 };
}
