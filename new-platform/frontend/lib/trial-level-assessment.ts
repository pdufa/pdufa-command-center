/** Current registry evidence adapter. Never mixes retained worksheets into a new source version. */
import {createHash,randomUUID} from 'node:crypto';
import {assessTrial} from './level16-assessment-runner';
import type {EvidenceTrial} from './level16-assessment-runner';
export const NCT=/^NCT\d{8}$/;
export class AssessmentError extends Error {constructor(message:string,public status:number){super(message);}}
export type TrialRequest={nct:string;level:number;mode:'CURRENT_EVIDENCE'|'BLIND_HISTORICAL';cutoffDate?:string};
export function parseTrialRequest(raw:unknown):TrialRequest{
 if(!raw||typeof raw!=='object'||Array.isArray(raw))throw new AssessmentError('Assessment request required',422);
 const v=raw as Record<string,unknown>;
 if(Object.keys(v).some(k=>!['nct','level','mode','cutoffDate'].includes(k))||typeof v.nct!=='string'||!NCT.test(v.nct)||!Number.isInteger(v.level)||Number(v.level)<1||Number(v.level)>6||!['CURRENT_EVIDENCE','BLIND_HISTORICAL'].includes(String(v.mode)))throw new AssessmentError('Exact NCT, level 1–6 and assessment mode required; extra fields are forbidden',422);
 if(v.mode==='BLIND_HISTORICAL'){
  const d=v.cutoffDate;
  if(typeof d!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(d)||!Number.isFinite(Date.parse(d+'T00:00:00Z'))||new Date(d+'T00:00:00Z').toISOString().slice(0,10)!==d||d>=new Date().toISOString().slice(0,10))throw new AssessmentError('Blind Historical requires a valid past cutoff date',422);
  // Current registry revisions and outcome-exposed research cannot be backdated.
  // No point-in-time outcome-unexposed evidence provider is installed.
  throw new AssessmentError('Blind Historical unavailable: no immutable outcome-isolated evidence bundle exists for this cutoff. No retrieval, scoring or prediction was performed.',409);
 }
 if('cutoffDate' in v)throw new AssessmentError('A historical cutoff cannot be applied to current evidence',422);
 return v as TrialRequest;
}
const strings=(value:unknown):string[]=>Array.isArray(value)?value.filter((s):s is string=>typeof s==='string'):[];
export function registryTrial(nct:string,raw:string,retrievedAt:string):EvidenceTrial{
 const source=JSON.parse(raw),p=source.protocolSection;
 if(p?.identificationModule?.nctId!==nct)throw new AssessmentError('Registry response does not match exact NCT',502);
 const status=p.statusModule,design=p.designModule,version=status?.lastUpdatePostDateStruct?.date;
 if(typeof version!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(version)||!Number.isFinite(Date.parse(version))||new Date(version).toISOString().slice(0,10)!==version||version>retrievedAt.slice(0,10))throw new AssessmentError('Registry version date is missing or invalid',502);
 const url='https://clinicaltrials.gov/api/v2/studies/'+nct,digest=createHash('sha256').update(raw).digest('hex');
 const phases=strings(design?.phases);
 if(phases.some(phase=>!['EARLY_PHASE1','PHASE1','PHASE2','PHASE3','PHASE4','NA'].includes(phase)))throw new AssessmentError('Registry phase is not recognized',502);
 const primary=Array.isArray(p.outcomesModule?.primaryOutcomes)?p.outcomesModule.primaryOutcomes:[];
 const population=typeof p.eligibilityModule?.eligibilityCriteria==='string'?p.eligibilityModule.eligibilityCriteria:null;
 const facts=[{text:'Registry phase and status from the exact-NCT current response',value:{phases,status:status?.overallStatus??null},locator:'protocolSection.statusModule; protocolSection.designModule',sourceUrl:url}];
 return {nct,ticker:'',company:p.sponsorCollaboratorsModule?.leadSponsor?.name||'Unknown sponsor',indications:strings(p.conditionsModule?.conditions),population,phases,registryStatus:status?.overallStatus??null,registryUrl:url,registryDigest:digest,registryVersionDate:version,retrievedAt,applicationMappingStatus:'NOT_MAPPED_APPLICATION_CYCLE',provisionalApplicationCycleIds:[],protocolCollected:false,sapCollected:false,registryResultsPresent:!!source.hasResults,reportedClinicalResultsPresent:false,design:design?.designInfo||{},primaryEndpoints:primary,sources:[{url,date:version,digest,kind:'CURRENT_REGISTRY_RESPONSE'}],levels:Array.from({length:6},(_,i)=>({level:i+1,facts,interpretation:'Registry-based research checks only. Original clinical, regulatory and indication-specific evidence has not been verified for this source version.',reasons:['Exact-NCT registry evidence retrieved on '+retrievedAt],questions:['Collect and reconcile original evidence required for this assessment level.'],limitations:['Registry entries are sponsor-reported. No FDA application identity or current filing status has been verified.','Registry results posting does not demonstrate efficacy. No quantitative clinical results have been extracted.'],contradictions:[],notYetExpected:[]})),reportedComparisons:[],publishedSafety:null,statisticalChronology:null};
}
export async function executeTrial(request:TrialRequest,signal?:AbortSignal){
 // Revalidate even for internal callers; reject historical BEFORE reading sources.
 request=parseTrialRequest(request);
 const url='https://clinicaltrials.gov/api/v2/studies/'+request.nct;
 const response=await fetch(url,{cache:'no-store',headers:{Accept:'application/json'},signal:AbortSignal.any([...(signal?[signal]:[]),AbortSignal.timeout(20000)])});
 if(!response.ok)throw new AssessmentError(response.status===404?'Trial not found in ClinicalTrials.gov':'ClinicalTrials.gov evidence retrieval failed',response.status===404?404:503);
 if(!response.headers.get('content-type')?.includes('application/json'))throw new AssessmentError('Unexpected registry response',502);
 const raw=await response.text();if(Buffer.byteLength(raw)>4_000_000)throw new AssessmentError('Registry response exceeds evidence budget',502);
 const executedAt=new Date().toISOString(),trial=registryTrial(request.nct,raw,executedAt);
 const result=assessTrial(trial,executedAt.slice(0,10),request.level);
 // The narrow retained Level 3 clinical lean is not an FDA prediction model.
 return {kind:'TRIAL_LEVEL_ASSESSMENT',runId:randomUUID(),nct:request.nct,level:request.level,mode:request.mode,executedAt,engineVersion:`phase-first-level-${request.level}-v1`,status:'PARTIAL_RESEARCH_ENGINE',savedToDatabase:false,score:null,scoreStatus:'NO_VALIDATED_SCORING_ALGORITHM',fdaPrediction:{outcome:'ABSTAIN',probability:null,calibration:'NO_VALIDATED_FDA_MODEL'},evidence:{url,sha256:trial.registryDigest,versionDate:trial.registryVersionDate,retrievedAt:executedAt,verification:'EXACT_NCT_REGISTRY_RESPONSE_ONLY',snapshot:trial},result};
}
export type SavedTrialAssessment=Awaited<ReturnType<typeof executeTrial>>&{reportHash?:string};
