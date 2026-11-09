const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
require.extensions[".ts"]=(mod,path)=>mod._compile(ts.transpileModule(fs.readFileSync(path,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}
}).outputText,path);
const {fetchLiveGithubActions,readWorkflowRows,readJobStep}=require("../lib/installation-live-github.ts");
const now="2026-11-08T22:20:00Z";
function run(id,status,conclusion=null){
 return {id,status,conclusion,name:"Actual CI run",head_branch:"main",
  html_url:"https://github.com/pdufa/pdufa-command-center/actions/runs/"+id,
  created_at:now,updated_at:now,run_started_at:now};
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
 assert.equal(api.calls.length,4);
 assert.ok(api.calls.every(c=>c.opts.headers.Authorization==="Bearer test-read-token"));
 assert.ok(!JSON.stringify(result).includes("test-read-token"));
});
test("no running GitHub Actions is a verified observation only when source API succeeds",async()=>{
 const api=fakeFetch({
  "runs?status=in_progress&per_page=50":{workflow_runs:[]},
  "runs?status=queued&per_page=50":{workflow_runs:[]},
  "runs?per_page=20":{workflow_runs:[]}
 });
 const result=await fetchLiveGithubActions("token",now,api.fn);
 assert.equal(result.state,"VERIFIED");
 assert.deepEqual(result.running,[]);
 assert.match(result.scope,/no Codex worker/);
});
test("API auth failure cannot be mistaken for no activity",async()=>{
 const api=fakeFetch({
  "runs?status=in_progress&per_page=50":{statusCode:401},
  "runs?status=queued&per_page=50":{workflow_runs:[]},
  "runs?per_page=20":{workflow_runs:[]}
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
