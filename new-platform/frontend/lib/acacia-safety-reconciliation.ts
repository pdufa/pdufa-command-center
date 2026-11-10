/** Exact-trial source-specific safety arithmetic. NOT a clinical grade or FDA forecast. */
export type Contrast={id:string;label:string;sourceUrl:string;a:number;b:number;differencePp:number;relativeRisk:number;approximate95:[number,number];kind:string};
const PUB="https://pubmed.ncbi.nlm.nih.gov/42663312/";
const SEC="https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm";
const SPONSOR="https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-Annual-Scientific-Meeting-2026/default.aspx";
const SECONDARY="https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/";
const round=(x:number)=>Math.round((x+Number.EPSILON)*100)/100;
function pair(id:string,label:string,url:string,a:number,b:number,kind:string):Contrast{
  const rr=(a/258)/(b/259),se=Math.sqrt(1/a-1/258+1/b-1/259);
  return {id,label,sourceUrl:url,a,b,kind,differencePp:round(100*(a/258-b/259)),
    relativeRisk:round(rr),approximate95:[round(Math.exp(Math.log(rr)-1.96*se)),round(Math.exp(Math.log(rr)+1.96*se))]};
}
const obj=(x:unknown):x is Record<string,any>=>x!==null&&typeof x==="object"&&!Array.isArray(x);
function check(rows:any[],id:string,a:number,b:number,url:string){
  const x=rows.find(x=>x.metric===id);
  return x&&x.treated===a&&x.treatedN===258&&x.control===b&&x.controlN===259&&
    x.source===url&&Math.abs(x.unadjustedRiskDifferencePp-round(100*(a/258-b/259)))<0.0001;
}
export function evaluateAcaciaSafetyResearch(x:unknown){
  if(!obj(x))return null;
  const p=x,s=p.sources,rows=p.descriptiveSafety;
  if(p.nct!=="NCT06081894"||p.trial!=="ACACIA-HCM"||p.protocolCode!=="CY 6033"||
    p.phaseReported!=="PHASE3"||p.phaseIndependentReviewerVerified!==false||
    p.publishedPrimary?.randomized?.aficamten!==258||p.publishedPrimary?.randomized?.placebo!==259||
    p.publishedPrimary?.finalSapVerified!==false||p.scientificFramework?.independentlyGradedMethodPositions!==0||
    p.scientificFramework?.currentPhaseReviewSignoffs!==0||
    p.finalDecision?.approval!=="ABSTAIN"||p.finalDecision?.crl!=="ABSTAIN"||
    p.finalDecision?.reviewDelay!=="ABSTAIN"||p.finalDecision?.calibratedAccuracy!==null||
    p.finalDecision?.calibratedProbabilities!==null||
    s?.NEJM_PIVOTAL?.url!==PUB||s?.SEC_10Q?.url!==SEC||s?.RESPONDER_ANALYSIS?.url!==SECONDARY||
    !Array.isArray(rows)||rows.length!==3||!/^20\d{2}-\d{2}-\d{2}$/.test(String(p.asOf)))return null;
  if(!check(rows,"LVEF_BELOW_50_PERCENT",27,2,PUB)||
    !check(rows,"ANY_SERIOUS_ADVERSE_EVENT",52,38,PUB)||
    !check(rows,"SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE",12,3,SEC)||
    rows.find(r=>r.metric==="SPONSOR_REPORTED_SERIOUS_HEART_FAILURE_AE")?.sourceDiscrepancy!=="SECONDARY_PAPER_REPORTS_11_VS_1")return null;
  return {
    nct:"NCT06081894",sourceSnapshot:p.asOf,
    contrasts:[
      pair("LVEF","LVEF below 50%",PUB,27,2,"PIVOTAL"),
      pair("SAE","All serious adverse events",PUB,52,38,"PIVOTAL"),
      pair("HF_SPONSOR","Serious HF (sponsor definition)",SPONSOR,12,3,"SPONSOR"),
      pair("HF_SECONDARY","Serious HF (secondary paper)",SECONDARY,11,1,"SECONDARY")
    ],
    sponsorMath:{associated:2,additional:10,total:12,placebo:3},
    crossSource:"NOT_RECONCILED",finalLockedSap:"NOT_VERIFIED",
    interruption:{paperCount:14,paperPercent:2.7,randomizedDenominatorPercent:round(14/258*100),status:"DENOMINATOR_OR_PRINT_MISMATCH"},
    scientificGrade:null,clinicalSignoff:false,regulatoryDecision:"ABSTAIN",accuracy:"NOT_CALIBRATED",
    notes:"Exploratory Katz log-risk-ratio 95% intervals with randomized denominators; sparse event counts, differing source definitions, missing original safety sets and multiple comparisons preclude formal safety grading."
  };
}
