/** Ordered, fail-closed next-action plan for completing one exact-trial SURVEY.
 * A missing value means work to verify, never a negative clinical result.
 * No efficacy, FDA outcome, valuation or stock prediction is calculated here.
 */
export type FinalSurveyResearchStatus="idle"|"loading"|"ready"|"unavailable";
export type FinalSurveyNextAction={
 key:string;
 category:"SOURCE"|"IDENTITY"|"STAGE"|"GROUP"|"QUESTION";
 heading:string;
 detail:string;
};
export type FinalSurveyResearchGroup={key:string;name:string;verified:number};
export type FinalSurveyResearchGate={label:string;passed:boolean};
export type FinalSurveyResearchQuestion={
 id:string;survey:number;label:string;status:"VERIFIED"|"MODELED"|"UNRECORDED";
};
export function finalSurveyNextActions(args:{
 researchStatus:FinalSurveyResearchStatus;
 exactRecord:boolean;
 gates:readonly FinalSurveyResearchGate[];
 groups:readonly FinalSurveyResearchGroup[];
 questions:readonly FinalSurveyResearchQuestion[];
}):{actions:FinalSurveyNextAction[];unverifiedQuestions:number|null}{
 const {researchStatus,exactRecord,gates,groups,questions}=args;
 if(researchStatus==="idle"||researchStatus==="loading")
  return {actions:[{key:"source-loading",category:"SOURCE",heading:"Confirm authenticated research feed",
   detail:"The research source is still being checked. Do not label unanswered questions as failed."}],
   unverifiedQuestions:null};
 if(researchStatus==="unavailable")
  return {actions:[{key:"source-unavailable",category:"SOURCE",heading:"Restore the source-backed research feed",
   detail:"Check source access and provenance before assigning evidence status or trial grades."}],
   unverifiedQuestions:null};
 if(!exactRecord)
  return {actions:[{key:"exact-trial-match",category:"IDENTITY",heading:"Resolve an exact, unique research record",
   detail:"Match NCT, ticker, drug/therapy and indication to a documented research record. Do not match a trial by ticker alone."}],
   unverifiedQuestions:null};
 // Refuse an invented checklist if the canonical 20 surveys / 38 fields are not intact.
 if(questions.length!==38||new Set(questions.map(q=>q.id)).size!==38||
   groups.length!==5||gates.length!==4||new Set(questions.map(q=>q.survey)).size!==20||
   groups.some(g=>!Number.isInteger(g.verified)||g.verified<0)||
   gates.some(g=>typeof g.passed!=="boolean"||!g.label.trim())||
   questions.some(q=>!Number.isInteger(q.survey)||q.survey<1||q.survey>20||
     !["VERIFIED","MODELED","UNRECORDED"].includes(q.status)))
  return {actions:[{key:"inventory-invalid",category:"SOURCE",
   heading:"Reconcile the 20-survey question inventory",
   detail:"Expected 38 unique research questions in five groups. Cannot prioritize an incomplete inventory."}],
   unverifiedQuestions:null};
 const actions:FinalSurveyNextAction[]=[];
 for(const gate of gates){
  if(!gate.passed)actions.push({key:"gate:"+gate.label,category:"STAGE",
   heading:"Verify required stage check: "+gate.label,
   detail:"Locate dated issuer, trial or primary-source documentation. A check not verified is not a failed clinical outcome."});
 }
 for(const group of groups){
  if(group.verified===0)actions.push({key:"group:"+group.key,category:"GROUP",
   heading:"Establish verified research in "+group.key+" · "+group.name,
   detail:"At least one independently source-verified input is required before this group contributes to the preliminary readiness gate."});
 }
 for(const q of questions){
  if(q.status==="VERIFIED")continue;
  actions.push({key:"question:"+q.id,category:"QUESTION",
   heading:"Survey "+q.survey+" · "+q.label,
   detail:q.status==="MODELED"?
    "Modeled only — obtain supporting primary evidence. A scenario estimate cannot count as verified.":
    "Not recorded — research the exact trial and record a verifiable source, date, method and confidence."});
 }
 return {actions,unverifiedQuestions:questions.filter(q=>q.status!=="VERIFIED").length};
}
