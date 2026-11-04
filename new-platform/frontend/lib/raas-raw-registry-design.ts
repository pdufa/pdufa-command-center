/** An exploratory numeric grade of OBSERVABLE Phase 3 study design, NOT a
 * validated RAAS 60-metric composite or FDA/clinical success probability.
 *
 * Uses four predeclared, source-observable design dimensions. A dimension
 * absent from the ClinicalTrials.gov receipt stays unknown, never zero.
 * The observed-only grade must accompany denominator and feasible bound.
 * This is a measurement-aid for deeper manual RAAS review, not the 30-metric
 * scientific efficacy or investment-rating output.
 */
import type {RegistryTrialEvidence} from "./raas-registry-evidence";

export type DesignFacet={
 id:"primary_endpoint"|"allocation"|"masking"|"control";
 name:string;status:"OBSERVED_FAVORABLE"|"OBSERVED_LIMITATION"|"UNKNOWN";
 evidence:string;
};
export type RawDesignDiagnostic={
 nctId:string;ticker:string;sourceUrl:string;retrievedAt:string;ruleVersion:"raas-registry-design-v1";
 kind:"RESEARCH_DESIGN_DIAGNOSTIC_NOT_OVERALL_RAAS";
 score:0|25|50|75|100|null;
 knownFacets:number;unknownFacets:number;totalFacets:4;
 lowerBound:number;upperBound:number;
 facets:readonly DesignFacet[];
 overallRaasScore:null;
};
const positive=(s:unknown)=>typeof s==="string"?s.trim().toUpperCase():"";
const facet=(id:DesignFacet["id"],name:string,observed:boolean|null,evidence:string):DesignFacet=>({
 id,name,status:observed===null?"UNKNOWN":observed?"OBSERVED_FAVORABLE":"OBSERVED_LIMITATION",evidence
});
const controlNames=/(?:placebo|sham|active\s*(?:comparator|control)|standard\s*of\s*care|best\s*supportive\s*care)/i;
export function rawRaasRegistryDesignDiagnostic(
 registry:RegistryTrialEvidence|null,trial:{nctId:string;ticker:string}
):RawDesignDiagnostic|null{
 if(!registry||registry.nctId!==trial.nctId||
  registry.ticker.trim().toLowerCase()!==trial.ticker.trim().toLowerCase()||
  !/^NCT\d{8}$/.test(trial.nctId))return null;
 const design=registry.registeredDesign||null;
 const allocation=positive(design?.allocation),masking=positive(design?.masking);
 const model=positive(design?.interventionModel);
 const labels=registry.registeredInterventions||[];
 const primary=registry.primaryDefinitions||[];
 const completeEndpoint=primary.some(x=>x.measure.trim()&&x.timeFrame.trim());
 const endpoint: boolean|null=completeEndpoint?true:primary.length===0?null:false;
 const random: boolean|null=allocation==="RANDOMIZED"?true:
  ["NON_RANDOMIZED","NA"].includes(allocation)?false:null;
 const blinded: boolean|null=["DOUBLE","TRIPLE","QUADRUPLE"].includes(masking)?true:
  ["NONE","SINGLE"].includes(masking)?false:null;
 const explicitControl=labels.some(s=>controlNames.test(s));
 const comparator: boolean|null=explicitControl?true:model==="SINGLE_GROUP"?false:null;
 const facets=[
  facet("primary_endpoint","Defined primary endpoint and time frame",endpoint,
   primary.length?primary.slice(0,2).map(x=>x.measure+" / "+x.timeFrame).join("; "):"Not recorded"),
  facet("allocation","Randomized allocation",random,allocation||"Not reported"),
  facet("masking","Double or greater masking",blinded,masking||"Not reported"),
  facet("control","Explicit placebo, sham or standard comparator",comparator,
   explicitControl?labels.filter(s=>controlNames.test(s)).join("; "):model||"Not verifiable")
 ] as const;
 const yes=facets.filter(x=>x.status==="OBSERVED_FAVORABLE").length;
 const known=facets.filter(x=>x.status!=="UNKNOWN").length;
 const unknown=4-known;
 const score=known>=2?
  (Math.round(yes/known*4)*25 as 0|25|50|75|100):null;
 return {nctId:trial.nctId,ticker:trial.ticker,sourceUrl:registry.sourceUrl,
  retrievedAt:registry.retrievedAt,ruleVersion:"raas-registry-design-v1",
  kind:"RESEARCH_DESIGN_DIAGNOSTIC_NOT_OVERALL_RAAS",
  score,knownFacets:known,unknownFacets:unknown,totalFacets:4,
  lowerBound:yes*25,upperBound:(yes+unknown)*25,facets,overallRaasScore:null};
}
