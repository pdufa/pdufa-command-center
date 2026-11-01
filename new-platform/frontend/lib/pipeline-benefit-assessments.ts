/** Original 20 ranked post–Phase 3 benefit assessments from the user-owned Google Doc.
 * Stable presentation schema. Preserves all 38 research fields in the existing source layer.
 * An assessment's existence is NOT evidence of benefit or a validated score.
 */
import { PIPELINE_RESEARCH_FIELDS, ALL_RESEARCH_FIELD_DEFINITIONS, researchFieldResult, type PipelineResearchRow, type ResearchFieldId } from "./pipeline-research-view";
export type AssessmentSpec={rank:number;title:string;objective:string;fields:readonly ResearchFieldId[]};
export const RANKED_BENEFIT_ASSESSMENTS:readonly AssessmentSpec[]=[
 { rank:1, title:"Patient Population", objective:"Eligible treated patients by jurisdiction, age, disease stage, biomarkers, prior therapy and treatment line.", fields:["eligibleUsPatients","bestSubgroup"] },
 { rank:2, title:"Unmet Medical Need", objective:"Document residual burden, current treatment gaps, refractory and intolerant populations.", fields:["standardOfCare","unmetNeed","treatmentResistantBenefit"] },
 { rank:3, title:"Clinical Benefit", objective:"Source endpoints, effect sizes, significance, durability and patient-important differences.", fields:["clinicalBenefit","magnitude","meaningfulBenefit","durability","responseRemission","timeToResponse"] },
 { rank:4, title:"Survival Benefit", objective:"Where applicable, evaluate OS/PFS, mortality, hazard ratio, follow-up and uncertainty; do not infer benefit otherwise.", fields:["survivalBenefit"] },
 { rank:5, title:"Quality-of-Life Improvement", objective:"Use validated patient-reported outcomes, daily functioning and minimal clinically important differences.", fields:["qualityOfLife"] },
 { rank:6, title:"Competitive Advantage", objective:"Compare approved and pipeline competitors by matched indication, line and population; distinguish direct vs indirect comparisons.", fields:["closestCompetitor","competitorCount","headToHead","competitivePipelineThreat","competitiveStrategy"] },
 { rank:7, title:"Treatment Convenience", objective:"Compare administration route, frequency, care setting, monitoring, treatment line and adherence.", fields:["convenience","treatmentSequence"] },
 { rank:8, title:"Safety Advantage", objective:"Compare relevant adverse events, serious risks and discontinuation with exposure-aligned denominators.", fields:["safetyAdvantage","seriousAes","discontinuation"] },
 { rank:9, title:"Healthcare Cost Savings", objective:"Assess patient-important cost offsets, hospitalizations, treatment cost differences and value per outcome.", fields:["hospitalizationReduction","costDifference","valuePerOutcome"] },
 { rank:10, title:"Insurance Coverage Potential", objective:"Source coverage policy, payer barriers and reimbursement conditions; distinguish prospective from active coverage.", fields:["payerAccess"] },
 { rank:11, title:"Expected Treatment Price", objective:"Source or explicitly model comparable net treatment pricing, duration and payer basis; no unsourced launch prices.", fields:["treatmentPrice"] },
 { rank:12, title:"Market Penetration", objective:"Model uptake from the actual eligible patient pool, treatment switching and addressable starts.", fields:["adoption","switchingPool"] },
 { rank:13, title:"International Patient Population", objective:"Break down eligible non-US populations and separate foreign regulatory and reimbursement status.", fields:["internationalPatients"] },
 { rank:14, title:"Additional Indications", objective:"Track adjacent indication-specific trial programs, distinct NCTs and required regulatory pathways.", fields:["additionalIndications"] },
 { rank:15, title:"Peak Annual Sales", objective:"Use explicit low/base/high uptake × net price × duration calculations and source territorial rights.", fields:["peakAnnualSales"] },
 { rank:16, title:"Revenue Growth Potential", objective:"Model launch ramp, new starts, persistence, price and competition over time with scenarios.", fields:["revenueGrowth"] },
 { rank:17, title:"Patent and Exclusivity Value", objective:"Check patent claims, expiry, regulatory exclusivity, challenges and market-entry timing.", fields:["exclusivity"] },
 { rank:18, title:"Licensing and Partnership Value", objective:"Check geographic commercial rights, partner identity, royalties, milestone and SEC agreement details.", fields:["licensingValue"] },
 { rank:19, title:"Company Valuation Impact", objective:"Model product-level risk-adjusted value versus enterprise value, dilution and assets; separate FDA probability.", fields:["valuationImpact"] },
 { rank:20, title:"Shareholder Upside and Risk", objective:"Model bear/base/bull scenarios, financing, liquidity and dilution without implying a trade recommendation.", fields:["shareholderRisk"] },
];
export const CROSS_CUTTING_RESEARCH_FIELDS:readonly ResearchFieldId[]=["trialId","company","therapy","indication","daysSinceReadout","daysToPdufa","evidence","verdict","overallRank"];
const assigned=new Set<string>(RANKED_BENEFIT_ASSESSMENTS.flatMap(x=>x.fields));
export function auditAssessmentFieldMapping(){
 const ids=PIPELINE_RESEARCH_FIELDS.map(f=>f.id);
 const duplicates=RANKED_BENEFIT_ASSESSMENTS.flatMap(a=>a.fields).filter((id,i,all)=>all.indexOf(id)!==i);
 const unassigned=ids.filter(id=>!assigned.has(id)&&!CROSS_CUTTING_RESEARCH_FIELDS.includes(id));
 const allIds=ALL_RESEARCH_FIELD_DEFINITIONS.map(f=>f.id);
 const unknown=[...assigned,...CROSS_CUTTING_RESEARCH_FIELDS].filter(id=>!allIds.includes(id as ResearchFieldId));
 return {originalFields:ids.length,rankedAssessments:RANKED_BENEFIT_ASSESSMENTS.length,assignedFields:assigned.size,originalAssignedFields:ids.filter(id=>assigned.has(id)).length,extensionFields:ALL_RESEARCH_FIELD_DEFINITIONS.length-ids.length,crossCuttingFields:CROSS_CUTTING_RESEARCH_FIELDS.length,duplicates,unassigned,unknown};
}
export type AssessmentCoverage={rank:number;title:string;state:"NOT_ASSESSED"|"PARTIAL_EVIDENCE"|"EVIDENCE_RECORDED";verified:number;required:number;summary:string};
export function assessmentCoverage(row:PipelineResearchRow,today:string):AssessmentCoverage[]{
 return RANKED_BENEFIT_ASSESSMENTS.map(spec=>{
  const verified=spec.fields.filter(id=>researchFieldResult(row,id,today).state==="VERIFIED").length;
  const state=verified===0?"NOT_ASSESSED":verified===spec.fields.length?"EVIDENCE_RECORDED":"PARTIAL_EVIDENCE";
  // Definitions never establish clinical findings: do not falsely complete them based on zero mapped fields.
  const summary=spec.fields.length===0?"Research inputs not implemented / not assessed":
   verified===0?"No verified assessment inputs":verified+" of "+spec.fields.length+" supporting inputs have verified sources; no automatic competitive score";
  return {rank:spec.rank,title:spec.title,state:spec.fields.length===0?"NOT_ASSESSED":state,verified,required:spec.fields.length,summary};
 });
}
export type CompetitorKind="APPROVED"|"PIPELINE";
export type ComparisonBasis="DIRECT_HEAD_TO_HEAD"|"INDIRECT"|"NOT_COMPARABLE";
export type ComparativeFinding="BETTER"|"SIMILAR"|"WORSE"|"MIXED"|"INSUFFICIENT_EVIDENCE";
export type ComparatorEvidence={
 programNctId:string;programTicker:string;indication:string;
 programTherapy?:string;verificationStatus?:"VERIFIED";lastVerified?:string;
 comparisonEvidence?:{parentTherapy:string;lineOfTherapy:string;patientPopulation:string;endpoint:string;effectEstimate:number;lower95:number;upper95:number;denominator:number;comparatorDenominator:number;followUpMonths:number;sourceUrl:string;verifiedAt:string};
 id:string;kind:CompetitorKind;therapy:string;manufacturer:string;
 /** FDA NDA/BLA identifier for approved products; exact NCT for investigational comparators. */
 regulatorOrTrialId:string;approvalOrPhase:string;
 lineOfTherapy:string;patientPopulation:string;
 sourceUrl:string;sourceDate:string;sourceType:"FDA"|"CLINICAL_TRIALS"|"PUBLICATION"|"SEC"|"SPONSOR";
 outcome:string;effectSize:string;duration:string;safety:string;convenience:string;
 firstYearPrice:string;payerAccess:string;
 comparisonBasis:ComparisonBasis;finding:ComparativeFinding;reason:string;
 confidence:"HIGH"|"MODERATE"|"LOW";
};
export type ComparatorInventoryResult={accepted:ComparatorEvidence[];rejected:number;approved:number;pipeline:number;rankingAllowed:boolean;issues:string[]};
function validDate(date:string):boolean{
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date))return false;
 const parsed=new Date(date+"T00:00:00Z");
 return Number.isFinite(parsed.getTime())&&parsed.toISOString().slice(0,10)===date&&parsed.getTime()<=Date.now();
}
/** Fail closed: matching disease alone or a name-only comparator never establishes comparability. */
export function validateComparatorInventory(row:Pick<PipelineResearchRow,"nctId"|"ticker"|"drug"|"indication">,records:readonly ComparatorEvidence[]):ComparatorInventoryResult{
 const accepted:ComparatorEvidence[]=[];const issues:string[]=[];const seen=new Set<string>();
 let rejected=0;
 for(const c of records){
  const sourceMatch=c.programNctId===row.nctId&&c.programTicker===row.ticker&&!!row.drug&&c.programTherapy===row.drug&&
    !!row.indication&&c.indication.trim().toLowerCase()===row.indication.trim().toLowerCase();
  const validMeta=c.verificationStatus==="VERIFIED"&&validDate(c.lastVerified||"")&&c.lastVerified!>=c.sourceDate&&!!c.id?.trim()&&!!c.therapy?.trim()&&!!c.manufacturer?.trim()&&
   !!c.lineOfTherapy?.trim()&&!!c.patientPopulation?.trim()&&
   /^https:\/\/[^\s]+$/.test(c.sourceUrl||"")&&validDate(c.sourceDate||"")&&
   ["FDA","CLINICAL_TRIALS","PUBLICATION","SEC","SPONSOR"].includes(c.sourceType);
  const validKind=c.kind==="APPROVED"?!!c.regulatorOrTrialId?.trim()&&!!c.approvalOrPhase?.trim():
   c.kind==="PIPELINE"&&/^NCT\d{8}$/.test(c.regulatorOrTrialId||"")&&!!c.approvalOrPhase?.trim();
  const validComparison=["DIRECT_HEAD_TO_HEAD","INDIRECT","NOT_COMPARABLE"].includes(c.comparisonBasis)&&
   ["BETTER","SIMILAR","WORSE","MIXED","INSUFFICIENT_EVIDENCE"].includes(c.finding);
  // A directional comparative claim needs comparator-specific outcome, method, rationale.
  const directional=c.finding!=="INSUFFICIENT_EVIDENCE";
  const e=c.comparisonEvidence;
  const claimSafe=!directional||(c.comparisonBasis==="DIRECT_HEAD_TO_HEAD"&&!!c.outcome?.trim()&&!!c.reason?.trim()&&!!c.effectSize?.trim()
    &&!!e&&e.parentTherapy===row.drug&&e.lineOfTherapy===c.lineOfTherapy&&e.patientPopulation===c.patientPopulation
    &&!!e.endpoint.trim()&&Number.isFinite(e.effectEstimate)&&Number.isFinite(e.lower95)&&Number.isFinite(e.upper95)
    &&e.lower95<=e.effectEstimate&&e.effectEstimate<=e.upper95&&Number.isSafeInteger(e.denominator)&&e.denominator>0
    &&Number.isSafeInteger(e.comparatorDenominator)&&e.comparatorDenominator>0&&Number.isFinite(e.followUpMonths)&&e.followUpMonths>0
    &&/^https:\/\//.test(e.sourceUrl)&&validDate(e.verifiedAt));
  const sameProduct=c.kind==="PIPELINE"&&c.regulatorOrTrialId===row.nctId;
  const key=c.kind+"|"+c.therapy.trim().toLowerCase()+"|"+c.lineOfTherapy.toLowerCase()+"|"+c.patientPopulation.toLowerCase();
  if(!sourceMatch||!validMeta||!validKind||!validComparison||!claimSafe||sameProduct||seen.has(key)){
   rejected++;issues.push("Rejected comparator "+(c.id||"?")+": identity, source, evidence, duplicate, or comparability gap");continue;
  }
  seen.add(key);accepted.push(c);
 }
 const approved=accepted.filter(c=>c.kind==="APPROVED").length;
 const pipeline=accepted.filter(c=>c.kind==="PIPELINE").length;
 // No quantitative rank unless all compared treatments share a defined line/population,
 // with direct evidence for each and no missing outcome/effect-size.
 const comparable=accepted.length>1&&accepted.every(c=>c.comparisonBasis==="DIRECT_HEAD_TO_HEAD"
   &&c.finding!=="INSUFFICIENT_EVIDENCE"&&!!c.outcome.trim()&&!!c.effectSize.trim());
 const populationSame=new Set(accepted.map(c=>c.lineOfTherapy.trim().toLowerCase()+"|"+c.patientPopulation.trim().toLowerCase())).size===1;
 return {accepted,rejected,approved,pipeline,rankingAllowed:comparable&&populationSame,issues};
}

