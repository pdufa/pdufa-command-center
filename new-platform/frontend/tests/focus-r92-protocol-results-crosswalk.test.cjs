"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>{
 const result=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(result.outputText,file);
};
const {
 R92_CURRENT_PROTOCOL_RESULTS_ROSTER,inspectR92CurrentProtocolResults,
 R92_SCIENTIFIC_LIMIT
}=require("../lib/focus-r92-protocol-results-crosswalk.ts");
const frozenR92=require("../data/focus-r92-current-protocol-results-primary-text-audit-20261110.json");
const {R92_DATED_CROSSWALK_AUDIT,buildR92DatedCrosswalkAudit}=
 require("../lib/focus-r92-dated-crosswalk-audit.ts");
const {GET}=require(
 "../app/predictions/scientific-reconciliation/protocol-crosswalk/check/route.ts");
function row(){const r=R92_CURRENT_PROTOCOL_RESULTS_ROSTER.rows[0];assert.ok(r);return r;}
function study(nct=row().nct){
 return {
  protocolSection:{
   identificationModule:{nctId:nct},
   outcomesModule:{
    primaryOutcomes:[
     {measure:"Clinical remission at week 8",timeFrame:"Week 8",
      description:"Registry's CURRENT protocol primary outcome"},
     {measure:"Smoking abstinence at week 8",timeFrame:"Week 8"}
    ]
   }
  },
  hasResults:true,
  resultsSection:{
   participantFlowModule:{groups:[
    {id:"FG000",title:"Active study arm"},{id:"FG001",title:"Control study arm"}
   ]},
   outcomeMeasuresModule:{outcomeMeasures:[
    {type:"PRIMARY",title:"Clinical Remission at Week 8",timeFrame:"Week 8",
     groups:[{id:"OG000",title:"Active"},{id:"OG001",title:"Control"}],
     denoms:[{units:"Participants",counts:[
      {groupId:"OG000",value:"122"},{groupId:"OG001",value:"117"}]}],
     classes:[{categories:[{measurements:[
      {groupId:"OG000",value:"77"},{groupId:"OG001",value:"53"}]}]}],
     analyses:[{groupIds:["OG000","OG001"],pValue:"0.039",
      statisticalMethod:"Fisher exact test"}]},
    {type:"PRIMARY",title:"Smoking abstinence at week 8",
     timeFrame:"Week 10",groups:[{id:"OG000",title:"Active"}]},
    {type:"PRIMARY",title:"Unrelated cardiovascular marker",
     timeFrame:"Week 20",groups:[{id:"OG000",title:"Active"}]},
    {type:"SECONDARY",title:"Other endpoint",
     groups:[{id:"OG000",title:"Active"}]}
   ]},
   adverseEventsModule:{
    eventGroups:[
     {id:"EG000",title:"Active",seriousNumAffected:5,seriousNumAtRisk:122},
     {id:"EG001",title:"Control",seriousNumAffected:2,seriousNumAtRisk:117}
    ],
    seriousEvents:[],otherEvents:[]
   }
  }
 };
}
test("R92 builds an exact 12-of-29/23 lock with no prospective SAP or FDA signoff",()=>{
 const r=R92_CURRENT_PROTOCOL_RESULTS_ROSTER;
 assert.ok(r);
 assert.equal(r.exactFocusTrials,29);
 assert.equal(r.provisionalFDACycles,23);
 assert.equal(r.registeredResultNcts,12);
 assert.equal(r.priorObservedPrimaryOutcomes,16);
 assert.equal(r.rows.length,12);
 assert.equal(new Set(r.rows.map(x=>x.nct)).size,12);
 assert.equal(r.originalSignedSAPsAuthenticated,0);
 assert.equal(r.independentScientificSignoffs,0);
 assert.equal(r.validatedFDAForecasts,0);
 assert.ok(r.rows.every(x=>x.originalSignedSAPAuthenticated===false&&
  x.independentlyAdjudicated===false&&x.FDAForecast==="ABSTAIN"&&
  /^[0-9a-f]{64}$/.test(x.datedOriginalResultsSHA256)));
 assert.match(R92_SCIENTIFIC_LIMIT,/DOES NOT|not evidence/i);
});
test("R92 frozen public-source text audit validates 12 official NCT receipts, all 16 title/timeframe pairs, no signed SAP or FDA claims",()=>{
 const d=R92_DATED_CROSSWALK_AUDIT;
 assert.ok(d);
 assert.equal(d.checkedNcts,12);
 assert.equal(d.plannedPrimaryTextEntries,16);
 assert.equal(d.postedPrimaryTextEntries,16);
 assert.equal(d.exactCurrentRegistryTitleTimeframeMatches,16);
 assert.equal(d.observedTextDifferences,0);
 assert.equal(d.rawR91SourceHashesStable,12);
 assert.equal(d.independentSignedSAPAttestations,0);
 assert.equal(d.qualifiedIndependentMedicalReviews,0);
 assert.equal(d.calibratedFDAPredictions,0);
 assert.equal(d.rows.length,12);
 assert.deepEqual(
  new Set(d.rows.map(x=>x.nct)),
  new Set(R92_CURRENT_PROTOCOL_RESULTS_ROSTER.rows.map(x=>x.nct))
 );
 assert.ok(d.rows.every(x=>x.originalSAPProspectivityVerified===false&&
  x.qualifiedClinicalReviewSigned===false&&x.FDAForecast==="ABSTAIN"&&
  /^[a-f0-9]{64}$/.test(x.sourceSHA256)));
});
test("R92 frozen source crosswalk fails closed if a title, SHA, NCT, or scientific signoff is forged",()=>{
 const tamper=[
  x=>{x.rows[0].nct="NCT00000000";},
  x=>{x.rows[0].ticker="FAKE";},
  x=>{x.rows[0].currentOriginalApiSha256="a".repeat(64);},
  x=>{x.rows[0].sourceUrl="https://attacker.example";},
  x=>{x.rows[0].plannedPrimaryOutcomes[0].title="Fake Protocol Title";},
  x=>{x.rows[0].postedPrimaryOutcomes[0].title="Forged outcome";},
  x=>{x.rows[0].textualCorrespondence[0].state="LEXICAL_CANDIDATE_REQUIRES_REVIEW";},
  x=>{x.rows[0].originalPreUnblindingSignedSAPAuthenticated=true;},
  x=>{x.rows[0].independentClinicalEndpointAdjudication=true;},
  x=>{x.rows[0].FDAOutcome="APPROVED";},
  x=>{x.rows[1].nct=x.rows[0].nct;},
  x=>{x.rows.pop();},
  x=>{x.counts.exactNormalizedTitleAndTimeFrameTextMatches=15;},
  x=>{x.counts.qualifedReviewSignoffs=1; x.counts.qualifiedClinicalStatisticalReviewSignoffs=1;}
 ];
 for(const fn of tamper){
  const fake=structuredClone(frozenR92);
  fn(fake);
  assert.equal(buildR92DatedCrosswalkAudit(fake),null);
 }
});
test("R92 preserves literal current registry planned and posted outcome titles separately",()=>{
 const result=inspectR92CurrentProtocolResults(row(),study());
 assert.ok(result);
 assert.equal(result.currentProtocolPrimaryCount,2);
 assert.equal(result.postedRegistryPrimaryCount,3);
 assert.equal(result.exactTitleAndTimeframeCount,1);
 assert.equal(result.exactTitleDifferentTimeframeCount,1);
 assert.equal(result.needsIndependentEndpointReviewCount,1);
 assert.equal(result.textualCrosswalk[0].state,"EXACT_TITLE_AND_TIME_FRAME");
 assert.equal(result.textualCrosswalk[1].state,"EXACT_TITLE_TIME_FRAME_DIFFERS");
 assert.equal(result.textualCrosswalk[2].state,"NO_LEXICAL_CANDIDATE_REQUIRES_REVIEW");
 assert.equal(result.textualCrosswalk[0].postedTitle,"Clinical Remission at Week 8");
 assert.equal(result.plannedPrimaryOutcomes[0].title,"Clinical remission at week 8");
 assert.equal(result.postedPrimaryOutcomes[0].sourceReportedDenominatorEntries,2);
 assert.equal(result.postedPrimaryOutcomes[0].sourceReportedPValueEntries,1);
 assert.equal(result.originalProspectiveSAPAuthenticated,false);
 assert.equal(result.clinicalEndpointConsistencyIndependentlySigned,false);
 assert.equal(result.sourceVersionEffectiveBeforeUnblindingVerified,false);
 assert.equal(result.scienceGrade,null);
 assert.equal(result.FDAForecast,"ABSTAIN");
});
test("R92 does not auto-resolve duplicate current protocol endpoint names",()=>{
 const studyBody=study();
 studyBody.protocolSection.outcomesModule.primaryOutcomes.push(
  structuredClone(studyBody.protocolSection.outcomesModule.primaryOutcomes[0]));
 const result=inspectR92CurrentProtocolResults(row(),studyBody);
 assert.ok(result);
 assert.equal(result.textualCrosswalk[0].state,
  "MULTIPLE_POSSIBLE_PROTOCOL_ENTRIES");
 assert.equal(result.textualCrosswalk[0].possibleProtocolKeys.length,2);
 assert.equal(result.needsIndependentEndpointReviewCount,2);
});
test("R92 fails on swapped NCT, no protocol primary metadata, corrupted posted safety, missing result",()=>{
 const changed=[
  x=>{x.protocolSection.identificationModule.nctId="NCT00000000";},
  x=>{delete x.protocolSection.outcomesModule;},
  x=>{x.protocolSection.outcomesModule.primaryOutcomes[0].measure="";},
  x=>{x.protocolSection.outcomesModule.primaryOutcomes[0].timeFrame="bad\nnewline";},
  x=>{x.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].groups[0].id="";},
  x=>{x.resultsSection.adverseEventsModule.eventGroups[0].id="";},
  x=>{x.resultsSection.outcomeMeasuresModule.outcomeMeasures=[];},
  x=>{x.hasResults=false;delete x.resultsSection;}
 ];
 for(const mutate of changed){
  const v=study();mutate(v);
  if(v.resultsSection?.outcomeMeasuresModule?.outcomeMeasures?.length===0){
    const noResults=inspectR92CurrentProtocolResults(row(),v);
    assert.ok(noResults);
    assert.equal(noResults.postedRegistryPrimaryCount,0);
    assert.equal(noResults.priorSourceCountChanged,true);
    continue;
  }
  assert.equal(inspectR92CurrentProtocolResults(row(),v),null);
 }
});
async function withFetch(impl,fn){
 const saved=global.fetch;global.fetch=impl;
 try{return await fn();}finally{global.fetch=saved;}
}
function req(q){return new Request(
 "https://preview.test/predictions/scientific-reconciliation/protocol-crosswalk/check"+q);
}
test("R92 GET exact current original source readback returns SHA256 and no FDA decision",async()=>{
 const nct=row().nct;
 await withFetch(async url=>{
  assert.equal(url,"https://clinicaltrials.gov/api/v2/studies/"+nct+"?format=json");
  return Response.json(study(nct));
 },async()=>{
  const response=await GET(req("?nct="+nct));
  assert.equal(response.status,200);
  const body=await response.json();
  assert.equal(body.nct,nct);
  assert.match(body.currentOriginalApiSha256,/^[a-f0-9]{64}$/);
  assert.equal(body.currentOriginalSourceMatchesR91Receipt,false);
  assert.equal(body.exactTitleAndTimeframeCount,1);
  assert.equal(body.signedProspectiveSAPsConfirmed,0);
  assert.equal(body.independentClinicalEndPointJudgments,0);
  assert.equal(body.FDAForecast,"ABSTAIN");
 });
});
test("R92 unknown/invalid identifiers and blocked source are safe and never fake trial failure",async()=>{
 assert.equal((await GET(req("?nct=NCT00000000"))).status,404);
 assert.equal((await GET(req("?nct=%3Cscript%3E"))).status,400);
 await withFetch(async()=>new Response("blocked",{status:403}),async()=>{
  const response=await GET(req("?nct="+row().nct));
  assert.equal(response.status,502);
  const data=await response.json();
  assert.equal(data.FDAForecast,"ABSTAIN");
 });
 await withFetch(async()=>Response.json(study("NCT00000000")),async()=>{
  const response=await GET(req("?nct="+row().nct));
  assert.equal(response.status,502);
 });
});
test("R92 browser source page is linked to original scientific review, never allows score writes",()=>{
 const page=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/protocol-crosswalk/page.tsx"),"utf8");
 const client=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/protocol-crosswalk/CurrentProtocolResultsR92Client.tsx"),"utf8");
 const route=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/protocol-crosswalk/check/route.ts"),"utf8");
 const existing=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/page.tsx"),"utf8");
 assert.match(page,/Registry design-to-results primary endpoint comparison/);
 assert.match(page,/R92_DATED_CROSSWALK_AUDIT/);
 assert.match(client,/Compare all 12 current protocol and posted result records/);
 assert.match(client,/No close text candidate/);
 assert.match(client,/FDA Forecast: ABSTAIN/);
 assert.match(route,/sourceMatchesR91|currentOriginalSourceMatchesR91Receipt/);
 assert.match(route,/redirect:"error"/);
 assert.match(existing,/\/predictions\/scientific-reconciliation\/protocol-crosswalk/);
 assert.doesNotMatch(route,/method:"POST"|submitClinicalScore|setGrade\(/);
});
