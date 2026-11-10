"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>{
 const x=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(x.outputText,file);
};
const {R91_POSTED_RESULTS_ROSTER,buildR91PostedResultsSourceRoster,
 inspectR91CurrentPostedResults}=require("../lib/focus-r91-posted-results-reconciliation.ts");
const {GET}=require("../app/predictions/scientific-reconciliation/check/route.ts");
function row(){const r=R91_POSTED_RESULTS_ROSTER.rows.find(x=>x.nct==="NCT05507203");
 assert.ok(r);return r;}
function posted(nct=row().nct){
 return {
  protocolSection:{identificationModule:{nctId:nct}},
  hasResults:true,
  resultsSection:{
   participantFlowModule:{groups:[
    {id:"FG000",title:"Active treatment"},{id:"FG001",title:"Control"}
   ]},
   outcomeMeasuresModule:{outcomeMeasures:[
    {type:"PRIMARY",title:"Primary reported endpoint",
     timeFrame:"Week 24",populationDescription:"Reported analysis population",
     unitOfMeasure:"Points",paramType:"MEAN",
     groups:[{id:"OG000",title:"Active"},{id:"OG001",title:"Control"}],
     denoms:[{units:"Participants",counts:[
      {groupId:"OG000",value:"122"},{groupId:"OG001",value:"117"}]}],
     classes:[{categories:[{measurements:[
      {groupId:"OG000",value:"12.8",spread:"2.1"},
      {groupId:"OG001",value:"9.3",spread:"2.2"}
     ]}]}],
     analyses:[{groups:["OG000","OG001"],pValue:"0.032",pValueMethod:"ANCOVA"}]},
    {type:"SECONDARY",title:"Secondary reported endpoint",
     groups:[{id:"OG000",title:"Active"}]}
   ]},
   adverseEventsModule:{
    groups:[
     {id:"EG000",title:"Active",seriousNumAffected:4,seriousNumAtRisk:122,
      otherNumAffected:40,otherNumAtRisk:122},
     {id:"EG001",title:"Control",seriousNumAffected:1,seriousNumAtRisk:117,
      otherNumAffected:36,otherNumAtRisk:117}
    ],
    seriousEvents:[{term:"Example serious event",organSystem:"Cardiac disorders",
     stats:[{groupId:"EG000",numAffected:3,numAtRisk:122,numEvents:4},
      {groupId:"EG001",numAffected:1,numAtRisk:117,numEvents:1}]}],
    otherEvents:[{term:"Example other event",stats:[
     {groupId:"EG000",numAffected:6,numAtRisk:122,numEvents:6}]}]
   }
  }
 };
}
test("R91 exact 29/23 focus roster preserves 12 original aggregate-results records without clinical certification",()=>{
 const d=R91_POSTED_RESULTS_ROSTER;
 assert.ok(d);
 assert.equal(d.exactTrials,29);
 assert.equal(d.provisionalCycles,23);
 assert.equal(d.rows.length,29);
 assert.equal(new Set(d.rows.map(r=>r.nct)).size,29);
 assert.equal(new Set(d.rows.flatMap(r=>r.cycleIds)).size,23);
 assert.equal(d.withPostedResultsAtSnapshot,12);
 assert.equal(d.withoutPostedResultsAtSnapshot,17);
 assert.equal(d.rows.filter(r=>r.resultsPostedInDatedRegistrySnapshot).length,12);
 assert.equal(d.originalSignedSAPsVerified,0);
 assert.equal(d.originalAnalysisPopulationsIndependentlyReconciled,0);
 assert.equal(d.qualifiedScienceSignoffs,0);
 assert.equal(d.validatedFDAPredictions,0);
 assert.ok(d.rows.every(x=>x.FDAForecast==="ABSTAIN"&&
   x.independentQualifiedClinicalReview===false&&
   x.signedProspectiveSAPAuthenticated===false));
});
test("R91 transcribes original posted primary measures, source p-value strings and safety exposure denominators without statistical judgment",()=>{
 const x=inspectR91CurrentPostedResults(row(),posted());
 assert.ok(x);
 assert.equal(x.sourceStatus,"ORIGINAL_PUBLIC_AGGREGATE_RESULTS_POSTED_NOT_ADJUDICATED");
 assert.equal(x.primaryOutcomeCount,1);
 assert.equal(x.outcomeMeasureCount,2);
 assert.equal(x.registeredOutcomes[0].title,"Primary reported endpoint");
 assert.deepEqual(x.registeredOutcomes[0].denominators[0].counts,[
  {groupId:"OG000",value:"122"},{groupId:"OG001",value:"117"}]);
 assert.equal(x.registeredOutcomes[0].measurements.length,2);
 assert.equal(x.registeredOutcomes[0].analyses[0].pValue,"0.032");
 assert.equal(x.registeredOutcomes[0].analyses[0].pValueMethod,"ANCOVA");
 assert.equal(x.safetyExposureGroups.length,2);
 assert.equal(x.safetyExposureGroups[0].seriousNumAffected,4);
 assert.equal(x.safetyExposureGroups[0].seriousNumAtRisk,122);
 assert.equal(x.seriousAdverseEventTerms[0].stats.length,2);
 assert.equal(x.originalSignedSAPVerified,false);
 assert.equal(x.independentStatisticalReanalysis,false);
 assert.equal(x.independentSafetyAdjudication,false);
 assert.equal(x.FDAForecast,"ABSTAIN");
});
test("R91 current record absent aggregates is a public source gap, never a failed-trial judgment",()=>{
 const current=posted();
 current.hasResults=false;
 delete current.resultsSection;
 const out=inspectR91CurrentPostedResults(row(),current);
 assert.ok(out);
 assert.equal(out.sourceStatus,"NO_AGGREGATE_RESULTS_CURRENTLY_POSTED");
 assert.equal(out.sourceChangedSinceDatedSnapshot,true);
 assert.equal(out.primaryOutcomeCount,0);
 assert.equal(out.FDAForecast,"ABSTAIN");
 const never=R91_POSTED_RESULTS_ROSTER.rows.find(x=>!x.resultsPostedInDatedRegistrySnapshot);
 assert.ok(never);
 const x=inspectR91CurrentPostedResults(never,posted(never.nct));
 assert.ok(x);
 assert.equal(x.sourceChangedSinceDatedSnapshot,true);
});
test("R91 rejects cross-NCT swaps, malformed original measure group IDs and unsafe data shapes",()=>{
 const base=row();
 for(const mutate of [
  x=>{x.protocolSection.identificationModule.nctId="NCT00000000";},
  x=>{x.hasResults="true";},
  x=>{x.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].type=undefined;},
  x=>{x.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].groups[1].id="OG000";},
  x=>{x.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].analyses[0].groups=["OG999"];},
  x=>{x.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0].categories[0].measurements[0].groupId="OG999";},
  x=>{x.resultsSection.adverseEventsModule.seriousEvents[0].stats[0].groupId="EG999";},
  x=>{delete x.resultsSection.adverseEventsModule;},
  x=>{x.resultsSection.outcomeMeasuresModule.outcomeMeasures=Array.from({length:601},()=>({type:"PRIMARY",title:"fake"}));}
 ]){
  const altered=posted();mutate(altered);
  assert.equal(inspectR91CurrentPostedResults(base,altered),null);
 }
 assert.equal(inspectR91CurrentPostedResults(base,null),null);
});
async function withFetch(fetchImpl,callback){
 const saved=global.fetch;global.fetch=fetchImpl;
 try{return await callback();}finally{global.fetch=saved;}
}
function request(nct){return new Request("https://preview.test/predictions/scientific-reconciliation/check?nct="+encodeURIComponent(nct));}
test("R91 original live source handler hashes the authentic exact-NCT public response and never creates grades",async()=>{
 const r=row();
 await withFetch(async url=>{
  assert.equal(url,"https://clinicaltrials.gov/api/v2/studies/"+r.nct+"?format=json");
  return Response.json(posted(r.nct));
 },async()=>{
  const response=await GET(request(r.nct));
  assert.equal(response.status,200);
  const body=await response.json();
  assert.match(body.sourceSHA256,/^[a-f0-9]{64}$/);
  assert.equal(body.nct,r.nct);
  assert.equal(body.sourceApiUrl,"https://clinicaltrials.gov/api/v2/studies/"+r.nct+"?format=json");
  assert.equal(body.primaryOutcomeCount,1);
  assert.equal(body.independentClinicalGrades,0);
  assert.equal(body.medicallyVerifiedSafetyReconciliations,0);
  assert.equal(body.FDAForecast,"ABSTAIN");
  assert.equal(body.regulatorOutcome,"ABSTAIN");
 });
});
test("R91 invalid/outside NCT or blocked source never turns into a treatment failure or FDA score",async()=>{
 assert.equal((await GET(request("bad"))).status,400);
 assert.equal((await GET(request("NCT00000000"))).status,404);
 await withFetch(async()=>new Response("unavailable",{status:503}),async()=>{
  const response=await GET(request(row().nct));
  assert.equal(response.status,502);
  assert.equal((await response.json()).FDAForecast,"ABSTAIN");
 });
 await withFetch(async()=>Response.json(posted("NCT00000000")),async()=>{
  const response=await GET(request(row().nct));
  assert.equal(response.status,502);
 });
});
test("R91 source page is accessible from original evidence inventory and never performs scientific model writes",()=>{
 const page=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/page.tsx"),"utf8");
 const client=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/PostedResultsR91Client.tsx"),"utf8");
 const route=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/check/route.ts"),"utf8");
 const inventory=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/page.tsx"),"utf8");
 assert.match(page,/Primary endpoints, analysis groups and adverse-event denominators/);
 assert.match(client,/Check all 12 publicly posted result records/);
 assert.match(client,/Independent efficacy model: NOT REANALYZED/);
 assert.match(client,/Safety adjudication: NOT SIGNED/);
 assert.match(route,/sha256/);
 assert.match(route,/redirect:"error"/);
 assert.match(route,/sourceApiUrl/);
 assert.match(inventory,/\/predictions\/scientific-reconciliation/);
 assert.doesNotMatch(route,/method:"POST"|submitClinicalScore|setGrade\(/);
});
