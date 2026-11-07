"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(module,filename)=>module._compile(
 ts.transpileModule(fs.readFileSync(filename,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
 }).outputText,filename);
const {POOL_DETAIL_FIELDS,normalizePoolRegistryDetail}=require("../lib/pool-registry-details.ts");
const root=path.join(__dirname,"..");
const component=fs.readFileSync(path.join(root,"app/PoolMasterSpreadsheet.tsx"),"utf8");
const api=fs.readFileSync(path.join(root,"app/api/pool-registry-details/route.ts"),"utf8");
const fake={
 protocolSection:{
  identificationModule:{nctId:"NCT12345678",officialTitle:"Official Phase 2 source trial"},
  statusModule:{overallStatus:"TERMINATED",whyStopped:"Enrollment could not be completed",
   primaryCompletionDateStruct:{date:"2026-01-01",type:"ACTUAL"},
   completionDateStruct:{date:"2026-03-01",type:"ESTIMATED"}},
  sponsorCollaboratorsModule:{leadSponsor:{name:"Example Sponsor"}},
  designModule:{studyType:"INTERVENTIONAL",enrollmentInfo:{count:150,type:"ACTUAL"},
   designInfo:{allocation:"RANDOMIZED",maskingInfo:{masking:"DOUBLE"}}},
  armsInterventionsModule:{armGroups:[{label:"Active",type:"EXPERIMENTAL",interventionNames:["Drug X"]},
   {label:"Placebo",type:"PLACEBO_COMPARATOR",interventionNames:["Placebo"]}]},
  eligibilityModule:{eligibilityCriteria:"Inclusion: adults. Exclusion: prior therapy."},
  outcomesModule:{primaryOutcomes:[{measure:"Responder rate",timeFrame:"12 weeks"}],
   secondaryOutcomes:[{measure:"Quality of life",timeFrame:"24 weeks"}]},
  contactsLocationsModule:{locations:[{city:"Boston",country:"United States"}]},
  referencesModule:{references:[{citation:"Example, 2026"}]}
 },
 resultsSection:{
  outcomeMeasuresModule:{outcomeMeasures:[{title:"Responder rate",unitOfMeasure:"Percent",
   groups:[{id:"G1",title:"Active"}],
   classes:[{categories:[{measurements:[{groupId:"G1",value:"62"}]}]}]}]},
  adverseEventsModule:{eventGroups:[{title:"Active",seriousNumAffected:2,
    seriousNumAtRisk:100,otherNumAffected:20,otherNumAtRisk:100}]}
 }
};
test("POOL extends only four existing segments, with 14 source fields",()=>{
 const matches=[...component.matchAll(/key:"(clinical|dates|qualifiers|focus)",label/g)].map(x=>x[1]);
 assert.deepEqual(matches,["clinical","dates","qualifiers","focus"]);
 assert.equal(POOL_DETAIL_FIELDS.length,14);
 assert.equal(new Set(POOL_DETAIL_FIELDS).size,14);
 for(const key of POOL_DETAIL_FIELDS)assert.ok(component.includes('key:"'+key+'"'),key);
 assert.match(component,/POOL Master · \{3\+ALL_KEYS.length\} columns/);
 assert.match(component,/Showing 3 identity columns/);
 assert.match(component,/pdufa:pool-column-layout:v1/);
});
test("official registry detail preserves facts and exact group denominators",()=>{
 const record=normalizePoolRegistryDetail(fake,"NCT12345678","2026-11-07T20:00:00Z");
 assert.equal(record.total,14);
 assert.equal(record.available,14);
 assert.equal(record.fields.studyTitle,"Official Phase 2 source trial");
 assert.equal(record.fields.leadSponsor,"Example Sponsor");
 assert.match(record.fields.treatmentArms,/PLACEBO_COMPARATOR/);
 assert.match(record.fields.reportedResults,/Active: 62 Percent/);
 assert.match(record.fields.safetyResults,/serious 2\/100/);
 assert.match(record.fields.milestoneDateTypes,/ESTIMATED/);
 assert.equal(record.fields.terminationReason,"Enrollment could not be completed");
 assert.equal(record.sourceUrl,"https://clinicaltrials.gov/study/NCT12345678");
});
test("missing evidence remains null, never zero or assumed passed",()=>{
 const blank={protocolSection:{identificationModule:{nctId:"NCT12345678"}}};
 const audit=normalizePoolRegistryDetail(blank,"NCT12345678","2026-11-07T20:00:00Z");
 assert.equal(audit.available,0);
 assert.deepEqual(Object.values(audit.fields),Array(14).fill(null));
 assert.throws(()=>normalizePoolRegistryDetail(blank,"NCT99999999","2026-11-07T20:00:00Z"),/ID_MISMATCH/);
 assert.throws(()=>normalizePoolRegistryDetail(blank,"INVALID","2026-11-07T20:00:00Z"),/ID_INVALID/);
});
test("lookup only on explicit NCT button click, authenticated and tied to official host",()=>{
 assert.match(component,/onClick=\{\(\)=>void loadRegistry\(nct\)\}/);
 assert.match(component,/registryByNct\[nct\]/);
 assert.match(component,/Not reported in this registry record/);
 assert.match(component,/not yet stored in the 16-column Google Sheet/);
 assert.match(api,/hasSession\(req.cookies.get\(COOKIE_NAME\)\?\.value\)/);
 assert.match(api,/https:\/\/clinicaltrials\.gov\/api\/v2\/studies\//);
 assert.match(api,/AbortSignal.timeout\(14000\)/);
 assert.match(api,/normalizePoolRegistryDetail\(raw,nct,/);
 assert.doesNotMatch(component,/useEffect\(\(\)=>\{[^}]*loadRegistry/);
 const src=ts.createSourceFile("PoolMasterSpreadsheet.tsx",component,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 assert.deepEqual(src.parseDiagnostics.map(x=>ts.flattenDiagnosticMessageText(x.messageText,"; ")),[]);
});
