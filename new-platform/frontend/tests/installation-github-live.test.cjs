const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
require.extensions[".ts"]=(mod,path)=>mod._compile(ts.transpileModule(fs.readFileSync(path,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}
}).outputText,path);
const {fetchLiveGithubActions,readWorkflowRows,readJobStep,verifyInstallationStep}=require("../lib/installation-live-github.ts");
const now="2026-11-08T22:20:00Z";
function run(id,status,conclusion=null){
 return {id,status,conclusion,name:"Actual CI run",head_branch:"main",
  html_url:"https://github.com/pdufa/pdufa-command-center/actions/runs/"+id,
  created_at:now,updated_at:now,run_started_at:now,
  path:".github/workflows/pdufa-installation-smoke.yml",event:"push"};
}
function fakeFetch(pathToResponse){
 const calls=[];
 const fn=async(url,opts)=>{
  calls.push({url,opts});
  const key=String(url).split("/actions/")[1];
  const reply=pathToResponse[key];
  if(!reply)return new Response("missing",{status:404});
  if(reply.statusCode)return new Response("inaccessible",{status:reply.statusCode});
  return Response.json(reply);
 };
 return {fn,calls};
}
test("no credential yields unavailable and never guesses stopped",async()=>{
 const state=await fetchLiveGithubActions(undefined,now,()=>{throw Error("unexpected network");});
 assert.equal(state.state,"UNAVAILABLE");
 assert.equal(state.running.length,0);
 assert.match(state.note,/cannot be verified/i);
});
test("authenticated direct GitHub run and currently running job step",async()=>{
 const api=fakeFetch({
  "runs?status=in_progress&per_page=50":{workflow_runs:[run(123,"in_progress")]},
  "runs?status=queued&per_page=50":{workflow_runs:[run(124,"queued")]},
  "runs?per_page=20":{workflow_runs:[run(125,"completed","success")]},
  "workflows/pdufa-installation-smoke.yml/runs?status=completed&per_page=3":{workflow_runs:[]},
  "runs/123/jobs?per_page=100":{jobs:[{name:"frontend",status:"in_progress",
    steps:[{name:"Checkout",status:"completed"},{name:"Run Next.js build",status:"in_progress"}]}]}
 });
 const result=await fetchLiveGithubActions("test-read-token",now,api.fn);
 assert.equal(result.state,"VERIFIED");
 assert.equal(result.running.length,1);
 assert.equal(result.running[0].id,123);
 assert.equal(result.running[0].job,"frontend");
 assert.equal(result.running[0].step,"Run Next.js build");
 assert.equal(result.queued[0].status,"queued");
 assert.equal(result.recent[0].conclusion,"success");
 assert.equal(result.running[0].stepCoverage,"OBSERVED");
 assert.equal(api.calls.length,5);
 assert.ok(api.calls.every(c=>c.opts.headers.Authorization==="Bearer test-read-token"));
 assert.ok(!JSON.stringify(result).includes("test-read-token"));
});
test("no running GitHub Actions is a verified observation only when source API succeeds",async()=>{
 const api=fakeFetch({
  "runs?status=in_progress&per_page=50":{workflow_runs:[]},
  "runs?status=queued&per_page=50":{workflow_runs:[]},
  "runs?per_page=20":{workflow_runs:[]},
  "workflows/pdufa-installation-smoke.yml/runs?status=completed&per_page=3":{workflow_runs:[]}
 });
 const result=await fetchLiveGithubActions("token",now,api.fn);
 assert.equal(result.state,"VERIFIED");
 assert.deepEqual(result.running,[]);
 assert.match(result.scope,/No Codex heartbeat/);
});
test("API auth failure cannot be mistaken for no activity",async()=>{
 const api=fakeFetch({
  "runs?status=in_progress&per_page=50":{statusCode:401},
  "runs?status=queued&per_page=50":{workflow_runs:[]},
  "runs?per_page=20":{workflow_runs:[]},
  "workflows/pdufa-installation-smoke.yml/runs?status=completed&per_page=3":{workflow_runs:[]}
 });
 const state=await fetchLiveGithubActions("bad",now,api.fn);
 assert.equal(state.state,"UNAVAILABLE");
 assert.deepEqual(state.running,[]);
});
test("partial GitHub coverage remains explicit",async()=>{
 const api=fakeFetch({
  "runs?status=in_progress&per_page=50":{workflow_runs:[run(333,"in_progress")]},
  "runs?status=queued&per_page=50":{statusCode:403},
  "runs?per_page=20":{workflow_runs:[]},
  "workflows/pdufa-installation-smoke.yml/runs?status=completed&per_page=3":{workflow_runs:[]},
  "runs/333/jobs?per_page=100":{statusCode:403}
 });
 const state=await fetchLiveGithubActions("token",now,api.fn);
 assert.equal(state.state,"PARTIAL");
 assert.equal(state.running[0].stepCoverage,"UNAVAILABLE");
});
test("rejects fake run ids, URLs, unsupported step shape",()=>{
 assert.equal(readWorkflowRows({workflow_runs:[{...run(1,"in_progress"),html_url:"https://evil.example/"}]},"in_progress").length,0);
 assert.throws(()=>readWorkflowRows({}, "in_progress"));
 assert.throws(()=>readJobStep({jobs:"not jobs"}));
});

test("exact running installation-smoke step produces verified task ID without acceptance",async()=>{
 const api=fakeFetch({
  "runs?status=in_progress&per_page=50":{workflow_runs:[run(701,"in_progress")]},
  "runs?status=queued&per_page=50":{workflow_runs:[]},
  "runs?per_page=20":{workflow_runs:[]},
  "runs/701/jobs?per_page=100":{jobs:[{name:"production-smoke",status:"in_progress",steps:[
    {name:"Check production deployment and installation API",status:"completed",conclusion:"success",started_at:now},
    {name:"Verify Render backend and PostgreSQL storage readiness",status:"in_progress",started_at:now}
  ]}]},
  "workflows/pdufa-installation-smoke.yml/runs?status=completed&per_page=3":{workflow_runs:[run(700,"completed","success")]},
  "runs/700/jobs?per_page=100":{jobs:[{name:"production-smoke",status:"completed",steps:[
    {name:"Verify Render backend and PostgreSQL storage readiness",status:"completed",conclusion:"success",started_at:now,completed_at:now},
    {name:"Verify signed-in POOL Pipeline reconciliation",status:"completed",conclusion:"success",started_at:now,completed_at:now}
  ]}]}
 });
 const result=await fetchLiveGithubActions("token",now,api.fn);
 assert.equal(result.state,"VERIFIED");
 assert.equal(result.taskExecution.taskId,"01-004");
 assert.equal(result.taskExecution.state,"RUNNING");
 assert.equal(result.taskExecution.step,"Verify Render backend and PostgreSQL storage readiness");
 assert.equal(result.taskExecution.acceptanceGranted,false);
 assert.match(result.taskExecution.runUrl,/actions\/runs\/701$/);
 assert.equal(result.lastTaskExecution.taskId,"01-015");
 assert.equal(result.lastTaskExecution.state,"SUCCEEDED");
 assert.equal(result.lastTaskExecution.acceptanceGranted,false);
 assert.equal(api.calls.length,6);
});
test("matching step text without exact workflow/branch/job/in-progress status never supplies active cursor",()=>{
 const trusted={id:42,name:"smoke",branch:"main",status:"in_progress",conclusion:null,
  startedAt:now,updatedAt:now,url:"https://github.com/pdufa/pdufa-command-center/actions/runs/42",
  job:null,step:null,jobStatus:null,stepCoverage:"NOT_CHECKED",
  workflowPath:".github/workflows/pdufa-installation-smoke.yml",event:"schedule"};
 const job={jobs:[{name:"production-smoke",status:"in_progress",steps:[
  {name:"Verify signed-in POOL Pipeline reconciliation",status:"in_progress",started_at:now}
 ]}]};
 assert.equal(verifyInstallationStep({...trusted,workflowPath:".github/workflows/other.yml"},job,now),null);
 assert.equal(verifyInstallationStep({...trusted,branch:"untrusted-feature"},job,now),null);
 assert.equal(verifyInstallationStep({...trusted,event:"pull_request"},job,now),null);
 assert.equal(verifyInstallationStep({...trusted,status:"queued"},job,now),null);
 assert.equal(verifyInstallationStep(trusted,{jobs:[{name:"another-job",status:"in_progress",steps:job.jobs[0].steps}]},now),null);
 assert.equal(verifyInstallationStep(trusted,{jobs:[{name:"production-smoke",status:"completed",steps:job.jobs[0].steps}]},now),null);
 assert.equal(verifyInstallationStep(trusted,{jobs:[{name:"production-smoke",status:"in_progress",steps:[{
   name:"Verify signed-in POOL Pipeline reconciliation",status:"completed",conclusion:"success"}]}]},now),null);
 const verified=verifyInstallationStep(trusted,job,now);
 assert.equal(verified.taskId,"01-015");
 assert.equal(verified.state,"RUNNING");
 assert.equal(verified.acceptanceGranted,false);
});
test("GitHub task-step history is never a live cursor",()=>{
 const completed={id:4,name:"smoke",branch:"main",status:"completed",conclusion:"success",
  startedAt:now,updatedAt:now,url:"https://github.com/pdufa/pdufa-command-center/actions/runs/4",
  job:null,step:null,jobStatus:null,stepCoverage:"NOT_CHECKED",
  workflowPath:".github/workflows/pdufa-installation-smoke.yml",event:"push"};
 const raw={jobs:[{name:"production-smoke",status:"completed",steps:[
  {name:"Verify Render backend and PostgreSQL storage readiness",status:"completed",conclusion:"success",completed_at:now}
 ]}]};
 assert.equal(verifyInstallationStep(completed,raw,now),null);
 assert.equal(verifyInstallationStep(completed,raw,now,"LATEST").state,"SUCCEEDED");
});
