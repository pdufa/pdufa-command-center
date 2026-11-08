import alksRegistry from "../data/alkermesPhaseFirstRegistry20261106.json";
import international from "../data/alkermesInternationalTrials20261106.json";
import censusRegistry from "../data/phaseFirstCensusRegistry20261106.json";
import legacyAlks from "../data/alks34ClinicalScorecard20261106.json";
import census from "../public/phase3-unified-classifications-2026-11-05.json";
import ir from "../data/phase3CompanyWebsiteEvidence20261105.json";
import {clinicalFiveForTrial} from "./raas-clinical-five";
import {raasSpreadsheetSummary} from "./raas-spreadsheet-status";
import {evaluatePhaseFirst,PHASE_FIRST_VERSION,type PhaseTrial,type ClinicalContext} from "./phase-first-clinical";
import {BENEFIT_GROUPS} from "./clinical-source-types";
import {phase3DeepRegistryRecord,PHASE3_DEEP_REGISTRY_AS_OF} from "./phase3-deep-registry-results";
import endpointAdjudications from "../data/phase3EndpointAdjudications20261105.json";
import axsomeRegistry from "../data/axsomePhaseFirstRegistry20261106.json";
import axsomeEvidence from "../data/axsomePhaseFirstEvidence20261106.json";
import sinovacRegistry from "../data/sinovacPhaseFirstRegistry20261106.json";
import sinovacEvidence from "../data/sinovacPhaseFirstEvidence20261106.json";
import agiosEvidence from "../data/agiosPhase3Evidence20261106.json";
import ionisEvidence from "../data/ionisPhase3Evidence20261106.json";
import peerEvidence from "../data/phase3PeerReviewedClinicalEvidence20261106.json";

const AS_OF="2026-11-06";
const oldById=new Map(legacyAlks.records.map(r=>[r.nctId,r]));
const companyById=new Map(census.rows.map(r=>[r.nctId,r]));
const irById=new Map(ir.records.map(r=>[r.nctId,r]));
const endpointById=new Map(endpointAdjudications.records.map(r=>[r.nctId,r]));
const pipelineUrl="https://www.alkermes.com/research-and-development/pipeline";
export const CURRENT_ALKERMES_PROGRAMS=[
 {id:"ALIXOREXTON",name:"Alixorexton / ALKS 2680",phase:"Phase 3 in NT1/NT2; Phase 2 in idiopathic hypersomnia",mechanism:"Selective oral orexin 2 receptor agonist"},
 {id:"OLZ_SAM",name:"Olanzapine / samidorphan",phase:"Phase 3 pediatric schizophrenia/bipolar I",mechanism:"Combination of olanzapine and samidorphan"},
 {id:"SODIUM_OXYBATE_ER",name:"Sodium oxybate ER / FT218 / LUMRYZ",phase:"Phase 3 idiopathic hypersomnia program",mechanism:"Extended-release sodium oxybate"},
 {id:"ALKS_7290",name:"ALKS 7290",phase:"Phase 2 in ADHD and adjunctive MDD",mechanism:"Investigational orexin 2 receptor agonist"},
 {id:"ALKS_4510",name:"ALKS 4510",phase:"Phase 1 healthy-volunteer studies; fatigue program",mechanism:"Investigational orexin 2 receptor agonist"},
 {id:"VALILOXYBATE",name:"Valiloxybate",phase:"Phase 1 healthy-volunteer PK program",mechanism:"Investigational GABA-B receptor agonist"}
].map(p=>({...p,sourceUrl:pipelineUrl,sourceDate:"2026-10",datePrecision:"MONTH",note:"Program phase is not an individual trial's phase. Historical NCTs may concern different indications or sponsors."}));
function currentProgram(drug:string){
 if(/alixorexton|ALKS[ -]?2680/i.test(drug))return CURRENT_ALKERMES_PROGRAMS[0];
 if(/OLZ\/SAM|3831|olanzapine.*samidorphan/i.test(drug))return CURRENT_ALKERMES_PROGRAMS[1];
 if(/FT218|LUMRYZ|sodium oxybate/i.test(drug))return CURRENT_ALKERMES_PROGRAMS[2];
 if(/ALKS[ -]?7290/i.test(drug))return CURRENT_ALKERMES_PROGRAMS[3];
 if(/ALKS[ -]?4510/i.test(drug))return CURRENT_ALKERMES_PROGRAMS[4];
 if(/valiloxybate|XW10172/i.test(drug))return CURRENT_ALKERMES_PROGRAMS[5];
 return null;
}
export function phaseFirstContext(trial:PhaseTrial,alkermes:boolean):ClinicalContext{
 const old=oldById.get(trial.trialId),row=companyById.get(trial.trialId);
 const drug=old?.clinicalProgramDrug||trial.interventions.filter(i=>!/placebo/i.test(i.name)).map(i=>i.name).join("; ")||"Intervention not recorded";
 const indication=old?.clinicalProgramIndication||trial.indications.join("; ")||"Indication not recorded";
 const ticker=alkermes?"ALKS":row?.ticker??"UNKNOWN";
 const program=currentProgram(drug);
 const link=irById.get(trial.trialId);
 const regulatory=link&&"regulatoryEvidenceStatus" in link&&link.regulatoryEvidenceStatus&&"regulatoryEvidenceUrl" in link&&link.regulatoryEvidenceUrl?
  {status:link.regulatoryEvidenceStatus,url:link.regulatoryEvidenceUrl,date:("regulatorySourceDate" in link?link.regulatorySourceDate:null)||link.sourceDate,
   text:("regulatoryEvidence" in link?link.regulatoryEvidence:null)||"Exact-trial regulatory link documented",
   goalDate:("pdufaGoalDate" in link?link.pdufaGoalDate:undefined)}:null;
 const stage=old?.clinicalStage==="post"?"post":old?.clinicalStage==="pre"?"pre":null;
 const isPhase3=trial.phases.includes("PHASE3");
 const stageVerified=!!old?.clinicalStageVerified&&isPhase3;
 const accepted=stage?clinicalFiveForTrial({nctId:trial.nctId??"",ticker,drug,indication},stage,stageVerified):null;
 const approved=trial.nctId?raasSpreadsheetSummary({nctId:trial.nctId,ticker,drug,indication,classifiedStage:stage}).approvedScore:null;
 const safetyPrimary=old?.studyPurpose==="SAFETY_PRIMARY"||
  (trial.primary.length>0&&trial.primary.every(p=>/adverse|safety|tolerab/i.test(p.measure)));
 const additional:NonNullable<ClinicalContext["additionalEvidence"]>={};
 if(program)additional.mechanism={text:program.mechanism+". Mechanistic description is not proof of clinical efficacy.",url:program.sourceUrl,date:program.sourceDate};
 const deep=phase3DeepRegistryRecord(trial.trialId);
 const saved=(text:string)=>({text:text+" Previously saved exact-NCT registry evidence; not a new clinical grade. Date denotes the saved snapshot, not original publication.",url:trial.sourceUrl,date:PHASE3_DEEP_REGISTRY_AS_OF.slice(0,10),dateKind:"STORED_REGISTRY_SNAPSHOT"});
 if(deep?.hasPublicProtocol)additional.protocol=saved("Public protocol attachment documented.");
 if(deep?.hasPublicSAP)additional.sap=saved("Public SAP attachment documented; analysis adequacy is not inferred.");
 if(deep?.adverseEventsPosted)additional.safety=saved("Posted adverse-event tables: "+deep.seriousAdverseEventsByArm);
 if(deep?.participantFlowDiscontinuations)additional.tolerability=saved(deep.participantFlowDiscontinuations);
 if(deep?.postedPrimaryAnalysesCount)additional.uncertainty=saved("Trial-specific primary statistical analyses saved; no numerical strength grade inferred.");
 const endpoint=endpointById.get(trial.trialId);
 if(endpoint&&trial.phases.includes("PHASE3")&&"sourceDate" in endpoint&&endpoint.sourceDate)
  additional.phase3Results={text:endpoint.rationale,url:endpoint.evidenceUrl,date:endpoint.sourceDate};
 if(regulatory?.goalDate)additional.pdufa={text:"Source-reported target: "+regulatory.goalDate+". Historical dates are not upcoming catalysts; this is not a forecast.",url:link&&"pdufaEvidenceUrl" in link&&link.pdufaEvidenceUrl?link.pdufaEvidenceUrl:regulatory.url,date:regulatory.date};
 const vibrance=trial.trialId==="NCT06358950"?{url:"https://alkermes.gcs-web.com/news-releases/news-release-details/lancet-neurology-publishes-data-alkermes-positive-vibrance-1",date:"2026-08-24",text:"Vibrance-1 Phase 2 placebo-controlled study: reported improvements in wakefulness, sleepiness and selected cataplexy comparisons. This trial remains Phase 2; later Brilliance trials are separate."}:
  trial.trialId==="NCT06555783"?{url:"https://investor.alkermes.com/news-releases/news-release-details/alkermes-presents-detailed-positive-results-vibrance-2-phase-2",date:"2026-06-17",text:"Vibrance-2 Phase 2: MWT prespecified significance reported for 14 mg (p=.049) and 18 mg (p=.047). Do not assume every dose met every primary comparison. No new clinical grade is inferred."}:null;
 if(vibrance)additional.proofOfConcept=vibrance;
 const companyEvidence=ticker==="AXSM"?axsomeEvidence:ticker==="SVA"?sinovacEvidence:null;
 if(companyEvidence){
  for(const fact of companyEvidence.records.filter(r=>r.nctId===trial.trialId)){
   const source=companyEvidence.sources.find(s=>s.id===fact.sourceId);
   if(!source)throw Error("PHASE_FIRST_SOURCE_NOT_FOUND");
   additional[fact.assessmentId]={text:fact.evidence,url:source.url,date:source.date,
    confidence:fact.confidence==="MODERATE"||source.url.includes("www.axsome.com")?"MODERATE":"HIGH",
    status:("status" in fact?fact.status:undefined) as import("./phase-first-clinical").EvidenceStatus|undefined};
  }
 }
 // Issuer/registry evidence for nine Agios active trials supplements only factual
 // phase-applicable documentation. It NEVER generates a clinical factor grade.
 if(ticker==="AGIO"){
  const fields:Record<number,string>={3:"safety",9:"design",12:"enrollment",
   17:"secondary",24:"tolerability",27:"comparator"};
  for(const fact of agiosEvidence.facts){
   if(fact.nctId!==trial.trialId)continue;
   const key=fields[fact.question];
   if(!key||additional[key])continue;
   additional[key]={text:fact.evidence+" Source fact, not a reviewed clinical grade.",
    url:fact.sourceUrl,date:fact.sourceDate,confidence:"HIGH"};
  }
 }
 // Additional dated Ionis source observations improve evidence coverage only.
 // No numerical factor grade, predicted efficacy or FDA probability is generated.
 if(ticker==="IONS"){
  const fields:Record<number,string>={3:"safety",7:"primary",9:"design",12:"enrollment",
   17:"secondary",24:"tolerability",27:"comparator",29:"phase3Results",30:"fdaOutcome"};
  for(const fact of ionisEvidence.facts){
   if(fact.nctId!==trial.trialId)continue;
   const key=fields[fact.question];
   if(!key||additional[key])continue;
   additional[key]={text:fact.evidence+" Descriptive exact-trial source evidence, not a reviewed grade.",
    url:fact.sourceUrl,date:fact.sourceDate,
    confidence:/^(https:\/\/www\.fda\.gov|https:\/\/ir\.ionis)/.test(fact.sourceUrl)?"HIGH":"MODERATE"};
  }
 }
 // Exact-NCT peer-reviewed/FDA outcomes are added to documentation requirements
 // only. They never produce reviewed factor grades or approved RAAS probabilities.
 for(const fact of peerEvidence.facts){
  if(fact.nctId!==trial.trialId)continue;
  const requirement=fact.question===20?"benefitRisk":
   fact.question===21?"phase3Results":
   fact.question===23?"safety":
   fact.question===24?"tolerability":
   fact.question===28?"fdaOutcome":null;
  if(!requirement||additional[requirement])continue;
  additional[requirement]={text:fact.evidence+
   " Historical observed evidence only, not a numerical clinical or FDA prediction.",
   url:fact.sourceUrl,date:fact.sourceDate,
   confidence:fact.sourceUrl.includes("fda.gov")?"HIGH":"MODERATE"};
 }
 return {ticker,drug,indication,programId:program?.id??"REGISTRY_INTERVENTION:"+drug.toLowerCase(),
  pipelineRestriction:ticker==="SVA"?sinovacEvidence.eligibilityNote:null,
  pipelineRestrictionSource:ticker==="SVA"?sinovacEvidence.eligibilitySourceUrl:null,
  programPhase:program?.phase??null,programSourceUrl:program?.sourceUrl??null,
  legacyStage:stage,stageVerified,safetyPrimary,
  notApplicableFactors:old?.notApplicableClinicalFactors??(safetyPrimary?["efficacy","clinicalBenefit","statistics","reproducibility"]:[]),
  reviewedFactors:accepted?.factors??[],approvedRaas:approved,regulatory,
  additionalEvidence:additional};
}
const surveySections=[{key:"A",name:"Medical Impact",min:1,max:5},{key:"B",name:"Competitive Strength",min:6,max:8},
 {key:"C",name:"Market Opportunity",min:9,max:14},{key:"D",name:"Revenue Value",min:15,max:18},
 {key:"E",name:"Investment Potential",min:19,max:20}];
// Existing three-level survey identifiers remain unchanged; this overlay does
// not replace their stored responses or silently turn documentation into grades.
export const PHASE_FIRST_SURVEY_HIERARCHY=surveySections.map(g=>({...g,surveys:BENEFIT_GROUPS.filter(s=>s.number>=g.min&&s.number<=g.max).map(s=>({number:s.number,name:s.name,questions:s.fields.map(f=>({id:f.id,label:f.label}))}))}));
export type PhaseFirstScope="alkermes"|"axsome"|"sinovac"|"census";
const caches:Partial<Record<PhaseFirstScope,ReturnType<typeof build>>>={};
function build(scope:PhaseFirstScope){
 const freshById=new Map([...axsomeRegistry.records,...sinovacRegistry.records].map(t=>[t.trialId,t]));
 const raw=(scope==="alkermes"?[...alksRegistry.records,...international.records]:scope==="axsome"?axsomeRegistry.records:scope==="sinovac"?sinovacRegistry.records:
  censusRegistry.records.map(t=>freshById.get(t.trialId)??t)) as unknown as PhaseTrial[];
 if(new Set(raw.map(r=>r.trialId)).size!==raw.length)throw Error("PHASE_FIRST_DUPLICATE_TRIAL");
 const trials=raw.map(t=>evaluatePhaseFirst(t,phaseFirstContext(t,scope==="alkermes"),AS_OF));
 const byPhase:Record<string,number>={},evidenceCounts:Record<string,number>={};
 for(const t of trials){byPhase[t.phase.label]=(byPhase[t.phase.label]??0)+1;
  for(const [s,count] of Object.entries(t.evidenceCounts))evidenceCounts[s]=(evidenceCounts[s]??0)+count;}
 return {modelVersion:PHASE_FIRST_VERSION,asOf:AS_OF,scope,trialCount:trials.length,
  sourceScope:scope==="alkermes"?"Alkermes sponsor/collaborator search plus verified current compound/Avadel aliases; associations do not establish current ownership.":scope==="axsome"?"Axsome: all 28 exact-NCT records in the existing census, not an exhaustive historical/acquired-program census.":scope==="sinovac"?sinovacEvidence.scope:"Existing exact-NCT 762-trial research census; analysis never admits a row to restricted Pipeline.",
  companyResearch:scope==="axsome"?{company:axsomeEvidence.company,documentsReviewed:axsomeEvidence.sources.length,factsRecorded:axsomeEvidence.records.length,blockers:axsomeEvidence.blockers,eligibilityNote:null,eligibilitySourceUrl:null}:scope==="sinovac"?{company:sinovacEvidence.company,documentsReviewed:sinovacEvidence.sources.length,factsRecorded:sinovacEvidence.records.length,blockers:sinovacEvidence.blockers,eligibilityNote:sinovacEvidence.eligibilityNote,eligibilitySourceUrl:sinovacEvidence.eligibilitySourceUrl}:null,
  currentAlkermesPrograms:scope==="alkermes"?CURRENT_ALKERMES_PROGRAMS:[],
  legacyAlkermesTrials:legacyAlks.records.length,byPhase,evidenceCounts,
  ratedTrials:trials.filter(t=>t.overallRating!==null).length,
  fullyCoveredRatings:trials.filter(t=>t.ratingCoverage.eligible>0&&t.ratingCoverage.scored===t.ratingCoverage.eligible).length,
  scoredComponents:trials.reduce((s,t)=>s+t.ratingCoverage.scored,0),
  fdaPredictions:trials.filter(t=>t.fdaPrediction.probabilities!==null).length,
  surveyHierarchy:PHASE_FIRST_SURVEY_HIERARCHY,
  notes:["Clinical research rating, evidence completeness, regulatory readiness and calibrated FDA probability are distinct.",
   "Partial means normalize existing 20% factor weights only over eligible scored components. They are not complete five-factor scores or cross-phase ranks.",
   "Missing and conflicting evidence are research gaps; pending and not-yet-expected milestones are excluded from evidence completeness.",
   "Current phase is source-verified per registry snapshot, not inferred from the program's most advanced phase. Original source dates and staleness remain visible.",
   "Existing clinical grades/history, survey responses, RAAS calibration and Pipeline eligibility are read-only. No GEM/GEM JR model is activated."],trials};
}
export function phaseFirstReport(scope:PhaseFirstScope="alkermes"){
 return caches[scope]??(caches[scope]=build(scope));
}
