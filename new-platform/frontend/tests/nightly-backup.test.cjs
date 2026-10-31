const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pacificTime,backupDecision}=require("../lib/nightly-backup.ts");
const RUN={
 id:123,event:"workflow_dispatch",head_branch:"main",
 path:".github/workflows/pdufa-overnight-sequential.yml",
 display_title:"POOL + PIPELINE — PDUFA overnight",
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
 assert.equal("gemAction" in sunday,false);
 const monday=backupDecision([],at("2026-10-20T05:40:00Z"));
 assert.equal(monday.scanMode,"DELTA");
 assert.equal("gemAction" in monday,false);
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
test("Vercel backup clocks are daily, authenticated and dispatch through guarded GitHub scheduler",()=>{
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,"../vercel.json"),"utf8"));
 assert.deepEqual(data.crons,[
   {path:"/api/cron/pdufa-nightly-backup-pdt",schedule:"15 3 * * *"},
   {path:"/api/cron/pdufa-nightly-backup-pst",schedule:"15 4 * * *"}
 ]);
 const base=path.join(__dirname,"../app/api/cron");
 const source=fs.readFileSync(path.join(base,"pdufa-nightly-backup/route.ts"),"utf8");
 assert.match(source,/process.env.CRON_SECRET/);
 assert.match(source,/request.headers.get\("authorization"\)/);
 assert.match(source,/process.env.PDUFA_GITHUB_TOKEN/);
 assert.match(source,/backupDecision\(history,new Date\(\)\)/);
 assert.match(source,/pdufa-nightly-pacific-start.yml/);
 assert.match(source,/dispatched.status!==204/);
 assert.ok(!source.includes('SCAN_WORKFLOW+"/dispatches"'),
   "Backup must not directly dispatch the full scan");
 for(const slot of ["pdt","pst"]){
   const alias=fs.readFileSync(path.join(base,"pdufa-nightly-backup-"+slot+"/route.ts"),"utf8");
   assert.ok(alias.includes('export { GET } from "../pdufa-nightly-backup/route"'));
 }
});
test("Backup only admits 8 PM-or-later Pacific; any 8 PM scan blocks duplicates",()=>{
 const summer=at("2026-10-23T03:15:00Z"); // 8:15 PM PDT October 22
 const winter=at("2026-12-23T04:15:00Z"); // 8:15 PM PST December 22
 assert.deepEqual(pacificTime(summer),{night:"2026-10-22",hour:20,weekday:"Thu"});
 assert.deepEqual(pacificTime(winter),{night:"2026-12-22",hour:20,weekday:"Tue"});
 assert.equal(backupDecision([],summer).action,"dispatch");
 assert.equal(backupDecision([],winter).action,"dispatch");
 assert.equal(backupDecision([],at("2026-12-23T03:15:00Z")).action,"skip",
   "DST backup must not start prior to 8 PM standard time");
 const existing={...RUN,created_at:"2026-10-23T03:01:00Z",status:"completed",conclusion:"success"};
 const decision=backupDecision([existing],summer);
 assert.equal(decision.action,"skip");
 assert.equal(decision.runId,123);
});

test("Current and historical full-chain titles both prevent duplicate collection",()=>{
 const now=at("2026-10-19T05:40:00Z");
 for(const display_title of ["POOL + PIPELINE — PDUFA overnight","ALL + GEM — PDUFA overnight"]){
  for(const status of ["in_progress","completed"]){
   assert.equal(backupDecision([{...RUN,display_title,status,conclusion:"success"}],now).action,"skip");
  }
 }
});
