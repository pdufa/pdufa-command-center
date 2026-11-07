/** Frozen TOP-only completion ledger. Never classifies or mutates another sheet. */
import baseline from "../data/topOnlyBaseline20261107.json";
import matrix from "../data/topOnly190Baseline20261107.json";
import fresh from "../data/topOnlyRegistry20261107.json";
import papers from "../data/topOnlyPublicationEvidence20261107.json";
import publications from "../data/topOnlyReviewedPublications20261107.json";
import searchLog from "../data/topOnlySourceSearch20261107.json";
import companySearchLog from "../data/topOnlyCompanySearch20261107.json";
import fallbacks from "../data/topOnlyDocumentFallbacks20261107.json";
import reviewedDocuments from "../data/topOnlyReviewedDocumentFacts20261107.json";
import documents from "../data/topOnlyDocumentCoverage20261107.json";
import priorData from "../data/phase3PreDataOfficialResearch.json";
import grades from "../data/raas-reviewed-metric-assessments.json";
import supplement from "../data/raas-clinical-five-reviewed-increment.json";
import {RAAS_METRIC_CATALOG} from "./raas-metric-specs";
import {fullReviewedTrialCandidate} from "./raas-reviewed-full-score";
import {clinicalFiveForTrial,ACTIVE_RAAS_VERSION} from "./raas-clinical-five";
export const TOP_COMPLETION_VERSION="TOP_ONLY_190_ACCOUNTABILITY_20261107_V1";
export type State="VERIFIED"|"MISSING EXPECTED"|"UNVERIFIED"|"PENDING"|"NOT YET EXPECTED"|"NOT APPLICABLE"|"CONFLICTING";
const asOf="2026-11-07";
const byNct=new Map(fresh.records.map(r=>[r.trialId,r]));
const matrixByNct=new Map(matrix.rows.map(r=>[r[0],r]));
const activeMetricIds=new Set(["pre-1-1","pre-1-2","pre-1-3","pre-1-4","pre-1-5"]);
const validSource=(s:string)=>/^https:\/\/[^\s<>]+/.test(s);
const empty=(s:string)=>!s||/^(?:NOT_VERIFIED|UNKNOWN|UNSCORED|NOT_YET_REVIEWED|REQUIRES_INTERPRETATION|NOT_INDEPENDENTLY_REVIEWED|UNDETERMINED)$/i.test(s);
export function topOnlyReport(){
 const ids=new Set(baseline.records.map(r=>r.nctId));
 if(ids.size!==baseline.records.length||matrix.headers.length!==190||matrix.rows.length!==ids.size||matrix.rows.some(r=>r.length!==190||!ids.has(r[0]))||byNct.size!==ids.size||[...byNct.keys()].some(id=>!ids.has(id)))throw Error("TOP_ONLY_SCOPE_OR_190_INTEGRITY");
 const trials=baseline.records.map(row=>{
  const r=byNct.get(row.nctId)!,original=matrixByNct.get(row.nctId)!;
  const registryVerified=r.sourceState==="VERIFIED_CURRENT_REGISTRY";
  const fieldSource={url:r.sourceUrl,date:"sourceDate" in r?r.sourceDate:null,retrievedAt:r.retrievedAt,type:"OFFICIAL_EXACT_NCT_REGISTRY"};
  const refs=papers.records.filter(p=>p.topNcts.includes(row.nctId));
  const manualFacts=reviewedDocuments.records.filter(f=>f.nctId===row.nctId);
  const hasPublicReadout=publications.records.some(p=>p.nctId===row.nctId)||manualFacts.some(f=>f.evidenceClassification==="DOCUMENTED_PUBLIC_READOUT_EXISTS");
  const sourceFacts:Array<{question:number;evidence:string;sourceUrl:string}>=[];
  const add=(question:number,evidence:string)=>sourceFacts.push({question,evidence,sourceUrl:r.sourceUrl});
  if(registryVerified&&"primary" in r){
   if(r.eligibility?.eligibilityCriteria)add(6,"Registered population and eligibility: "+r.eligibility.eligibilityCriteria.slice(0,1400)+". Eligibility criteria alone do not establish external generalizability.");
   const pro=r.secondary.filter(p=>/patient.report|quality.of.life|questionnaire|PRO\b|PROMIS|SF.?36|EQ.?5D/i.test(p.measure));
   if(pro.length)add(18,"Registered patient-reported/quality-of-life instruments: "+pro.map(p=>p.measure).join("; ")+". No completed result or validated benefit inferred.");
   add(7,r.primary.map(p=>p.measure).join("; "));add(8,r.primary.map(p=>p.timeFrame??"").join("; "));
   if(r.design.allocation)add(9,"Registered allocation: "+r.design.allocation);
   if(r.design.maskingInfo)add(10,"Registered masking: "+JSON.stringify(r.design.maskingInfo));
   add(11,"Registered arms: "+r.arms.map(a=>a.label+" ("+a.type+")").join("; ")+". Absence of a coded control is not a failure.");
   if(r.enrollment)add(12,"Enrollment "+r.enrollment.count+" ("+r.enrollment.type+")");
   if(r.secondary.length)add(17,"Registered secondary outcomes: "+r.secondary.map(p=>p.measure).join("; ")+". No future result inferred.");
   add(25,"Registry status "+r.status+"; retrieved "+r.retrievedAt+". Program activity is separate.");
   add(27,r.interventions.some(i=>/placebo/i.test(i.name))?"Placebo explicitly named in registered interventions.":"No explicit placebo name in intervention list; an active comparator may exist. No scientific failure inferred.");
   const mechanism=r.briefSummary?.match(/.{0,80}(?:agonist|antagonist|inhibit|antisense|mechanism).{0,220}/i);
   if(mechanism)add(4,mechanism[0]+". Registered mechanistic rationale is not proof of clinical target validation.");
  }
  const normalize=(s:string)=>s.toLowerCase().replace(/[^a-z0-9]/g,"");
  const oldPrior=priorData.records.find(p=>p.nctId===row.nctId) as unknown as {priorPhase2?:{matches?:{nctId:string;conditions?:string[];interventions?:{name:string;aliases?:string[]}[];hasResults:boolean;sourceUpdated:string;registeredResults?:{primary?:unknown[];seriousEventCount?:number}}[]}}|undefined;
  const priors=registryVerified&&"interventions" in r?(oldPrior?.priorPhase2?.matches??[]).filter(p=>p.hasResults&&p.registeredResults&&p.nctId!==row.nctId&&p.conditions?.some(c=>r.indications.some(d=>normalize(c)===normalize(d)))&&p.interventions?.some(i=>[i.name,...i.aliases??[]].some(n=>r.interventions.some(x=>normalize(x.name)===normalize(n))))):[];
  for(const p of priors){
   const text="Earlier exact-drug/indication study "+p.nctId+": "+JSON.stringify(p.registeredResults).slice(0,1300)+". These are prior-study findings, not current TOP trial results or a success prediction.";
   for(const question of [1,2,3,16])sourceFacts.push({question,evidence:text,sourceUrl:"https://clinicaltrials.gov/study/"+p.nctId});
  }
  for(const f of manualFacts)sourceFacts.unshift({question:f.question,evidence:f.evidence,sourceUrl:f.sourceUrl});
  const questionStates:Array<{number:number;state:State;reason:string;sourceUrl:string|null;score:number|null}>=[];
  const values=[...original];
  const published=publications.records.find(p=>p.nctId===row.nctId);
  if(registryVerified&&"interventions" in r&&empty(values[11]))values[11]=r.interventions.filter(i=>!/placebo/i.test(i.name)).map(i=>i.name).join("; ");
  for(let i=0;i<30;i++){
   const offset=40+i*5,status=original[offset],evidence=original[offset+3],url=original[offset+4],fact=sourceFacts.find(f=>f.question===i+1&&f.evidence.trim());
   const documented=/SOURCE_FACT|OBSERVED_|DOCUMENTED_/.test(status)&&validSource(url);
   const publishedFact=published&&[1,3,20,29].includes(i+1)?{evidence:i+1===3?published.safety??published.rationale:published.rationale+" Historical reported findings only; TOP membership retained and no prospective prediction created.",sourceUrl:published.url}:null;
   let state:State=documented?"VERIFIED":"MISSING EXPECTED";
   let reason=documented?evidence:"Expected input not found in reviewed sources; not proof of public nonavailability or clinical failure.";
   if(!documented&&(publishedFact||fact)){const found=publishedFact??fact!;state="VERIFIED";reason=found.evidence;values[offset]="DOCUMENTED_SOURCE_FACT";values[offset+3]=found.evidence;values[offset+4]=found.sourceUrl;}
   else if(!documented&&[18,19].includes(i+1)){state="UNVERIFIED";reason="Instrument/subgroup applicability and matched evidence require review; no numerical benefit inferred.";}
   else if(!documented&&[21,22,23,24,29].includes(i+1)&&!hasPublicReadout){state="PENDING";reason="Current-study final outcome tables or follow-up are not yet required in this TOP pre-data view; prior evidence is researched separately.";}
   else if(!documented&&i+1===30){state="NOT YET EXPECTED";reason="Later application/decision readiness is not required merely because the trial is Phase3.";}
   const number=original[offset+2].trim();const score=number!==""&&Number.isFinite(Number(number))?Number(number):null;
   questionStates.push({number:i+1,state,reason,sourceUrl:documented?url:publishedFact?.sourceUrl??fact?.sourceUrl??null,score});
  }
  // Source facts do not become numerical question scores. Existing nonblank
  // values and historical forecasts are preserved verbatim in their columns.
  const records=[...grades.records,...supplement.records].filter(g=>g.nctId===row.nctId&&g.ticker===row.ticker&&g.stage==="pre");
  const programs=[...new Map(records.map(g=>[JSON.stringify([g.drug,g.indication]),g])).values()];
  const program=programs.length===1?programs[0]:null;
  const clinical=clinicalFiveForTrial({nctId:row.nctId,ticker:row.ticker,...(program?{drug:program.drug,indication:program.indication}:{drug:row.drug??row.registeredInterventions,indication:row.indication})},"pre",registryVerified);
  const reviewed=program?fullReviewedTrialCandidate({nctId:row.nctId,ticker:row.ticker,drug:program.drug,indication:program.indication},"pre",registryVerified):null;
  const reviewedByMetric=new Map(reviewed?.grades.map(g=>[g.metricId,g])??[]);
  const metrics=RAAS_METRIC_CATALOG.pre.flatMap(category=>category.metrics.map(m=>{
   const historical=reviewedByMetric.get(m.id);const factor=clinical.factors.find(f=>f.id===m.id);
   const score=factor?.grade??historical?.score??null;
   const active=activeMetricIds.has(m.id);
   return {id:m.id,name:m.name,definition:m.requiredEvidence,scoreRule:m.scoreRule,criticalRisk:m.criticalRisk,category:category.name,originalWeightPercent:category.weight/5,activeClinicalWeightPercent:active?20:0,activeInClinicalModel:active,
    state:score!==null?"VERIFIED_RESEARCH_GRADE":active?"UNSCORED_MISSING_BENCHMARK_REVIEW":"ARCHIVED_METRIC_NOT_IN_ACTIVE_CLINICAL_COMPOSITE",score,
    sourceUrl:factor?.sourceUrl??historical?.sourceUrl??null,sourceDate:factor?.sourceDate??historical?.sourceDate??null,benchmarkSourceUrl:factor?.benchmarkSourceUrl??historical?.benchmarkSourceUrl??null,assessedAt:factor?.assessedAt??historical?.assessedAt??null,
    finding:factor?.finding??historical?.finding??null,confidence:score===null?"NOT_ASSESSABLE":"REVIEWED_INPUTS_NOT_CALIBRATED_PREDICTION",
    blocker:score===null?(active?"Established rubric requires a dated exact-program primary source, benchmark, uncertainty and explicit reviewed grade; source availability alone is insufficient.":"Preserved historical definition; financial/commercial/FDA/investment metrics are excluded by the existing active clinical-five policy. No new historical grade fabricated."):null};
  }));
  const sourceDiscovery={exactNctSearch:searchLog.batches.flatMap(b=>b.queries).find(q=>q.nctId===row.nctId)??null,companySearch:companySearchLog.batches.flatMap(b=>b.queries).find(q=>q.ticker===row.ticker)??null,documents:documents.records.filter(d=>d.candidateTopNcts.includes(row.nctId)).map(d=>({...d,alternateAccess:fallbacks.records.find(f=>f.url===d.url)?.state??null})),caution:"Discovery and HTTP/NCT validation do not establish scientific findings or numerical grades."};
  const phase=registryVerified&&"phases" in r?r.phases.join(" / "):"UNVERIFIED";
  const clinicalFull=clinical.researchScore;
  const legacyFull=reviewed?.fullResearchScore??null;
  const fields=values.map((value,index)=>{
   const question=index>=40?questionStates[Math.floor((index-40)/5)]:null;
   const sub=index>=40?(index-40)%5:null;
   let state:State=empty(value)?"UNVERIFIED":"VERIFIED";
   if(question){state=question.state;if(sub===1||sub===2)state=value.trim()!==""?"VERIFIED":["PENDING","NOT YET EXPECTED","NOT APPLICABLE"].includes(question.state)?question.state:"UNVERIFIED";if(sub===4)state=validSource(value)?"VERIFIED":question.state;}
   const missing=empty(value)||value.trim()==="";
   const sourceUrl=question?.sourceUrl??matrix.sourceUrl;
   const manual=manualFacts.find(f=>f.sourceUrl===sourceUrl&&f.question===question?.number);
   const prior=priors.find(p=>sourceUrl.endsWith(p.nctId));
   const provenance=manual?{url:sourceUrl,date:manual.sourceDate,retrievedAt:manual.retrievedAt,type:manual.evidenceClassification}:sourceUrl===r.sourceUrl?fieldSource:published?.url===sourceUrl?{url:sourceUrl,date:published.date,retrievedAt:r.retrievedAt,type:"REVIEWED_PUBLICATION"}:prior?{url:sourceUrl,date:prior.sourceUpdated,retrievedAt:r.retrievedAt,type:"EARLIER_TRIAL_REGISTRY_NOT_CURRENT_TRIAL_OUTCOME"}:{url:sourceUrl,date:null,retrievedAt:baseline.capturedAt,type:"PRESERVED_EXPORT_ORIGINAL_SOURCE_DATE_NOT_IN_CELL"};
   return {column:index+1,name:matrix.headers[index],value:missing?null:value,exportValue:missing?(sub===1||sub===2?"N/A_UNSCORED":state.replaceAll(" ","_")):value,state,questionNumber:question?.number??null,provenance,existingValuePreserved:original[index]===value,reason:missing?question?.reason??"No verified value in the preserved source matrix; no replacement invented.":question?.reason??"Preserved original nonblank source value."};
  });
  const expected=questionStates.filter(q=>!["PENDING","NOT YET EXPECTED","NOT APPLICABLE"].includes(q.state));
  const missingSource=metrics.some(m=>m.activeInClinicalModel&&m.score===null)||questionStates.some(q=>["MISSING EXPECTED","UNVERIFIED","CONFLICTING"].includes(q.state));
  const blockers=[...new Set(metrics.filter(m=>m.activeInClinicalModel&&m.score===null).map(m=>m.id+": "+m.blocker)),...questionStates.filter(q=>["MISSING EXPECTED","UNVERIFIED"].includes(q.state)).map(q=>"Q"+q.number+": "+q.reason)];
  return {nctId:row.nctId,ticker:row.ticker,company:row.company,drug:row.drug??row.registeredInterventions,indication:row.indication,worksheet:"TOP",membership:"UNCHANGED_FROZEN_TOP",knownPublicResults:hasPublicReadout,additionalReviewedFacts:manualFacts,prospectivePrediction:null,predictionEligibility:"ABSTAIN",predictionReason:"No new FDA prediction: established minimum regulatory evidence and prospective chronology are not demonstrated by a registry fact or a historical readout.",sourceDiscovery,phase,status:registryVerified&&"status" in r?r.status:"UNVERIFIED",registryVerified,source:fieldSource,fields,fieldsAccounted:fields.length,questions:questionStates,metrics,metricsEvaluated:metrics.length,clinicalModel:ACTIVE_RAAS_VERSION,clinicalFactors:clinical.factors,clinicalFullScore:clinicalFull,clinicalScoredFactors:clinical.graded,clinicalMissingFactors:clinical.missing,legacyThirtyMetricFullScore:legacyFull,legacyReviewedMetrics:reviewed?.reviewedCount??0,historicalPartialMean:reviewed?.observedMean??null,sourceCompleteness:expected.length?Math.round(expected.filter(q=>q.state==="VERIFIED").length/expected.length*1000)/10:null,hasMissingSourceEvidence:missingSource,blockers,publicationLeads:refs.map(p=>({pmid:p.pmid,title:p.title,url:p.sourceUrl,publicationDate:p.publicationDate,classification:"RELEVANCE_REQUIRES_EXACT_TRIAL_AND_PHASE_REVIEW_NOT_AUTOMATIC_GRADE"})),historyLinks:{raas:"/raas-history?nctId="+row.nctId,phaseFirst:"/api/phase-first/history?trialId="+row.nctId},assessedAt:asOf,version:TOP_COMPLETION_VERSION};
 });
 return {scope:"EXISTING_TOP_ONLY",asOf,version:TOP_COMPLETION_VERSION,headers:matrix.headers,trialCount:trials.length,fieldsPerTrial:190,companiesSearched:new Set(baseline.records.map(r=>r.ticker)).size,exactNctSearches:searchLog.batches.reduce((n,b)=>n+b.queries.length,0),documentsAttempted:documents.records.length,documentsRetrieved:documents.records.filter(d=>d.state!=="SOURCE_BLOCKED").length,documentsBlocked:documents.records.filter(d=>d.state==="SOURCE_BLOCKED").length,documentsRecoveredViaFallback:fallbacks.records.filter(f=>f.state==="WEB_FALLBACK_RETRIEVED_SOURCE_TEXT_REQUIRES_REVIEW").length,unresolvedDocumentBlocks:fallbacks.records.filter(f=>f.state==="WEB_FALLBACK_BLOCKED").length,allFieldsAccounted:trials.filter(t=>t.fields.length===190&&t.fields.every(f=>f.exportValue!=="")).length,allMetricsEvaluated:trials.filter(t=>t.metrics.length===30).length,completeClinicalOverallScores:trials.filter(t=>t.clinicalFullScore!==null).length,completeThirtyMetricOverallScores:trials.filter(t=>t.legacyThirtyMetricFullScore!==null).length,withMissingSourceEvidence:trials.filter(t=>t.hasMissingSourceEvidence).length,sourceStateCounts:Object.fromEntries(["VERIFIED","MISSING EXPECTED","UNVERIFIED","PENDING","NOT YET EXPECTED","NOT APPLICABLE","CONFLICTING"].map(s=>[s,trials.reduce((sum,t)=>sum+t.questions.filter(q=>q.state===s).length,0)])),trials};
}
export const topOnlySummary=(t:ReturnType<typeof topOnlyReport>["trials"][number])=>({nctId:t.nctId,ticker:t.ticker,company:t.company,drug:t.drug,indication:t.indication,phase:t.phase,status:t.status,fieldsAccounted:t.fieldsAccounted,metricsEvaluated:t.metricsEvaluated,clinicalFullScore:t.clinicalFullScore,clinicalScoredFactors:t.clinicalScoredFactors,legacyThirtyMetricFullScore:t.legacyThirtyMetricFullScore,sourceCompleteness:t.sourceCompleteness,hasMissingSourceEvidence:t.hasMissingSourceEvidence,blockerCount:t.blockers.length});
