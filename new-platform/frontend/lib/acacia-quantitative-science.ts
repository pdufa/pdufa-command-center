/** MAIN: phase-first quantitative research signals for a single published trial.
 *
 * This is reproducible descriptive arithmetic, not a qualified clinical review,
 * independently authorized 0–5 method grade, causality claim or FDA prediction.
 * The source-pinned original snapshot cannot mutate an official clinical ledger.
 */
type SafetyRow={metric:string;source:string;treated:number;treatedN:number;
  control:number;controlN:number;sourceDiscrepancy?:string};
type Endpoint={difference:number;ci95:number[];unit:string;pValueRounded?:number;pValue?:number};
type PilotSnapshot={
  nct:string;trial:string;protocolCode:string;phaseReported:string;
  phaseIndependentReviewerVerified:boolean;asOf:string;
  publishedPrimary:{
    publication:string;randomized:{aficamten:number;placebo:number};
    kccq:Endpoint;peakVo2:Endpoint;
    finalSapVerified:boolean;clinicalImportanceReviewed:boolean;
    sponsorReportedInitialAlphaEach:number;
  };
  descriptiveSafety:SafetyRow[];
  criticalAssessmentEvidence:Array<{id:string;candidateMethodIndices:number[]}>;
  sources:Record<string,{url:string;sha256?:string;retrieved?:boolean}>;
  scientificFramework:{positions:number;independentlyGradedMethodPositions:number;
    independentlyCompletedAssessments:number;currentPhaseReviewSignoffs:number};
  finalDecision:{approval:string;crl:string;reviewDelay:string;certainty:string;
    calibratedAccuracy:null;calibratedProbabilities:null};
};
export type EndpointSignal={
  id:"KCCQ_CSS"|"PEAK_VO2";label:string;estimate:number;unit:string;ci95:[number,number];
  reportedP:number;criterion:"CI_EXCLUDES_ZERO_AND_REPORTED_P_MEETS_SPONSOR_ALPHA"|
    "NO_POSITIVE_DIRECTIONAL_SIGNAL";directionalPass:boolean;
  approximateStandardError:number;sourceUrl:string;
};
export type SafetySignal={
  id:"LVEF_BELOW_50_PERCENT"|"ANY_SERIOUS_ADVERSE_EVENT";
  treated:number;treatedN:number;control:number;controlN:number;
  treatedRatePercent:number;controlRatePercent:number;absoluteDifferencePp:number;
  imbalanceTowardTreated:boolean;sourceUrl:string;
};
export type QuantitativeResearchReport={
  schema:"MAIN_ACACIA_QUANTITATIVE_RESEARCH_V1";
  nct:"NCT06081894";asOf:string;
  phaseBasis:"REPORTED_PHASE3_NOT_INDEPENDENTLY_SIGNED_OFF";
  methods:[{assessmentId:"5.1";methodIndex:12;name:"Published co-primary estimate and uncertainty"},
           {assessmentId:"5.3";methodIndex:19;name:"Unadjusted safety arithmetic audit"}];
  endpoints:[EndpointSignal,EndpointSignal];
  positivePublishedEndpointSignals:number;primaryEndpointSignalsOutOf:2;
  safety:[SafetySignal,SafetySignal];
  treatedArmExcessInDescriptiveSafety:number;safetyOutOf:2;
  seriousHeartFailureReconciliation:"UNRESOLVED_11_1_VS_12_3";
  lockedSapVerified:false;clinicalImportanceVerified:false;
  officialMethodGrade:null;provisionalClinicalGrade:null;
  independentClinicalReview:false;
  fdaPrediction:"ABSTAIN";calibratedAccuracy:null;probability:null;
  limitations:string[];
};
const SOURCE="https://pubmed.ncbi.nlm.nih.gov/42663312/";
const SEC="https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm";
const originalNumerics={
  kccq:{difference:3,ci95:[0.5,5.5],p:0.02},
  pvo2:{difference:0.67,ci95:[0.22,1.11],p:0.003},
  lvef:[27,258,2,259],
  sae:[52,258,38,259],
  hf:[12,258,3,259]
} as const;
const pair=(a:number[],b:readonly number[])=>a.length===b.length&&a.every((x,i)=>x===b[i]);
const safe=(url:string)=>{try{const u=new URL(url);return u.protocol==="https:"&&!u.username&&!u.password;}catch{return false;}};
const round=(n:number,places:number)=>Math.round((n+Number.EPSILON)*10**places)/10**places;
function validRow(row:SafetyRow|undefined,expected:readonly number[],metric:string,url:string){
  if(!row||row.metric!==metric||row.source!==url||!safe(row.source))return false;
  return pair([row.treated,row.treatedN,row.control,row.controlN],expected)&&
    [row.treated,row.treatedN,row.control,row.controlN].every(Number.isSafeInteger)&&
    row.treatedN>0&&row.controlN>0&&row.treated>=0&&row.control>=0&&
    row.treated<=row.treatedN&&row.control<=row.controlN;
}
function endpoint(id:EndpointSignal["id"],label:string,input:Endpoint,p:number):EndpointSignal{
  const ci=input.ci95;
  const normalSE=(ci[1]-ci[0])/(2*1.96);
  const directionalPass=ci[0]>0&&p>0&&p<=0.025;
  return {
    id,label,estimate:input.difference,unit:input.unit,
    ci95:[ci[0],ci[1]],reportedP:p,
    criterion:directionalPass?"CI_EXCLUDES_ZERO_AND_REPORTED_P_MEETS_SPONSOR_ALPHA":"NO_POSITIVE_DIRECTIONAL_SIGNAL",
    directionalPass,approximateStandardError:round(normalSE,4),sourceUrl:SOURCE
  };
}
function safety(id:SafetySignal["id"],row:SafetyRow):SafetySignal {
  const treatedRate=row.treated/row.treatedN*100;
  const controlRate=row.control/row.controlN*100;
  return {id,treated:row.treated,treatedN:row.treatedN,control:row.control,controlN:row.controlN,
    treatedRatePercent:round(treatedRate,2),controlRatePercent:round(controlRate,2),
    absoluteDifferencePp:round(treatedRate-controlRate,2),
    imbalanceTowardTreated:treatedRate>controlRate,sourceUrl:SOURCE};
}
export function evaluatePilotScientificSignals(v:PilotSnapshot):QuantitativeResearchReport|null{
  if(!v||v.nct!=="NCT06081894"||v.trial!=="ACACIA-HCM"||
    v.protocolCode!=="CY 6033"||v.phaseReported!=="PHASE3"||
    v.phaseIndependentReviewerVerified!==false||
    v.scientificFramework?.positions!==800||
    v.scientificFramework?.independentlyGradedMethodPositions!==0||
    v.scientificFramework?.independentlyCompletedAssessments!==0||
    v.scientificFramework?.currentPhaseReviewSignoffs!==0||
    v.finalDecision?.approval!=="ABSTAIN"||
    v.finalDecision?.crl!=="ABSTAIN"||v.finalDecision?.reviewDelay!=="ABSTAIN"||
    v.finalDecision?.certainty!=="NOT_VALIDATED"||
    v.finalDecision?.calibratedAccuracy!==null||
    v.finalDecision?.calibratedProbabilities!==null||
    !/^20\d{2}-\d{2}-\d{2}$/.test(v.asOf))return null;
  const p=v.publishedPrimary;
  if(!p||p.publication!==SOURCE||v.sources?.NEJM_PIVOTAL?.url!==SOURCE||
    v.sources?.SEC_10Q?.url!==SEC||
    p.randomized?.aficamten!==258||p.randomized?.placebo!==259||
    p.finalSapVerified!==false||p.clinicalImportanceReviewed!==false||
    p.sponsorReportedInitialAlphaEach!==0.025||
    p.kccq?.difference!==originalNumerics.kccq.difference||
    p.peakVo2?.difference!==originalNumerics.pvo2.difference||
    !Array.isArray(p.kccq?.ci95)||!Array.isArray(p.peakVo2?.ci95)||
    !pair(p.kccq.ci95,originalNumerics.kccq.ci95)||
    !pair(p.peakVo2.ci95,originalNumerics.pvo2.ci95)||
    p.kccq.unit!=="points"||p.peakVo2.unit!=="ml/kg/min"||
    p.kccq.pValueRounded!==originalNumerics.kccq.p||
    p.peakVo2.pValue!==originalNumerics.pvo2.p)return null;
  const leads=v.criticalAssessmentEvidence;
  if(!Array.isArray(leads)||
    !leads.find(x=>x.id==="5.1"&&x.candidateMethodIndices?.includes(12))||
    !leads.find(x=>x.id==="5.3"&&x.candidateMethodIndices?.includes(19)))return null;
  const rows=v.descriptiveSafety;
  if(!Array.isArray(rows)||rows.length!==3)return null;
  const a=rows.find(x=>x.metric==="LVEF_BELOW_50_PERCENT");
  const b=rows.find(x=>x.metric==="ANY_SERIOUS_ADVERSE_EVENT");
  const c=rows.find(x=>x.metric==="SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE");
  if(!validRow(a,originalNumerics.lvef,"LVEF_BELOW_50_PERCENT",SOURCE)||
    !validRow(b,originalNumerics.sae,"ANY_SERIOUS_ADVERSE_EVENT",SOURCE)||
    !validRow(c,originalNumerics.hf,"SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE",SEC)||
    c?.sourceDiscrepancy!=="SECONDARY_PAPER_REPORTS_11_VS_1")return null;
  const endpoints=[
    endpoint("KCCQ_CSS","Patient-reported KCCQ-CSS",p.kccq,originalNumerics.kccq.p),
    endpoint("PEAK_VO2","Peak oxygen uptake",p.peakVo2,originalNumerics.pvo2.p),
  ] as [EndpointSignal,EndpointSignal];
  const safetySignals=[
    safety("LVEF_BELOW_50_PERCENT",a!),
    safety("ANY_SERIOUS_ADVERSE_EVENT",b!)
  ] as [SafetySignal,SafetySignal];
  return {
    schema:"MAIN_ACACIA_QUANTITATIVE_RESEARCH_V1",
    nct:"NCT06081894",asOf:v.asOf,phaseBasis:"REPORTED_PHASE3_NOT_INDEPENDENTLY_SIGNED_OFF",
    methods:[
      {assessmentId:"5.1",methodIndex:12,name:"Published co-primary estimate and uncertainty"},
      {assessmentId:"5.3",methodIndex:19,name:"Unadjusted safety arithmetic audit"},
    ],
    endpoints,positivePublishedEndpointSignals:endpoints.filter(e=>e.directionalPass).length,
    primaryEndpointSignalsOutOf:2,
    safety:safetySignals,treatedArmExcessInDescriptiveSafety:safetySignals.filter(x=>x.imbalanceTowardTreated).length,
    safetyOutOf:2,
    seriousHeartFailureReconciliation:"UNRESOLVED_11_1_VS_12_3",
    lockedSapVerified:false,clinicalImportanceVerified:false,
    officialMethodGrade:null,provisionalClinicalGrade:null,
    independentClinicalReview:false,
    fdaPrediction:"ABSTAIN",calibratedAccuracy:null,probability:null,
    limitations:[
      "Published point estimates and 95% CIs are rounded. Approximate standard errors are descriptive normal-approximation checks, not a replacement for the original statistical analysis plan.",
      "A favorable reported CI direction and p-value do not establish clinically important benefit, independent multiplicity verification, endpoint robustness or approval probability.",
      "Safety differences use raw randomized denominators and no time-at-risk or covariate adjustment; observed imbalance is not independently adjudicated drug causality.",
      "Separate serious-heart-failure adverse-event reports of 11/1 and 12/3 cannot be reconciled without original coding, populations and observation windows; no composite safety score is released."
    ]
  };
}
