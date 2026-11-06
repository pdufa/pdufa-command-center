import discoveryAvenues from "../../../data/phase3DiscoveryAvenues20261106.json";
import agiosEvidence from "../../../data/agiosPhase3Evidence20261106.json";
import ionisEvidence from "../../../data/ionisPhase3Evidence20261106.json";
import {activePhase3Cohorts} from "../../../lib/phase3-active-cohorts";
import {activeOfficialRegistryRecord,activeOfficialRegistryIntegrity} from "../../../lib/phase3-active-official-registry";
import companySearchLog from "../../../data/phase3CompanyWebsiteSearchLog20261106.json";
import {populationGeographyFact,populationGeographyIntegrity,populationGeographyRecords} from "../../../lib/phase3-population-geography";
import {irAssessment,irResearchIntegrity,isObservedStatus,isSourceFactStatus,requiresResearchStatus,investorRelationsCoverage} from "../../../lib/phase3-ir-research";
const ledger=activePhase3Cohorts.snapshot;
import registryCrosswalk from "../../../data/phase3RegistryDrugComparatorCrosswalk20261106.json";
import adjudications from "../../../data/phase3EndpointAdjudications20261105.json";
import investorRelationsEvidence from "../../../data/phase3CompanyWebsiteEvidence20261105.json";
import preData from "../../../data/phase3PreDataBatch20261105.json";
import officialResearch from "../../../data/phase3PreDataOfficialResearch.json";
import {UNIVERSAL_PHASE3_QUESTIONS} from "../../../lib/phase3-universal-questions";
import {phase3QuestionSlots} from "../../../lib/phase3-top-questions";
import {phase3OnlineRecord,phase3OnlineSourceFact,PHASE3_ONLINE_TRIAL_COUNT,PHASE3_ONLINE_SOURCE_DATE} from "../../../lib/phase3-online-source-evidence";

export const dynamic="force-dynamic";

const endpointByNct=new Map(adjudications.records.map(x=>[x.nctId,x] as const));
const agiosFacts=new Map(agiosEvidence.facts.map(f=>[f.nctId+"#"+f.question,f] as const));
const ionisFacts=new Map(ionisEvidence.facts.map(f=>[f.nctId+"#"+f.question,f] as const));
const investorByNct=new Map(investorRelationsEvidence.records.map(x=>[x.nctId,x] as const));
const registryByNct=new Map(registryCrosswalk.records.map(x=>[x.nctId,x] as const));
const preDataByNct=new Map(preData.trials.map(x=>[x.nctId,x] as const));
const officialByNct=new Set(officialResearch.records.map(x=>x.nctId));
type QuestionAudit={number:number;heading:string;predictions:number;observed:number;sourceFacts:number;unscored:number;verifiedFacts:number;numericalAssessments:number;observedOutcomes:number;requiringResearch:number;notPubliclyAvailable:number;requiresInterpretation:number;documentaryInterpretationPending:number};
type TrialAudit={
 nctId:string;ticker:string;classificationCode:string;registryStatus:string;
 missingDrug:boolean;unknownRegistryStatus:boolean;hasDetailedOfficialResearch:boolean;
 hasStoredProtocol:boolean;hasEndpointAdjudication:boolean;
 onlinePrimaryEndpoint:boolean;onlineRegistryResults:boolean;onlineStatisticalAnalyses:boolean;
 pubmedArticleLeads:boolean;secFilingLeads:boolean;
 unverifiedFDAApplication:boolean;unverifiedPDUFADate:boolean;outsideDatedMarketCapScreen:boolean;
 predicted:number;observed:number;sourceFacts:number;unscored:number;questionStatuses:string[];
};
function statusFor(
 q:ReturnType<typeof phase3QuestionSlots>[number],
 r:(typeof ledger.rows)[number],
 e:(typeof adjudications.records)[number]|undefined
){
 if(q.answer)return "PREDICTED_PRE_READOUT";
 if(q.number===1&&e?.endpointOutcome==="PRIMARY_ENDPOINT_MET")return "OBSERVED_PRIMARY_ENDPOINT_MET";
 if(q.number===1&&e?.endpointOutcome==="PRIMARY_ENDPOINT_NOT_MET")return "OBSERVED_PRIMARY_ENDPOINT_NOT_MET";
 if(q.number===1&&e?.endpointOutcome==="NO_BINARY_PASS_FAIL")return "DOCUMENTED_NON_BINARY_ENDPOINT";
 if(q.number===1&&!e&&r.classificationVerified&&r.readoutEvidenceUrl){
  if(r.readoutOutcome==="PRIMARY_ENDPOINT_MET")return "OBSERVED_PRIMARY_ENDPOINT_MET";
  if(r.readoutOutcome==="PRIMARY_ENDPOINT_NOT_MET")return "OBSERVED_PRIMARY_ENDPOINT_NOT_MET";
  if(r.readoutOutcome==="NO_BINARY_PASS_FAIL")return "DOCUMENTED_NON_BINARY_ENDPOINT";
 }
 if(q.number===29&&(e||r.classificationVerified&&r.readoutEvidenceUrl&&r.classificationCode==="P3_POST_DATA_ISSUER"))return "DOCUMENTED_PUBLIC_READOUT";
 const researched=irAssessment(r.nctId,q.number);
 if(researched)return researched.classification;
 if(agiosFacts.has(r.nctId+"#"+q.number))return "SOURCE_FACT_ONLY";
 if(ionisFacts.has(r.nctId+"#"+q.number))return "SOURCE_FACT_ONLY";
 const ir=investorByNct.get(r.nctId);
 if(q.number===30&&ir?.regulatoryEvidenceStatus&&ir.regulatoryEvidenceUrl)return "SOURCE_FACT_ONLY";
 if(ir?.companyUrl){
  if(q.number===3&&ir.safetyEvidence)return "SOURCE_FACT_ONLY";
  if(q.number===17&&/secondary endpoint/i.test(ir.specificEvidence||""))return "SOURCE_FACT_ONLY";
  if(q.number===18&&/patient.reported|\bPRO\b/i.test(ir.specificEvidence||""))return "SOURCE_FACT_ONLY";
  if(q.number===24&&/discontinuation/i.test(ir.safetyEvidence||""))return "SOURCE_FACT_ONLY";
  if(q.number===30&&ir.regulatoryUrl&&/NDA under FDA review.*PDUFA/i.test(ir.regulatory||""))return "SOURCE_FACT_ONLY";
 }
 if(populationGeographyFact(r.nctId,q.number))return "DOCUMENTED_SOURCE_FACT";
 const official=activeOfficialRegistryRecord(r.nctId);
 if(official){
  const qn=q.number;
  if(qn===1&&official.postedPrimaryOutcomeCount>0)return "SOURCE_FACT_ONLY";
  if(qn===3&&official.adverseEventsPosted)return "SOURCE_FACT_ONLY";
  if(qn===6&&official.eligibilityCriteria)return "SOURCE_FACT_ONLY";
  if(qn===7&&official.primaryOutcomes)return "SOURCE_FACT_ONLY";
  if(qn===8&&official.primaryTimeframes)return "SOURCE_FACT_ONLY";
  if(qn===9&&official.allocation)return "SOURCE_FACT_ONLY";
  if(qn===10&&official.masking)return "SOURCE_FACT_ONLY";
  if(qn===11&&official.comparators)return "SOURCE_FACT_ONLY";
  if(qn===12&&official.enrollment!==null)return "SOURCE_FACT_ONLY";
  if([13,14,15].includes(qn)&&official.hasPublicSAP)return "SOURCE_FACT_ONLY";
  if(qn===18&&official.patientReportedOutcomeTitles)return "SOURCE_FACT_ONLY";
  if(qn===19&&official.subgroupOutcomeTitles)return "SOURCE_FACT_ONLY";
  if(qn===22&&official.infectionEventTerms)return "SOURCE_FACT_ONLY";
  if(qn===24&&official.participantFlowDiscontinuations)return "SOURCE_FACT_ONLY";
  if(qn===26&&(official.siteCount>0||official.countries))return "SOURCE_FACT_ONLY";
  if(qn===17&&official.secondaryOutcomeCount>0)return "SOURCE_FACT_ONLY";
  if(qn===23&&official.seriousAdverseEventTerms>0)return "SOURCE_FACT_ONLY";
  if(qn===25&&official.registryStatus)return "SOURCE_FACT_ONLY";
  if(qn===27&&/\bplacebo\b/i.test(official.interventionNames))return "SOURCE_FACT_ONLY";
  if(qn===29&&official.registryResultsPosted)return "SOURCE_FACT_ONLY";
 }
 if(q.observation)return "SOURCE_FACT_ONLY";
 if(q.number===11&&registryByNct.get(r.nctId)?.comparators)return "SOURCE_FACT_ONLY";
 if(q.number===25&&r.registrySourceUrl)return "SOURCE_FACT_ONLY";
 if(q.number===27&&/\bplacebo\b/i.test(r.registeredInterventions||""))return "SOURCE_FACT_ONLY";
 if(phase3OnlineSourceFact(r.nctId,q.number))return "SOURCE_FACT_ONLY";
 return "UNSCORED";
}
const counts=(statuses:string[])=>({
 predicted:statuses.filter(x=>x==="PREDICTED_PRE_READOUT").length,
 observed:statuses.filter(x=>isObservedStatus(x)).length,
 sourceFacts:statuses.filter(x=>isSourceFactStatus(x)).length,
 unscored:statuses.filter(x=>requiresResearchStatus(x)||x==="NOT_PUBLICLY_DISCLOSED").length
});
const escapeCsv=(v:unknown)=>{
 let s=v===null||v===undefined?"":String(v).replace(/[\r\n]+/g," ");
 if(/^[=+@-]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const csv=(v:unknown[])=>v.map(escapeCsv).join(",");
export async function GET(request:Request){
 if(ledger.total!==762||ledger.rows.length!==762||
    new Set(ledger.rows.map(r=>r.nctId)).size!==762||
    UNIVERSAL_PHASE3_QUESTIONS.length!==30||
    preData.trials.length!==253||
    officialResearch.records.length!==253||
    endpointByNct.size!==adjudications.records.length||
    !irResearchIntegrity(new Set(ledger.rows.map(r=>r.nctId)))||
    !populationGeographyIntegrity(new Set(ledger.rows.map(r=>r.nctId)))||
    investorByNct.size!==investorRelationsEvidence.records.length||
    PHASE3_ONLINE_TRIAL_COUNT!==762||
    registryCrosswalk.records.length!==762||registryByNct.size!==762||
    agiosEvidence.trials.length!==9||agiosFacts.size!==agiosEvidence.facts.length||
    ionisEvidence.trials.length!==12||ionisFacts.size!==ionisEvidence.facts.length||
    !activeOfficialRegistryIntegrity(new Set([...activePhase3Cohorts.pre,...activePhase3Cohorts.post].map(r=>r.nctId)))){
   return Response.json({error:"The research snapshot failed a count/identity check"},{status:503});
 }
 const perQuestion:QuestionAudit[]=UNIVERSAL_PHASE3_QUESTIONS.map((q,i)=>({
  number:i+1,heading:q.heading,predictions:0,observed:0,sourceFacts:0,unscored:0,verifiedFacts:0,numericalAssessments:0,observedOutcomes:0,requiringResearch:0,notPubliclyAvailable:0,requiresInterpretation:0,documentaryInterpretationPending:0
 }));
 const rows:TrialAudit[]=[];
 for(const r of ledger.rows){
  const evidence=endpointByNct.get(r.nctId),p=preDataByNct.get(r.nctId);
  const online=phase3OnlineRecord(r.nctId);
  const crosswalk=registryByNct.get(r.nctId);
  const slots=phase3QuestionSlots(r.nctId);
  const statuses=slots.map(q=>statusFor(q,r,evidence));
  if(statuses.length!==30)return Response.json({error:"Question count mismatch"},{status:503});
  const c=counts(statuses);
  for(let i=0;i<30;i++){
   const q=perQuestion[i],st=statuses[i];
   if(st==="PREDICTED_PRE_READOUT")q.predictions++;
   else if(isSourceFactStatus(st))q.sourceFacts++;
   else if(isObservedStatus(st))q.observed++;
   else q.unscored++;
   if(isSourceFactStatus(st)||isObservedStatus(st))q.verifiedFacts++;
   if(st==="PREDICTED_PRE_READOUT")q.numericalAssessments++;
   if(isObservedStatus(st))q.observedOutcomes++;
   if(requiresResearchStatus(st))q.requiringResearch++;
   if(st==="NOT_PUBLICLY_DISCLOSED")q.notPubliclyAvailable++;
   if(st==="REQUIRES_INTERPRETATION")q.requiresInterpretation++;
   // Newly collected design fields document eligibility/sites, not a critical
   // generalizability assessment. Keep that work in the research denominator.
   if(isSourceFactStatus(st)&&!irAssessment(r.nctId,i+1)&&populationGeographyFact(r.nctId,i+1)){
    q.documentaryInterpretationPending++;
    q.requiringResearch++;
   }
  }
  rows.push({
   nctId:r.nctId,ticker:r.ticker,classificationCode:r.classificationCode,
   registryStatus:r.registryStatus,missingDrug:!r.drug&&!crosswalk?.drugInterventions,
   unknownRegistryStatus:!r.registryStatus||r.registryStatus==="UNKNOWN",
   hasDetailedOfficialResearch:officialByNct.has(r.nctId),
   hasStoredProtocol:Boolean(p?.protocol),
   hasEndpointAdjudication:Boolean(evidence),
   onlinePrimaryEndpoint:Boolean(online?.primaryEndpoint),
   onlineRegistryResults:Boolean(online?.resultsPosted),
   onlineStatisticalAnalyses:Boolean(online?.resultsAnalysisCount),
   pubmedArticleLeads:Boolean(online?.pubmedPMIDs.length),
   secFilingLeads:Boolean((online?.secFilingMentions||0)>0),
   unverifiedFDAApplication:r.fdaApplicationStatus==="NOT_VERIFIED"&&!investorByNct.get(r.nctId)?.regulatoryEvidenceStatus,
   unverifiedPDUFADate:!r.pdufaGoalDate&&!investorByNct.get(r.nctId)?.pdufaGoalDate,
   outsideDatedMarketCapScreen:!r.inDatedMarketCapScreen,
   ...c,questionStatuses:statuses
  });
 }
 const total=rows.length*30;
 const assessment={
  totalSlots:total,
  predicted:rows.reduce((a,r)=>a+r.predicted,0),
  observed:rows.reduce((a,r)=>a+r.observed,0),
  sourceFacts:rows.reduce((a,r)=>a+r.sourceFacts,0),
  unscored:rows.reduce((a,r)=>a+r.unscored,0),
  researchPendingIncludingDocumentedDesign:perQuestion.reduce((a,q)=>a+q.requiringResearch,0),
  documentedDesignInterpretationPending:perQuestion.reduce((a,q)=>a+q.documentaryInterpretationPending,0),
  trialsWithNumericalPredictions:rows.filter(r=>r.predicted>0).length,
  trialsWithOutcomeAdjudication:rows.filter(r=>r.hasEndpointAdjudication).length
 };
 const fields={
  missingDrugField:rows.filter(r=>r.missingDrug).length,
  unknownRegistryStatus:rows.filter(r=>r.unknownRegistryStatus).length,
  detailedOfficialResearch:rows.filter(r=>r.hasDetailedOfficialResearch).length,
  missingDetailedOfficialResearch:rows.filter(r=>!r.hasDetailedOfficialResearch).length,
  storedProtocol:rows.filter(r=>r.hasStoredProtocol).length,
  missingStoredProtocol:rows.filter(r=>!r.hasStoredProtocol).length,
  unverifiedFDAApplication:rows.filter(r=>r.unverifiedFDAApplication).length,
  unverifiedPDUFADate:rows.filter(r=>r.unverifiedPDUFADate).length,
  missingAdjudicatedEndpoint:rows.filter(r=>!r.hasEndpointAdjudication).length,
  investorRelationsRegulatoryTrialLinks:rows.filter(r=>Boolean(investorByNct.get(r.nctId)?.regulatoryEvidenceStatus)).length,
  investorRelationsFDAApplicationPrograms:new Set(investorRelationsEvidence.records.filter(r=>Boolean(r.regulatoryProgramId)).map(r=>r.regulatoryProgramId)).size,
  outsideDatedMarketCapScreen:rows.filter(r=>r.outsideDatedMarketCapScreen).length,
  populationGeographyRecords:populationGeographyRecords.length,
  populationEligibilityFacts:rows.filter(r=>populationGeographyFact(r.nctId,6)).length,
  registeredGeographyFacts:rows.filter(r=>populationGeographyFact(r.nctId,26)).length,
  onlineRegistryRecords:PHASE3_ONLINE_TRIAL_COUNT,
  onlinePrimaryEndpointCount:rows.filter(r=>r.onlinePrimaryEndpoint).length,
  registryResultsPosted:rows.filter(r=>r.onlineRegistryResults).length,
  registryStatisticalAnalyses:rows.filter(r=>r.onlineStatisticalAnalyses).length,
  pubmedNctArticleLeads:rows.filter(r=>r.pubmedArticleLeads).length,
  secNctFilingLeads:rows.filter(r=>r.secFilingLeads).length
 };
 const derivedOutcomes=Object.fromEntries(Object.keys(adjudications.counts).map(key=>
  [key,adjudications.records.filter(r=>r.endpointOutcome===key).length]));
 if(assessment.totalSlots!==rows.length*30||
    assessment.predicted+assessment.observed+assessment.sourceFacts+assessment.unscored!==total||
    adjudications.records.some(e=>!rows.some(r=>r.nctId===e.nctId))||
    Object.entries(adjudications.counts).some(([key,value])=>derivedOutcomes[key]!==value)||
    Object.values(derivedOutcomes).reduce((a,b)=>a+b,0)!==adjudications.records.length||
    perQuestion.some(q=>q.predictions+q.observed+q.sourceFacts+q.unscored!==rows.length)){
  return Response.json({error:"Missingness audit reconciliation failed"},{status:503});
 }
 const report={
  asOf:ledger.asOf,officialResearchAsOf:officialResearch.asOf,
  onlineResearchAsOf:PHASE3_ONLINE_SOURCE_DATE,
  registryDrugCrosswalkAsOf:registryCrosswalk.asOf,
  populationGeographyScope:"Registered eligibility and site entries only; scientific interpretation remains pending. Documentary coverage is not completed numerical assessment.",
  scope:"Saved numerical assessments plus the online exact-NCT 762-registry, PubMed and SEC source discovery; publication and filing hits remain research leads, not adjudicated clinical outcomes",
  trials:rows.length,questionsPerTrial:30,columnsInAssessmentExport:190,
  assessment,fields,perQuestion,
  endpointOutcomes:derivedOutcomes,
  investorRelationsCoverage:investorRelationsCoverage(),
  companyWebsiteResearch:{
   ...companySearchLog,
   companiesSearchedThisBatch:companySearchLog.companies.length,
   companiesWithPartialReview:investorRelationsCoverage().filter(c=>c.searchStatus==="PARTIALLY_REVIEWED").length,
   companiesAwaitingWebsiteReview:investorRelationsCoverage().filter(c=>c.searchStatus!=="PARTIALLY_REVIEWED"&&c.searchStatus!=="COMPLETE").length,
   hardToResolveCompanies:companySearchLog.companies.filter(c=>c.requiresUserDirection)
  },
  discoveryAvenues,
  exceptions:{
   unknownRegistryNcts:rows.filter(r=>r.unknownRegistryStatus).map(r=>r.nctId),
   outsideMarketCapScreenNcts:rows.filter(r=>r.outsideDatedMarketCapScreen).map(r=>r.nctId)
  },
  notes:[
   "Unscored means no verified source fact or defensible numerical prediction is stored for that question; it does not prove evidence is absent publicly.",
   "Source-fact columns document available registry facts, not favorable clinical or FDA predictions.",
   "Crosswalk identifies registered DRUG-type interventions in 657 studies; other intervention types such as biologics, devices, or vaccines are not automatically labeled DRUG.",
   "Not every historical or pre-readout Phase 3 trial has an FDA application or PDUFA date.",
   "Application links and distinct programs are counted from records; trial efficacy remains distinct from FDA decisions.",
   "Approval dates are not inferred to be PDUFA goal dates. Historical dates are not upcoming catalysts.",
   "NOT_PUBLICLY_DISCLOSED requires affirmative review evidence; an unreviewed or blocked source remains research pending.",
   "Online registry primary outcome documentation, comparator arms and posted results have been imported as source facts, never as numeric drug-success forecasts."
  ]
 };
 const u=new URL(request.url);
 if(u.searchParams.get("format")==="csv"){
  const base=[
   "NCT","Ticker","Classification","Registry status","Separate drug field missing",
   "Registry status unknown","Detailed official registry saved","Protocol summary saved",
   "Primary endpoint reviewed","FDA application not verified","PDUFA date not verified",
   "Outside dated market cap screen","Numerically predicted questions",
   "Observed endpoint/readout facts","Documented source facts","Unscored questions"
  ];
  const headers=[...base,...UNIVERSAL_PHASE3_QUESTIONS.map((_,i)=>"Q"+String(i+1).padStart(2,"0")+" status")];
  const lines=[csv(headers),...rows.map(r=>csv([
   r.nctId,r.ticker,r.classificationCode,r.registryStatus,r.missingDrug,
   r.unknownRegistryStatus,r.hasDetailedOfficialResearch,r.hasStoredProtocol,
   r.hasEndpointAdjudication,r.unverifiedFDAApplication,r.unverifiedPDUFADate,
   r.outsideDatedMarketCapScreen,r.predicted,r.observed,r.sourceFacts,r.unscored,
   ...r.questionStatuses
  ]))];
  if(lines.length!==763||headers.length!==46)
   return Response.json({error:"CSV row/column count mismatch"},{status:503});
  return new Response("\uFEFF"+lines.join("\r\n")+"\r\n",{
   status:200,headers:{
    "Content-Type":"text/csv; charset=utf-8",
    "Content-Disposition":'attachment; filename="Phase3-762-Trials-Missing-Data-Audit.csv"',
    "Cache-Control":"no-store"
   }
  });
 }
 return Response.json(report,{headers:{"Cache-Control":"no-store"}});
}
