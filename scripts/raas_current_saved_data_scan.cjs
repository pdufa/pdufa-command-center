"use strict";
const fs=require("node:fs");
const path=require("node:path");
const base=path.resolve(__dirname,"..");
const prefix="new-platform/frontend/data/";
const files=[
 "tools-pool-snapshot.json","registry-benefit-research-snapshot.json",
 "phase3-readout-survey-research.json","raas-pilot-observations.json",
 "raas-prospective-source-baselines.json","raas-historical-cases.json",
 "raas-historical-metric-snapshots.json","raas-approved-calibrations.json",
 "raas-reviewed-snapshots.json"
];
const describe=(file)=>{
 const raw=fs.readFileSync(path.join(base,prefix,file),"utf8");
 const doc=JSON.parse(raw);
 const arrays=[];
 const describeArray=(label,a)=>({
  path:label,count:a.length,firstKeys:a.length&&a[0]&&typeof a[0]==="object"?Object.keys(a[0]).slice(0,20):[]
 });
 for(const [key,value] of Object.entries(doc)){
  if(Array.isArray(value))arrays.push(describeArray(key,value));
  else if(value&&typeof value==="object"){
   for(const [nestedKey,nestedVal] of Object.entries(value))
    if(Array.isArray(nestedVal))arrays.push(describeArray(key+"."+nestedKey,nestedVal));
  }
 }
 const ids=new Set(raw.match(/NCT\d{8}/g)||[]);
 return {file,bytes:Buffer.byteLength(raw,"utf8"),
  sourceAsOf:doc.sourceAsOf??doc.sourceDate??doc.generatedAt??doc.snapshotDate??null,
  scope:doc.scope??doc.reportType??null,
  keys:Object.keys(doc).slice(0,28),
  arrays,uniqueNctIdsText:ids.size,
  // NCT text occurrences do not prove eligible trades or verification.
  nctIdCountIsTextOnly:true};
};
const inventory=files.map(describe);
const pilot=JSON.parse(fs.readFileSync(path.join(base,prefix+"raas-pilot-observations.json"),"utf8"));
const prospective=JSON.parse(fs.readFileSync(path.join(base,prefix+"raas-prospective-source-baselines.json"),"utf8"));
const findings=pilot.records.map(x=>({
 ticker:x.ticker,nctId:x.nctId,stage:x.stage,
 sourceObservations:x.observations.length,
 candidateMetricIds:[...new Set(x.observations.flatMap(o=>o.metricIds))],
 clinicalCalculations:x.observations.map(o=>({
  evidenceId:o.id,kind:o.kind,assessmentDate:o.assessmentDate,
  placeboAdjustedSymptomReduction:o.kind==="active_control_mean_change"?
    Math.round((o.controlChange-o.activeChange)*100)/100:null,
  comparatorResponsePercentagePointGap:o.kind==="active_control_response"?
    Math.round((o.activePercent-o.controlPercent)*100)/100:null,
  treatedArmResponsePercent:o.kind==="single_arm_response"?o.activePercent:null
 }))
}));
const pool=JSON.parse(fs.readFileSync(path.join(base,prefix+"tools-pool-snapshot.json"),"utf8"));
const registry=JSON.parse(fs.readFileSync(path.join(base,prefix+"registry-benefit-research-snapshot.json"),"utf8"));
const distribution=(items,fn)=>Object.fromEntries([...items.reduce((m,x)=>{
 const key=String(fn(x)??"UNKNOWN");m.set(key,(m.get(key)??0)+1);return m;
},new Map())].sort((a,b)=>b[1]-a[1]).slice(0,40));
const poolRows=pool.pipeline;
const poolExactNcts=new Set(poolRows.map(x=>x.id).filter(x=>typeof x==="string"&&/^NCT\\d{8}$/.test(x)));
const poolResult={
 snapshotGeneratedAt:pool.snapshotGeneratedAt??null,
 asOf:pool.asOf??null,
 sourceHealth:pool.sourceHealth??null,
 totalRows:poolRows.length,
 distinctExactNctRowIds:poolExactNcts.size,
 nonExactNctRowIds:poolRows.length-poolRows.filter(x=>poolExactNcts.has(x.id)).length,
 withNonemptyTicker:poolRows.filter(x=>typeof x.ticker==="string"&&x.ticker.trim()).length,
 withNonemptyDrug:poolRows.filter(x=>typeof x.drug==="string"&&x.drug.trim()).length,
 withNonemptyIndication:poolRows.filter(x=>typeof x.indication==="string"&&x.indication.trim()).length,
 stageDistribution:distribution(poolRows,x=>x.stage)
};
const registryRows=registry.records;
const registryResult={
 censusAsOf:registry.censusAsOf??null,
 scanStartedAt:registry.scanStartedAt??null,
 scanned:registry.scanned??null,
 successful:registry.successful??null,
 failed:registry.failed??null,
 reusedWithin72Hours:registry.reusedWithin72Hours??null,
 trialRecords:registryRows.length,
 distinctNctIds:new Set(registryRows.map(x=>x.nctId)).size,
 resultsPosted:registryRows.filter(x=>x.resultsPosted===true).length,
 noResultsPosted:registryRows.filter(x=>x.resultsPosted===false).length,
 unknownResultsPosted:registryRows.filter(x=>typeof x.resultsPosted!=="boolean").length,
 withPrimaryEndpointRows:registryRows.filter(x=>Array.isArray(x.primary)&&x.primary.length>0).length,
 withSecondaryEndpointRows:registryRows.filter(x=>Array.isArray(x.secondary)&&x.secondary.length>0).length,
 withSeriousAdverseEventTerms:registryRows.filter(x=>Array.isArray(x.seriousAdverseEvents)&&x.seriousAdverseEvents.length>0).length,
 comparatorVerification:distribution(registryRows,x=>x.comparisonVerified),
 evidenceClassification:distribution(registryRows,x=>x.evidenceClassification),
 fdaDecisionVerification:distribution(registryRows,x=>x.fdaDecisionVerified),
 registryStatus:distribution(registryRows,x=>x.registryStatus),
 benefitRank:distribution(registryRows,x=>x.benefitRank)
};
const report={
 kind:"RAAS_CURRENT_SAVED_EVIDENCE_SCAN_NOT_A_METRIC_CALIBRATION",
 runAtUtc:new Date().toISOString(),sourceRef:process.env.GITHUB_SHA??null,
 scope:"REPOSITORY_SAVED_DATA_ONLY_NO_LIVE_11K_CLINICALTRIALS_API_REFRESH",
 inventories:inventory,
 fullPool:poolResult,registryResearch:registryResult,
 pilot:{trialRows:pilot.records.length,uniqueIssuers:new Set(pilot.records.map(x=>x.ticker)).size,
  independentTherapyPrograms:new Set(pilot.records.map(x=>[x.ticker,x.drug,x.indication].join("|"))).size,
  observations:pilot.records.reduce((s,x)=>s+x.observations.length,0),findings},
 prospective:{programRecords:prospective.records.length,
  separateSourceFacts:prospective.records.reduce((n,x)=>n+x.observations.length,0)},
 calibratedMetricCount:JSON.parse(fs.readFileSync(path.join(base,prefix+"raas-approved-calibrations.json"),"utf8")).entries.length,
 validatedHistoricalReturnCaseCount:JSON.parse(fs.readFileSync(path.join(base,prefix+"raas-historical-cases.json"),"utf8")).cases.length
};
const out=process.env.RAAS_SCAN_RESULT_PATH;
if(out)fs.writeFileSync(out,JSON.stringify(report,null,2)+"\n");
console.log("RAAS_CURRENT_SNAPSHOT_SCAN_BEGIN");
console.log(JSON.stringify(report,null,2));
console.log("RAAS_CURRENT_SNAPSHOT_SCAN_END");
