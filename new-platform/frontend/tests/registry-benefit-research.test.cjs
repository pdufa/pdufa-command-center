"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),
 {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {parseRegistryBenefitResearch}=require("../lib/registry-benefit-research.ts");
const id="NCT12345678",now="2026-10-31T19:15:00.000Z";
const study=()=>({
 hasResults:true,protocolSection:{
  identificationModule:{nctId:id},
  statusModule:{overallStatus:"COMPLETED",lastUpdatePostDateStruct:{date:"2026-10-15"}},
  designModule:{phases:["PHASE3"]},
  conditionsModule:{conditions:["Disease X"]},
  armsInterventionsModule:{interventions:[{name:"Example therapy"},{name:"Active comparator"}]},
  sponsorCollaboratorsModule:{leadSponsor:{name:"Example sponsor"}}
 },
 resultsSection:{
  outcomeMeasuresModule:{outcomeMeasures:[{
   type:"PRIMARY",title:"Primary Response Rate",unitOfMeasure:"Percentage of participants",timeFrame:"Week 24",
   groups:[{id:"OG1",title:"Treatment arm"},{id:"OG2",title:"Comparator arm"}],
   classes:[{categories:[{measurements:[
    {groupId:"OG1",value:"51.2"},{groupId:"OG2",value:"46.3"}
   ]}]}],analyses:[{pValue:"0.1"}]
  }]},
  adverseEventsModule:{eventGroups:[{id:"EG1",title:"Treatment"},{id:"EG2",title:"Comparator"}],
   seriousEvents:[{term:"Pneumonia",stats:[
    {groupId:"EG1",numAffected:2,numAtRisk:100},
    {groupId:"EG2",numAffected:4,numAtRisk:102}
   ]}]}
 }
});
test("primary source extraction yields exactly sourced arm measurements, not a comparative grade",()=>{
 const out=parseRegistryBenefitResearch(study(),id,now);
 assert.equal(out.sourceUrl,"https://clinicaltrials.gov/study/"+id);
 assert.equal(out.resultsPosted,true);
 assert.equal(out.primary.length,1);
 assert.deepEqual(out.primary[0].measurements.map(x=>x.value),["51.2","46.3"]);
 assert.deepEqual(out.primary[0].measurements.map(x=>x.group),["Treatment arm","Comparator arm"]);
 assert.equal(out.primary[0].analysisReported,true);
 assert.equal(out.seriousAdverseEvents[0].groups[0].affected,2);
 assert.equal(out.seriousAdverseEvents[0].groups[0].atRisk,100);
 assert.equal(out.comparisonVerified,false);
 assert.equal(out.benefitRank,null);
 assert.equal(out.fdaDecisionVerified,false);
});
test("absent posted results produce protocol-only not zero events",()=>{
 const raw=study();raw.hasResults=false;delete raw.resultsSection;
 const result=parseRegistryBenefitResearch(raw,id,now);
 assert.equal(result.evidenceClassification,"REGISTRY_PROTOCOL_ONLY");
 assert.equal(result.resultsPosted,false);
 assert.deepEqual(result.primary,[]);
 assert.deepEqual(result.seriousAdverseEvents,[]);
 assert.equal(result.registryStatus,"COMPLETED");
});
test("mismatched NCT and implausible counts are withheld",()=>{
 assert.throws(()=>parseRegistryBenefitResearch(study(),"NCT87654321",now),/REGISTRY_NCT_MISMATCH/);
 const raw=study();
 raw.resultsSection.adverseEventsModule.seriousEvents[0].stats[0].numAffected=120;
 const out=parseRegistryBenefitResearch(raw,id,now);
 assert.equal(out.seriousAdverseEvents[0].groups.some(g=>g.affected>g.atRisk),false);
});
test("source endpoint protects sign-in, pinned IDs, strict origin and bounded response",()=>{
 const r=fs.readFileSync(path.join(__dirname,"../app/api/registry-benefit-research/route.ts"),"utf8");
 const ui=fs.readFileSync(path.join(__dirname,"../app/ToolsBenefitMatrix.tsx"),"utf8");
 const viewer=fs.readFileSync(path.join(__dirname,"../app/RegistryBenefitEvidence.tsx"),"utf8");
 assert.match(r,/hasSession/);
 assert.match(r,/parsePhase3CensusCsv/);
 assert.match(r,/pinned\.rows\.length!==741/);
 assert.match(r,/origin\+nct/);
 assert.match(r,/redirect:"error"/);
 assert.match(r,/body\.length>max/);
 assert.match(ui,/RegistryBenefitEvidence nctId=\{selected\.nctId\} assessment=\{active\}/);
 assert.match(viewer,/registry-benefit-research\?nct=/);
 assert.match(viewer,/controller\.abort\(\)/);
 assert.match(viewer,/benefitRank!==null/);
 assert.match(viewer,/No FDA decision/);
});

test("research refresh job covers exactly 375 historical completed NCTs and never changes evidence grades",()=>{
 const script=fs.readFileSync(path.join(__dirname,"../scripts/refresh-registry-benefit-research.cjs"),"utf8");
 const workflow=fs.readFileSync(path.join(__dirname,"../../../.github/workflows/nightly-registry-benefit-research.yml"),"utf8");
 const route=fs.readFileSync(path.join(__dirname,"../app/api/registry-benefit-research/route.ts"),"utf8");
 assert.match(script,/eligible\.length!==375/);
 assert.match(script,/parseRegistryBenefitResearch/);
 assert.match(script,/REGISTRY_REFRESH_NO_PRIMARY_SOURCE_SUCCESS/);
 assert.match(script,/MAX_KEEP_MS=72\*3600000/);
 assert.match(script,/length>8_000_000/);
 assert.match(workflow,/schedule:/);
 assert.match(workflow,/refresh-registry-benefit-research\.cjs/);
 assert.match(workflow,/contents: write/);
 assert.match(route,/archivedEvidence\(nct\)/);
 assert.match(route,/age<48\*3600000/);
 assert.match(route,/fromArchive/);
 assert.doesNotMatch(script,/benefitRank\s*=\s*\d|comparisonVerified\s*=\s*true|fdaDecisionVerified\s*=\s*true/);
});
test("large outcome source tables are bounded and marked incomplete, never misread as zero",()=>{
 const raw=study();
 raw.resultsSection.adverseEventsModule.seriousEvents=Array.from({length:95},(_,i)=>({
   term:"Event "+i,stats:[{groupId:"EG1",numAffected:0,numAtRisk:100}]
 }));
 const out=parseRegistryBenefitResearch(raw,id,now);
 assert.equal(out.truncatedEvidence.seriousEvents,true);
 assert.equal(out.seriousAdverseEvents.length,80);
 assert.equal(out.comparisonVerified,false);
});
