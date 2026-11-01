/** TOOLS-only selection taxonomy: groups do not change the 20 original ranks. */
import {BENEFIT_GROUPS} from "./benefit-assessments";

export const TOOLS_RANKING_GROUPS=[
  {id:1,title:"Patient Health & Clinical Benefit",assessmentIds:[2,3,4,5,8]},
  {id:2,title:"Treatment & Competitive Advantage",assessmentIds:[1,6,7,14]},
  {id:3,title:"Patient Affordability & Access",assessmentIds:[9,10,11]},
  {id:4,title:"Market & Revenue Opportunity",assessmentIds:[12,13,15,16]},
  {id:5,title:"Strategic & Competitive Protection",assessmentIds:[17,18]},
  {id:6,title:"Valuation & Shareholder Risk",assessmentIds:[19,20]}
] as const;

export type RankingChecklistSelection={
  groupIds:number[];
  groupAssessments:number[];
  groupCriteria:Record<string,string[]>;
  priorities:number[];
};

/** All 20 canonical groups remain present once, independent of user priority order. */
export function rankingTaxonomyAudit(){
  const all=TOOLS_RANKING_GROUPS.flatMap(g=>[...g.assessmentIds]);
  const expected=BENEFIT_GROUPS.map(g=>g.number);
  return {
    total:all.length,
    originalTotal:expected.length,
    duplicates:all.filter((id,i)=>all.indexOf(id)!==i),
    missing:expected.filter(id=>!all.includes(id as typeof all[number])),
    unknown:all.filter(id=>!expected.includes(id))
  };
}
export function selectedAssessmentIds(groupIds:readonly number[]){
  const allowed=new Set(TOOLS_RANKING_GROUPS.filter(g=>groupIds.includes(g.id)).flatMap(g=>[...g.assessmentIds]));
  return BENEFIT_GROUPS.map(g=>g.number).filter(id=>allowed.has(id));
}
export function movePriority(current:readonly number[],id:number,position:number):number[]{
  if(!current.includes(id)||!Number.isInteger(position))return [...current];
  const without=current.filter(x=>x!==id);
  without.splice(Math.max(0,Math.min(without.length,position-1)),0,id);
  return without;
}
export function normalizeRankingSelection(raw:unknown):RankingChecklistSelection{
  const empty=()=>({groupIds:[],groupAssessments:[],groupCriteria:{},priorities:[]} as RankingChecklistSelection);
  if(!raw||typeof raw!=="object"||Array.isArray(raw))return empty();
  const value=raw as Record<string,unknown>;
  const uniqueNumbers=(input:unknown,allow:Set<number>)=>
    Array.isArray(input)?[...new Set(input.filter((x):x is number=>typeof x==="number"&&Number.isInteger(x)&&allow.has(x)))]:[];
  const groupIds=uniqueNumbers(value.groupIds,new Set(TOOLS_RANKING_GROUPS.map(g=>g.id)));
  const allowedAssessments=new Set(selectedAssessmentIds(groupIds));
  const groupAssessments=uniqueNumbers(value.groupAssessments,allowedAssessments);
  const priorities=uniqueNumbers(value.priorities,new Set(BENEFIT_GROUPS.map(g=>g.number)));
  const groupCriteria:Record<string,string[]>={};
  const rawCriteria=value.groupCriteria&&typeof value.groupCriteria==="object"&&!Array.isArray(value.groupCriteria)
    ?value.groupCriteria as Record<string,unknown>:{};
  for(const assessment of BENEFIT_GROUPS){
    if(!groupAssessments.includes(assessment.number))continue;
    const permitted=new Set(assessment.fields.map(f=>f.id));
    const chosen=rawCriteria[String(assessment.number)];
    groupCriteria[String(assessment.number)]=Array.isArray(chosen)
      ?[...new Set(chosen.filter((id):id is string=>typeof id==="string"&&permitted.has(id)))]:[];
  }
  return {groupIds,groupAssessments,groupCriteria,priorities};
}
