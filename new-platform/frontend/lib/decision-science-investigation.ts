import type {DecisionIdentity} from "./decision-workstream";
import type {ResearchReadiness} from "./decision-research-readiness";
import {validatePrimaryTrialSourceIdentity} from "./decision-trial-source-identity";

export type InvestigationSource={url:string;publishedAt:string;observedAt:string;independentlyReviewed:boolean;primaryTrial?:{trialId:string;protocolId:string}};
export type ApprovalDirection="SUPPORTS_APPROVAL"|"OPPOSES_APPROVAL"|"MATERIALLY_UNCHANGED"|"UNDETERMINED";
export type InvestigationAssessment={id:string;status:"COMPLETE"|"PARTIAL"|"MISSING"|"CONFLICT";reviewer:string;criticalEvaluation:string;uncertainty:string;unresolvedCriticalFindings:number;sources:InvestigationSource[];approvalDirection?:ApprovalDirection;directionRationale?:string};
export type InvestigationArgument={rationale:string;assessmentIds:string[];sources:InvestigationSource[]};
export type InvestigationChallenge={reviewer:string;reviewedAt:string;independentReviewDeclared:boolean;supporting:InvestigationArgument;opposing:InvestigationArgument;unresolvedCriticalFindings:number};
export type ScienceInvestigation={
 identity:DecisionIdentity;asOf:string;drug:string;indication:string;companyCik:string;fdaApplication:string|null;
 layers:{id:string;label:string}[];
 levels:{id:string;label:string;layerId:string;assessments:InvestigationAssessment[]}[];
 adversarialReview?:InvestigationChallenge;
};
export type ScienceInvestigationAudit={
 status:"NOT_READY"|"READY_FOR_RESEARCH_REVIEW";completedLevels:number;requiredLevels:20;
 completedAssessments:number;requiredAssessments:40;coveredLayers:number;requiredLayers:8;
 evidenceCompletenessPct:number|null;readyForAnalysis:"NOT_READY"|"READY_FOR_RESEARCH_REVIEW";
 reluctantAssessment:"WITHHELD"|"CAUTIOUS_RESEARCH_ONLY";issues:string[];warnings:string[];
 adversarialReviewStatus:"MISSING"|"INCOMPLETE"|"RECORDED_FOR_REVIEW";
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
const directions:ApprovalDirection[]=["SUPPORTS_APPROVAL","OPPOSES_APPROVAL","MATERIALLY_UNCHANGED","UNDETERMINED"];
function validateSources(value:unknown,trialId:string):asserts value is InvestigationSource[]{
 if(!Array.isArray(value)||value.length>20)throw new Error("Scientific source record is invalid");
 for(const s of value){
  if(!object(s)||!keys(s,["url","publishedAt","observedAt","independentlyReviewed","primaryTrial"])||!text(s.url,4096)||!https(s.url)||!text(s.publishedAt,100)
   ||!text(s.observedAt,100)||typeof s.independentlyReviewed!=="boolean")throw new Error("Scientific source record is invalid");
  if(s.primaryTrial!==undefined){
   if(!object(s.primaryTrial)||!keys(s.primaryTrial,["trialId","protocolId"])||!text(s.primaryTrial.trialId,32)||!text(s.primaryTrial.protocolId,100))
    throw new Error("Primary trial source metadata is invalid");
   validatePrimaryTrialSourceIdentity({trialId,protocolId:s.primaryTrial.protocolId},{trialId:s.primaryTrial.trialId,protocolId:s.primaryTrial.protocolId});
  }
 }
}
function sourcesAvailable(sources:InvestigationSource[],until:number):boolean{
 return sources.length>0&&sources.every(s=>{
  const published=timestamp(s.publishedAt),observed=timestamp(s.observedAt);
  return s.independentlyReviewed===true&&Number.isFinite(published)&&Number.isFinite(observed)&&published<=observed&&observed<until;
 });
}

/** Shape validation is not independent scientific verification. Partial inventories may
 * be transported; the audit below requires every declared level/assessment/layer. */
export function parseScienceInvestigation(value:unknown):ScienceInvestigation {
 if(!object(value)||!keys(value,["identity","asOf","drug","indication","companyCik","fdaApplication","layers","levels","adversarialReview"])||!object(value.identity)||!text(value.asOf,100)||!text(value.drug,512)
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
   if(!object(a)||!keys(a,["id","status","reviewer","criticalEvaluation","uncertainty","unresolvedCriticalFindings","sources","approvalDirection","directionRationale"])||!text(a.id,100)||!["COMPLETE","PARTIAL","MISSING","CONFLICT"].includes(a.status as string)
    ||!text(a.reviewer,512)||!text(a.criticalEvaluation)||!text(a.uncertainty)
    ||(a.approvalDirection!==undefined&&!directions.includes(a.approvalDirection as ApprovalDirection))
    ||(a.directionRationale!==undefined&&!text(a.directionRationale))
    ||!Number.isSafeInteger(a.unresolvedCriticalFindings)||Number(a.unresolvedCriticalFindings)<0
    ||!Array.isArray(a.sources)||a.sources.length>20)throw new Error("Scientific assessment is invalid");
   validateSources(a.sources,identity.trialId as string);
  }
 }
 if(value.adversarialReview!==undefined){
  const review=value.adversarialReview;
  if(!object(review)||!keys(review,["reviewer","reviewedAt","independentReviewDeclared","supporting","opposing","unresolvedCriticalFindings"])
   ||!text(review.reviewer,512)||!text(review.reviewedAt,100)||typeof review.independentReviewDeclared!=="boolean"
   ||!Number.isSafeInteger(review.unresolvedCriticalFindings)||Number(review.unresolvedCriticalFindings)<0)
   throw new Error("Scientific adversarial review is invalid");
  for(const argument of [review.supporting,review.opposing]){
   if(!object(argument)||!keys(argument,["rationale","assessmentIds","sources"])||!text(argument.rationale)
    ||!Array.isArray(argument.assessmentIds)||argument.assessmentIds.length>40||argument.assessmentIds.some(id=>!text(id,100)))
    throw new Error("Scientific adversarial argument is invalid");
   validateSources(argument.sources,identity.trialId as string);
  }
 }
 return value as unknown as ScienceInvestigation;
}

/** Counts describe review records, not predictive accuracy, trial success or grades
 * assigned by a scientific model. Citation/reviewer assertions require source review. */
export function auditScienceInvestigation(input:ScienceInvestigation|null,expected:DecisionIdentity,cutoff:string):ScienceInvestigationAudit {
 const issues:string[]=[],warnings=["Scientific review records and source citations require independent verification; these counts do not establish prediction accuracy.","Approval directions are qualitative reviewer inferences, not validated predictive factors or numerical probabilities. Reviewer identities and an independence declaration do not authenticate independent review."];
 const base:ScienceInvestigationAudit={status:"NOT_READY",completedLevels:0,requiredLevels:20,completedAssessments:0,requiredAssessments:40,
  coveredLayers:0,requiredLayers:8,evidenceCompletenessPct:null,readyForAnalysis:"NOT_READY",reluctantAssessment:"WITHHELD",adversarialReviewStatus:"MISSING",issues,warnings,readiness:null};
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
   const sourcesOk=sourcesAvailable(a.sources,until);
   const directionOk=a.approvalDirection!==undefined&&a.approvalDirection!=="UNDETERMINED"&&!!a.directionRationale?.trim();
   if(!directionOk)issues.push("SCIENCE: approval direction or source-grounded rationale missing or undetermined for "+a.id);
   const complete=unique&&a.status==="COMPLETE"&&a.reviewer.trim()&&a.criticalEvaluation.trim()&&a.uncertainty.trim()
    &&a.unresolvedCriticalFindings===0&&sourcesOk&&directionOk;
   if(complete)completed++;else{levelComplete=false;issues.push("SCIENCE: incomplete or conflicting assessment "+a.id);}
  }
  if(levelComplete)completeLevels++;
 }
 if(dossier.levels.length!==20||levels.size!==20||assessments.size!==40)issues.push("SCIENCE: complete 20-level / 40-assessment inventory required");
 if(covered.size!==8)issues.push("SCIENCE: all eight scientific layers must be represented");
 let adversarialReviewStatus:ScienceInvestigationAudit["adversarialReviewStatus"]="MISSING";
 const review=dossier.adversarialReview;
 if(!review)issues.push("SCIENCE: source-cited adversarial review missing");
 else{
  const reviewed=timestamp(review.reviewedAt),reviewer=review.reviewer.trim().toLocaleLowerCase("en-US");
  const differentReviewer=!!reviewer&&dossier.levels.every(level=>level.assessments.every(a=>a.reviewer.trim().toLocaleLowerCase("en-US")!==reviewer));
  const currentEvidenceReviewed=dossier.levels.every(level=>level.assessments.every(a=>a.sources.every(source=>timestamp(source.observedAt)<=reviewed)));
  const argumentsOk=[review.supporting,review.opposing].every(argument=>argument.rationale.trim()
   &&argument.assessmentIds.length>0&&new Set(argument.assessmentIds).size===argument.assessmentIds.length
   &&argument.assessmentIds.every(id=>assessments.has(id))&&sourcesAvailable(argument.sources,until)
   &&argument.sources.every(source=>timestamp(source.observedAt)<=reviewed));
  const complete=review.independentReviewDeclared===true&&differentReviewer&&currentEvidenceReviewed&&Number.isFinite(reviewed)&&reviewed<until
   &&review.unresolvedCriticalFindings===0&&argumentsOk;
  adversarialReviewStatus=complete?"RECORDED_FOR_REVIEW":"INCOMPLETE";
  if(!complete)issues.push("SCIENCE: adversarial review requires a distinct declared reviewer, pre-cutoff review, source-bound supporting and opposing arguments, and resolved critical findings");
 }
 const ready=issues.length===0;
 const readiness:ResearchReadiness={programId:expected.programId,trialId:expected.trialId,asOf:dossier.asOf,
  status:ready?"COMPLETE":"PARTIAL",sourceStatus:ready?"VERIFIED":"UNVERIFIED",reviewedLevels:completeLevels,requiredLevels:20,criticalFindingsResolved:ready};
 return {...base,status:ready?"READY_FOR_RESEARCH_REVIEW":"NOT_READY",completedLevels:completeLevels,completedAssessments:completed,
  coveredLayers:covered.size,evidenceCompletenessPct:levels.size===20&&assessments.size===40&&layers.size===8?100*completed/40:null,
  readyForAnalysis:ready?"READY_FOR_RESEARCH_REVIEW":"NOT_READY",reluctantAssessment:ready?"CAUTIOUS_RESEARCH_ONLY":"WITHHELD",adversarialReviewStatus,issues:[...new Set(issues)],readiness};
}
