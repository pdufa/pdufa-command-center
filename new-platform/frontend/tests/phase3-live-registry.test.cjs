"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022},
  }).outputText,file
);
const {normalizeRegistryResearchRecord,REGISTRY_SOURCE_ORIGIN}=
  require("../lib/phase3-live-registry.ts");
const source=()=>({
  protocolSection:{
    identificationModule:{nctId:"NCT02142738",briefTitle:"Randomized randomized Phase 3 trial"},
    statusModule:{overallStatus:"COMPLETED",lastUpdatePostDate:"2025-04-01"},
    designModule:{phases:["PHASE3"]},
    sponsorCollaboratorsModule:{leadSponsor:{name:"Example registered sponsor"}},
    conditionsModule:{conditions:["Non-small Cell Lung Cancer"]},
    armsInterventionsModule:{interventions:[{type:"DRUG",name:"Pembrolizumab"},{type:"DRUG",name:"Example comparator"}]},
  },
});
const checkedAt="2026-10-26T12:40:00Z";
const route=fs.readFileSync(path.join(__dirname,"../app/api/phase3-registry/route.ts"),"utf8");
const ui=fs.readFileSync(path.join(__dirname,"../app/installation-audit/phase3-census/Phase3LiveRegistry.tsx"),"utf8");
const details=fs.readFileSync(path.join(__dirname,"../app/installation-audit/phase3-census/Phase3EvidenceDetails.tsx"),"utf8");

test("exact current registry source parses only bounded observational fields, without pretending PDUFA eligibility",()=>{
  const original=source();const snapshot=JSON.stringify(original);
  const r=normalizeRegistryResearchRecord(original,"NCT02142738",checkedAt);
  assert.equal(REGISTRY_SOURCE_ORIGIN,"https://clinicaltrials.gov");
  assert.equal(r.nctId,"NCT02142738");
  assert.equal(r.registryOverallStatus,"COMPLETED");
  assert.equal(r.sourceUpdated,"2025-04-01");
  assert.deepEqual(r.reportedPhases,["PHASE3"]);
  assert.equal(r.phase3CurrentlyReported,true);
  assert.equal(r.registryLeadSponsor,"Example registered sponsor");
  assert.deepEqual(r.conditions,["Non-small Cell Lung Cancer"]);
  assert.equal(r.interventions.length,2);
  assert.equal(r.interventions[0].name,"Pembrolizumab");
  assert.equal(r.recordUrl,"https://clinicaltrials.gov/study/NCT02142738");
  assert.equal(r.apiRecordUrl,"https://clinicaltrials.gov/api/v2/studies/NCT02142738");
  for(const flag of ["verifiedUsFdaPdufa","verifiedCommercialDevelopment","verifiedPipelineQualification"])
    assert.equal(r[flag],false);
  assert.equal(r.qualifiedPipelineTotal,null);
  assert.equal(r.approvalProbability,null);
  assert.equal(JSON.stringify(original),snapshot);
});

test("cross-NCT payload, invented statuses, hostile content and oversized source arrays fail closed",()=>{
  const cases=[
    ["/protocolSection/identificationModule/nctId","NCT02142739"],
    ["/protocolSection/identificationModule/nctId","NCT21"],
    ["/protocolSection/statusModule/overallStatus","<script>alert(1)</script>"],
    ["/protocolSection/identificationModule/briefTitle","X".repeat(1001)],
    ["/protocolSection/conditionsModule/conditions",Array(26).fill("A")],
    ["/protocolSection/armsInterventionsModule/interventions",Array(41).fill({type:"DRUG",name:"A"})],
    ["/protocolSection/armsInterventionsModule/interventions",[{type:"DRUG",name:"=HYPERLINK()"},{name:"Broken"}]],
    ["/protocolSection/designModule/phases",["NOT_PHASE3","X".repeat(61)]],
    ["/protocolSection/statusModule/lastUpdatePostDate","not a date"],
  ];
  for(const [pointer,value] of cases){
    const example=source();const keys=pointer.slice(1).split("/");let obj=example;
    for(const k of keys.slice(0,-1))obj=obj[k];
    obj[keys.at(-1)]=value;
    assert.throws(()=>normalizeRegistryResearchRecord(example,"NCT02142738",checkedAt),undefined,pointer);
  }
  for(const invalid of ["NCT123","NCT0214273X","NCT02142738?x=1"]){
    assert.throws(()=>normalizeRegistryResearchRecord(source(),invalid,checkedAt));
  }
});

test("missing optional registered fields remain missing rather than fabricated",()=>{
  const x=source();
  delete x.protocolSection.armsInterventionsModule;
  delete x.protocolSection.conditionsModule;
  delete x.protocolSection.sponsorCollaboratorsModule;
  delete x.protocolSection.designModule;
  delete x.protocolSection.statusModule.lastUpdatePostDate;
  const result=normalizeRegistryResearchRecord(x,"NCT02142738",checkedAt);
  assert.deepEqual(result.reportedPhases,[]);
  assert.deepEqual(result.interventions,[]);
  assert.deepEqual(result.conditions,[]);
  assert.equal(result.registryLeadSponsor,null);
  assert.equal(result.sourceUpdated,null);
  assert.equal(result.phase3CurrentlyReported,false);
  assert.equal(result.verifiedUsFdaPdufa,false);
});

test("protected fixed-origin source proxy only accepts signed-in exact NCT GET and withholds invalid results",()=>{
  assert.match(route,/authConfigured\(\) \|\| !hasSession/);
  assert.match(route,/status:401/);
  assert.match(route,/req\.nextUrl\.searchParams\.size !== 1/);
  assert.match(route,/\/\^NCT\\d\{8\}\$\//);
  assert.match(route,/REGISTRY_SOURCE_ORIGIN\+"\/api\/v2\/studies\/"\+nct/);
  assert.match(route,/method:"GET"/);
  assert.match(route,/cache:"no-store",redirect:"error"/);
  assert.match(route,/MAX_SOURCE_BYTES = 800_000/);
  assert.match(route,/normalizeRegistryResearchRecord/);
  assert.doesNotMatch(route,/PDUFA_INTERNAL_API_KEY|PDUFA_HOP_INTERNAL_API_KEY|req\.headers\.get\("authorization"\)|method:"POST"|placeTrade/);
});

test("the trial-level UI is manually triggered and never automatically promotes registry content to scientific grades",()=>{
  assert.match(details,/Phase3LiveRegistry nctId=\{assessed.nctId\}/);
  assert.match(ui,/Read current ClinicalTrials.gov source/);
  assert.match(ui,/\/api\/phase3-registry\?exact_nct=/);
  assert.match(ui,/data\.verifiedUsFdaPdufa!==false/);
  assert.match(ui,/data\.verifiedPipelineQualification!==false/);
  assert.match(ui,/data\.approvalProbability!==null/);
  assert.match(ui,/FDA pathway\/PDUFA: NOT VERIFIED/);
  assert.match(ui,/SEC EDGAR company filings/);
  assert.match(ui,/FDA Drugs@FDA database/);
  assert.match(ui,/registration does not establish present intellectual-property|Registration does not establish present intellectual-property/);
  assert.doesNotMatch(ui+route,/runScan\(|placeTrade\(|submitOrder\(|saveGrade\(|database\.insert/);
});
