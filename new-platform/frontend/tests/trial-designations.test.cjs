const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(m,file)=>m._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
}).outputText,file);
const lib=require("../lib/trial-designations.ts");
const keys=lib.DESIGNATION_COLUMNS.map(x=>x.key);
const header=["event_key","ticker",...keys,"designation_audit_status","designation_source_url","designation_evidence_note","nct_id","fast_track_designation_date","designation_verified_at","pdufa_date"];
const csv=rows=>[header,...rows.map(row=>header.map(key=>row[key]||""))].map(row=>row.map(value=>'"'+String(value).replaceAll('"','""')+'"').join(",")).join("\n");
const event="TEST|2027-01-02|drug-a";
const source={event_key:event,ticker:"TEST",...Object.fromEntries(keys.map(k=>[k,"YES"])),
  designation_audit_status:"VERIFIED_POSITIVE",designation_source_url:"https://www.fda.gov/drugs/example-drug-a",
  designation_evidence_note:"Exact application evidence",pdufa_date:"2027-01-02"};
const candidate={id:"APPLICATION|"+event,eventKey:event,ticker:"TEST",drug:"Drug A",pdufaDate:"2027-01-02"};
const build=(rows=[source],links=null)=>lib.buildDesignationIndex(csv(rows),links,"2026-10-21T20:00:00Z");

test("all six statuses use the exact application while same-company programs retain unknown evidence",()=>{
  const index=build();
  const values=lib.resolveTrialDesignations(candidate,index);
  assert.ok(keys.every(key=>values[key].status==="GRANTED"));
  assert.equal(values.fast_track.verification,"SOURCE_RECORDED");
  assert.equal(lib.designationLabel(values.fast_track,"fast_track"),"Grant reported");
  for(const wrong of [
    {...candidate,id:"APPLICATION|TEST|2027-01-02|drug-b",eventKey:"TEST|2027-01-02|drug-b"},
    {...candidate,ticker:"OTHER"},
    {...candidate,id:"TRIAL|NCT00000001",nctId:"NCT00000001"},
  ])assert.ok(keys.every(key=>lib.resolveTrialDesignations(wrong,index)[key].status==="UNKNOWN"));
});

test("an incidental trial event key does not substitute for an explicit NCT-to-application link",()=>{
  const row={id:"TRIAL|NCT00000001",nctId:"NCT00000001",ticker:"TEST",eventKey:event};
  assert.equal(lib.resolveTrialDesignations(row,build()).fast_track.status,"UNKNOWN");
  const links="event_key,ticker,nct_id,drug,indication\n"+event+",TEST,NCT00000001,Drug A,Disease A\n";
  assert.equal(lib.resolveTrialDesignations(row,build([source],links)).fast_track.status,"GRANTED");
  assert.equal(lib.resolveTrialDesignations({...row,ticker:"OTHER"},build([source],links)).fast_track.status,"UNKNOWN");
  const mismatch={...candidate,eventKey:"TEST|different",nctId:"NCT00000001"};
  assert.equal(lib.resolveTrialDesignations(mismatch,build([source],links)).fast_track.status,"UNKNOWN");
});

test("multiple application links and duplicate evidence never select an arbitrary program",()=>{
  const other={...source,event_key:"TEST|2027-03-04|drug-b",nct_id:"NCT00000001"};
  const index=build([{...source,nct_id:"NCT00000001"},other]);
  const values=lib.resolveTrialDesignations({id:"TRIAL|NCT00000001",ticker:"TEST"},index);
  assert.ok(keys.every(key=>values[key].status==="UNKNOWN"));
  assert.match(values.fast_track.note,/Multiple applications/);
  assert.equal(lib.resolveTrialDesignations(candidate,build([source,{...source,fast_track:"NO"}])).fast_track.status,"UNKNOWN");
});

test("blank flags, missing sources and no-positive scan results are not negative designations",()=>{
  const blank={event_key:event,ticker:"TEST",designation_audit_status:"SCANNED_NO_POSITIVE_VERIFIED"};
  assert.ok(keys.every(key=>lib.resolveTrialDesignations(candidate,build([blank]))[key].status==="UNKNOWN"));
  assert.equal(lib.resolveTrialDesignations(candidate,build([{...source,designation_source_url:""}])).fast_track.status,"UNKNOWN");
  assert.equal(lib.resolveTrialDesignations(candidate,build([{...source,fast_track:"NO"}])).fast_track.status,"NOT_GRANTED");
});

test("a review deadline and source retrieval timestamp never become a designation or verification date",()=>{
  let values=lib.resolveTrialDesignations(candidate,build());
  assert.equal(values.fast_track.designationDate,"");assert.equal(values.fast_track.checkedAt,"");
  values=lib.resolveTrialDesignations(candidate,build([{...source,fast_track_designation_date:"2026-02-31",designation_verified_at:"invalid"}]));
  assert.equal(values.fast_track.designationDate,"");assert.equal(values.fast_track.checkedAt,"");
  values=lib.resolveTrialDesignations(candidate,build([{...source,fast_track_designation_date:"2026-02-03",designation_verified_at:"2026-10-20T12:00:00Z"}]));
  assert.equal(values.fast_track.designationDate,"2026-02-03");assert.equal(values.fast_track.checkedAt,"2026-10-20");
});

test("requested accelerated approval stays requested and does not imply another designation",()=>{
  const index=build([{event_key:event,ticker:"TEST",accelerated_approval:"REQUESTED",designation_source_url:source.designation_source_url}]);
  const values=lib.resolveTrialDesignations(candidate,index);
  assert.equal(values.accelerated_approval.status,"REQUESTED");
  assert.equal(values.fast_track.status,"UNKNOWN");assert.equal(values.priority_review.status,"UNKNOWN");
});

test("FDA-verified Priority Review alert is preserved and unsafe or lookalike source URLs are rejected",()=>{
  const priority={...candidate,priorityReview:{status:"FDA_VERIFIED",source:source.designation_source_url,designationDate:"2026-09-05"}};
  const values=lib.resolveTrialDesignations(priority);
  assert.equal(values.priority_review.verification,"FDA_VERIFIED");
  assert.equal(lib.designationLabel(values.priority_review,"priority_review"),"IMP: Priority Review");
  for(const url of ["javascript:alert(1)","http://www.fda.gov/drugs/a","https://fda.gov.evil.example/a","https://www.fda.gov/"]){
    assert.equal(lib.resolveTrialDesignations({...priority,priorityReview:{status:"FDA_VERIFIED",source:url}}).priority_review.status,"UNKNOWN");
  }
  assert.equal(lib.designationSource("https://user:password@example.org/source"),"");
  const conflict=lib.resolveTrialDesignations(priority,build([{...source,priority_review:"WITHDRAWN"}]));
  assert.equal(conflict.priority_review.status,"CONFLICT");
});

test("Pipeline renders 34 columns including Details, with each designation once and one cell per header",()=>{
  const React=require("react"),{renderToStaticMarkup}=require("react-dom/server");
  const Component=require("../app/PipelineData.tsx").default;
  const html=renderToStaticMarkup(React.createElement(Component,{rows:[candidate]}));
  const head=html.match(/<thead>([\s\S]*?)<\/thead>/)[1];
  const body=html.match(/<tbody>([\s\S]*?)<\/tbody>/)[1];
  assert.equal((head.match(/<th(?:\s[^>]*)?>/g)||[]).length,34);
  assert.equal((body.match(/<td(?:\s[^>]*)?>/g)||[]).length,34);
  assert.equal(head.split('>Details<').length-1,1);
  for(const {label}of lib.DESIGNATION_COLUMNS)assert.equal(head.split('>'+label+'<').length-1,1);
});

test("designation details expose dates and source links while an unknown never renders a false NO",()=>{
  const React=require("react"),{renderToStaticMarkup}=require("react-dom/server");
  const {TrialDesignationCells}=require("../app/TrialDesignations.tsx");
  const html=renderToStaticMarkup(React.createElement(TrialDesignationCells,{row:candidate,index:build(),loading:false,error:""}));
  assert.match(html,/Grant reported/);assert.match(html,/Not recorded/);assert.match(html,/Open supporting source/);
  assert.equal((html.match(/<details /g)||[]).length,6);
  const unknown=renderToStaticMarkup(React.createElement(TrialDesignationCells,{row:{id:"TRIAL|NCT00000001",ticker:"TEST"},index:build(),loading:false,error:""}));
  assert.equal((unknown.match(/Not verified/g)||[]).length,6);assert.doesNotMatch(unknown,/Not granted|Grant reported/);
});

test("individual trial download retains every registry section and adds all thirteen supplemental statuses",()=>{
  const study={protocolSection:{identificationModule:{nctId:"NCT00000001"}},resultsSection:{example:[1,2]},futureSection:{keep:true}};
  const before=JSON.stringify(study),output=lib.trialDesignationDownload(study,candidate,build());
  assert.equal(JSON.stringify(study),before);assert.equal(output.protocolSection,study.protocolSection);
  assert.equal(output.resultsSection,study.resultsSection);assert.equal(output.futureSection,study.futureSection);
  assert.deepEqual(Object.keys(output.pdufaRegulatoryDetails.designations),["fast_track","breakthrough_therapy","priority_review","accelerated_approval","orphan_drug","rmat","qidp","rare_pediatric_disease","tropical_disease_prv","rare_pediatric_disease_prv","material_threat_mcm_prv","lpad","animal_rule"]);
  assert.equal(output.pdufaRegulatoryDetails.designations.fast_track.designationDate,"");
});

test("authenticated designation endpoint reads saved evidence and discloses a source outage",async()=>{
  const {NextRequest}=require("next/server"),auth=require("../lib/auth.ts");
  const {GET}=require("../app/api/trial-designations/route.ts");
  const old={fetch:global.fetch,password:process.env.DASHBOARD_PASSWORD,key:process.env.SESSION_SIGNING_KEY};
  process.env.DASHBOARD_PASSWORD="designation-test-password";process.env.SESSION_SIGNING_KEY="designation-test-signing-key-for-unit-tests-only";
  let reads=0;
  global.fetch=async url=>{reads++;return new Response(String(url).endsWith("prediction_engine_designations.csv")?csv([source]):"event_key,ticker,nct_id\n",{status:200});};
  const req=()=>new NextRequest("https://local.test/api/trial-designations",{headers:{cookie:auth.COOKIE_NAME+"="+auth.makeSession()}});
  try{
    assert.equal((await GET(new NextRequest("https://local.test/api/trial-designations"))).status,401);assert.equal(reads,0);
    const result=await GET(req());assert.equal(result.status,200);assert.equal(result.headers.get("Cache-Control"),"private, no-store");
    const index=await result.json();assert.equal(lib.resolveTrialDesignations(candidate,index).fast_track.status,"GRANTED");
    global.fetch=async()=>new Response("unavailable",{status:503});
    const failed=await GET(req());assert.equal(failed.status,503);assert.match((await failed.json()).error,/unavailable/);
  }finally{
    global.fetch=old.fetch;
    if(old.password===undefined)delete process.env.DASHBOARD_PASSWORD;else process.env.DASHBOARD_PASSWORD=old.password;
    if(old.key===undefined)delete process.env.SESSION_SIGNING_KEY;else process.env.SESSION_SIGNING_KEY=old.key;
  }
});

test("the checked-in designation source parses without assigning historical issuer evidence to unlinked trials",()=>{
  const root=path.resolve(__dirname,"../../../data");
  const index=lib.buildDesignationIndex(fs.readFileSync(path.join(root,"prediction_engine_designations.csv"),"utf8"),fs.readFileSync(path.join(root,"pdufa_candidates.csv"),"utf8"),"2026-10-21T20:00:00Z");
  assert.ok(Object.keys(index.programs).length>100);
  assert.ok(Object.values(index.programs).some(p=>keys.some(key=>p.designations[key].status==="GRANTED")));
  for(const nct of ["NCT05156320","NCT00000001"]){
    const values=lib.resolveTrialDesignations({id:"TRIAL|"+nct,ticker:"TEST"},index);
    assert.ok(keys.every(key=>values[key].status==="UNKNOWN"));
  }
});


test("reviewed 2026 crosswalk links drug- and indication-specific FDA programs to exact NCT trials",()=>{
  const designationCsv=fs.readFileSync(path.join(__dirname,"../../../data/prediction_engine_designations.csv"),"utf8");
  const candidateCsv=fs.readFileSync(path.join(__dirname,"../../../data/pdufa_candidates.csv"),"utf8");
  const crosswalkCsv=fs.readFileSync(path.join(__dirname,"../../../data/fda_designation_nct_evidence.csv"),"utf8");
  const i=lib.applyReviewedDesignationLinks(lib.buildDesignationIndex(designationCsv,candidateCsv,"2026-10-31T19:00:00Z"),crosswalkCsv);
  assert.equal(i.linkageCoverage.verifiedNctCount,4);
  assert.equal(i.linkageCoverage.verifiedClaimCount,14);
  assert.ok(i.linkageAvailable);
  assert.equal(i.availableKeys.rare_pediatric_disease,true);
  const capr={id:"TRIAL|NCT03406780",nctId:"NCT03406780",ticker:"CAPR"};
  const cort={id:"TRIAL|NCT04308590",nctId:"NCT04308590",ticker:"CORT"};
  const srrk={id:"TRIAL|NCT05156320",nctId:"NCT05156320",ticker:"SRRK"};
  const dyn={id:"TRIAL|NCT07608432",nctId:"NCT07608432",ticker:"DYN"};
  for(const k of ["orphan_drug","priority_review","rmat","rare_pediatric_disease"])
    assert.equal(lib.resolveTrialDesignations(capr,i)[k].status,"GRANTED",k);
  assert.equal(lib.resolveTrialDesignations(cort,i).orphan_drug.verification,"FDA_VERIFIED");
  for(const k of ["fast_track","orphan_drug","priority_review","rare_pediatric_disease"])
    assert.equal(lib.resolveTrialDesignations(srrk,i)[k].status,"GRANTED",k);
  for(const k of ["fast_track","breakthrough_therapy","orphan_drug","priority_review","rare_pediatric_disease"])
    assert.equal(lib.resolveTrialDesignations(dyn,i)[k].status,"GRANTED",k);
  assert.equal(lib.resolveTrialDesignations(dyn,i).accelerated_approval.status,"UNKNOWN",
    "A requested accelerated approval pathway must not become granted approval");
  assert.equal(lib.resolveTrialDesignations({...dyn,ticker:"WRONG"},i).priority_review.status,"UNKNOWN");
  assert.equal(lib.resolveTrialDesignations({id:"TRIAL|NCT04610866",ticker:"AGIO"},i).orphan_drug.status,"UNKNOWN",
    "Earlier same-company orphan designation for another indication must not propagate to sickle cell");
});
test("the reviewed crosswalk is fail-closed for missing files, fabricated trials and duplicate claims",()=>{
  const designationCsv=fs.readFileSync(path.join(__dirname,"../../../data/prediction_engine_designations.csv"),"utf8");
  const crosswalkCsv=fs.readFileSync(path.join(__dirname,"../../../data/fda_designation_nct_evidence.csv"),"utf8");
  const make=()=>lib.buildDesignationIndex(designationCsv,null,"2026-10-31T19:00:00Z");
  assert.throws(()=>lib.applyReviewedDesignationLinks(make(),""),/Invalid trial/);
  assert.throws(()=>lib.applyReviewedDesignationLinks(make(),crosswalkCsv+"\n"+crosswalkCsv.split("\n")[1]),
    /Duplicate reviewed designation claim/);
  assert.throws(()=>lib.applyReviewedDesignationLinks(make(),crosswalkCsv.replace("https://clinicaltrials.gov/study/NCT03406780","https://clinicaltrials.gov/study/NCT99999999")),
    /Unverifiable trial-to-designation row/);
});
