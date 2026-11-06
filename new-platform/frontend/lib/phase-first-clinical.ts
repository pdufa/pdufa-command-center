/** Phase-first applicability and partial clinical research ratings.
 * Never modifies a saved score, calibration, prediction or Pipeline membership.
 */
export const PHASE_FIRST_VERSION="PHASE_FIRST_CLINICAL_2026_11_06_V1";
export type EvidenceStatus="AVAILABLE"|"MISSING"|"NOT YET EXPECTED"|"NOT APPLICABLE"|"PENDING"|"CONFLICTING";
export type SourceConfidence="HIGH"|"MODERATE"|"LOW";
export type PhaseTrial={
 trialId:string;nctId:string|null;title:string;protocol:string|null;acronym?:string|null;
 sponsor:string;phases:string[];studyType:string;status:string;whyStopped?:string|null;
 indications:string[];interventions:{name:string;type:string;description?:string}[];
 arms:{label:string;type?:string}[];design:Record<string,unknown>;
 enrollment:{count:number;type?:string}|null;primary:{measure:string;timeFrame?:string;description?:string}[];
 secondary:{measure:string;timeFrame?:string;description?:string}[];
 start:{date:string;type?:string}|null;primaryCompletion:{date:string;type?:string}|null;
 firstPosted?:{date:string}|null;sourceDate:string;sourceUrl:string;retrievedAt:string;
 hasResults:boolean;results:Record<string,unknown>;documents:{hasProtocol?:boolean;hasSap?:boolean;filename?:string;uploadDate?:string}[];
 sourceSha256:string;sourceConflicts?:string[];sourceNotes?:string[];
};
export type EvidenceItem={id:string;label:string;status:EvidenceStatus;evidence:string;
 sourceUrl:string|null;evidenceDate:string|null;confidence:SourceConfidence;
 expectedAt:string;searchScope:string;dateKind:string;reviewedAt:string;searchedSourceUrl:string;group:"IDENTITY"|"CLINICAL"|"REGULATORY"};
export type FactorKey="efficacy"|"clinicalBenefit"|"statistics"|"reproducibility"|"safety";
export type ReviewedFactor={key:FactorKey;grade:number|null;sourceUrl:string|null;
 sourceDate:string|null;benchmarkSourceUrl:string|null;finding:string|null;assessedAt?:string|null;phaseScope?:readonly string[]};
export type ClinicalContext={
 pipelineRestriction?:string|null;pipelineRestrictionSource?:string|null;
 ticker:string;drug:string;indication:string;programId:string;programPhase:string|null;
 programSourceUrl:string|null;legacyStage:"pre"|"post"|null;stageVerified:boolean;
 safetyPrimary:boolean;notApplicableFactors:readonly string[];
 reviewedFactors:readonly ReviewedFactor[];approvedRaas:number|null;
 regulatory:{status:string;url:string;date:string;text:string;goalDate?:string}|null;
 additionalEvidence?:Partial<Record<string,{text:string;url:string;date:string;dateKind?:string;confidence?:SourceConfidence;status?:EvidenceStatus}>>;
};
const FACTORS:readonly {key:FactorKey;label:string;requirements:string[]}[]=[
 {key:"efficacy",label:"Clinical efficacy",requirements:["earlyEfficacy","phase3Results","priorEfficacySafety"]},
 {key:"clinicalBenefit",label:"Patient benefit and counterevidence",requirements:["proofOfConcept","benefitRisk"]},
 {key:"statistics",label:"Design and statistical strength",requirements:["design","power","uncertainty"]},
 {key:"reproducibility",label:"Mechanism, dose and reproducibility",requirements:["mechanism","doseSelection","pkPd"]},
 {key:"safety",label:"Safety and tolerability",requirements:["safety","tolerability"]}
];
const REQUIREMENTS:readonly [string,string,number,"IDENTITY"|"CLINICAL"|"REGULATORY"][]=[
 ["phase","Verified individual-trial phase",0,"IDENTITY"],["status","Recruitment/completion status",0,"IDENTITY"],
 ["indication","Indication and intended clinical benefit",0,"IDENTITY"],
 ["mechanism","Mechanism of action",1,"CLINICAL"],["preclinical","Preclinical rationale",1,"CLINICAL"],
 ["safety","Initial / cumulative safety results",1,"CLINICAL"],["tolerability","Tolerability and discontinuations",1,"CLINICAL"],
 ["pkPd","PK/PD results",1,"CLINICAL"],["doseEscalation","Dose-escalation evidence",1,"CLINICAL"],
 ["biologicalActivity","Early biological activity",1,"CLINICAL"],
 ["priorPhase1","Phase 1 findings supporting this trial",2,"CLINICAL"],["proofOfConcept","Proof of concept",2,"CLINICAL"],
 ["doseSelection","Dose selection rationale",2,"CLINICAL"],["earlyEfficacy","Early efficacy estimates",2,"CLINICAL"],
 ["endpointPerformance","Endpoint performance",2,"CLINICAL"],["uncertainty","Statistical uncertainty",2,"CLINICAL"],
 ["phase3Entry","Phase 3 entry documentation",3,"CLINICAL"],["design","Trial design",1,"CLINICAL"],
 ["primary","Primary endpoints",1,"CLINICAL"],["secondary","Secondary endpoints",1,"CLINICAL"],
 ["comparator","Comparator / control",1,"CLINICAL"],["enrollment","Enrollment",1,"CLINICAL"],
 ["power","Statistical power assumptions",3,"CLINICAL"],["protocol","Public protocol",1,"CLINICAL"],
 ["sap","Statistical analysis plan",2,"CLINICAL"],["priorEfficacySafety","Prior efficacy and safety evidence",3,"CLINICAL"],
 ["phase3Results","Available Phase 3 outcomes",3,"CLINICAL"],["benefitRisk","Benefit–risk evidence",3,"CLINICAL"],
 ["pivotalResults","Pivotal results supporting an application",4,"REGULATORY"],
 ["ndaSubmission","NDA/BLA submission",4,"REGULATORY"],["fdaAcceptance","FDA acceptance",4,"REGULATORY"],
 ["pdufa","Assigned PDUFA target",4,"REGULATORY"],["adcom","Advisory committee information, if applicable",4,"REGULATORY"],
 ["inspections","FDA review / inspection information",4,"REGULATORY"],
 ["labelManufacturing","Labeling and manufacturing evidence",4,"REGULATORY"],
 ["fdaOutcome","Approval / CRL / extension outcome",4,"REGULATORY"]
];
export function verifiedPhase(phases:readonly string[],studyType:string){
 const known=new Set(["EARLY_PHASE1","PHASE1","PHASE2","PHASE3","PHASE4"]);
 const accepted=phases.filter(p=>known.has(p));
 const verified=accepted.length>0&&studyType==="INTERVENTIONAL";
 // Preserve mixed phases; never promote the trial to its program's highest phase.
 return {verified,label:verified?accepted.map(p=>p==="EARLY_PHASE1"?"Early Phase 1":p.replace("PHASE","Phase ")).join(" / "):
  studyType==="OBSERVATIONAL"?"Observational / N/A":"Phase not specified",phases:[...accepted],
  maturity:verified?Math.max(...accepted.map(p=>p==="EARLY_PHASE1"?1:Number(p.slice(-1)))):null};
}
const serialized=(x:unknown)=>JSON.stringify(x);
export function evaluatePhaseFirst(trial:PhaseTrial,context:ClinicalContext,asOf:string){
 if(!/^NCT\d{8}$|^ISRCTN\d{8}$/.test(trial.trialId)||trial.sourceDate>asOf||
  !/^https:\/\//.test(trial.sourceUrl)||!context.programId||
  (trial.nctId!==null&&trial.nctId!==trial.trialId)||
  new URL(trial.sourceUrl).pathname.split('/').at(-1)!==trial.trialId)throw Error("PHASE_FIRST_IDENTITY_OR_CHRONOLOGY_INVALID");
 const phase=verifiedPhase(trial.phases,trial.studyType);
 const mature=phase.maturity??0;
 const ongoing=["RECRUITING","NOT_YET_RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION","SUSPENDED"].includes(trial.status);
 const noEnrollment=trial.status==="WITHDRAWN"&&trial.enrollment?.count===0;
 const noClinical=trial.studyType!=="INTERVENTIONAL"||!phase.verified;
 const regulatoryLinked=!!context.regulatory;
 const regContext=regulatoryLinked?"EXACT_TRIAL_HISTORICAL_REGULATORY_LINK":
  context.legacyStage==="post"&&mature>=3?"POST_READOUT_APPLICATION_NOT_ESTABLISHED":"CLINICAL_DEVELOPMENT";
 const registryResults=trial.results as {adverseEventsModule?:unknown;participantFlowModule?:unknown;outcomeMeasuresModule?:{outcomeMeasures?:{title:string;type?:string;analyses?:unknown[]}[]}};
 const outcomes=registryResults.outcomeMeasuresModule?.outcomeMeasures??[];
 const direct:Record<string,string|undefined>={
  phase:phase.verified?phase.label:undefined,status:trial.status,
  indication:trial.indications.length?trial.indications.join("; "):undefined,
  design:Object.keys(trial.design).length?serialized(trial.design):undefined,
  primary:trial.primary.length?trial.primary.map(x=>x.measure+(x.timeFrame?" ["+x.timeFrame+"]":"")).join("; "):undefined,
  secondary:trial.secondary.length?trial.secondary.map(x=>x.measure).join("; "):undefined,
  comparator:trial.arms.length?trial.arms.map(a=>a.label+" ("+(a.type??"unspecified")+")").join("; "):undefined,
  enrollment:trial.enrollment?serialized(trial.enrollment):undefined,
  phase3Entry:trial.phases.includes("PHASE3")?"Registry explicitly lists Phase 3. Study start "+(trial.start?.date??"unknown")+" is not proof of the date the protocol entered Phase 3.":undefined,
  protocol:trial.documents.some(d=>d.hasProtocol)?"Public registry protocol attachment located; scientific content needs separate review.":undefined,
  sap:trial.documents.some(d=>d.hasSap)?"Public SAP attachment located; adequacy is not inferred.":undefined,
  safety:registryResults.adverseEventsModule?"Exact-trial adverse-event table available. "+serialized(registryResults.adverseEventsModule).slice(0,650):undefined,
  tolerability:registryResults.participantFlowModule?"Exact-trial participant-flow/discontinuation table available; not all withdrawals are treatment-related.":undefined,
  pkPd:outcomes.some(o=>/pharmacokinetic|\bAUC\b|\bCmax\b/i.test(o.title))?"PK/PD outcome measurements posted in exact-trial results.":undefined,
  earlyEfficacy:trial.hasResults&&mature===2?"Trial results posted; effect interpretation and benchmark grading are separate.":undefined,
  endpointPerformance:trial.hasResults&&outcomes.length?"Posted endpoint measurements available; validation/clinical importance not inferred.":undefined,
  uncertainty:outcomes.some(o=>o.analyses?.length)?"Registered statistical analyses available; multiplicity and uncertainty still require interpretation.":undefined,
  phase3Results:trial.hasResults&&trial.phases.includes("PHASE3")?"Exact Phase 3 registry results posted. Availability does not establish success.":undefined,
  fdaOutcome:context.regulatory?.status.includes("APPROVED")?context.regulatory.text:undefined
 };
 const resultItems=new Set(["safety","tolerability","pkPd","biologicalActivity","earlyEfficacy","proofOfConcept","endpointPerformance","uncertainty","phase3Results","benefitRisk","pivotalResults"]);
 const evidence:EvidenceItem[]=REQUIREMENTS.map(([id,label,minimum,group])=>{
  const extra=context.additionalEvidence?.[id];const value=extra?.text??direct[id];
  if(extra&&(!extra.url.startsWith("https://")||!/^\d{4}-\d{2}(-\d{2})?$/.test(extra.date)||extra.date>asOf))throw Error("PHASE_FIRST_EVIDENCE_CHRONOLOGY_INVALID");
  let status:EvidenceStatus;let explanation:string;
  if(value){status="AVAILABLE";explanation=value;}
  else if(id==="phase"&&!phase.verified){status=trial.studyType==="OBSERVATIONAL"?"NOT APPLICABLE":"CONFLICTING";explanation="No interventional phase is assigned; no numerical phase-adjusted rating can be issued.";}
  else if(noClinical&&group!=="IDENTITY"){status="NOT APPLICABLE";explanation="No verified interventional clinical phase; do not infer a phase from drug-program maturity.";}
  else if(group==="REGULATORY"&&mature<3){status="NOT YET EXPECTED";explanation="Later regulatory-stage evidence; excluded from this trial's current completeness denominator.";}
  else if(group==="REGULATORY"&&!regulatoryLinked){status=ongoing?"NOT YET EXPECTED":"PENDING";explanation="An exact trial/application milestone is not established. Trial completion is not proof of submission, acceptance or an FDA decision.";}
  else if(id==="adcom"){status="PENDING";explanation="Advisory committee applicability has not been established; no meeting is presumed required.";}
  else if(mature===4&&["phase3Entry","phase3Results","pivotalResults"].includes(id)&&!regulatoryLinked){status="NOT APPLICABLE";explanation="This is a Phase 4 study, not a new pivotal Phase 3 trial or application by inference.";}
  else if(minimum>(group==="REGULATORY"&&regulatoryLinked?4:mature)){status="NOT YET EXPECTED";explanation="Evidence belongs to a later phase than this individual trial.";}
  else if((id==="doseEscalation"&&mature>1)||(noEnrollment&&resultItems.has(id))){status="NOT APPLICABLE";explanation=noEnrollment?"Study withdrawn with zero enrollment; no clinical result can exist for this trial.":"Dose-escalation experiment is not this study's objective; supporting dose selection is evaluated separately.";}
  else if(context.safetyPrimary&&["earlyEfficacy","proofOfConcept","benefitRisk","phase3Results","pivotalResults"].includes(id)){status="NOT APPLICABLE";explanation="Safety-primary study without a confirmatory efficacy hypothesis; safety evidence is assessed separately.";}
  else if(ongoing&&resultItems.has(id)){status="PENDING";explanation="Applicable study results are pending; no adverse score or missing-efficacy penalty is assigned.";}
  else {status="MISSING";explanation="Expected at this phase but not located in the reviewed exact-trial source set. This is a scoped research gap, not proof that the information is unavailable publicly.";}
  if(id==="indication"&&trial.sourceConflicts?.length){status="CONFLICTING";explanation=trial.sourceConflicts.join("; ");}
  if(extra?.status){status=extra.status;explanation=extra.text;}
  const regulatorySource=["inspections","fdaOutcome"].includes(id)&&context.regulatory;
  return {id,label,status,evidence:explanation,sourceUrl:extra?.url??(value?(regulatorySource?context.regulatory!.url:trial.sourceUrl):null),
   evidenceDate:extra?.date??(value?(regulatorySource?context.regulatory!.date:trial.sourceDate):null),
   confidence:extra?.confidence??(status==="AVAILABLE"?"HIGH":"LOW"),
   dateKind:extra?.dateKind??(extra||regulatorySource?"DOCUMENT_DATE":"REGISTRY_LAST_UPDATE"),reviewedAt:asOf,searchedSourceUrl:trial.sourceUrl,
   expectedAt:minimum===4?"Regulatory":minimum===0?"Identity":"Phase "+minimum,
   searchScope:"Exact trial registry, existing source-reviewed dossiers and explicitly matched manufacturer/FDA/publication sources; unreviewed publications are leads only.",group};
 });
 const factors=FACTORS.map(f=>{
  const na=noClinical||context.notApplicableFactors.includes(f.key);
  const later=mature===1&&["efficacy","clinicalBenefit"].includes(f.key);
  const prior=context.reviewedFactors.find(r=>r.key===f.key);
  const phaseBound=prior?.phaseScope?prior.phaseScope.includes(trial.phases.join("|")):trial.phases.includes("PHASE3");
  const acceptable=!na&&!later&&phaseBound&&context.stageVerified&&context.legacyStage!==null&&
   prior?.grade!==null&&prior?.grade!==undefined&&[0,25,50,75,100].includes(prior.grade)&&
   prior.sourceUrl?.startsWith("https://")&&prior.benchmarkSourceUrl?.startsWith("https://")&&
   prior.sourceDate&&prior.assessedAt&&prior.sourceDate<=prior.assessedAt&&prior.assessedAt<=asOf;
  const grade=acceptable?prior!.grade:null;
  return {...f,weight:20,score:grade,
   applicability:(na?"NOT APPLICABLE":later?"NOT YET EXPECTED":"APPLICABLE") as "NOT APPLICABLE"|"NOT YET EXPECTED"|"APPLICABLE",
   reason:na?"Not applicable to this study's verified purpose.":later?"Confirmatory efficacy/patient-benefit grading is premature for Phase 1; early biological activity remains in the checklist.":
    grade===null?"No accepted exact-trial, phase-appropriate benchmark grade. Source availability is not a scientific score.":"Preserved existing exact-trial reviewed research grade; not a calibrated FDA probability.",
   sourceUrl:grade!==null?prior!.sourceUrl:null,sourceDate:grade!==null?prior!.sourceDate:null,
   benchmarkSourceUrl:grade!==null?prior!.benchmarkSourceUrl:null,finding:grade!==null?prior!.finding:null,
   confidence:grade!==null?"MODERATE":"NOT_ASSESSABLE"};
 });
 const eligible=factors.filter(f=>f.applicability==="APPLICABLE");const scored=eligible.filter(f=>f.score!==null);
 const coveredWeight=scored.reduce((n,f)=>n+f.weight,0);
 const overall=coveredWeight?Math.round(scored.reduce((n,f)=>n+f.score!*f.weight,0)/coveredWeight*10)/10:null;
 const due=evidence.filter(e=>["AVAILABLE","MISSING","CONFLICTING"].includes(e.status));
 const counts=Object.fromEntries((['AVAILABLE','MISSING','PENDING','NOT YET EXPECTED','NOT APPLICABLE','CONFLICTING'] as const).map(s=>[s,evidence.filter(e=>e.status===s).length]));
 const early=mature<3||!phase.verified;
 const fdaState=early?"NOT YET ELIGIBLE":"ABSTAIN";
 return {trialId:trial.trialId,nctId:trial.nctId,ticker:context.ticker,title:trial.title,drug:context.drug,
  indication:context.indication,sponsor:trial.sponsor,protocol:trial.protocol,phase,status:trial.status,
  programId:context.programId,programPhase:context.programPhase,programSourceUrl:context.programSourceUrl,
  start:trial.start,phaseEntryDate:null,phaseEntryNote:"Trial start and program phase-entry dates are distinct; no exact individual phase-entry date inferred.",
  sourceUrl:trial.sourceUrl,sourceDate:trial.sourceDate,retrievedAt:trial.retrievedAt,regulatoryContext:regContext,
  modelVersion:PHASE_FIRST_VERSION,evidence,factors,overallRating:overall,
  ratingKind:overall===null?"NOT_ASSESSABLE":scored.length===eligible.length?"PHASE_ADJUSTED_RESEARCH_RATING":"PARTIAL_SCORED_COMPONENT_MEAN",
  ratingCoverage:{scored:scored.length,eligible:eligible.length,total:5,percent:eligible.length?Math.round(scored.length/eligible.length*100):null,
   coveredWeight,eligibleWeight:eligible.reduce((n,f)=>n+f.weight,0)},
  evidenceCompleteness:due.length?Math.round(counts.AVAILABLE/due.length*1000)/10:null,
  evidenceCounts:counts,evidenceConfidence:counts.CONFLICTING?"LOW":counts.MISSING?"MODERATE":"HIGH",
  missingExpected:evidence.filter(e=>e.status==="MISSING"||e.status==="CONFLICTING"),
  notYetExpected:evidence.filter(e=>e.status==="NOT YET EXPECTED"),pending:evidence.filter(e=>e.status==="PENDING"),
  raasScore:context.approvedRaas,raasPredictionConfidence:null,
  fdaPrediction:{status:fdaState,probabilities:null,confidence:null,
   reason:early?"The individual trial has not reached the applicable regulatory-prediction stage.":
    "A calibrated, exact-application, pre-decision FDA model and complete frozen eligibility evidence have not been established. A clinical research rating is not an approval/CRL/extension probability."},
  pipeline:{automaticTransfer:false,companyRestriction:context.pipelineRestriction??null,companyRestrictionSource:context.pipelineRestrictionSource??null,phaseRequirementMet:trial.phases.includes("PHASE3"),marketCapStatus:"CURRENT_MARKET_CAP_RECHECK_REQUIRED",
   restrictions:"Existing public-company, $300m–$10bn, Phase 3/post-Phase 3, US FDA and validated Pipeline filters remain authoritative; no admission or score history is changed."}};
}
