/** Read-only official-source identity probes for MAIN's pilot documentary checklists.
 *
 * Do not promote registry/pubmed metadata to clinical evidence or reviewer events.
 * The recorded source packet is immutable; a changed identity flags a discrepancy,
 * not automatic approval/efficacy/signoff.
 */
import {evaluatePilotReadiness,evaluateAdditionalPilotReadiness} from "./pilot-research-readiness";

export type ProbeStatus="MATCH"|"CHANGED"|"UNAVAILABLE";
export type Probe={
  sourceId:"REGISTRY"|"NEJM_PIVOTAL";
  status:ProbeStatus;
  observedAt:string;
  sourceUrl:string;
  message:string;
};
export const ACACIA_NCT="NCT06081894";
export const REGISTRY_API_URL="https://clinicaltrials.gov/api/v2/studies/NCT06081894";
export const PUBMED_INDEX_API_URL="https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID%3A42663312&format=json&pageSize=5";
const SOURCE_IDS=["REGISTRY","NEJM_PIVOTAL"] as const;
type SourceSnapshot={
 nct:string;
 phaseIndependentReviewerVerified:boolean;
 scientificFramework:{independentlyGradedMethodPositions:number;positions:number};
 finalDecision:{approval:string;crl:string;reviewDelay:string;certainty:string;calibratedAccuracy:null};
 provisionalResearchScore:Parameters<typeof evaluatePilotReadiness>[0]["provisionalResearchScore"];
 additionalProvisionalResearchScores:NonNullable<Parameters<typeof evaluateAdditionalPilotReadiness>[0]["additionalProvisionalResearchScores"]>;
 sources:Parameters<typeof evaluatePilotReadiness>[0]["sources"];
 publishedPrimary:NonNullable<Parameters<typeof evaluateAdditionalPilotReadiness>[0]["publishedPrimary"]>;
 descriptiveSafety:NonNullable<Parameters<typeof evaluateAdditionalPilotReadiness>[0]["descriptiveSafety"]>;
};
function object(value:unknown):Record<string,unknown>|null {
  return value!==null&&typeof value==="object"&&!Array.isArray(value)?value as Record<string,unknown>:null;
}
function inner(obj:unknown,key:string):Record<string,unknown>|null {
  const x=object(obj);return x?object(x[key]):null;
}
export function registryIdentityValid(input:unknown):boolean{
  const protocol=inner(input,"protocolSection");
  const id=inner(protocol,"identificationModule");
  const design=inner(protocol,"designModule");
  const name=String(id?.briefTitle??"")+" "+String(id?.officialTitle??"");
  return id?.nctId===ACACIA_NCT&&
    Array.isArray(design?.phases)&&design.phases.includes("PHASE3")&&
    /(?:ACACIA|nonobstructive)/i.test(name);
}
export function publicationIdentityValid(input:unknown):boolean{
  const list=inner(input,"resultList")?.result;
  if(!Array.isArray(list))return false;
  return list.some((row:unknown)=>{
    const r=object(row);
    if(!r)return false;
    const title=String(r.title??"");
    return (String(r.pmid??r.id)==="42663312")&&
      /aficamten/i.test(title)&&/hypertrophic cardiomyopathy/i.test(title);
  });
}
export const pinnedSourceUrls={REGISTRY:REGISTRY_API_URL,NEJM_PIVOTAL:PUBMED_INDEX_API_URL} as const;

export function evaluateSourceRefresh(snapshot:SourceSnapshot,probes:Probe[],verifiedAt:string){
  const original=evaluatePilotReadiness(snapshot);
  const extra=evaluateAdditionalPilotReadiness(snapshot);
  if(!original||!extra||extra.length!==2||!/^\d{4}-\d{2}-\d{2}T/.test(verifiedAt))return null;
  if(probes.length!==2||probes.some((p,i)=>p.sourceId!==SOURCE_IDS[i]||
      p.sourceUrl!==pinnedSourceUrls[p.sourceId]||
      !["MATCH","CHANGED","UNAVAILABLE"].includes(p.status)))return null;
  const statuses=probes.map(p=>p.status);
  const currentness=statuses.includes("CHANGED")?"REVIEW_REQUIRED":
    statuses.includes("UNAVAILABLE")?"PARTIALLY_UNAVAILABLE":"SOURCE_IDENTITIES_MATCH";
  const cards=[
    {assessmentId:original.assessmentId,methodIndex:1,
      points:original.points,outOf:5,label:original.label},
    ...extra.map(x=>({assessmentId:x.assessmentId,methodIndex:1,points:x.points,outOf:5,label:x.label}))
  ];
  return {
    schema:"MAIN_PILOT_DOCUMENTARY_REFRESH_V1" as const,
    nct:ACACIA_NCT,
    observedAt:verifiedAt,
    evidenceSnapshotAsOf:original.sourceDate,
    mode:"ON_VIEW_REFRESH_NOT_BACKGROUND_SCAN" as const,
    currentness,
    probes,
    cards,
    researchOnly:true as const,
    officialClinicalMethodGrades:0 as const,
    independentPhaseVerified:false as const,
    fdaPrediction:"ABSTAIN" as const,
    accuracy:"NOT_CALIBRATED" as const,
    automaticClinicalRescore:false as const,
    note:"Automatically re-evaluated dated documentary checklists and two source identities. An updated document, SAP or safety finding requires evidence review before changing a verified checklist gate."
  };
}
