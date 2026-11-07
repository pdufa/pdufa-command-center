/**
 * Source-only ClinicalTrials.gov POOL enrichment.
 * No scoring, inferred outcomes, FDA qualification, or guessed zeroes.
 * Fields remain null when the official record does not report them.
 */
export const POOL_DETAIL_FIELDS=[
 "studyTitle","leadSponsor","studyDesign","treatmentArms","enrollment",
 "eligibility","primaryEndpoints","secondaryEndpoints","reportedResults",
 "safetyResults","studyLocations","milestoneDateTypes",
 "terminationReason","documentsPublications"
] as const;
export type PoolDetailField=typeof POOL_DETAIL_FIELDS[number];
export type PoolRegistryDetail={
 nctId:string;sourceUrl:string;retrievedAt:string;
 fields:Record<PoolDetailField,string|null>;
 available:number;total:14;
};
type ObjectMap=Record<string,unknown>;
const obj=(v:unknown):ObjectMap=>v!==null&&typeof v==="object"&&!Array.isArray(v)?v as ObjectMap:{};
const arr=(v:unknown):unknown[]=>Array.isArray(v)?v:[];
const str=(v:unknown):string=>typeof v==="string"?v.trim():typeof v==="number"&&Number.isFinite(v)?String(v):"";
const clean=(v:unknown,max=300):string=>str(v).replace(/\s+/g," ").slice(0,max);
const unique=(v:string[])=>[...new Set(v.filter(Boolean))];
const list=(v:string[],max=5):string|null=>{
 const values=unique(v).slice(0,max);
 return values.length?values.join("; ").slice(0,2200):null;
};
function endpointList(v:unknown):string|null{
 return list(arr(v).map(x=>{
  const o=obj(x),label=clean(o.measure,240),period=clean(o.timeFrame,120);
  return label+(period?" ("+period+")":"");
 }),8);
}
function outcomeMeasurements(v:unknown):string|null{
 const result:string[]=[];
 for(const item of arr(v).slice(0,8)){
  const o=obj(item),groupNames=new Map(arr(o.groups).map(g=>{
   const group=obj(g);return [str(group.id),clean(group.title,100)] as const;
  }));
  const title=clean(o.title,150),unit=clean(o.unitOfMeasure,40);
  for(const cls of arr(o.classes)){
   const block=obj(cls);
   for(const category of arr(block.categories).length?arr(block.categories):[{}]){
    for(const raw of arr(obj(category).measurements)){
     const measurement=obj(raw),value=clean(measurement.value,90);
     if(!value)continue;
     const group=groupNames.get(str(measurement.groupId))||str(measurement.groupId);
     const label=[title,group].filter(Boolean).join(" · ");
     result.push(label+": "+value+(unit?" "+unit:""));
     if(result.length>=12)return list(result,12);
    }
   }
  }
 }
 return list(result,12);
}
function safetyNumbers(v:unknown):string|null{
 const groups=arr(obj(v).eventGroups);
 return list(groups.map(x=>{
  const group=obj(x),name=clean(group.title,100)||clean(group.id,50);
  const serious=clean(group.seriousNumAffected,30),seriousN=clean(group.seriousNumAtRisk,30);
  const other=clean(group.otherNumAffected,30),otherN=clean(group.otherNumAtRisk,30);
  const parts=[serious&&seriousN?"serious "+serious+"/"+seriousN:"",
   other&&otherN?"other "+other+"/"+otherN:""].filter(Boolean);
  return name&&parts.length?name+" ("+parts.join(", ")+")":"";
 }),8);
}
export function normalizePoolRegistryDetail(raw:unknown,nctId:string,retrievedAt:string):PoolRegistryDetail{
 if(!/^NCT\d{8}$/.test(nctId)||!Number.isFinite(Date.parse(retrievedAt)))throw Error("POOL_REGISTRY_ID_INVALID");
 const protocol=obj(obj(raw).protocolSection);
 const identity=obj(protocol.identificationModule);
 if(str(identity.nctId)!==nctId)throw Error("POOL_REGISTRY_ID_MISMATCH");
 const status=obj(protocol.statusModule),design=obj(protocol.designModule);
 const arms=obj(protocol.armsInterventionsModule),eligibility=obj(protocol.eligibilityModule);
 const results=obj(obj(raw).resultsSection);
 const outcomes=obj(protocol.outcomesModule);
 const contacts=obj(protocol.contactsLocationsModule);
 const references=obj(protocol.referencesModule),documents=obj(protocol.documentSection);
 const dates=([["Start",status.startDateStruct],["Primary completion",status.primaryCompletionDateStruct],
  ["Study completion",status.completionDateStruct]] as [string,unknown][]).map(([name,entry])=>{
   const e=obj(entry),date=clean(e.date,40),kind=clean(e.type,40);
   return date?name+": "+date+(kind?" ("+kind+")":""):"";
  });
 const population=obj(design.enrollmentInfo);
 const enrollment=clean(population.count,30);
 const type=clean(population.type,30);
 const designInfo=obj(design.designInfo);
 const maskingInfo=obj(designInfo.maskingInfo);
 const comparatorArms=arr(arms.armGroups).map(x=>{
  const a=obj(x),name=clean(a.label,100),kind=clean(a.type,40);
  const interventions=arr(a.interventionNames).map(y=>clean(y,90)).filter(Boolean);
  return [name,kind,interventions.join(" / ")].filter(Boolean).join(" · ");
 });
 const locations=arr(contacts.locations).map(x=>{
  const v=obj(x);
  return [clean(v.city,50),clean(v.state,50),clean(v.country,50)].filter(Boolean).join(", ");
 });
 const citationList=arr(references.references).map(x=>clean(obj(x).citation,200));
 const documentList=arr(documents.largeDocuments).map(x=>{
  const d=obj(x),name=clean(d.label,80)||clean(d.type,80),url=clean(d.url,200);
  return [name,url].filter(Boolean).join(": ");
 });
 const labels=([
  ["Type",design.studyType],["Allocation",designInfo.allocation],
  ["Intervention model",designInfo.interventionModel],["Masking",maskingInfo.masking],
  ["Purpose",designInfo.primaryPurpose]
 ] as [string,unknown][]).map(([label,v])=>{const value=clean(v,100);return value?label+": "+value:"";});
 const fields:Record<PoolDetailField,string|null>={
  studyTitle:clean(identity.officialTitle,350)||clean(identity.briefTitle,350)||null,
  leadSponsor:clean(obj(obj(protocol.sponsorCollaboratorsModule).leadSponsor).name,220)||null,
  studyDesign:list(labels,6),
  treatmentArms:list(comparatorArms,8),
  enrollment:enrollment?enrollment+(type?" ("+type+")":""):null,
  eligibility:clean(eligibility.eligibilityCriteria,1800)||null,
  primaryEndpoints:endpointList(outcomes.primaryOutcomes),
  secondaryEndpoints:endpointList(outcomes.secondaryOutcomes),
  reportedResults:outcomeMeasurements(obj(results.outcomeMeasuresModule).outcomeMeasures),
  safetyResults:safetyNumbers(obj(results.adverseEventsModule)),
  studyLocations:list(locations,12),
  milestoneDateTypes:list(dates,3),
  terminationReason:clean(status.whyStopped,500)||null,
  documentsPublications:list([...citationList,...documentList],8),
 };
 return {nctId,sourceUrl:"https://clinicaltrials.gov/study/"+nctId,retrievedAt,
  fields,available:Object.values(fields).filter(Boolean).length,total:14};
}
