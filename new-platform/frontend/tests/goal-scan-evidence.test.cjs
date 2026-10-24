const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText,file);
const {goalScanView,pacificGoalDay}=require("../lib/goal-scan-evidence.ts");
const NOW=new Date("2026-10-24T04:20:00Z");
const URL="https://github.com/pdufa/pdufa-command-center/actions/runs/40057578041";
const full=()=>{
  return {
    daily:{schema_version:1,days:[{
      date_pacific:"2026-10-23",status:"PARTIAL",run_id:40057578041,run_url:URL,
      sections:{
        master:{new:null,updated:68,total:11598},
        pipeline:{new:null,updated:null,total:null},
        designations:{new:null,updated:null,total:null},
        gem_jr:{new:0,updated:null,total:11},
        gem:{new:0,updated:null,total:6},
      }
    }]},
    newFromScan:{
      runId:40057578041,scanPacificDate:"2026-10-23",
      pipelineNewPrograms:null,pipelineChangedTrials:68,
      rows:[{stage:"GEM JR",kind:"NEW_PHASE3_RESULT",ticker:"EXBT",
        drug:"Example drug",trialId:"NCT01234567",label:"New Phase 3 result",
        exactRun:true,sourceUrl:"https://clinicaltrials.gov/study/NCT01234567"}]
    }
  };
};

test("GOAL reconciles Oct 23 partial daily report without inventing new trials or FDA designations",()=>{
  assert.equal(pacificGoalDay(NOW),"2026-10-23");
  const result=goalScanView(full(),NOW);
  assert.equal(result.today,true);
  assert.equal(result.status,"PARTIAL");
  assert.equal(result.masterNew,null);
  assert.equal(result.masterUpdated,68);
  assert.equal(result.newPrograms,null);
  assert.equal(result.changedPrograms,68);
  assert.equal(result.designationTotal,null);
  assert.equal(result.runUrl,URL);
  assert.match(result.note,/Partial published evidence/);
  assert.equal(result.rows.length,1);
  assert.equal(result.rows[0].link,"https://clinicaltrials.gov/study/NCT01234567");
});

test("GOAL daily report never transfers yesterday's counts into today's summary",()=>{
  const later=goalScanView(full(),new Date("2026-10-25T04:20:00Z"));
  assert.equal(later.today,false);
  assert.equal(later.date,"2026-10-23");
  assert.equal(later.masterUpdated,68);
  assert.equal(goalScanView(full(),new Date("2026-10-22T04:20:00Z")),null);
});

test("mismatched source run, date or updated count hides exact scan details",()=>{
  const wrongRun=full();
  wrongRun.newFromScan.runId=40057578040;
  let view=goalScanView(wrongRun,NOW);
  assert.equal(view.masterUpdated,68);
  assert.equal(view.newPrograms,null);
  assert.equal(view.changedPrograms,null);
  assert.equal(view.rows.length,0);
  const wrongDate=full();
  wrongDate.newFromScan.scanPacificDate="2026-10-22";
  view=goalScanView(wrongDate,NOW);
  assert.equal(view.rows.length,0);
  const wrongCount=full();
  wrongCount.newFromScan.pipelineChangedTrials=67;
  view=goalScanView(wrongCount,NOW);
  assert.equal(view.changedPrograms,null);
  assert.equal(view.rows.length,0);
  assert.match(view.note,/disagree/);
});

test("failed, unauthenticated and malformed daily publications fail closed",()=>{
  const errors=[
    null,{}, {daily:{schema_version:1,days:[]}},
    {daily:{schema_version:2,days:[]}},
  ];
  for(const item of errors)assert.equal(goalScanView(item,NOW),null);
  const bad=full(); bad.daily.days[0].run_url="https://host.example/actions/runs/40057578041";
  assert.equal(goalScanView(bad,NOW),null);
  const badId=full();badId.daily.days[0].run_id=0;
  assert.equal(goalScanView(badId,NOW),null);
  const badStatus=full();badStatus.daily.days[0].status="RUNNING";
  assert.equal(goalScanView(badStatus,NOW),null);
  const failed=full(); failed.daily.days[0].status="RUN_FAILED";
  const result=goalScanView(failed,NOW);
  assert.equal(result.masterUpdated,null);
  assert.equal(result.newPrograms,null);
  assert.deepEqual(result.rows,[]);
});

test("only validated ClinicalTrials.gov links and well-formed scan rows can appear",()=>{
  const payload=full();
  payload.newFromScan.rows.push(
    {...payload.newFromScan.rows[0],ticker:"EXBT",trialId:"NCT00000000",
      sourceUrl:"https://evil.example/study/NCT00000000"},
    {...payload.newFromScan.rows[0],ticker:"TWO",trialId:"NCT00000001",
      sourceUrl:"https://clinicaltrials.gov/study/NCT00000001?token=secret"},
    {...payload.newFromScan.rows[0],ticker:"bad*ticker",trialId:"NCT00000002"},
    {...payload.newFromScan.rows[0],ticker:"EVIL",exactRun:"yes"},
  );
  const view=goalScanView(payload,NOW);
  assert.equal(view.rows.length,3);
  assert.equal(view.rows.filter(row=>row.link===null).length,2);
  assert.equal(view.rows.filter(row=>row.link!==null).length,1);
});
