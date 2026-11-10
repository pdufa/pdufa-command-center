/** Pilot-only, reproducible documentary research checklist, not a clinical score.
 * Five equal *research availability* checks can be counted without assigning
 * a biological efficacy strength grade or an FDA outcome probability.
 */
export type SourceRecord = {url:string; label:string; retrieved?:boolean; sha256?:string};
export type ResearchGate = {id:string;title:string;state:string;
  sourceId:string|null;detail:string};
export type PilotReadiness = {schema:string;assessmentId:string;methodIndex:number;
  asOf:string;label:string;basis:string;gates:ResearchGate[];
  officialClinicalGrade:number|null;reviewerSignedOff:boolean;approvalProbability:number|null;interpretation:string};
type ResearchSnapshot={nct:string;phaseIndependentReviewerVerified:boolean;
  scientificFramework:{independentlyGradedMethodPositions:number; positions:number};
  finalDecision:{approval:string;crl:string;reviewDelay:string;certainty:string;calibratedAccuracy:null};
  sources:Record<string,SourceRecord>;provisionalResearchScore:PilotReadiness};

const IDs=["TRIAL_IDENTITY","ORIGINAL_PROTOCOL","PUBLISHED_PRIMARY","FINAL_LOCKED_SAP","PRIMARY_SENSITIVITY"];
const SOURCES:Record<string,string>={TRIAL_IDENTITY:"REGISTRY",
  ORIGINAL_PROTOCOL:"CTIS_AM04",PUBLISHED_PRIMARY:"NEJM_PIVOTAL"};
const FIXED_URLS:Record<string,string>={
  REGISTRY:"https://clinicaltrials.gov/study/NCT06081894",
  NEJM_PIVOTAL:"https://pubmed.ncbi.nlm.nih.gov/42663312/",
  CTIS_AM04:"https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398"
};
const FIXED_PROTOCOL_SHA256="853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8";
const PATTERN=/^[a-f0-9]{64}$/;

function validLink(src:SourceRecord|undefined):boolean {
  if(!src||typeof src.url!=="string"||typeof src.label!=="string"||!src.label)return false;
  try{const u=new URL(src.url);return u.protocol==="https:"&&!u.username&&!u.password;}catch{return false;}
}
export function evaluatePilotReadiness(value:ResearchSnapshot):{points:number;outOf:5;
  label:string;assessmentId:"5.1";methodIndex:1;checks:ResearchGate[];
  sourceDate:string;officialClinicalGrade:null;fdaPrediction:"ABSTAIN";
  scoreKind:"DOCUMENTARY_RESEARCH_CHECKLIST_NOT_CLINICAL_GRADE"}|null {
  if(!value||value.nct!=="NCT06081894"||value.phaseIndependentReviewerVerified!==false||
      value.scientificFramework?.positions!==800||
      value.scientificFramework?.independentlyGradedMethodPositions!==0||
      value.finalDecision?.approval!=="ABSTAIN"||
      value.finalDecision?.crl!=="ABSTAIN"||
      value.finalDecision?.reviewDelay!=="ABSTAIN"||
      value.finalDecision?.certainty!=="NOT_VALIDATED"||
      value.finalDecision?.calibratedAccuracy!==null)return null;
  const x=value.provisionalResearchScore;
  if(!x||x.schema!=="MAIN_RESEARCH_DOCUMENT_READINESS_V1"||x.assessmentId!=="5.1"||
    x.methodIndex!==1||x.officialClinicalGrade!==null||
    x.reviewerSignedOff!==false||x.approvalProbability!==null||
    x.basis!=="FIVE_EQUALLY_WEIGHTED_DOCUMENTARY_CHECKS_NOT_CLINICAL_METHOD_QUALITY"||
    !/^2026-\d\d-\d\d$/.test(x.asOf)||
    !Array.isArray(x.gates)||x.gates.length!==5||
    typeof x.interpretation!=="string"||x.interpretation.length<40)return null;
  for(let i=0;i<5;i++){
    const g=x.gates[i],expected=IDs[i];
    if(!g||g.id!==expected||!g.title||!g.detail||
      !["RESEARCH_OBSERVED","NOT_VERIFIED"].includes(g.state))return null;
    if(g.state==="RESEARCH_OBSERVED"){
      if(!g.sourceId||g.sourceId!==SOURCES[expected]||!validLink(value.sources[g.sourceId])||
         value.sources[g.sourceId].url!==FIXED_URLS[g.sourceId])return null;
      // The official protocol must retain its content digest and capture receipt.
      if(g.id==="ORIGINAL_PROTOCOL"&&
        (value.sources[g.sourceId].retrieved!==true||
         !PATTERN.test(value.sources[g.sourceId].sha256||"")||
         value.sources[g.sourceId].sha256!==FIXED_PROTOCOL_SHA256))return null;
    }else if(g.sourceId!==null)return null;
  }
  // Research-only availability count, intentionally not a clinical 0–5 grade.
  const points=x.gates.filter(g=>g.state==="RESEARCH_OBSERVED").length;
  return {points,outOf:5,label:x.label,assessmentId:"5.1",methodIndex:1,
    checks:x.gates,sourceDate:x.asOf,officialClinicalGrade:null,
    fdaPrediction:"ABSTAIN",scoreKind:"DOCUMENTARY_RESEARCH_CHECKLIST_NOT_CLINICAL_GRADE"};
}


/** Phase-first additional documentary scorecards. The missing checks are pinned as
 * NOT_VERIFIED: changing one to "observed" without a new independently scoped
 * source review INVALIDATES this snapshot instead of granting a point.
 */
type AdditionalSnapshot=ResearchSnapshot & {
  publishedPrimary?:{randomized:{aficamten:number;placebo:number};
    kccq:{difference:number;ci95:number[]};peakVo2:{difference:number;ci95:number[]};
    clinicalImportanceReviewed:boolean;finalSapVerified:boolean};
  descriptiveSafety?:Array<{metric:string;treated:number;treatedN:number;
    control:number;controlN:number;sourceDiscrepancy?:string}>;
  additionalProvisionalResearchScores?:PilotReadiness[];
};
export type AdditionalReadinessResult={points:number;outOf:5;label:string;
  assessmentId:"4.2"|"5.3";methodIndex:1;checks:ResearchGate[];
  sourceDate:string;officialClinicalGrade:null;fdaPrediction:"ABSTAIN";
  scoreKind:"DOCUMENTARY_RESEARCH_CHECKLIST_NOT_CLINICAL_GRADE"};

const ADDITIONAL_SPECS=[
  {
    assessmentId:"4.2",
    ids:["SOURCE_DESIGN_AMENDMENT","CURRENT_PROTOCOL_ENDPOINTS",
      "PUBLISHED_ENDPOINT_ESTIMATES","FINAL_ENDPOINT_SAP","ENDPOINT_CLINICAL_MEANING"],
    observedSources:["ISSUER_MAY_2025","CTIS_AM04","NEJM_PIVOTAL",null,null],
  },
  {
    assessmentId:"5.3",
    ids:["PIVOTAL_SAFETY_RESULTS","SUBSEQUENT_ISSUER_SAFETY",
      "HF_EVENT_ACCOUNTING","INTERRUPTION_DENOMINATORS","ADJUDICATED_SAFETY_PACKAGE"],
    observedSources:["NEJM_PIVOTAL","SEC_10Q",null,null,null],
  },
] as const;

const ADDITIONAL_PINNED_URLS:Record<string,string>={
  ...FIXED_URLS,
  ISSUER_MAY_2025:"https://ir.cytokinetics.com/press-releases/press-release-details/2025/Cytokinetics-Reports-First-Quarter-2025-Financial-Results-and-Provides-Business-Update-05-06-2025/default.aspx",
  SEC_10Q:"https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm",
};

function supportsAdditionalOriginalEvidence(x:AdditionalSnapshot):boolean {
  const p=x.publishedPrimary;
  if(!p||p.randomized?.aficamten!==258||p.randomized?.placebo!==259||
    p.kccq?.difference!==3||JSON.stringify(p.kccq?.ci95)!=="[0.5,5.5]"||
    p.peakVo2?.difference!==0.67||JSON.stringify(p.peakVo2?.ci95)!=="[0.22,1.11]"||
    p.clinicalImportanceReviewed!==false||p.finalSapVerified!==false)return false;
  const safety=x.descriptiveSafety||[];
  const lvef=safety.find(row=>row.metric==="LVEF_BELOW_50_PERCENT");
  const anySae=safety.find(row=>row.metric==="ANY_SERIOUS_ADVERSE_EVENT");
  const hf=safety.find(row=>row.metric==="SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE");
  return !!lvef&&lvef.treated===27&&lvef.treatedN===258&&lvef.control===2&&lvef.controlN===259&&
    !!anySae&&anySae.treated===52&&anySae.treatedN===258&&anySae.control===38&&anySae.controlN===259&&
    !!hf&&hf.treated===12&&hf.treatedN===258&&hf.control===3&&hf.controlN===259&&
      hf.sourceDiscrepancy==="SECONDARY_PAPER_REPORTS_11_VS_1";
}
export function evaluateAdditionalPilotReadiness(
  value:AdditionalSnapshot
):AdditionalReadinessResult[]|null {
  // Require the existing, primary checkpoint to pass before any additional
  // research-only indexes are displayed.
  const original=evaluatePilotReadiness(value);
  if(!original||!supportsAdditionalOriginalEvidence(value))return null;
  const cards=value.additionalProvisionalResearchScores;
  if(!Array.isArray(cards)||cards.length!==2)return null;
  const results:AdditionalReadinessResult[]=[];
  for(let c=0;c<ADDITIONAL_SPECS.length;c++){
    const spec=ADDITIONAL_SPECS[c],card=cards[c];
    if(!card||card.schema!=="MAIN_RESEARCH_DOCUMENT_READINESS_V1"||
      card.assessmentId!==spec.assessmentId||card.methodIndex!==1||
      card.asOf!==original.sourceDate||
      card.basis!=="FIVE_EQUALLY_WEIGHTED_DOCUMENTARY_CHECKS_NOT_CLINICAL_METHOD_QUALITY"||
      card.officialClinicalGrade!==null||card.reviewerSignedOff!==false||
      card.approvalProbability!==null||typeof card.label!=="string"||
      card.label.length<20||typeof card.interpretation!=="string"||
      card.interpretation.length<60||
      !Array.isArray(card.gates)||card.gates.length!==5)return null;
    for(let i=0;i<5;i++){
      const g=card.gates[i],expectedSource=spec.observedSources[i];
      if(!g||g.id!==spec.ids[i]||typeof g.title!=="string"||
        g.title.length<20||typeof g.detail!=="string"||g.detail.length<45)return null;
      if(expectedSource===null){
        if(g.state!=="NOT_VERIFIED"||g.sourceId!==null)return null;
      }else{
        if(g.state!=="RESEARCH_OBSERVED"||g.sourceId!==expectedSource)return null;
        const src=value.sources[g.sourceId];
        if(!validLink(src)||src.url!==ADDITIONAL_PINNED_URLS[g.sourceId])return null;
        if(g.sourceId==="CTIS_AM04"&&
          (src.retrieved!==true||src.sha256!==FIXED_PROTOCOL_SHA256))return null;
      }
    }
    results.push({
      points:card.gates.filter(g=>g.state==="RESEARCH_OBSERVED").length,
      outOf:5,label:card.label,
      assessmentId:spec.assessmentId,methodIndex:1,
      checks:card.gates,sourceDate:card.asOf,officialClinicalGrade:null,
      fdaPrediction:"ABSTAIN",
      scoreKind:"DOCUMENTARY_RESEARCH_CHECKLIST_NOT_CLINICAL_GRADE",
    });
  }
  return results;
}
