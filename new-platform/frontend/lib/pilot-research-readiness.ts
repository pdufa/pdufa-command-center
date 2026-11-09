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
