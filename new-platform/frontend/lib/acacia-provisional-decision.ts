/** Research-only source-gated ACACIA provisional pathway analysis.
 * Neither official method grades nor FDA approval probabilities are produced. */
export type ScenarioInputs={
  filing:"PLANNED"|"FDA_ACCEPTED";
  sap:"UNVERIFIED"|"RECONCILED"|"MATERIAL_ISSUE";
  safety:"UNRESOLVED"|"MANAGEABLE"|"MATERIAL_CONCERN";
  review:"PENDING"|"SUPPORTIVE"|"ADVERSE";
};
export type ResearchFinding={domain:string;status:string;description:string;sourceUrl:string|null};
export type ProvisionalSynthesis={
  nct:"NCT06081894";asOf:string;direction:"EFFICACY_FAVORABLE_SAFETY_REGULATORY_UNRESOLVED";
  uncertainty:"HIGH_UNQUANTIFIED";positivePrimaryEndpoints:2;
  sourceMappedMethods:18;officialGrades:0;findings:ResearchFinding[];
  fdaOutcomes:{APPROVAL:"ABSTAIN";CRL:"ABSTAIN";REVIEW_DELAY:"ABSTAIN"};
  approvalProbability:null;accuracy:null;scientificSignoff:false;
  modelKind:"RESEARCH_RULE_NOT_TRAINED";
};
export type ScenarioResult={
  class:"PRE_FILING"|"CONDITIONAL_APPROVAL_PATH"|"REGULATORY_CONCERN_PATH"|"ADDITIONAL_REVIEW_PATH";
  meaning:string;hypothetical:true;probability:null;accuracy:null;fdaOutcome:"ABSTAIN";
};
const NEJM="https://pubmed.ncbi.nlm.nih.gov/42663312/";
const SEC="https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm";
const ok=(a:unknown,b:number)=>typeof a==="number"&&Number.isFinite(a)&&Math.abs(a-b)<0.0000001;
const diff=(a:number,na:number,b:number,nb:number)=>Math.round((a/na-b/nb)*10000)/100;
export function evaluateProvisionalEvidence(input:unknown):ProvisionalSynthesis|null{
  if(!input||typeof input!=="object"||Array.isArray(input))return null;
  const p=input as Record<string,any>;
  const z=p.scientificFramework, f=p.finalDecision, n=p.publishedPrimary, cycle=p.fdaCycle;
  if(p.nct!=="NCT06081894"||p.trial!=="ACACIA-HCM"||p.protocolCode!=="CY 6033"||
    p.indication!=="symptomatic nonobstructive hypertrophic cardiomyopathy"||
    p.phaseReported!=="PHASE3"||p.phaseIndependentReviewerVerified!==false||
    !/^20\d{2}-\d{2}-\d{2}$/.test(p.asOf??"")||
    z?.positions!==800||z?.mappedCandidateMethodLeads!==18||
    z?.independentlyGradedMethodPositions!==0||z?.currentPhaseReviewSignoffs!==0||
    f?.approval!=="ABSTAIN"||f?.crl!=="ABSTAIN"||f?.reviewDelay!=="ABSTAIN"||
    f?.certainty!=="NOT_VALIDATED"||f?.calibratedAccuracy!==null||
    f?.calibratedProbabilities!==null)return null;
  if(n?.publication!==NEJM||p.sources?.NEJM_PIVOTAL?.url!==NEJM||
    p.sources?.SEC_10Q?.url!==SEC||n.randomized?.aficamten!==258||
    n.randomized?.placebo!==259||n.finalSapVerified!==false||
    n.clinicalImportanceReviewed!==false||n.sponsorReportedInitialAlphaEach!==0.025||
    !ok(n.kccq?.difference,3)||!ok(n.kccq?.pValueRounded,0.02)||
    n.kccq?.ci95?.[0]!==0.5||n.kccq?.ci95?.[1]!==5.5||
    !ok(n.peakVo2?.difference,0.67)||!ok(n.peakVo2?.pValue,0.003)||
    n.peakVo2?.ci95?.[0]!==0.22||n.peakVo2?.ci95?.[1]!==1.11)return null;
  if(cycle?.status!=="PLANNED_NOT_ESTABLISHED_FILED_AS_OF_2026_11_04"||
    cycle?.date!==null||cycle?.app!=="ACACIA_HCM_NHCM_SNDA"||
    cycle?.source!==SEC||cycle?.otherIndicationPdufaMustNotCopy!==true)return null;
  if(!Array.isArray(p.criticalAssessmentEvidence)||p.criticalAssessmentEvidence.length!==11)return null;
  const mapped=new Set<string>();
  for(const a of p.criticalAssessmentEvidence){
    if(!/^[1-8]\.[1-5]$/.test(a.id)||!Array.isArray(a.candidateMethodIndices)||
      a.candidateMethodIndices.length<1||!Array.isArray(a.sourceLeadIds)||
      a.sourceLeadIds.length<1)return null;
    for(const method of a.candidateMethodIndices){
      if(!Number.isInteger(method)||method<1||method>20)return null;
      const id=a.id+"-L"+method;
      if(mapped.has(id))return null;
      mapped.add(id);
    }
  }
  if(mapped.size!==18||!mapped.has("5.1-L12")||!mapped.has("5.3-L19"))return null;
  const rows=p.descriptiveSafety;
  if(!Array.isArray(rows)||rows.length!==3)return null;
  const check=(metric:string,a:number,b:number,rd:number,src:string)=>{
    const r=rows.find((x:any)=>x.metric===metric);
    return r&&r.treated===a&&r.treatedN===258&&r.control===b&&r.controlN===259&&
      r.source===src&&ok(r.unadjustedRiskDifferencePp,rd)&&ok(diff(a,258,b,259),rd);
  };
  if(!check("LVEF_BELOW_50_PERCENT",27,2,9.69,NEJM)||
    !check("ANY_SERIOUS_ADVERSE_EVENT",52,38,5.48,NEJM)||
    !check("SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE",12,3,3.49,SEC)||
    rows.find((x:any)=>x.metric==="SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE")?.sourceDiscrepancy!=="SECONDARY_PAPER_REPORTS_11_VS_1")return null;
  return {
    nct:"NCT06081894",asOf:p.asOf,direction:"EFFICACY_FAVORABLE_SAFETY_REGULATORY_UNRESOLVED",
    uncertainty:"HIGH_UNQUANTIFIED",positivePrimaryEndpoints:2,sourceMappedMethods:18,officialGrades:0,
    findings:[
      {domain:"Published primary efficacy",status:"FAVORABLE_REPORTED",description:"Two positive co-primary treatment differences; clinical importance and locked SAP not independently adjudicated.",sourceUrl:NEJM},
      {domain:"Left ventricular function and serious AEs",status:"SAFETY_REVIEW_REQUIRED",description:"LVEF below 50%: 27/258 vs 2/259; all serious AEs: 52/258 vs 38/259. Descriptive, not causal estimates.",sourceUrl:NEJM},
      {domain:"Heart failure event reconciliation",status:"DISCREPANCY_OPEN",description:"Secondary 11/1 vs sponsor-reported 12/3 counts need original population and follow-up definitions.",sourceUrl:SEC},
      {domain:"Statistical analysis plan",status:"FINAL_LOCKED_SAP_UNVERIFIED",description:"Missing exact locked SAP and primary missing-data and multiplicity verification.",sourceUrl:NEJM},
      {domain:"FDA application",status:"EXACT_NHCM_FILING_PLANNED",description:"November 4 issuer filing described Q4 nHCM submission as planned; do not borrow obstructive HCM PDUFA date.",sourceUrl:SEC},
      {domain:"Independent science and calibration",status:"NOT_YET_VALIDATED",description:"Zero signed method grades and no independent outcome-model calibration.",sourceUrl:null}
    ],
    fdaOutcomes:{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"},
    approvalProbability:null,accuracy:null,scientificSignoff:false,modelKind:"RESEARCH_RULE_NOT_TRAINED"
  };
}
export function simulateHypotheticalPath(x:ScenarioInputs):ScenarioResult|null{
  if(!x||!["PLANNED","FDA_ACCEPTED"].includes(x.filing)||
    !["UNVERIFIED","RECONCILED","MATERIAL_ISSUE"].includes(x.sap)||
    !["UNRESOLVED","MANAGEABLE","MATERIAL_CONCERN"].includes(x.safety)||
    !["PENDING","SUPPORTIVE","ADVERSE"].includes(x.review))return null;
  const concerned=x.sap==="MATERIAL_ISSUE"||x.safety==="MATERIAL_CONCERN"||x.review==="ADVERSE";
  const kind:ScenarioResult["class"]=concerned?"REGULATORY_CONCERN_PATH":
    x.filing==="PLANNED"?"PRE_FILING":
    x.sap==="RECONCILED"&&x.safety==="MANAGEABLE"&&x.review==="SUPPORTIVE"?
    "CONDITIONAL_APPROVAL_PATH":"ADDITIONAL_REVIEW_PATH";
  const meanings={
    PRE_FILING:"The exact nHCM application is not accepted under these assumptions. No regulatory review clock can be inferred.",
    CONDITIONAL_APPROVAL_PATH:"If filing is accepted, the SAP and independent benefit-risk review are supportive, an approval pathway is plausible, not assured.",
    REGULATORY_CONCERN_PATH:"Hypothetical substantive safety, method or reviewer concerns could prompt requests for data or adverse action, depending on FDA review.",
    ADDITIONAL_REVIEW_PATH:"Despite an assumed accepted application, open science and safety questions make further review possible."
  };
  return {class:kind,meaning:meanings[kind],hypothetical:true,probability:null,accuracy:null,fdaOutcome:"ABSTAIN"};
}
