const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pacificTime,backupDecision}=require("../lib/nightly-backup.ts");
const RUN={
 id:123,event:"workflow_dispatch",head_branch:"main",
 path:".github/workflows/pdufa-overnight-sequential.yml",
 display_title:"ALL + GEM — PDUFA overnight",
 created_at:"2026-10-19T04:20:00Z",status:"in_progress",conclusion:null
};
const at=s=>new Date(s);
test("DST-safe local night and full Sunday versus weekday delta",()=>{
 assert.deepEqual(pacificTime(at("2026-10-19T05:40:00Z")),
   {night:"2026-10-18",hour:22,weekday:"Sun"});
 assert.deepEqual(pacificTime(at("2026-12-07T05:40:00Z")),
   {night:"2026-12-06",hour:21,weekday:"Sun"});
 const sunday=backupDecision([],at("2026-10-19T05:40:00Z"));
 assert.equal(sunday.action,"dispatch");
 assert.equal(sunday.scanMode,"FULL");
 assert.equal(sunday.gemAction,"RESCAN_ALL");
 const monday=backupDecision([],at("2026-10-20T05:40:00Z"));
 assert.equal(monday.scanMode,"DELTA");
 assert.equal(monday.gemAction,"REVERIFY_PARTIAL");
});
test("Any active or already dispatched scan prevents duplicate",()=>{
 const date=at("2026-10-19T05:40:00Z");
 for(const status of ["queued","in_progress","waiting","completed"]){
   const r=backupDecision([{...RUN,status}],date);
   assert.equal(r.action,"skip");
   assert.equal(r.runId,123);
 }
 const r=backupDecision([{...RUN,created_at:"2026-10-17T04:20:00Z"}],date);
 assert.equal(r.action,"skip","previous night's active scan must block overlap");
});
test("Failed current-night scan requires repair; never retrigger automatically",()=>{
 const r=backupDecision([{...RUN,status:"completed",conclusion:"failure"}],
   at("2026-10-19T05:40:00Z"));
 assert.equal(r.action,"skip");
 assert.match(r.reason,/no automatic duplicate/);
});
test("Old completed, push validation, and nonmatching refs do not block",()=>{
 const now=at("2026-10-19T05:40:00Z");
 assert.equal(backupDecision([{...RUN,status:"completed",conclusion:"success",
   created_at:"2026-10-18T04:20:00Z"}],now).action,"dispatch");
 assert.equal(backupDecision([{...RUN,event:"push"}],now).action,"dispatch");
 assert.equal(backupDecision([{...RUN,head_branch:"test"}],now).action,"dispatch");
});
test("Missing, truncated or invalid state fails closed; unsafe local time skips",()=>{
 const now=at("2026-10-19T05:40:00Z");
 assert.equal(backupDecision(null,now).action,"error");
 assert.equal(backupDecision(new Array(100).fill({event:"push"}),now).action,"error");
 assert.equal(backupDecision([{...RUN,id:"not-number"}],now).action,"error");
 assert.equal(backupDecision([{...RUN,created_at:"bad"}],now).action,"error");
 assert.equal(backupDecision([],at("2026-10-18T20:00:00Z")).action,"skip");
});
test("Vercel schedule remains daily, authenticated and direct GitHub dispatch",()=>{
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,"../vercel.json"),"utf8"));
 assert.deepEqual(data.crons,[{path:"/api/cron/pdufa-nightly-backup",schedule:"40 5 * * *"}]);
 const source=fs.readFileSync(path.join(__dirname,"../app/api/cron/pdufa-nightly-backup/route.ts"),"utf8");
 assert.match(source,/process.env.CRON_SECRET/);
 assert.match(source,/request.headers.get\("authorization"\)/);
 assert.match(source,/process.env.PDUFA_GITHUB_TOKEN/);
 assert.match(source,/backupDecision\(history,new Date\(\)\)/);
 assert.match(source,/scan_mode:decision.scanMode/);
 assert.match(source,/dispatched.status!==204/);
});
