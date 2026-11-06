import {populationGeographyFact,populationGeographyIntegrity,populationGeographyRecords} from "../../../lib/phase3-population-geography";
import {irAssessment,irResearchIntegrity,requiresResearchStatus} from "../../../lib/phase3-ir-research";
import {activePhase3Cohorts,IONIS_VERIFIED_READOUTS} from "../../../lib/phase3-active-cohorts";
import agiosEvidence from "../../../data/agiosPhase3Evidence20261106.json";
import ionisEvidence from "../../../data/ionisPhase3Evidence20261106.json";
import {loadLivePhase3Registry} from "../phase3-live-registry-backfill/route";
import registryCrosswalk from "../../../data/phase3RegistryDrugComparatorCrosswalk20261106.json";
import endpointAdjudications from "../../../data/phase3EndpointAdjudications20261105.json";
import investorRelationsEvidence from "../../../data/phase3CompanyWebsiteEvidence20261105.json";
import {UNIVERSAL_PHASE3_QUESTIONS} from "../../../lib/phase3-universal-questions";
import {phase3QuestionSlots} from "../../../lib/phase3-top-questions";
import {PHASE3_ONLINE_TRIAL_COUNT,phase3OnlineRecord,phase3OnlineSourceFact,phase3OnlineCoverageLabel,phase3OnlineReviewLeads} from "../../../lib/phase3-online-source-evidence";

export const dynamic = "force-dynamic";
export const maxDuration = 60;
const ledger=activePhase3Cohorts.snapshot;
const agiosFacts=new Map(agiosEvidence.facts.map(f=>[f.nctId+"#"+f.question,f] as const));
const ionisFacts=new Map(ionisEvidence.facts.map(f=>[f.nctId+"#"+f.question,f] as const));

/** One Phase 3 trial per exact NCT; predictions never count as observed PASS/FAIL. */
const baseHeaders = [
 "NCT","Ticker","Company","Trial Classification","Classification Code",
 "Current Registry Status","Original Roster Status","Registry Snapshot Date",
 "Readout Evidence Type","Public Readout Evidence Date","Readout Outcome","Drug",
 "Indication","Registered Interventions","FDA Application Status","FDA Review Type",
 "PDUFA Goal Date","Readout Source URL","Registry Source URL","Classification Basis"
];
const extendedHeaders = [
 "Passing Classification","Passing Classification Rationale","Passing Evidence URL",
 "Passing Evidence Reviewed At","Passing Evidence Type","Results Publication Group",
 "Readout Evidence Verified","Registry State Group","Registry Source As Of",
 "Market Cap Source Status","In Dated $300M–$10B Screen","FDA Application Verified",
 "PDUFA Date Verified","Predictions Completed","Documented Source Facts",
 "Questions Not Scored","Question Model","Research Source Coverage",
 "Unified Ledger As Of","Interpretation Note"
];
const questionHeaders = UNIVERSAL_PHASE3_QUESTIONS.flatMap((q,i)=>{
 const p="Q"+String(i+1).padStart(2,"0")+" "+q.heading+" — ";
 return [p+"Evidence status",p+"Predicted outcome",p+"Score 0–100 (subjective)",
  p+"Evidence / missing information",p+"Source URL(s)"];
});
const HEADERS=[...baseHeaders,...extendedHeaders,...questionHeaders];
const endpointByNct=new Map(endpointAdjudications.records.map(x=>[x.nctId,x] as const));
const investorByNct=new Map(investorRelationsEvidence.records.map(x=>[x.nctId,x] as const));
const registryByNct=new Map(registryCrosswalk.records.map(r=>[r.nctId,r] as const));

const escaped=(input:unknown):string=>{
 let s=input===null||input===undefined?"":String(input);
 s=s.replace(/[\r\n]+/g," ");
 if(/^[=+\-@]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const writeRow=(cells:unknown[])=>cells.map(escaped).join(",");

export async function GET(request:Request){
 const params=new URL(request.url).searchParams;
 const includeLive=params.get("live")==="1";
 const cohort=params.get("cohort")||"all";
 const ticker=(params.get("ticker")||"").trim().toUpperCase();
 const nctId=(params.get("nctId")||"").trim().toUpperCase();
 if(!["all","active","pre","post"].includes(cohort)||!/^([A-Z0-9.]{1,8})?$/.test(ticker)||
  !/^(NCT\d{8})?$/.test(nctId))
  return Response.json({error:"Invalid cohort, ticker or exact NCT selector"},{status:400});
 const preIds=new Set(activePhase3Cohorts.pre.map(r=>r.nctId));
 const postIds=new Set(activePhase3Cohorts.post.map(r=>r.nctId));
 const included=(r:(typeof ledger.rows)[number])=>
  (!ticker||r.ticker===ticker)&&(!nctId||r.nctId===nctId)&&
  (cohort==="all"||(cohort==="pre"&&preIds.has(r.nctId))||
   (cohort==="post"&&postIds.has(r.nctId))||
   (cohort==="active"&&(preIds.has(r.nctId)||postIds.has(r.nctId))));
 const includedCount=ledger.rows.filter(included).length;
 type LiveRegistry=Awaited<ReturnType<typeof loadLivePhase3Registry>>["rows"][number]["registry"];
 let liveByNct=new Map<string,LiveRegistry>();
 if(includeLive){
  try{
   const live=await loadLivePhase3Registry();
   if(live.failedBatches>0||live.rows.some(row=>!row.registry))
    return Response.json({error:"Live registry collection incomplete; use default snapshot or retry"},{status:503});
   liveByNct=new Map(live.rows.map(row=>[row.original.nctId,row.registry] as const));
  }catch(e){
   return Response.json({error:e instanceof Error?e.message:"Live registry unavailable"},{status:503});
  }
 }
 if(HEADERS.length!==190||ledger.total!==762||ledger.rows.length!==762||
    new Set(ledger.rows.map(r=>r.nctId)).size!==762||
    PHASE3_ONLINE_TRIAL_COUNT!==762||registryByNct.size!==762||registryCrosswalk.records.length!==762||
    endpointByNct.size!==endpointAdjudications.records.length||
    !irResearchIntegrity(new Set(ledger.rows.map(r=>r.nctId)))||
    !populationGeographyIntegrity(new Set(ledger.rows.map(r=>r.nctId)))||
    investorByNct.size!==investorRelationsEvidence.records.length||
    endpointAdjudications.records.some(x=>!ledger.rows.some(r=>r.nctId===x.nctId))||
    agiosEvidence.trials.length!==9||agiosFacts.size!==agiosEvidence.facts.length||
    ionisEvidence.trials.length!==12||ionisFacts.size!==ionisEvidence.facts.length||
    ionisEvidence.trials.some(t=>!(t.cohort==="PRE_DATA"?preIds:postIds).has(t.nctId))||
    ionisEvidence.facts.some(f=>!ionisEvidence.trials.some(t=>t.nctId===f.nctId)||
      f.question<1||f.question>30||f.score!==null||!f.sourceUrl.startsWith("https://"))||
    agiosEvidence.trials.some(t=>!(t.cohort==="PRE_DATA"?preIds:postIds).has(t.nctId))||
    agiosEvidence.facts.some(f=>!agiosEvidence.trials.some(t=>t.nctId===f.nctId)||
      f.question<1||f.question>30||f.score!==null||!f.sourceUrl.startsWith("https://"))){
  return Response.json({error:"Phase 3 190-column ledger integrity check failed"},{status:503});
 }
 const rows=[writeRow(HEADERS)];
 let passedCount=0,failedCount=0;
 for(const r of ledger.rows){
  const endpoint=endpointByNct.get(r.nctId);
  const investor=investorByNct.get(r.nctId);
  const onlineRecord=phase3OnlineRecord(r.nctId);
  const registry=registryByNct.get(r.nctId);
  const liveRegistry=liveByNct.get(r.nctId);
  const outcome=endpoint?.endpointOutcome||r.readoutOutcome;
  const endpointEvidenceUrl=endpoint?.evidenceUrl||r.readoutEvidenceUrl||"";
  const observedPass=outcome==="PRIMARY_ENDPOINT_MET"&&
   Boolean(endpointEvidenceUrl)&&(Boolean(endpoint)||r.classificationVerified);
  const observedFail=outcome==="PRIMARY_ENDPOINT_NOT_MET"&&
   Boolean(endpointEvidenceUrl)&&Boolean(endpoint);
  const noBinary=outcome==="NO_BINARY_PASS_FAIL";
  if(observedPass)passedCount++;
  if(observedFail)failedCount++;
  const passing=observedPass?"PASS_DOCUMENTED_PRIMARY_ENDPOINT":
   observedFail?"FAIL_DOCUMENTED_PRIMARY_ENDPOINT":
   noBinary?"NON_BINARY_ENDPOINT":"UNDETERMINED";
  const passRationale=endpoint?.rationale||
   (r.readoutEvidenceType==="FDA_APPROVAL_SUPPORTING_TRIAL"?
     "FDA confirms historical approval supported by this exact NCT; no separate binary primary-endpoint verdict inferred":
    r.readoutEvidenceType==="PEER_REVIEWED_OPEN_LABEL_RESULTS"?
     "Peer-reviewed exact-trial open-label safety data are descriptive; a placebo-controlled efficacy PASS/FAIL is not established":
    r.readoutEvidenceType==="ISSUER_READOUT"&&r.readoutOutcome==="PRIMARY_ENDPOINT_MET"?
     "Issuer reports primary endpoint met; interpret evidence and limitations from the exact source":
   (r.classificationCode==="P3_TERMINATED"?"Trial terminated; an efficacy FAIL is not established by trial status":
    r.classificationCode==="P3_WITHDRAWN"?"Trial withdrawn; an efficacy FAIL is not established by trial status":
    "No source-qualified Phase 3 primary-endpoint determination available in the saved evidence"));
  const fullPassRationale=passRationale+(endpoint?.qualification?" | Qualification: "+endpoint.qualification:"");
  const slots=phase3QuestionSlots(r.nctId);
  const predictions=slots.filter(q=>Boolean(q.answer)).length;
  const observations=slots.filter(q=>!q.answer&&Boolean(q.observation)).length;
  const base=[
   r.nctId,r.ticker,r.company,r.classification,r.classificationCode,
   liveRegistry?.registryStatus||r.registryStatus,r.rosterStatus,
   liveRegistry?.sourceUpdated||r.registryAsOf,
   endpoint?.evidenceType||(r.readoutEvidenceType==="NOT_VERIFIED"&&onlineRecord?.resultsPosted?"CTGOV_RESULTS_POSTED_UNADJUDICATED":r.readoutEvidenceType),
   endpoint&&"sourceDate" in endpoint?endpoint.sourceDate:r.readoutSourceDate,
   outcome,r.drug||liveRegistry?.drugInterventions||registry?.drugInterventions||"",
   r.indication,liveRegistry?.interventionNames||r.registeredInterventions,
   investor?.regulatoryEvidenceStatus||r.fdaApplicationStatus,
   investor?.regulatoryReviewType&&investor.regulatoryReviewType!=="NOT_VERIFIED"?investor.regulatoryReviewType:r.fdaReviewType,
   investor?.pdufaGoalDate||r.pdufaGoalDate,
   endpointEvidenceUrl||(onlineRecord?.resultsPosted?"https://clinicaltrials.gov/study/"+r.nctId:""),
   r.registrySourceUrl,r.classificationEvidence
  ];
  const extra=[
   passing,fullPassRationale,endpoint?endpointEvidenceUrl:observedPass?endpointEvidenceUrl:"",
   endpoint?.reviewedAt||r.readoutSourceDate||"",
   endpoint?.evidenceType||r.readoutEvidenceType||"NOT_VERIFIED",
   r.classificationCode,Boolean(endpoint)||r.classificationVerified,
   r.registryStatus,r.registryAsOf,r.marketCapSourceStatus,r.inDatedMarketCapScreen,
   Boolean(investor?.regulatoryEvidenceStatus&&investor?.regulatoryEvidenceUrl)||r.fdaApplicationStatus!=="NOT_VERIFIED",
   Boolean(investor?.pdufaGoalDate&&investor?.pdufaEvidenceUrl)||Boolean(r.pdufaGoalDate),
   predictions,observations,30-predictions-observations,
   "UNIVERSAL_PHASE3_30_QUESTION_EVIDENCE_AWARE_V1",
   predictions?"REVIEWED_PRE_READOUT_PREDICTIONS":
    observations?"PARTIAL_REGISTRY_SOURCE_FACTS":"NO_REVIEWED_QUESTION_EVIDENCE",
   ledger.asOf+" | drug/comparator source "+registryCrosswalk.asOf,"Research classifications are not final clinical or FDA verdicts"
  ];
  const questions=slots.flatMap(q=>{
   if(q.answer)return ["PREDICTED_PRE_READOUT",q.answer.prediction,
    q.answer.score,q.answer.summary+" | "+q.answer.reason,
    q.answer.sources.map(s=>s.url).join(" | ")];
   if(q.number===1&&(observedPass||observedFail))return [observedPass?"OBSERVED_PRIMARY_ENDPOINT_MET":"OBSERVED_PRIMARY_ENDPOINT_NOT_MET","","",
    fullPassRationale+"; observed result, not a prospective prediction",endpointEvidenceUrl];
   if(q.number===1&&noBinary)return ["DOCUMENTED_NON_BINARY_ENDPOINT","","",
    fullPassRationale,endpointEvidenceUrl];
   if(q.number===29&&(endpoint||(r.classificationVerified&&r.readoutEvidenceUrl&&r.classificationCode==="P3_POST_DATA_ISSUER")))return ["DOCUMENTED_PUBLIC_READOUT","","",
    "Public Phase 3 readout or results exist. "+fullPassRationale,endpointEvidenceUrl];
   const researched=irAssessment(r.nctId,q.number);
   if(researched)return [researched.classification,"","",
    researched.evidence+" | Published: "+researched.publicationDate+" | Scope: "+researched.evidenceScope+
     ("chronologyQualification" in researched&&researched.chronologyQualification?" | Chronology: "+researched.chronologyQualification:""),
    researched.sourceUrl];
   const agiosFact=agiosFacts.get(r.nctId+"#"+q.number);
   if(agiosFact)return [agiosFact.status,"","",
    agiosFact.evidence+" | Published: "+agiosFact.sourceDate+" | Source fact only; no forecast or clinical score inferred",
    agiosFact.sourceUrl];
   const ionisFact=ionisFacts.get(r.nctId+"#"+q.number);
   if(ionisFact)return [ionisFact.status,"","",
    ionisFact.evidence+" | Dated evidence: "+ionisFact.sourceDate+
    " | Source fact, not a prospective efficacy or RAAS score",ionisFact.sourceUrl];
   // Issuer investor-relations statements are historical SOURCE FACTS, not subjective predictive scores.
   if(q.number===30&&investor?.regulatoryEvidenceStatus&&investor?.regulatoryEvidenceUrl)
    return ["SOURCE_FACT_ONLY","","",
     "FDA drug/indication application evidence crosswalk (not a trial outcome): "+investor.regulatoryEvidence,
     [investor.regulatoryEvidenceUrl,investor.pdufaEvidenceUrl].filter(Boolean).join(" | ")];
   if(investor?.companyUrl){
    if(q.number===3&&investor.safetyEvidence)
     return ["SOURCE_FACT_ONLY","","","Issuer-reported safety/tolerability: "+investor.safetyEvidence+"; no calibrated safety forecast inferred",investor.companyUrl];
    if(q.number===17&&/secondary endpoint/i.test(investor.specificEvidence||""))
     return ["SOURCE_FACT_ONLY","","","Issuer mentions clinical secondary endpoint(s): "+investor.specificEvidence+"; no prospective score inferred",investor.companyUrl];
    if(q.number===18&&/patient.reported|\bPRO\b/i.test(investor.specificEvidence||""))
     return ["SOURCE_FACT_ONLY","","","Issuer mentions patient-reported outcomes: "+investor.specificEvidence,investor.companyUrl];
    if(q.number===24&&/discontinuation/i.test(investor.safetyEvidence||""))
     return ["SOURCE_FACT_ONLY","","","Issuer-reported retention/discontinuation fact: "+investor.safetyEvidence,investor.companyUrl];
    if(q.number===30&&investor.regulatoryUrl&&/NDA under FDA review.*PDUFA/i.test(investor.regulatory||""))
     return ["SOURCE_FACT_ONLY","","","Drug/indication-level issuer regulatory milestone, NOT an individual trial approval or predicted outcome: "+investor.regulatory,investor.regulatoryUrl];
   }
   const population=populationGeographyFact(r.nctId,q.number);
   if(population)return [population.classification,"","",
    population.evidence+" | Registry published: "+population.publicationDate+" | Critical review: "+population.criticalReviewStatus,
    population.sourceUrl];
   if(liveRegistry){
    const url=liveRegistry.registryUrl;
    const fact=(description:string)=>["SOURCE_FACT_ONLY","","",description,url];
    if(q.number===1&&liveRegistry.postedPrimaryOutcomeCount>0)
     return fact("Official registry results list "+liveRegistry.postedPrimaryOutcomeCount+
      " primary measure(s). "+liveRegistry.firstPostedPrimaryResult+
      (liveRegistry.firstPostedPrimaryPValues?" | Reported statistical values: "+liveRegistry.firstPostedPrimaryPValues:"")+
      ". This is NOT an independently adjudicated primary-endpoint PASS/FAIL.");
    if(q.number===3&&liveRegistry.adverseEventsPosted)
     return fact("Official registry adverse-event data posted, "+
      liveRegistry.seriousAdverseEventTerms+" serious-event terms; safety acceptability has not been judged.");
    if(q.number===7&&liveRegistry.primaryOutcomes)
     return fact("Live registry primary outcome(s): "+liveRegistry.primaryOutcomes);
    if(q.number===8&&liveRegistry.primaryTimeframes)
     return fact("Live registry primary timeframe(s): "+liveRegistry.primaryTimeframes);
    if(q.number===9&&liveRegistry.allocation)
     return fact("Live registry allocation: "+liveRegistry.allocation+"; design adequacy not assessed.");
    if(q.number===10&&liveRegistry.masking)
     return fact("Live registry masking: "+liveRegistry.masking+"; blinding adequacy not assessed.");
    if(q.number===11&&liveRegistry.comparators)
     return fact("Official comparator arms: "+liveRegistry.comparators+"; adequacy not determined.");
    if(q.number===12&&liveRegistry.enrollment!==null)
     return fact("Live registry enrollment: "+liveRegistry.enrollment+
      " ("+liveRegistry.enrollmentType+"); statistical power not inferred.");
    if([13,14,15].includes(q.number)&&liveRegistry.hasPublicSAP)
     return fact("Public statistical analysis plan located in registry. The plan has not been critically reviewed "+
      "for power, missing-data handling or multiplicity: "+liveRegistry.protocolOrSAPDocuments);
    if(q.number===17&&(liveRegistry.secondaryOutcomeCount??0)>0)
     return fact("Official registry lists "+liveRegistry.secondaryOutcomeCount+
      " secondary outcomes; no efficacy inference made.");
    if(q.number===23&&liveRegistry.seriousAdverseEventTerms>0)
     return fact("Official registry reports "+liveRegistry.seriousAdverseEventTerms+
      " serious-event terms; treatment-attributable risk and rates not assessed.");
    if(q.number===25&&liveRegistry.registryStatus)
     return fact("Live registry status: "+liveRegistry.registryStatus+
      "; status is distinct from primary endpoint success.");
    if(q.number===27&&/\\bplacebo\\b/i.test(liveRegistry.interventionNames))
     return fact("Live registry names placebo in interventions; comparator adequacy not assessed.");
    if(q.number===29&&liveRegistry.registryResultsPosted)
     return fact("Official trial results have been posted; PASS/FAIL not independently adjudicated.");
   }
   if(q.observation)return ["SOURCE_FACT_ONLY","","",
    q.observation.description,q.observation.sourceUrl];
   if(q.number===11&&registry?.comparators)return ["SOURCE_FACT_ONLY","","",
    "Official registry comparator arm(s): "+registry.comparators+
    "; presence of a comparator is NOT proof of statistical adequacy or efficacy",
    r.registrySourceUrl];
   if(q.number===25&&r.registrySourceUrl)return ["SOURCE_FACT_ONLY","","",
    "Dated registry recruitment status: "+r.registryStatus+" (as of "+r.registryAsOf+")",
    r.registrySourceUrl];
   if(q.number===27&&/\bplacebo\b/i.test(r.registeredInterventions||""))
    return ["SOURCE_FACT_ONLY","","",
     "Placebo appears in the registered intervention list; comparator adequacy not assessed",
     r.registrySourceUrl];
   const newlySourced=phase3OnlineSourceFact(r.nctId,q.number);
   if(newlySourced)return [newlySourced.status,"","",newlySourced.description,newlySourced.sourceUrl];
   if([1,2,3,28,29,30].includes(q.number)){
    const leads=phase3OnlineReviewLeads(r.nctId);
    if(leads.summary)return ["UNSCORED","", "",
     q.missingEvidence+" | Source leads awaiting question-specific adjudication: "+leads.summary,
     leads.urls.join(" | ")];
   }
   return ["UNSCORED","","",q.missingEvidence,""];
  });
  const statuses=Array.from({length:30},(_,i)=>questions[i*5]);
  const countedPredictions=statuses.filter(x=>x==="PREDICTED_PRE_READOUT").length;
  const countedEvidence=statuses.filter(x=>x!=="PREDICTED_PRE_READOUT"&&!requiresResearchStatus(String(x))&&x!=="NOT_PUBLICLY_DISCLOSED").length;
  extra[13]=countedPredictions;
  extra[14]=countedEvidence;
  extra[15]=30-countedPredictions-countedEvidence;
  extra[17]=phase3OnlineCoverageLabel(r.nctId)+"; "+
   (endpoint?"PUBLIC_ENDPOINT_EVIDENCE_REVIEWED":
   countedPredictions?"REVIEWED_PRE_READOUT_PREDICTIONS":
   countedEvidence?"PARTIAL_DOCUMENTED_SOURCE_FACTS":"NO_SCORED_QUESTION_EVIDENCE");
  const values=[...base,...extra,...questions];
  if(values.length!==190){
   return Response.json({error:"Question-field alignment failed"},{status:503});
  }
  if(included(r))rows.push(writeRow(values));
 }
 const additionalPasses=IONIS_VERIFIED_READOUTS.filter(r=>r.outcome==="PRIMARY_ENDPOINT_MET"&&!endpointByNct.has(r.nctId)).length;
 if((cohort==="all"&&!ticker&&!nctId&&rows.length!==763)||
    rows.length!==includedCount+1||passedCount!==endpointAdjudications.counts.PRIMARY_ENDPOINT_MET+additionalPasses||
    failedCount!==endpointAdjudications.counts.PRIMARY_ENDPOINT_NOT_MET){
  return Response.json({error:"Trial/pass reconciliation failed"},{status:503});
 }
 return new Response("\uFEFF"+rows.join("\r\n")+"\r\n",{
  status:200,headers:{
   "Content-Type":"text/csv; charset=utf-8",
   "Content-Disposition":'attachment; filename="Phase3-'+(cohort==="all"?"Historical": "Active")+
    "-"+includedCount+"-Trials-190-Columns-2026-11-06"+(includeLive?"-Live":"")+".csv"+'"',
   "Cache-Control":"no-store"
  }
 });
}
