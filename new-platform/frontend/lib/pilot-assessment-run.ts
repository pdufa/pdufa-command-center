import type {DecisionIdentity} from "./decision-workstream";
import {validateDecisionIdentity} from "./decision-reviewed-manifest";
import {auditScienceInvestigation,parseScienceInvestigation,type ScienceInvestigation,type ScienceInvestigationAudit} from "./decision-science-investigation";

export type PilotIdentity={exactKey:string;nctId:string};
export type PilotRun={
 schemaVersion:1;runId:string;exactKey:string;nctId:string;drug:string;indication:string;asOf:string;
 decisionTarget:{date:string;status:"SPONSOR_REPORTED";sourceIds:string[]};
 sources:{id:string;url:string;publishedOn:string|null;observedAt:string;captureStatus:"TEXT_OBSERVED"|"UNAVAILABLE";sourceClass:string;notes:string[]}[];
 findings:{id:string;domain:string;approvalDirection:"SUPPORTS_APPROVAL"|"OPPOSES_APPROVAL"|"UNDETERMINED"|"MATERIALLY_UNCHANGED";text:string;sourceIds:string[]}[];
 history:{id:string;drug:string;nctId:string|null;applicationId:string|null;actionObserved:"APPROVAL"|"COMPLETE_RESPONSE"|"WITHDRAWN"|"UNRESOLVED";actionDate:string|null;sourceIds:string[];similarities:string[];differences:string[];modelEligible:false}[];
 science:{status:"NEEDS_REVIEWED_PROTOCOL";requiredLevels:20;requiredAssessments:40;requiredLayers:8;completedAssessments:0;notes:string[]};
 adversarial:{supportingFindingIds:string[];opposingFindingIds:string[];notes:string[]};
 timing:{totalSeconds:number|null;collectionSeconds:number|null;comparisonSeconds:number|null;scienceSeconds:number|null;predictionSeconds:number|null;measurementBasis:string};
 blockers:string[];identity?:DecisionIdentity;scienceDossier?:ScienceInvestigation|null;
};
export type PilotAssessment={
 status:"INVALID"|"INCOMPLETE"|"RESEARCH_REVIEW_REQUIRED";run:PilotRun|null;
 preliminaryOutcome:"INDETERMINATE";approvalProbability:null;nonapprovalProbability:null;confidence:null;
 modelValidated:false;tradeAuthorized:false;methodVersion:"evidence-gated-pilot-v1";issues:string[];
 sources:{textObserved:number;unavailable:number;unknownPublicationDate:number;usableFindingCount:number};
 usableFindingIds:string[];usableHistoricalIds:string[];
 science:ScienceInvestigationAudit|null;independentlyVerifiedHistoricalCycles:0;
};
const invalid=():never=>{throw new Error("Persisted pilot record shape is invalid");};
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==="object"&&!Array.isArray(v);
function shape(v:unknown,required:string[],optional:string[]=[]):asserts v is Record<string,unknown>{
 if(!object(v)||required.some(k=>!(k in v))||Object.keys(v).some(k=>!required.includes(k)&&!optional.includes(k)))invalid();
}
const text=(v:unknown,max=2000):v is string=>typeof v==="string"&&!!v.trim()&&v.length<=max&&!/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(v);
const texts=(v:unknown)=>Array.isArray(v)&&v.length<=200&&v.every(x=>text(x));
const ids=(v:unknown)=>Array.isArray(v)&&v.length<=200&&v.every(x=>text(x,100))&&new Set(v).size===v.length;
function day(v:unknown):v is string{
 return typeof v==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+"T00:00:00Z"))&&new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
}
function stamp(v:unknown):v is string{
 if(typeof v!=="string"||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)||!day(v.slice(0,10)))return false;
 return Number(v.slice(11,13))<24&&Number(v.slice(14,16))<60&&Number(v.slice(17,19))<60&&Number.isFinite(Date.parse(v));
}
function https(v:unknown):boolean{
 if(!text(v,4096)||/\s|\\/.test(v))return false;
 try{const u=new URL(v);return u.protocol==="https:"&&!!u.hostname&&!u.username&&!u.password;}catch{return false;}
}
const nct=(v:unknown)=>typeof v==="string"&&/^NCT\d{8}$/.test(v);
const directions=["SUPPORTS_APPROVAL","OPPOSES_APPROVAL","UNDETERMINED","MATERIALLY_UNCHANGED"];
const actions=["APPROVAL","COMPLETE_RESPONSE","WITHDRAWN","UNRESOLVED"];
const timingFields=["totalSeconds","collectionSeconds","comparisonSeconds","scienceSeconds","predictionSeconds"] as const;

/** Validate bounded persisted observations, never certify external evidence. No write,
 * data fetching, score change, queue activation or forecast creation occurs here. */
export function parsePilotRun(value:unknown):PilotRun{
 if(JSON.stringify(value)?.length>2*1024*1024)invalid();
 shape(value,["schemaVersion","runId","exactKey","nctId","drug","indication","asOf","decisionTarget","sources","findings","history","science","adversarial","timing","blockers"],["identity","scienceDossier"]);
 if(value.schemaVersion!==1||!text(value.runId,100)||!text(value.exactKey,512)||!nct(value.nctId)||!text(value.drug,512)||!text(value.indication)||!stamp(value.asOf)||!texts(value.blockers))invalid();
 for(const field of ["sources","findings","history"])if(!Array.isArray(value[field])||value[field].length>200)invalid();
 shape(value.decisionTarget,["date","status","sourceIds"]);
 if(!day(value.decisionTarget.date)||value.decisionTarget.status!=="SPONSOR_REPORTED"||!ids(value.decisionTarget.sourceIds))invalid();
 const sourceIds=new Set<string>(),findingIds=new Set<string>(),historyIds=new Set<string>();
 for(const source of value.sources as unknown[]){
  shape(source,["id","url","publishedOn","observedAt","captureStatus","sourceClass","notes"]);
  if(!text(source.id,100)||sourceIds.has(source.id)||!https(source.url)||!(source.publishedOn===null||day(source.publishedOn))||!stamp(source.observedAt)
   ||!["TEXT_OBSERVED","UNAVAILABLE"].includes(source.captureStatus as string)||!text(source.sourceClass,100)||!texts(source.notes))invalid();
  sourceIds.add(source.id as string);
 }
 for(const finding of value.findings as unknown[]){
  shape(finding,["id","domain","approvalDirection","text","sourceIds"]);
  if(!text(finding.id,100)||findingIds.has(finding.id)||!text(finding.domain,200)||!directions.includes(finding.approvalDirection as string)||!text(finding.text,20000)||!ids(finding.sourceIds))invalid();
  findingIds.add(finding.id as string);
 }
 for(const historical of value.history as unknown[]){
  shape(historical,["id","drug","nctId","applicationId","actionObserved","actionDate","sourceIds","similarities","differences","modelEligible"]);
  if(!text(historical.id,100)||historyIds.has(historical.id)||!text(historical.drug,512)||!(historical.nctId===null||nct(historical.nctId))
   ||!(historical.applicationId===null||typeof historical.applicationId==="string"&&/^(NDA|BLA|ANDA)\d{6}$/.test(historical.applicationId))
   ||!actions.includes(historical.actionObserved as string)||!(historical.actionDate===null||day(historical.actionDate))||!ids(historical.sourceIds)||!texts(historical.similarities)||!texts(historical.differences)||historical.modelEligible!==false)invalid();
  historyIds.add(historical.id as string);
 }
 shape(value.science,["status","requiredLevels","requiredAssessments","requiredLayers","completedAssessments","notes"]);
 if(value.science.status!=="NEEDS_REVIEWED_PROTOCOL"||value.science.requiredLevels!==20||value.science.requiredAssessments!==40||value.science.requiredLayers!==8||value.science.completedAssessments!==0||!texts(value.science.notes))invalid();
 shape(value.adversarial,["supportingFindingIds","opposingFindingIds","notes"]);
 if(!ids(value.adversarial.supportingFindingIds)||!ids(value.adversarial.opposingFindingIds)||!texts(value.adversarial.notes))invalid();
 shape(value.timing,[...timingFields,"measurementBasis"]);
 const timing=value.timing;
 if(!text(timing.measurementBasis)||timingFields.some(k=>timing[k]!==null&&!(typeof timing[k]==="number"&&Number.isFinite(timing[k])&&timing[k]>=0)))invalid();
 if(value.identity!==undefined)validateDecisionIdentity(value.identity);
 if(value.scienceDossier!==undefined&&value.scienceDossier!==null)parseScienceInvestigation(value.scienceDossier);
 return value as unknown as PilotRun;
}

/** This version audits the first real case and abstains until a justified prediction
 * method exists. Passing source-shape checks is neither source authentication nor
 * an independent model-validation result. Historical examples are development
 * context and cannot also be counted as independent holdout observations. */
export function evaluatePilotRun(value:unknown,expected?:PilotIdentity,now=new Date()):PilotAssessment{
 const result:PilotAssessment={status:"INVALID",run:null,preliminaryOutcome:"INDETERMINATE",approvalProbability:null,nonapprovalProbability:null,confidence:null,
  modelValidated:false,tradeAuthorized:false,methodVersion:"evidence-gated-pilot-v1",issues:[],sources:{textObserved:0,unavailable:0,unknownPublicationDate:0,usableFindingCount:0},usableFindingIds:[],usableHistoricalIds:[],science:null,independentlyVerifiedHistoricalCycles:0};
 let run:PilotRun;
 try{run=parsePilotRun(value);}catch{return {...result,issues:["Persisted assessment record is invalid; evidence and predictions withheld"]};}
 const issues:string[]=[],cutoff=Date.parse(run.asOf),available=new Set<string>();
 if(!Number.isFinite(now.getTime())||cutoff>now.getTime())issues.push("Assessment cutoff is invalid or in the future");
 if(expected&&(run.exactKey!==expected.exactKey||run.nctId!==expected.nctId))issues.push("Persisted assessment identity differs from the selected trial");
 if(run.identity&&(run.identity.exactKey!==run.exactKey||run.identity.trialId!==run.nctId))issues.push("Persistent program identity differs from the assessment trial");
 if(issues.length)return {...result,issues};
 if(run.decisionTarget.date<=new Date(cutoff).toISOString().slice(0,10))issues.push("FDA target is not an upcoming decision at the assessment cutoff");
 const sourceById=new Map(run.sources.map(source=>[source.id,source]));
 for(const source of run.sources){
  const observed=Date.parse(source.observedAt);
  if(observed>cutoff)issues.push("Source observed after assessment cutoff: "+source.id);
  if(source.publishedOn!==null&&(source.publishedOn>new Date(observed).toISOString().slice(0,10)||source.publishedOn>new Date(cutoff).toISOString().slice(0,10)))issues.push("Source publication chronology is inconsistent: "+source.id);
  if(source.publishedOn===null)issues.push("Original source publication date is unverified: "+source.id);
  if(source.captureStatus==="UNAVAILABLE")issues.push("Source remains unavailable: "+source.id);
  if(source.captureStatus==="TEXT_OBSERVED"&&observed<=cutoff&&(source.publishedOn===null||source.publishedOn<=new Date(observed).toISOString().slice(0,10)))available.add(source.id);
 }
 const cited=(references:string[],label:string)=>{
  if(!references.length){issues.push("Missing citations for "+label);return false;}
  const valid=references.every(id=>sourceById.has(id)&&available.has(id));
  if(!valid)issues.push("Unknown, unavailable or post-cutoff citations for "+label);
  return valid;
 };
 cited(run.decisionTarget.sourceIds,"sponsor-reported FDA target");
 const usableFindings=run.findings.filter(finding=>cited(finding.sourceIds,"finding "+finding.id));
 if(!usableFindings.length)issues.push("No usable source-cited clinical findings are recorded");
 const usableHistoricalIds:string[]=[];
 for(const historical of run.history){
  let usable=cited(historical.sourceIds,"historical example "+historical.id);
  if(historical.nctId===run.nctId){issues.push("Current trial cannot also be its historical comparator: "+historical.id);usable=false;}
  if(historical.actionDate===null||historical.actionDate>=new Date(cutoff).toISOString().slice(0,10)){issues.push("Historical action date is missing or unavailable at cutoff: "+historical.id);usable=false;}
  if(!historical.applicationId)issues.push("Historical application identity requires reconciliation: "+historical.id);
  if(usable)usableHistoricalIds.push(historical.id);
 }
 if(!run.history.length)issues.push("No historical comparison examples are recorded");
 const findingsById=new Map(usableFindings.map(finding=>[finding.id,finding]));
 for(const [side,refs,direction] of [["supporting",run.adversarial.supportingFindingIds,"SUPPORTS_APPROVAL"],["opposing",run.adversarial.opposingFindingIds,"OPPOSES_APPROVAL"]] as const){
  if(!refs.length||refs.some(id=>findingsById.get(id)?.approvalDirection!==direction))issues.push("Source-cited "+side+" argument is missing or inconsistent");
 }
 let science:ScienceInvestigationAudit|null=null;
 if(run.identity&&run.scienceDossier){
  const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
  if(!same(run.scienceDossier.drug,run.drug)||!same(run.scienceDossier.indication,run.indication))issues.push("Scientific dossier drug or indication differs from this trial assessment");
  else science=auditScienceInvestigation(run.scienceDossier,run.identity,run.asOf);
 }
 if(!science||science.status!=="READY_FOR_RESEARCH_REVIEW")issues.push("Reviewed 20-level / 40-assessment / 8-layer scientific protocol and dossier are incomplete");
 if(science)issues.push(...science.issues);
 const durations=timingFields.slice(1).map(k=>run.timing[k]);
 if(run.timing.totalSeconds!==null&&durations.reduce<number>((sum,n)=>sum+(n??0),0)>run.timing.totalSeconds)issues.push("Recorded stage durations exceed total elapsed processing time");
 issues.push(...run.blockers);
 const status=issues.length?"INCOMPLETE":"RESEARCH_REVIEW_REQUIRED";
 issues.push("A documented, source-grounded case-level PASS/FAIL decision method and independent model validation are unavailable; this version abstains and withholds numerical probabilities. Completing the entire historical FDA database is not a prerequisite for preliminary case review.");
 return {...result,status,run,science,usableFindingIds:usableFindings.map(f=>f.id),usableHistoricalIds,issues:[...new Set(issues)],sources:{textObserved:run.sources.filter(s=>s.captureStatus==="TEXT_OBSERVED").length,
  unavailable:run.sources.filter(s=>s.captureStatus==="UNAVAILABLE").length,unknownPublicationDate:run.sources.filter(s=>s.publishedOn===null).length,usableFindingCount:usableFindings.length}};
}
