/** MAIN R91 — bounded, read-only retrieval of original publicly POSTED
 * ClinicalTrials.gov aggregate outcome and safety result structures.
 *
 * No treatment-effect recalculation, imputation, cross-study comparison,
 * clinical significance, statistical-significance judgment, retrospective
 * Bayesian forecast or independent review may be asserted by this module.
 */
import census from "../data/focus-r86-live-source-census-20261110.json";
import {R86_ORIGINAL_DOCUMENT_MANIFEST} from "./focus-r86-original-document-inventory";

export const R91_NOTICE=
 "Source-reported ClinicalTrials.gov aggregate outcome rows and adverse-event denominators. Values, p-values, populations and arms are transcribed as registry metadata; neither an original signed prospective SAP, source-verified subject-level analysis, independent medical review nor FDA outcome is established.";
type J=Record<string,unknown>;
function obj(v:unknown):J|null{
 return v!==null&&typeof v==="object"&&!Array.isArray(v)?v as J:null;
}
function array(v:unknown,max:number):unknown[]|null{
 return Array.isArray(v)&&v.length<=max?v:null;
}
function s(v:unknown,max=450):string|null{
 return typeof v==="string"&&v.length>0&&v.length<=max&&
 !/[\u0000-\u001f\u007f]/u.test(v)?v:null;
}
function num(v:unknown):number|null{
 return typeof v==="number"&&Number.isSafeInteger(v)&&v>=0&&v<=10_000_000?
  v:null;
}
export function buildR91PostedResultsSourceRoster(){
 const manifest=R86_ORIGINAL_DOCUMENT_MANIFEST;
 if(!manifest||manifest.exactTrials!==29||
    manifest.provisionalApplications!==23||manifest.rows.length!==29||
    manifest.independentSignedSAPsAuthenticated!==0||
    manifest.qualifiedIndependentScientificReviews!==0||
    manifest.validatedFutureFDAPredictions!==0||
    census.totalExactNcts!==29||census.successfulHttp200!==29||
    census.trialsWithPostedAggregateResults!==12||
    census.trialsWithoutPostedAggregateResults!==17||
    census.observedRows.length!==29||
    census.completedIndependentClinicalAssessments!==0||
    census.validatedFDAForecasts!==0||census.officialFDAOutcome!=="ABSTAIN")return null;
 const observations=new Map(census.observedRows.map(r=>[r.nct,r]));
 if(observations.size!==29)return null;
 const seen=new Set<string>();
 const rows=[];
 for(const row of manifest.rows){
  const c=observations.get(row.nct);
  if(!c||seen.has(row.nct)||c.FDAForecast!=="ABSTAIN"||
     c.qualifiedScientificReview!==false||c.originalBytesAuthenticated!==false||
     c.hasResults!==row.currentPrimaryTableRetained||
     c.hasResults!==row.currentSafetyArmsRetained||
     row.authenticatedSignedProspectiveSAP!==false||
     row.signedIndependentScientificReview!==false||
     row.FDAOutcome!=="ABSTAIN")return null;
  seen.add(row.nct);
  rows.push({
   nct:row.nct,ticker:row.ticker,
   cycleIds:[...row.cycleIds],phase:row.registryReportedPhase,
   resultsPostedInDatedRegistrySnapshot:c.hasResults,
   originalRegistryUrl:row.registryUrl,
   sourceArchiveDate:census.observationDateUtc,
   independentQualifiedClinicalReview:false as const,
   signedProspectiveSAPAuthenticated:false as const,
   FDAForecast:"ABSTAIN" as const
  });
 }
 if(seen.size!==29||rows.filter(x=>x.resultsPostedInDatedRegistrySnapshot).length!==12)return null;
 rows.sort((a,b)=>Number(b.resultsPostedInDatedRegistrySnapshot)-
  Number(a.resultsPostedInDatedRegistrySnapshot)||
  a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R91_29_NCT_POSTED_AGGREGATE_RESULTS_SOURCE_ONLY" as const,
  exactTrials:29 as const,provisionalCycles:23 as const,
  datedRegistrySnapshot:census.observationDateUtc,
  withPostedResultsAtSnapshot:12 as const,
  withoutPostedResultsAtSnapshot:17 as const,
  originalSignedSAPsVerified:0 as const,
  originalAnalysisPopulationsIndependentlyReconciled:0 as const,
  qualifiedScienceSignoffs:0 as const,
  validatedFDAPredictions:0 as const,
  notice:R91_NOTICE,rows
 };
}
export const R91_POSTED_RESULTS_ROSTER=buildR91PostedResultsSourceRoster();
type RosterRow=NonNullable<typeof R91_POSTED_RESULTS_ROSTER>["rows"][number];
function sourceGroup(value:unknown){
 const g=obj(value);
 if(!g)return null;
 const id=s(g.id,50),title=s(g.title,230);
 if(!id||!title)return null;
 return {id,title,description:s(g.description,450)};
}
function groupCounts(value:unknown,ids:Set<string>){
 const items=array(value,60);if(!items)return null;
 const result=[];
 for(const item of items){
  const r=obj(item),id=s(r?.groupId,50);
  if(!id||!ids.has(id))return null;
  const value=(typeof r?.value==="string"&&r.value.length<=150)?r.value:
   num(r?.value)!==null?String(r?.value):null;
  if(value===null)return null;
  result.push({groupId:id,value});
 }
 return result;
}
function extractOutcome(value:unknown){
 const m=obj(value);
 if(!m)return null;
 const type=s(m.type,60),title=s(m.title,400);
 if(!type||!title)return null;
 const groupsRaw=array(m.groups??[],45);
 if(!groupsRaw)return null;
 const groups=groupsRaw.map(sourceGroup);
 if(groups.some(g=>g===null))return null;
 const g=groups as Array<NonNullable<ReturnType<typeof sourceGroup>>>;
 const ids=new Set(g.map(x=>x.id));
 if(ids.size!==g.length)return null;
 const denomsRaw=array(m.denoms??[],30);
 if(!denomsRaw)return null;
 const denominators=[];
 for(const item of denomsRaw){
  const d=obj(item),units=s(d?.units,100);
  if(!d||!units)return null;
  const counts=groupCounts(d.counts,ids);
  if(!counts)return null;
  denominators.push({units,counts});
 }
 const classesRaw=array(m.classes??[],30);
 if(!classesRaw)return null;
 const measurements=[];
 for(const item of classesRaw){
  const cl=obj(item);
  if(!cl)return null;
  const catsRaw=array(cl.categories??[],80);
  if(!catsRaw)return null;
  for(const cat of catsRaw){
   const c=obj(cat);
   if(!c)return null;
   const observed=array(c.measurements??[],70);
   if(!observed)return null;
   for(const val of observed){
    const mval=obj(val),gid=s(mval?.groupId,50);
    if(!gid||!ids.has(gid))return null;
    measurements.push({
     groupId:gid,category:s(c.title,230),classTitle:s(cl.title,230),
     value:s(mval?.value,180),
     spread:s(mval?.spread,180),
     lowerLimit:s(mval?.lowerLimit,180),
     upperLimit:s(mval?.upperLimit,180)
    });
    if(measurements.length>2000)return null;
   }
  }
 }
 const rawAnalyses=array(m.analyses??[],50);
 if(!rawAnalyses)return null;
 const analyses=[];
 for(const val of rawAnalyses){
  const a=obj(val);
  if(!a)return null;
  const groupIds=array(a.groups??[],30);
  if(groupIds===null||groupIds.some(v=>typeof v!=="string"||!ids.has(v)))return null;
  analyses.push({
   groupIds:groupIds as string[],
   pValue:s(a.pValue,110),pValueMethod:s(a.pValueMethod,150),
   ciPct:num(a.ciPct),ciLowerLimit:s(a.ciLowerLimit,120),
   ciUpperLimit:s(a.ciUpperLimit,120),estimateComment:s(a.estimateComment,450)
  });
 }
 return {
  type,title,timeFrame:s(m.timeFrame,270),
  populationDescription:s(m.populationDescription,900),
  description:s(m.description,900),
  unitOfMeasure:s(m.unitOfMeasure,120),
  paramType:s(m.paramType,120),
  reportingStatus:s(m.reportingStatus,120),
  groups:g,denominators,measurements,analyses
 };
}
function aggregateEvents(value:unknown){
 const v=obj(value);if(!v)return null;
 const groupId=s(v.id,60),title=s(v.title,230);
 if(!groupId||!title)return null;
 return {
  groupId,title,
  seriousNumAffected:num(v.seriousNumAffected),
  seriousNumAtRisk:num(v.seriousNumAtRisk),
  otherNumAffected:num(v.otherNumAffected),
  otherNumAtRisk:num(v.otherNumAtRisk),
  deathsNumAffected:num(v.deathsNumAffected),
  deathsNumAtRisk:num(v.deathsNumAtRisk)
 };
}
function eventTerms(value:unknown,groupIds:Set<string>){
 const arr=array(value??[],2000);if(!arr)return null;
 const terms=[];
 for(const val of arr){
  const e=obj(val),term=s(e?.term,230);
  if(!term)return null;
  const st=array(e?.stats??[],100);if(!st)return null;
  const stats=[];
  for(const v of st){
   const x=obj(v),g=s(x?.groupId,50);
   if(!x||!g||!groupIds.has(g))return null;
   stats.push({
    groupId:g,affected:num(x.numAffected),
    atRisk:num(x.numAtRisk),
    events:num(x.numEvents)
   });
  }
  terms.push({term,organSystem:s(e?.organSystem,220),stats});
 }
 return terms;
}
/** The returned structures preserve reported quantities, not adjudicated
 * denominators or significance. Missing fields stay null.
 */
export function inspectR91CurrentPostedResults(row:RosterRow,body:unknown){
 const root=obj(body),p=obj(root?.protocolSection);
 const identity=obj(p?.identificationModule);
 if(s(identity?.nctId,30)!==row.nct||typeof root?.hasResults!=="boolean")
  return null;
 if(root.hasResults===false)return {
  nct:row.nct,ticker:row.ticker,
  originalStudyUrl:"https://clinicaltrials.gov/study/"+row.nct+"?tab=results",
  sourceStatus:"NO_AGGREGATE_RESULTS_CURRENTLY_POSTED" as const,
  sourceChangedSinceDatedSnapshot:row.resultsPostedInDatedRegistrySnapshot,
  outcomeMeasureCount:0,primaryOutcomeCount:0,
  participantFlowGroups:[],registeredOutcomes:[],
  safetyExposureGroups:[],seriousAdverseEventTerms:[],otherAdverseEventTerms:[],
  originalSignedSAPVerified:false as const,
  independentStatisticalReanalysis:false as const,
  independentSafetyAdjudication:false as const,
  FDAForecast:"ABSTAIN" as const,notice:R91_NOTICE
 };
 const results=obj(root.resultsSection);
 const flow=obj(results?.participantFlowModule);
 const outcomes=obj(results?.outcomeMeasuresModule);
 const adverse=obj(results?.adverseEventsModule);
 if(!results||!flow||!outcomes||!adverse)return null;
 const flowRaw=array(flow.groups,60);
 const outcomeRaw=array(outcomes.outcomeMeasures,600);
 const eventGroupsRaw=array(adverse.groups,50);
 if(!flowRaw||!outcomeRaw||!eventGroupsRaw)return null;
 const flowGroups=flowRaw.map(sourceGroup);
 const eventGroups=eventGroupsRaw.map(aggregateEvents);
 if(flowGroups.some(v=>v===null)||eventGroups.some(v=>v===null))return null;
 const groups=flowGroups as Array<NonNullable<ReturnType<typeof sourceGroup>>>;
 const safety=eventGroups as Array<NonNullable<ReturnType<typeof aggregateEvents>>>;
 if(new Set(groups.map(g=>g.id)).size!==groups.length||
    new Set(safety.map(g=>g.groupId)).size!==safety.length)return null;
 // Parse actual registry posted primary measures, plus source-only all-endpoint
 // census for completeness; no inferred hierarchy if type is unavailable.
 const primary=[];
 for(const x of outcomeRaw){
  const m=obj(x),kind=s(m?.type,100);
  if(!m||!kind)return null;
  if(kind!=="PRIMARY")continue;
  const parsed=extractOutcome(x);
  if(!parsed)return null;
  primary.push(parsed);
 }
 const adverseIds=new Set(safety.map(x=>x.groupId));
 const serious=eventTerms(adverse.seriousEvents,adverseIds);
 const other=eventTerms(adverse.otherEvents,adverseIds);
 if(!serious||!other)return null;
 return {
  nct:row.nct,ticker:row.ticker,
  originalStudyUrl:"https://clinicaltrials.gov/study/"+row.nct+"?tab=results",
  sourceStatus:"ORIGINAL_PUBLIC_AGGREGATE_RESULTS_POSTED_NOT_ADJUDICATED" as const,
  sourceChangedSinceDatedSnapshot:!row.resultsPostedInDatedRegistrySnapshot,
  outcomeMeasureCount:outcomeRaw.length,primaryOutcomeCount:primary.length,
  participantFlowGroups:groups,
  registeredOutcomes:primary,
  safetyExposureGroups:safety,
  seriousAdverseEventTerms:serious,
  otherAdverseEventTerms:other,
  originalSignedSAPVerified:false as const,
  independentStatisticalReanalysis:false as const,
  independentSafetyAdjudication:false as const,
  FDAForecast:"ABSTAIN" as const,notice:R91_NOTICE
 };
}
