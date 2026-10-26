/**
 * Minimal read-only extraction from the public ClinicalTrials.gov API v2.
 *
 * Nothing here verifies commercial development, sponsor ownership,
 * US FDA decisions, PDUFA targets, or Pipeline restriction eligibility.
 * The API record is a research SOURCE, not an FDA outcome.
 */
export const REGISTRY_SOURCE_ORIGIN = "https://clinicaltrials.gov";
export type RegistryResearchRecord = {
  nctId: string;
  recordUrl: string;
  apiRecordUrl: string;
  queriedAt: string;
  sourceUpdated: string | null;
  title: string;
  registryOverallStatus: string;
  registryLeadSponsor: string | null;
  phase3CurrentlyReported: boolean;
  reportedPhases: string[];
  conditions: string[];
  interventions: {type: string; name: string}[];
  verifiedUsFdaPdufa: false;
  verifiedCommercialDevelopment: false;
  verifiedPipelineQualification: false;
  qualifiedPipelineTotal: null;
  approvalProbability: null;
};

type JsonObject = Record<string,unknown>;
function record(value:unknown):value is JsonObject {
  return value!==null && typeof value==="object" && !Array.isArray(value);
}
function safeString(value: unknown, maxLength=260): string | null {
  return typeof value==="string" && value.length>0 && value.length<=maxLength
    && !/[\u0000-\u001f\u007f<>\u202a-\u202e\u2066-\u2069]/u.test(value)
    ? value.trim() || null : null;
}
function safeStringArray(input:unknown, maxRows:number, maxLength=260):string[] {
  if(input===undefined || input===null) return [];
  if(!Array.isArray(input) || input.length>maxRows) throw new Error("Invalid registry research-source response");
  return input.map(value=>{
    const s=safeString(value,maxLength);
    if(!s) throw new Error("Invalid registry research-source response");
    return s;
  });
}

/**
 * A parser cannot certify authorship or substantive accuracy of the source.
 * It only enforces identity/structure and strips unsafe/unbounded content.
 */
export function normalizeRegistryResearchRecord(
  payload:unknown, expectedNctId:string, queriedAt:string,
):RegistryResearchRecord {
  if(!/^NCT\d{8}$/.test(expectedNctId)
    || !Number.isFinite(Date.parse(queriedAt))
    || !record(payload) || !record(payload.protocolSection)) {
    throw new Error("Invalid registry research-source response");
  }
  const section=payload.protocolSection;
  const identity=section.identificationModule;
  const status=section.statusModule;
  if(!record(identity)||!record(status)
    || identity.nctId!==expectedNctId
    || !safeString(identity.briefTitle,1000)
    || !safeString(status.overallStatus,80)) {
    throw new Error("Registry identity/status mismatch: research source withheld");
  }
  const updated=status.lastUpdatePostDate;
  if(updated!==undefined && updated!==null
    && (typeof updated!=="string" || !/^\d{4}-\d{2}-\d{2}$/.test(updated)
        || !Number.isFinite(Date.parse(updated)))) {
    throw new Error("Invalid registry research-source response");
  }
  const phasesModule=section.designModule;
  if(phasesModule!==undefined && !record(phasesModule)) throw new Error("Invalid registry research-source response");
  const phases=safeStringArray(record(phasesModule)?phasesModule.phases:undefined,5,60);
  const conditionsModule=section.conditionsModule;
  if(conditionsModule!==undefined && !record(conditionsModule)) throw new Error("Invalid registry research-source response");
  const conditions=safeStringArray(record(conditionsModule)?conditionsModule.conditions:undefined,25);
  const arms=section.armsInterventionsModule;
  if(arms!==undefined && !record(arms)) throw new Error("Invalid registry research-source response");
  const interventionValues=record(arms)?arms.interventions:undefined;
  if(interventionValues!==undefined
    && (!Array.isArray(interventionValues) || interventionValues.length>40)) {
    throw new Error("Invalid registry research-source response");
  }
  const interventions=(Array.isArray(interventionValues)?interventionValues:[]).map(entry=>{
    if(!record(entry)) throw new Error("Invalid registry research-source response");
    const type=safeString(entry.type,80),name=safeString(entry.name,260);
    if(!type || !name) throw new Error("Invalid registry research-source response");
    return {type,name};
  });
  const sponsorModule=section.sponsorCollaboratorsModule;
  if(sponsorModule!==undefined && !record(sponsorModule))
    throw new Error("Invalid registry research-source response");
  const sponsor=record(sponsorModule)?sponsorModule.leadSponsor:undefined;
  if(sponsor!==undefined && !record(sponsor))throw new Error("Invalid registry research-source response");
  const lead=record(sponsor)?safeString(sponsor.name,260):null;

  return {
    nctId:expectedNctId,
    recordUrl:REGISTRY_SOURCE_ORIGIN+"/study/"+expectedNctId,
    apiRecordUrl:REGISTRY_SOURCE_ORIGIN+"/api/v2/studies/"+expectedNctId,
    queriedAt,
    sourceUpdated:(updated as string|null|undefined) ?? null,
    title:safeString(identity.briefTitle,1000)!,
    registryOverallStatus:safeString(status.overallStatus,80)!,
    registryLeadSponsor:lead,
    phase3CurrentlyReported:phases.includes("PHASE3"),
    reportedPhases:phases,
    conditions,
    interventions,
    verifiedUsFdaPdufa:false,
    verifiedCommercialDevelopment:false,
    verifiedPipelineQualification:false,
    qualifiedPipelineTotal:null,
    approvalProbability:null,
  };
}
