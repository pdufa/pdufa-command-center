/** Final SURVEY evidence-readiness audit. This never grades clinical efficacy,
 * FDA approval probability, or shareholder returns. Unknown inputs are not zeroes.
 * 5 groups, 20 surveys and 38 canonical questions remain unchanged.
 */
export type FinalSurveyGroup={
 key:string;name:string;verified:number;modeled:number;missing:number;total:number;
};
export type FinalSurveyGate={label:string;passed:boolean};
export type FinalSurveyReadiness={
 assessable:boolean;fullReady:boolean;reviewReady:boolean;
 verified:number;modeled:number;missing:number;total:number;
 verifiedPercent:number|null;provisionalGrade:string;
 fullReadinessGrade:string;missingGroups:string[];failedGates:string[];
};
const EXPECTED_GROUPS=["A","B","C","D","E"];
const gradeForCoverage=(fraction:number):string=>
 fraction>=.9?"A":fraction>=.75?"B":fraction>=.5?"C":fraction>=.25?"D":"E";

/** Fails closed on missing exact-trial evidence, a malformed question inventory,
 * or unavailable feed. Provisional letter measures COVERAGE ONLY and is not a
 * validated risk/benefit score; 100% completeness does not imply FDA approval.
 */
export function finalSurveyReadiness(
 groups:readonly FinalSurveyGroup[],gates:readonly FinalSurveyGate[],
 exactEvidenceAvailable:boolean
):FinalSurveyReadiness{
 const valid=groups.length===5&&gates.length===4&&
  groups.every((g,i)=>g.key===EXPECTED_GROUPS[i]&&
   [g.verified,g.modeled,g.missing,g.total].every(n=>Number.isInteger(n)&&n>=0)&&
   g.verified+g.modeled+g.missing===g.total)&&
  groups.reduce((n,g)=>n+g.total,0)===38;
 const total=valid?38:0;
 const verified=valid?groups.reduce((n,g)=>n+g.verified,0):0;
 const modeled=valid?groups.reduce((n,g)=>n+g.modeled,0):0;
 const missing=valid?groups.reduce((n,g)=>n+g.missing,0):0;
 const assessable=valid&&exactEvidenceAvailable;
 const failedGates=assessable?gates.filter(g=>!g.passed).map(g=>g.label):[];
 const missingGroups=assessable?groups.filter(g=>g.verified===0).map(g=>g.key+" · "+g.name):[];
 const reviewReady=assessable&&missingGroups.length===0&&failedGates.length===0;
 const fullReady=reviewReady&&verified===38;
 return {
  assessable,fullReady,reviewReady,verified,modeled,missing,total,
  verifiedPercent:assessable?Math.round(100*verified/38):null,
  provisionalGrade:!assessable||verified===0?"UNGRADABLE":gradeForCoverage(verified/38)+" · PROVISIONAL",
  fullReadinessGrade:!assessable?"NOT ASSESSED":
    fullReady?"READY — 38/38 VERIFIED":"NOT READY — INPUTS INCOMPLETE",
  missingGroups,failedGates
 };
}
