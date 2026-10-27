import type {DecisionIdentity} from "./decision-workstream";
import type {ResearchReadiness} from "./decision-research-readiness";
import {validatePrimaryTrialSourceIdentity} from "./decision-trial-source-identity";

export type InvestigationSource={url:string;publishedAt:string;observedAt:string;independentlyReviewed:boolean;primaryTrial?:{trialId:string;protocolId:string}};
export type InvestigationAssessment={id:string;status:"COMPLETE"|"PARTIAL"|"MISSING"|"CONFLICT";reviewer:string;criticalEvaluation:string;uncertainty:string;unresolvedCriticalFindings:number;sources:InvestigationSource[]};
export type ScienceInvestigation={
 identity:DecisionIdentity;asOf:string;drug:string;indication:string;companyCik:string;fdaApplication:string|null;
 layers:{id:string;label:string}[];
 levels:{id:string;label:string;layerId:string;assessments:InvestigationAssessment[]}[];
};
export type ScienceInvestigationAudit={
 status:"NOT_READY"|"READY_FOR_RESEARCH_REVIEW";completedLevels:number;requiredLevels:20;
 completedAssessments:number;requiredAssessments:40;coveredLayers:number;requiredLayers:8;
 evidenceCompletenessPct:number|null;readyForAnalysis:"NOT_READY"|"READY_FOR_RESEARCH_REVIEW";
 reluctantAssessment:"WITHHELD"|"CAUTIOUS_RESEARCH_ONLY";issues:string[];warnings:string[];
 readiness:ResearchReadiness|null;
};
const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==="object"&&!Array.isArray(x);
const keys=(x:Record<string,unknown>,allowed:string[])=>Object.keys(x).every(k=>allowed.includes(k));
const text=(x:unknown,max=20000):x is string=>typeof x==="string"&&x.length<=max;
const https=(s:string)=>{try{const u=new URL(s);return u.protocol==="https:"&&!!u.hostname&&!u.username&&!u.password;}catch{return false;}};
const timestamp=(s:string)=>{
 const match=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/.exec(s);
 if(!match)return NaN;
 const [,year,month,day,hour,minute,second]=match.map(Number);
 if(month<1||month>12||day<1||day>new Date(Date.UTC(year,month,0)).getUTCDate()||hour>23||minute>59||second>59)return NaN;
 return Date.parse(s);
};

/** Shape validation is not independent scientific verification. Partial inventories may
 * be transported; the audit below requires every declared level/assessment/layer. */
export function parseScienceInvestigation(value:unknown):ScienceInvestigation {
 if(!object(value)||!keys(value,["identity","asOf","drug","indication","companyCik","fdaApplication","layers","levels"])||!object(value.identity)||!text(value.asOf,100)||!text(value.drug,512)
  ||!text(value.indication,2000)||!text(value.companyCik,10)
  ||!(value.fdaApplication===null||text(value.fdaApplication,16))
  ||!Array.isArray(value.layers)||value.layers.length>8||!Array.isArray(value.levels)||value.levels.length>20)
  throw new Error("Scientific investigation shape is invalid");
 const identity=value.identity;
 if(!keys(identity,["exactKey","programId","trialId","ticker","stage"])||!["exactKey","programId","trialId","ticker","stage"].every(k=>text(identity[k],512)))
  throw new Error("Scientific investigation identity is invalid");
 for(const layer of value.layers)if(!object(layer)||!keys(layer,["id","label"])||!text(layer.id,100)||!text(layer.label,512))
  throw new Error("Scientific subject layer is invalid");
 for(const level of value.levels){
  if(!object(level)||!keys(level,["id","label","layerId","assessments"])||!text(level.id,100)||!text(level.label,512)||!text(level.layerId,100)
   ||!Array.isArray(level.assessments)||level.assessments.length>2)throw new Error("Scientific level is invalid");
  for(const a of level.assessments){
   if(!object(a)||!keys(a,["id","status","reviewer","criticalEvaluation","uncertainty","unresolvedCriticalFindings","sources"])||!text(a.id,100)||!["COMPLETE","PARTIAL","MISSING","CONFLICT"].includes(a.status as string)
    ||!text(a.reviewer,512)||!text(a.criticalEvaluation)||!text(a.uncertainty)
    ||!Number.isSafeInteger(a.unresolvedCriticalFindings)||Number(a.unresolvedCriticalFindings)<0
    ||!Array.isArray(a.sources)||a.sources.length>20)throw new Error("Scientific assessment is invalid");
   for(const s of a.sources)if(!object(s)||!keys(s,["url","publishedAt","observedAt","independentlyReviewed","primaryTrial"])||!text(s.url,4096)||!https(s.url)||!text(s.publishedAt,100)
    ||!text(s.observedAt,100)||typeof s.independentlyReviewed!=="boolean")throw new Error("Scientific source record is invalid");
   for(const s of a.sources){
    if(object(s)&&s.primaryTrial!==undefined){
     if(!object(s.primaryTrial)||!keys(s.primaryTrial,["trialId","protocolId"])||!text(s.primaryTrial.trialId,32)||!text(s.primaryTrial.protocolId,100))
      throw new Error("Primary trial source metadata is invalid");
     validatePrimaryTrialSourceIdentity({trialId:identity.trialId as string,protocolId:s.primaryTrial.protocolId as string},{trialId:s.primaryTrial.trialId,protocolId:s.primaryTrial.protocolId});
    }
   }
  }
 }
 return value as unknown as ScienceInvestigation;
}

/** Counts describe review records, not predictive accuracy, trial success or grades
 * assigned by a scientific model. Citation/reviewer assertions require source review. */
export function auditScienceInvestigation(input:ScienceInvestigation|null,expected:DecisionIdentity,cutoff:string):ScienceInvestigationAudit {
 const issues:string[]=[],warnings=["Scientific review records and source citations require independent verification; these counts do not establish prediction accuracy."];
 const base:ScienceInvestigationAudit={status:"NOT_READY",completedLevels:0,requiredLevels:20,completedAssessments:0,requiredAssessments:40,
  coveredLayers:0,requiredLayers:8,evidenceCompletenessPct:null,readyForAnalysis:"NOT_READY",reluctantAssessment:"WITHHELD",issues,warnings,readiness:null};
 if(!input){issues.push("SCIENCE: source-cited 20-level / 40-assessment / 8-layer dossier missing");return base;}
 let dossier:ScienceInvestigation;
 try{dossier=parseScienceInvestigation(input);}catch{issues.push("SCIENCE: scientific dossier structure invalid");return base;}
 if((Object.keys(expected) as (keyof DecisionIdentity)[]).some(k=>dossier.identity[k]!==expected[k])){
  issues.push("SCIENCE: scientific dossier identity or stage mismatch");return base;
 }
 const until=timestamp(cutoff);
 if(!Number.isFinite(until)||dossier.asOf!==cutoff)issues.push("SCIENCE: scientific dossier cutoff mismatch");
 if(!dossier.drug.trim()||!dossier.indication.trim()||!/^\d{10}$/.test(dossier.companyCik)||Number(dossier.companyCik)===0)
  issues.push("SCIENCE: drug, indication or company identity incomplete");
 if(dossier.fdaApplication!==null&&!/^(NDA|BLA)\d{6}$/.test(dossier.fdaApplication))issues.push("SCIENCE: FDA application identity invalid");
 const layers=new Set(dossier.layers.map(l=>l.id));
 if(layers.size!==8||dossier.layers.length!==8||dossier.layers.some(l=>!l.id.trim()||!l.label.trim()))issues.push("SCIENCE: eight distinct scientific subject layers required");
 const levels=new Set<string>(),assessments=new Set<string>(),covered=new Set<string>();
 let completed=0,completeLevels=0;
 for(const level of dossier.levels){
  const uniqueLevel=!!level.id.trim()&&!levels.has(level.id);
  if(!uniqueLevel||!level.label.trim())issues.push("SCIENCE: level identity missing or duplicated");
  levels.add(level.id);
  const layerOk=layers.has(level.layerId);
  if(!layerOk)issues.push("SCIENCE: level has no declared scientific layer");else covered.add(level.layerId);
  if(level.assessments.length!==2)issues.push("SCIENCE: each investigation level requires two assessments");
  let levelComplete=uniqueLevel&&layerOk&&level.assessments.length===2;
  for(const a of level.assessments){
   const unique=!!a.id.trim()&&!assessments.has(a.id);assessments.add(a.id);
   if(!unique)issues.push("SCIENCE: assessment identity missing or duplicated");
   const sourcesOk=a.sources.length>0&&a.sources.every(s=>{
    const published=timestamp(s.publishedAt),observed=timestamp(s.observedAt);
    return s.independentlyReviewed===true&&Number.isFinite(published)&&Number.isFinite(observed)
     &&published<=observed&&observed<until;
   });
   const complete=unique&&a.status==="COMPLETE"&&a.reviewer.trim()&&a.criticalEvaluation.trim()&&a.uncertainty.trim()
    &&a.unresolvedCriticalFindings===0&&sourcesOk;
   if(complete)completed++;else{levelComplete=false;issues.push("SCIENCE: incomplete or conflicting assessment "+a.id);}
  }
  if(levelComplete)completeLevels++;
 }
 if(dossier.levels.length!==20||levels.size!==20||assessments.size!==40)issues.push("SCIENCE: complete 20-level / 40-assessment inventory required");
 if(covered.size!==8)issues.push("SCIENCE: all eight scientific layers must be represented");
 const ready=issues.length===0;
 const readiness:ResearchReadiness={programId:expected.programId,trialId:expected.trialId,asOf:dossier.asOf,
  status:ready?"COMPLETE":"PARTIAL",sourceStatus:ready?"VERIFIED":"UNVERIFIED",reviewedLevels:completeLevels,requiredLevels:20,criticalFindingsResolved:ready};
 return {...base,status:ready?"READY_FOR_RESEARCH_REVIEW":"NOT_READY",completedLevels:completeLevels,completedAssessments:completed,
  coveredLayers:covered.size,evidenceCompletenessPct:levels.size===20&&assessments.size===40&&layers.size===8?100*completed/40:null,
  readyForAnalysis:ready?"READY_FOR_RESEARCH_REVIEW":"NOT_READY",reluctantAssessment:ready?"CAUTIOUS_RESEARCH_ONLY":"WITHHELD",issues:[...new Set(issues)],readiness};
}
