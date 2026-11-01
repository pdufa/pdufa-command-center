/** Primary-source ClinicalTrials.gov evidence packet for one exactly identified
 * Phase 3 NCT study. Outcome measurements are raw registry observations, NOT
 * proven treatment benefit or comparative superiority. Never infer FDA status.
 */
export type RegistryMeasuredValue={group:string;value:string;spread:string|null};
export type RegistryOutcome={
  title:string;type:"PRIMARY"|"SECONDARY"|"OTHER";timeFrame:string|null;
  unit:string|null;measurements:RegistryMeasuredValue[];
  analysisReported:boolean;
};
export type RegistryAdverseEvent={term:string;groups:{group:string;affected:number;atRisk:number}[]};
export type RegistryBenefitResearch={
  nctId:string;sourceUrl:string;retrievedAt:string;sourceUpdated:string|null;
  registryStatus:string|null;registeredPhases:string[];
  resultsPosted:boolean;primary:RegistryOutcome[];secondary:RegistryOutcome[];
  seriousAdverseEvents:RegistryAdverseEvent[];
  interventions:string[];sponsor:string|null;conditionNames:string[];
  evidenceClassification:"REGISTRY_POSTED_RESULTS"|"REGISTRY_PROTOCOL_ONLY";
  comparisonVerified:false;benefitRank:null;fdaDecisionVerified:false;
};
type Obj=Record<string,unknown>;
const obj=(v:unknown):Obj=>v!==null&&typeof v==="object"&&!Array.isArray(v)?v as Obj:{};
const clean=(v:unknown,max=300):string|null=>
  typeof v==="string"&&v.trim().length>0&&v.length<=max&&!/[\u0000-\u001f\u007f<>]/u.test(v)?v.trim():null;
const array=(v:unknown,max=40):unknown[]=>{
  if(v===undefined||v===null)return [];
  if(!Array.isArray(v)||v.length>max)throw Error("REGISTRY_UNBOUNDED_ARRAY");
  return v;
};
const validDate=(v:unknown):string|null=>{
  const s=clean(v,10);
  if(!s||!/^\d{4}-\d{2}-\d{2}$/.test(s))return null;
  const t=Date.parse(s+"T00:00:00Z");
  return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===s?s:null;
};
const names=(v:unknown,max=25)=>array(v,max).map(x=>clean(x,180)).filter((x):x is string=>x!==null);
const groupName=(groups:Map<string,string>,id:unknown)=>groups.get(String(id))||"Group not identified";
const LIMIT=24;
function measuredOutcomes(raw:unknown):RegistryOutcome[]{
  const module=obj(obj(raw).outcomeMeasuresModule);
  return array(module.outcomeMeasures,LIMIT).map(x=>{
    const o=obj(x),type=o.type==="PRIMARY"?"PRIMARY":o.type==="SECONDARY"?"SECONDARY":"OTHER";
    const groups=new Map<string,string>();
    for(const entry of array(o.groups,20)){
      const g=obj(entry),id=clean(g.id,80),title=clean(g.title,200);
      if(id&&title)groups.set(id,title);
    }
    const measurements:RegistryMeasuredValue[]=[];
    for(const c of array(o.classes,24)){
      for(const cat of array(obj(c).categories,24)){
        for(const m of array(obj(cat).measurements,24)){
          const v=obj(m),value=clean(v.value,80);
          if(value)measurements.push({group:groupName(groups,v.groupId),value,
            spread:clean(v.spread,90)});
          if(measurements.length>=100)break;
        }
        if(measurements.length>=100)break;
      }
      if(measurements.length>=100)break;
    }
    return {title:clean(o.title,380)||"Unspecified reported outcome",type,
      timeFrame:clean(o.timeFrame,150),unit:clean(o.unitOfMeasure,130),
      measurements,analysisReported:array(o.analyses,25).length>0};
  });
}
function seriousEvents(raw:unknown):RegistryAdverseEvent[]{
  const module=obj(obj(raw).adverseEventsModule);
  const names=new Map<string,string>();
  for(const g0 of array(module.eventGroups,25)){
    const g=obj(g0),id=clean(g.id,100),title=clean(g.title,180);
    if(id&&title)names.set(id,title);
  }
  return array(module.seriousEvents,80).map(event=>{
    const e=obj(event),groups:RegistryAdverseEvent["groups"]=[];
    for(const s0 of array(e.stats,25)){
      const s=obj(s0),affected=s.numAffected,atRisk=s.numAtRisk;
      if(Number.isSafeInteger(affected)&&Number.isSafeInteger(atRisk)
        &&Number(affected)>=0&&Number(atRisk)>0&&Number(affected)<=Number(atRisk)){
        groups.push({group:groupName(names,s.groupId),affected:Number(affected),atRisk:Number(atRisk)});
      }
    }
    return {term:clean(e.term,280)||"Serious adverse event term not recorded",groups};
  });
}
export function parseRegistryBenefitResearch(raw:unknown,nctId:string,retrievedAt:string):RegistryBenefitResearch{
  if(!/^NCT\d{8}$/.test(nctId)||!Number.isFinite(Date.parse(retrievedAt)))
    throw Error("REGISTRY_EXPECTED_ID_INVALID");
  const study=obj(raw),p=obj(study.protocolSection),identity=obj(p.identificationModule);
  if(identity.nctId!==nctId)throw Error("REGISTRY_NCT_MISMATCH");
  const status=obj(p.statusModule),results=obj(study.resultsSection);
  const hasResults=study.hasResults===true&&Object.keys(results).length>0;
  const primaryAndSecondary=hasResults?measuredOutcomes(results):[];
  const interventions=array(obj(p.armsInterventionsModule).interventions,40)
    .map(x=>clean(obj(x).name,180)).filter((x):x is string=>!!x);
  return {nctId,sourceUrl:"https://clinicaltrials.gov/study/"+nctId,
    retrievedAt,sourceUpdated:validDate(obj(status.lastUpdatePostDateStruct).date)||validDate(status.lastUpdatePostDate),
    registryStatus:clean(status.overallStatus,80),
    registeredPhases:names(obj(p.designModule).phases,8),
    resultsPosted:hasResults,
    primary:primaryAndSecondary.filter(x=>x.type==="PRIMARY"),
    secondary:primaryAndSecondary.filter(x=>x.type!=="PRIMARY"),
    seriousAdverseEvents:hasResults?seriousEvents(results):[],
    interventions,sponsor:clean(obj(obj(p.sponsorCollaboratorsModule).leadSponsor).name,220),
    conditionNames:names(obj(p.conditionsModule).conditions,25),
    evidenceClassification:hasResults?"REGISTRY_POSTED_RESULTS":"REGISTRY_PROTOCOL_ONLY",
    comparisonVerified:false,benefitRank:null,fdaDecisionVerified:false};
}
