/** BOTTOM-only 23-trial evidence accounting and five-factor post-readout grades.
 * Frozen post-readout membership; zero writes to TOP, shared grade/history, or Pipeline.
 * Sourced facts do not themselves imply numeric grades. Null is never zero.
 */
import baseline from "../data/bottomOnlyBaseline20261107.json";
import matrix from "../data/bottomOnly190Baseline20261107.json";
import reviewedFacts from "../data/bottomOnlyReviewedFacts20261107.json";
import gradeIncrement from "../data/bottomOnlyReviewedGradeIncrement20261107.json";
import endpointAdjudications from "../data/phase3EndpointAdjudications20261105.json";
import originalGrades from "../data/raas-reviewed-metric-assessments.json";
import supplement from "../data/raas-clinical-five-reviewed-increment.json";
import {RAAS_METRIC_CATALOG} from "./raas-metric-specs";
import {clinicalFiveDefinitions,ACTIVE_RAAS_VERSION} from "./raas-clinical-five";
import {fullReviewedTrialCandidate,parseReviewedMetricFeed} from "./raas-reviewed-full-score";
export const BOTTOM_ONLY_VERSION="BOTTOM_ONLY_POST_READOUT_20261107_V1";
const asOf="2026-11-07";
const activeIds=new Set(["post-1-1","post-1-2","post-1-3","post-1-4","post-1-5"]);
/** Source questions relevant to each of the five approved post-data clinical factors. */
const factorQuestions:Readonly<Record<string,readonly number[]>>={
 "post-1-1":[1,7,8,20,21,29],
 "post-1-2":[2,6,17,18,20],
 "post-1-3":[1,9,10,12,13,14,15,19],
 "post-1-4":[4,16,20,24,29],
 "post-1-5":[3,24,27]
};
const matrixByNct=new Map(matrix.rows.map(r=>[r[0],r]));
const endpointByNct=new Map(endpointAdjudications.records.map(r=>[r.nctId,r]));
const allReviews=[...originalGrades.records,...supplement.records,...gradeIncrement.records];
const feed=parseReviewedMetricFeed({schemaVersion:1,scope:"RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY",sourceAsOf:asOf,records:allReviews});
const isUrl=(s:string|null|undefined):s is string=>typeof s==="string"&&/^https:\/\/[^ ]+/.test(s);
const missing=(s:string|null|undefined)=>s===null||s===undefined||!s.trim()||
 /^(?:NOT_VERIFIED|UNKNOWN|UNSCORED|NOT_YET_REVIEWED|REQUIRES_INTERPRETATION|NOT_INDEPENDENTLY_REVIEWED|UNDETERMINED|N\/A)$/i.test(s.trim());
const tagQuestion=(raw:string,hasSource:boolean,hasAdded:boolean)=>{
 if(hasAdded)return "VERIFIED_ADDITIONAL_SOURCE_FACT";
 if(!hasSource)return "MISSING_SOURCE_REVIEW";
 if(raw.startsWith("OBSERVED_")||raw==="DOCUMENTED_NON_BINARY_ENDPOINT")return "OBSERVED_PHASE3_ENDPOINT";
 if(raw==="DOCUMENTED_PUBLIC_READOUT")return "PUBLIC_READOUT_DOCUMENTED";
 if(raw==="PREDICTED_PRE_READOUT")return "HISTORICAL_PREDICTION_NOT_POSTDATA_GRADE";
 return "SOURCED_UNGRADED_FACT";
};
export function bottomOnlyReport(){
 const ids=new Set(baseline.records.map(r=>r.nctId));
 if(ids.size!==23||matrix.headers.length!==190||matrix.rows.length!==ids.size||
  matrix.rows.some(r=>r.length!==190||!ids.has(r[0]))||
  baseline.records.some(r=>r.cohort!=="POST_DATA")||
  reviewedFacts.records.some(r=>!ids.has(r.nctId)||r.question<1||r.question>30||!isUrl(r.sourceUrl))||
  gradeIncrement.records.some(r=>!ids.has(r.nctId)||r.stage!=="post"))
  throw Error("BOTTOM_ONLY_IDENTITY_OR_190_INTEGRITY");
 const trials=baseline.records.map(row=>{
  const original=matrixByNct.get(row.nctId);
  if(!original)throw Error("BOTTOM_NCT_MISSING_MATRIX:"+row.nctId);
  const savedEndpoint=endpointByNct.get(row.nctId);
  const observedOutcome=row.readoutOutcome!=="NOT_INDEPENDENTLY_REVIEWED"&&row.readoutOutcome!=="UNDETERMINED"?row.readoutOutcome:(savedEndpoint?.endpointOutcome??row.readoutOutcome);
  const readoutUrl=savedEndpoint?.evidenceUrl??row.readoutEvidenceUrl;
  const trialFacts=reviewedFacts.records.filter(f=>f.nctId===row.nctId);
  const seenFacts=new Set<string>();
  if(trialFacts.some(f=>{const key=f.question+"|"+f.sourceUrl;const duplicate=seenFacts.has(key);seenFacts.add(key);return duplicate;}))
   throw Error("BOTTOM_REPEATED_SOURCE_FACT:"+row.nctId);
  const reviewedProgram=allReviews.filter(r=>r.nctId===row.nctId&&r.ticker===row.ticker&&r.stage==="post");
  const programs=new Map(reviewedProgram.map(r=>[JSON.stringify([r.drug.trim().toLowerCase(),r.indication.trim().toLowerCase()]),r]));
  const program=programs.size===1?[...programs.values()][0]:null;
  const graded=program?fullReviewedTrialCandidate({nctId:row.nctId,ticker:row.ticker,drug:program.drug,indication:program.indication},"post",true,feed):null;
  const byMetric=new Map(graded?.grades.map(g=>[g.metricId,g])??[]);
  const scoreSource=graded?allReviews.filter(g=>g.nctId===row.nctId&&g.ticker===row.ticker&&g.stage==="post"&&g.drug.toLowerCase()===program!.drug.toLowerCase()&&g.indication.toLowerCase()===program!.indication.toLowerCase()):[];
  const rawByMetric=new Map(scoreSource.map(g=>[g.metricId,g]));
  const factors=clinicalFiveDefinitions("post").map(m=>{
   const grade=byMetric.get(m.id),source=rawByMetric.get(m.id);
   const related=new Set(factorQuestions[m.id]??[]);
   const addedEvidence=trialFacts.filter(f=>related.has(f.question)).map(f=>({
    question:f.question,sourceUrl:f.sourceUrl,sourceDate:f.sourceDate,
    evidence:f.evidence,classification:f.classification,
    criticalLimit:f.criticalLimit,assessmentStatus:"DOCUMENTED_SOURCE_ONLY_NOT_A_NUMERICAL_GRADE"
   }));
   const originalEvidence=[...related].flatMap(question=>{
    const offset=40+(question-1)*5,status=original[offset],evidence=original[offset+3],url=original[offset+4];
    if(status==="UNSCORED"||status==="PREDICTED_PRE_READOUT"||!isUrl(url)||missing(evidence))return [];
    return [{question,sourceUrl:url.split(" | ")[0],sourceDate:row.readoutSourceDate??null,
     evidence:evidence.slice(0,1500),classification:status,
     criticalLimit:"Saved source statement only; matched benchmark, uncertainty and analytical limitations require separate review.",
     assessmentStatus:"PRESERVED_SOURCED_FACT_NOT_A_NUMERICAL_GRADE"}];
   });
   const evidencePack=[...addedEvidence,...originalEvidence];
   const ratingReadiness=grade?"NUMERICAL_RESEARCH_GRADE_PRESENT":
    evidencePack.length?"EVIDENCE_FOUND_SCIENTIFIC_GRADING_REQUIRED":"SOURCE_DISCOVERY_OR_DISCLOSURE_REQUIRED";
   return {...m,reviewEvidence:evidencePack,reviewEvidenceCount:evidencePack.length,ratingReadiness,
    grade:grade?.score??null,finding:grade?.finding??null,
    sourceUrl:grade?.sourceUrl??null,benchmarkSourceUrl:grade?.benchmarkSourceUrl??null,
    sourceDate:grade?.sourceDate??null,assessedAt:grade?.assessedAt??null,
    observedResult:source?.observedResult??null,benchmarkContext:source?.benchmarkContext??null,
    uncertaintyReview:source?.uncertaintyReview??null,criticalRiskReview:source?.criticalRiskReview??null,
    evidenceState:grade?"SOURCE_REVIEWED_PROVISIONAL_GRADE":"MISSING_RUBRIC_READY_EVIDENCE"};
  });
  const clinicalScoredFactors=factors.filter(f=>f.grade!==null).length;
  const clinicalFullScore=clinicalScoredFactors===5?
   Math.round(factors.reduce((acc,f)=>acc+(f.grade??0),0)/5*10)/10:null;
  const metrics=RAAS_METRIC_CATALOG.post.flatMap(category=>category.metrics.map(m=>{
   const grade=byMetric.get(m.id),raw=rawByMetric.get(m.id),active=activeIds.has(m.id);
   return {id:m.id,name:m.name,definition:m.requiredEvidence,scoreRule:m.scoreRule,criticalRisk:m.criticalRisk,
    category:category.name,originalWeightPercent:category.weight/5,activeClinicalWeightPercent:active?20:0,
    activeInClinicalModel:active,score:grade?.score??null,finding:grade?.finding??null,
    sourceUrl:grade?.sourceUrl??null,benchmarkSourceUrl:grade?.benchmarkSourceUrl??null,
    sourceDate:grade?.sourceDate??null,assessedAt:grade?.assessedAt??null,
    observedResult:raw?.observedResult??null,benchmarkContext:raw?.benchmarkContext??null,
    uncertaintyReview:raw?.uncertaintyReview??null,criticalRiskReview:raw?.criticalRiskReview??null,
    state:grade?"SOURCE_REVIEWED_PROVISIONAL_GRADE":active?"UNSCORED_EVIDENCE_REVIEW_REQUIRED":"ARCHIVED_NOT_ACTIVE",
    blocker:grade?null:active?"Requires dated exact-program observed results, a relevant benchmark, uncertainty and an explicit rubric grade; readout existence or positive p-value is not sufficient.":"Not active in the approved five-factor clinical model."};
  }));
  const values=[...original];
  const questions=Array.from({length:30},(_,i)=>{
   const offset=40+5*i,originalStatus=original[offset],sourceUrl=original[offset+4];
   const added=trialFacts.find(f=>f.question===i+1);
   const fromSaved=isUrl(sourceUrl)&&originalStatus!=="UNSCORED";
   const state=tagQuestion(originalStatus,fromSaved,Boolean(added));
   if(added&&!fromSaved){values[offset]=added.classification;if(!original[offset+3].trim())values[offset+3]=added.evidence+" | Limit: "+added.criticalLimit;if(!original[offset+4].trim())values[offset+4]=added.sourceUrl;}
   return {number:i+1,state,originalStatus,
    explanation:added?.evidence??original[offset+3]??"",
    criticalLimit:added?.criticalLimit??null,
    sourceUrl:added?.sourceUrl??(isUrl(sourceUrl)?sourceUrl:null),
    sourceDate:added?.sourceDate??null,
    isScored:!missing(original[offset+2])&&Number.isFinite(Number(original[offset+2])),
    requiresFurtherReview:state==="MISSING_SOURCE_REVIEW"||
      state==="HISTORICAL_PREDICTION_NOT_POSTDATA_GRADE"};
  });
  const fields=values.map((value,index)=>{
   const questionIndex=index>=40?Math.floor((index-40)/5):null;
   const q=questionIndex===null?null:questions[questionIndex];
   const sub=index>=40?(index-40)%5:null;
   const absent=missing(value);
   const sourceUrl=q?.sourceUrl??(index===17||index===8||index===9||index===10||index===20||index===21?
    readoutUrl:row.registrySourceUrl);
   const available=typeof sourceUrl==="string"&&isUrl(sourceUrl);
   let state=absent?"MISSING_OR_UNSCORED":q?.state??"PRESERVED_FIELD";
   if(sub===1||sub===2)state=absent?"UNSCORED_OR_NOT_APPLICABLE":"PRESERVED_HISTORICAL_PREDICTION";
   if(sub===4)state=isUrl(value)?"SOURCE_URL_PRESENT":"SOURCE_URL_MISSING";
   return {column:index+1,name:matrix.headers[index],value:absent?null:value,
    exportValue:absent?(value.trim()?value:(sub===1||sub===2?"N/A_UNSCORED":"MISSING_OR_UNDISCLOSED")):value,
    state,sourceUrl:available?sourceUrl:null,sourceDate:q?.sourceDate??row.readoutSourceDate??null,
    sourceScope:q?"EXACT_NCT_QUESTION_SOURCE_OR_REVIEW":"PRESERVED_ORIGINAL_COHORT_CLASSIFICATION",
    evidenceVerified:!!q&&["OBSERVED_PHASE3_ENDPOINT","PUBLIC_READOUT_DOCUMENTED","SOURCED_UNGRADED_FACT","VERIFIED_ADDITIONAL_SOURCE_FACT"].includes(q.state),
    note:absent?"Value absent from dated original source or no numeric grade; no imputation.":q?.criticalLimit??"Original source text retained; provenance is recorded separately."};
  });
  const blockers=[
   ...factors.filter(f=>f.grade===null).map(f=>f.id+": "+f.name+" requires "+f.requiredEvidence),
   ...questions.filter(q=>q.state==="MISSING_SOURCE_REVIEW").map(q=>"Q"+q.number+": missing reviewed exact-NCT source fact (may be not yet disclosed).")
  ];
  const observedOutcomes=new Set(["PRIMARY_ENDPOINT_MET","PRIMARY_ENDPOINT_NOT_MET","MIXED_COPRIMARY_RESULTS","NO_BINARY_PASS_FAIL"]);
  const publicReadoutVerified=isUrl(readoutUrl)&&
    (observedOutcomes.has(observedOutcome)||row.evidenceBasis==="REGISTRY_RESULTS_POSTED"||row.evidenceBasis==="ISSUER_READOUT"||row.evidenceBasis==="FDA_APPROVAL_SUPPORTING_TRIAL"||row.evidenceBasis==="PEER_REVIEWED_RESULTS");
  return {nctId:row.nctId,ticker:row.ticker,company:row.company,drug:row.drug??row.registeredInterventions,
   indication:row.indication,status:row.registryStatus,cohort:"BOTTOM",phase:"PHASE3",classification:row.classificationCode,
   readoutOutcome:observedOutcome,readoutSourceDate:row.readoutSourceDate,readoutEvidenceUrl:readoutUrl,
   readoutEvidenceBasis:row.evidenceBasis,readoutVerified:publicReadoutVerified,
   endpointRationale:savedEndpoint?.rationale??null,endpointSourceType:savedEndpoint?.evidenceType??row.evidenceBasis,
   fields,fieldsAccounted:fields.length,questions,metrics,metricsEvaluated:metrics.length,
   clinicalFactors:factors,clinicalScoredFactors,clinicalFullScore,clinicalModel:ACTIVE_RAAS_VERSION,
   legacyThirtyMetricFullScore:graded?.fullResearchScore??null,
   additionalReviewedFacts:trialFacts,
   sourceBackedQuestions:questions.filter(q=>!q.requiresFurtherReview).length,
   evidenceCompletenessPercent:Math.round(questions.filter(q=>!q.requiresFurtherReview).length/30*1000)/10,
   blockers,sourceGaps:questions.filter(q=>q.requiresFurtherReview).length,
   programIdentityStatus:program?"UNAMBIGUOUS_EXACT_REVIEW_PROGRAM":programs.size?"AMBIGUOUS_PROGRAM":"NO_NUMERICAL_REVIEW_YET",
   historyLinks:{raas:"/raas-history?nctId="+row.nctId,phaseFirst:"/api/phase-first/history?trialId="+row.nctId},
   scoreIsCalibratedFdaProbability:false,asOf,version:BOTTOM_ONLY_VERSION};
 });
 const allMetricsEvaluated=trials.filter(t=>t.metrics.length===30).length;
 return {scope:"EXISTING_BOTTOM_ONLY",asOf,version:BOTTOM_ONLY_VERSION,
  trialCount:trials.length,fieldsPerTrial:matrix.headers.length,headers:matrix.headers,
  allFieldsAccounted:trials.filter(t=>t.fields.length===190&&t.fields.every(f=>f.exportValue!=="")).length,
  allMetricsEvaluated,completeClinicalOverallScores:trials.filter(t=>t.clinicalFullScore!==null).length,
  completeThirtyMetricOverallScores:trials.filter(t=>t.legacyThirtyMetricFullScore!==null).length,
  activeFactorCount:trials.length*5,activeFactorsScored:trials.reduce((n,t)=>n+t.clinicalScoredFactors,0),
  observedReadouts:trials.filter(t=>t.readoutVerified).length,
  sourceBackedQuestionCount:trials.reduce((n,t)=>n+t.sourceBackedQuestions,0),
  totalQuestionCount:trials.length*30,
  unresolvedQuestionCount:trials.reduce((n,t)=>n+t.sourceGaps,0),
  additionalSourceFacts:reviewedFacts.records.length,
  additionalProvisionalGrades:gradeIncrement.records.length,trials};
}
export const bottomOnlySummary=(t:ReturnType<typeof bottomOnlyReport>["trials"][number])=>({
 nctId:t.nctId,ticker:t.ticker,company:t.company,drug:t.drug,indication:t.indication,
 status:t.status,readoutOutcome:t.readoutOutcome,readoutSourceDate:t.readoutSourceDate,
 readoutEvidenceBasis:t.readoutEvidenceBasis,fieldsAccounted:t.fieldsAccounted,
 metricsEvaluated:t.metricsEvaluated,clinicalFullScore:t.clinicalFullScore,
 clinicalScoredFactors:t.clinicalScoredFactors,legacyThirtyMetricFullScore:t.legacyThirtyMetricFullScore,
 evidenceCompletenessPercent:t.evidenceCompletenessPercent,sourceGaps:t.sourceGaps,readoutVerified:t.readoutVerified});
