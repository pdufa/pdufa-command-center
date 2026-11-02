/** Deterministic sorting of documented Phase 3 issuer-readout spreadsheets.
 * Survey columns sort by documented research completeness, never clinical merit.
 * Unknown or absent evidence is always last in both directions.
 */
import {BENEFIT_GROUPS,benefitForTrial,type BenefitFeed,type BenefitRecord} from "./benefit-assessments";
import type {ReadoutRow} from "./phase3-public-readout";

export type Phase3ReadoutSortKey="row"|"nctId"|"ticker"|"company"|"factorP"|"survey"|"synthesis"|"drug"|"indication"|"status"|"date"|"source";
export type Phase3ReadoutBucket="pre"|"post";
const FIVE_GROUP_FIELD_SETS=[
 [1,5],[6,8],[9,14],[15,18],[19,20]
].map(([first,last])=>BENEFIT_GROUPS.filter(g=>g.number>=first&&g.number<=last).flatMap(g=>g.fields.map(f=>f.id)));

export function exactReadoutBenefit(row:ReadoutRow,feed:BenefitFeed|null):BenefitRecord|null{
 if(!feed)return null;
 // A ticker does not identify a trial. Refuse ambiguous NCT matches.
 const nctRecords=feed.records.filter(r=>r.nctId===row.nctId);
 if(nctRecords.length!==1)return null;
 return benefitForTrial(feed,{
  nctId:row.nctId,ticker:row.ticker,
  drug:row.evidence?.drug||"",indication:row.evidence?.indication||""
 });
}

export function readoutResearchCoverage(row:ReadoutRow,bucket:Phase3ReadoutBucket,feed:BenefitFeed|null){
 const record=exactReadoutBenefit(row,feed);
 if(!record)return null;
 const verified=(id:string)=>record.facts[id]?.status==="VERIFIED";
 const any=(...ids:string[])=>ids.some(verified);
 const verifiedCount=FIVE_GROUP_FIELD_SETS.flat().filter(verified).length;
 const groupCoverage=FIVE_GROUP_FIELD_SETS.map(ids=>ids.some(verified));
 const checks=bucket==="pre"?[
   row.evidence?.kind==="PRE_AS_OF_CHECK",
   any("eligibleUsPatients","standardOfCare","unmetNeed"),
   any("closestCompetitor","competitorCount","competitivePipelineThreat"),
   any("valuationImpact","shareholderRisk")
 ]:[
   row.evidence?.kind==="POST_PUBLIC_READOUT",
   verified("clinicalBenefit")&&verified("magnitude"),
   any("safetyAdvantage","seriousAes","discontinuation"),
   any("valuationImpact","shareholderRisk")
 ];
 const passedChecks=checks.filter(Boolean).length;
 const groupsVerified=groupCoverage.filter(Boolean).length;
 return {verified:verifiedCount,groupsVerified,passedChecks,
  ready:groupsVerified===5&&passedChecks===checks.length};
}
function factorPNumeric(display:string|undefined):number|null{
 if(!display)return null;
 const value=/^p\s*(?:<|=|≤)\s*(0?\.\d+)$/i.exec(display.trim());
 if(!value)return null;
 const n=Number(value[1]);return Number.isFinite(n)?n:null;
}
export function sortPhase3Readouts(
 rows:readonly ReadoutRow[],order:readonly ReadoutRow[],key:Phase3ReadoutSortKey,
 descending:boolean,bucket:Phase3ReadoutBucket,feed:BenefitFeed|null
):ReadoutRow[]{
 const base=new Map(order.map((r,i)=>[r.nctId,i]));
 const extracted=new Map<string,string|number|null>();
 const value=(r:ReadoutRow):string|number|null=>{
  if(extracted.has(r.nctId))return extracted.get(r.nctId)??null;
  const evidence=r.evidence;
  const research=key==="survey"||key==="synthesis"?readoutResearchCoverage(r,bucket,feed):null;
  let v:string|number|null=null;
  switch(key){
   case "row":v=base.get(r.nctId)??null;break;
   case "nctId":v=r.nctId;break;
   case "ticker":v=r.ticker;break;
   case "company":v=r.company;break;
   case "factorP":v=factorPNumeric(evidence?.primaryEndpointP?.display);break;
   case "survey":v=research?.verified??null;break;
   case "synthesis":v=research?(research.ready?100:0)+research.passedChecks*10+research.groupsVerified:null;break;
   case "drug":v=evidence?.drug||null;break;
   case "indication":v=evidence?.indication||null;break;
   case "status":v=r.status;break;
   case "date":v=evidence?.evidenceDate||null;break;
   case "source":v=evidence?.evidenceUrl||null;break;
  }
  if(typeof v==="string"&&!v.trim())v=null;
  extracted.set(r.nctId,v);return v;
 };
 return [...rows].sort((a,b)=>{
  const av=value(a),bv=value(b);
  // Missing data is never a zero and never placed ahead of a sourced value.
  if(av===null&&bv!==null)return 1;
  if(bv===null&&av!==null)return -1;
  let cmp=0;
  if(av!==null&&bv!==null){
   cmp=typeof av==="number"&&typeof bv==="number"?av-bv:
     String(av).localeCompare(String(bv),"en-US",{numeric:true,sensitivity:"base"});
  }
  return (descending?-cmp:cmp)
   ||(base.get(a.nctId)??0)-(base.get(b.nctId)??0)
   ||a.nctId.localeCompare(b.nctId);
 });
}
