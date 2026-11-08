/** Trial-specific direct-comparison evidence; independent of all survey systems. */
import type {PipelineResearchRow} from "./pipeline-research-view";
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

