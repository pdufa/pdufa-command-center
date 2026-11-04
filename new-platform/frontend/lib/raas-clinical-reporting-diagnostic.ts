/** Source-reporting completeness, not clinical merit, treatment benefit,
 * safety, FDA probability, or a RAAS clinical/financial metric.
 * Five predeclared documented facts *only when trial results were posted*.
 */
import type {RegistryTrialEvidence} from "./raas-registry-evidence";

export type RaasClinicalReportingDiagnostic={
 readonly nctId:string;readonly ticker:string;readonly sourceUrl:string;
 readonly kind:"CLINICAL_RESULTS_DOCUMENTATION_NOT_RAAS";
 readonly score:0|20|40|60|80|100|null;
 readonly documentedOf5:number|null;
 readonly facets:Readonly<{
  primaryArmMeasurements:boolean;identifiedGroupContrast:boolean;
  primaryConfidenceLimits:boolean;statisticalResult:boolean;
  observedSeriousEventDenominators:boolean
 }>;
 readonly fullRaasScore:null;
};
const numeric=(v:unknown)=>typeof v==="string"&&
 /^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?$/i.test(v.trim());
const usableRate=(g:{numAffected?:number|null;numAtRisk?:number|null})=>
 Number.isInteger(g.numAffected)&&Number.isInteger(g.numAtRisk)&&
 g.numAtRisk!>0&&g.numAtRisk!<=1000000&&
 g.numAffected!>=0&&g.numAffected!<=g.numAtRisk!;
export function raasClinicalReportingDiagnostic(
 evidence:RegistryTrialEvidence|null,
 trial:{nctId:string;ticker:string}
):RaasClinicalReportingDiagnostic|null{
 if(!evidence||evidence.nctId!==trial.nctId||
  evidence.ticker.trim().toLowerCase()!==trial.ticker.trim().toLowerCase())return null;
 const primary=evidence.primaryResults||[];
 const analyses=primary.flatMap(out=>(out.comparisons||[]).filter(a=>
  Array.isArray(a.groupIds)&&a.groupIds.length>=2&&
  a.groupIds.every(g=>typeof g==="string"&&!!g.trim())));
 const facets={
  primaryArmMeasurements:primary.some(out=>(out.measurements||[]).length>0),
  identifiedGroupContrast:analyses.length>0,
  primaryConfidenceLimits:analyses.some(a=>numeric(a.ciLowerLimit)&&numeric(a.ciUpperLimit)),
  statisticalResult:analyses.some(a=>!!a.pValue?.trim()||numeric(a.paramValue)),
  observedSeriousEventDenominators:(evidence.seriousEventDetails||[]).some(
   event=>event.groups.some(usableRate))
 };
 const documented=Object.values(facets).filter(Boolean).length;
 return {nctId:trial.nctId,ticker:trial.ticker,sourceUrl:evidence.sourceUrl,
  kind:"CLINICAL_RESULTS_DOCUMENTATION_NOT_RAAS",
  score:evidence.postedResults?(documented*20 as 0|20|40|60|80|100):null,
  documentedOf5:evidence.postedResults?documented:null,
  facets,fullRaasScore:null};
}
