/** GitHub workflow observations; task mapping is restricted to verified CI step contracts.
 * A running CI validation step is not a Codex worker or task acceptance.
 */
export type WorkflowEvidence = {
  id: number; name: string; branch: string; status: string; conclusion: string | null;
  startedAt: string | null; updatedAt: string | null; url: string;
  job: string | null; step: string | null; jobStatus: string | null;
  stepCoverage: "OBSERVED" | "NOT_CHECKED" | "UNAVAILABLE";
  workflowPath: string | null; event: string | null;
};
export type VerifiedTaskExecution = {
  taskId:string; label:string; state:"RUNNING"|"SUCCEEDED"|"FAILED";
  runId:number;runUrl:string;job:string;step:string;source:"GITHUB_ACTIONS_STEP";
  observedAt:string;stepStartedAt:string|null;stepCompletedAt:string|null;
  acceptanceGranted:false;
};
export type LiveGithubEvidence = {
  state: "VERIFIED" | "PARTIAL" | "UNAVAILABLE" | "AUTH_REQUIRED";
  checkedAt: string;
  sourceUrl: string;
  running: WorkflowEvidence[];
  queued: WorkflowEvidence[];
  recent: WorkflowEvidence[];
  scope: string;
  note: string;
  taskExecution:VerifiedTaskExecution|null;
  lastTaskExecution:VerifiedTaskExecution|null;
};
const sourceUrl="https://github.com/pdufa/pdufa-command-center/actions";
const restBase="https://api.github.com/repos/pdufa/pdufa-command-center";
const trackedWorkflowPath=".github/workflows/pdufa-installation-smoke.yml";
const trackedJobName="production-smoke";
// Restricted contract: these exact CI steps execute the corresponding smoke
// checks. They are NOT complete acceptance of either master requirement.
const taskStepContracts:Record<string,{id:string;label:string}>={
  "Verify Render backend and PostgreSQL storage readiness":{
    id:"01-004",label:"Verify PostgreSQL connectivity"},
  "Verify signed-in POOL Pipeline reconciliation":{
    id:"01-015",label:"Verify dashboard routes and authenticated access"}
};
const validEvents=new Set(["push","workflow_dispatch","schedule"]);
function object(raw: unknown): Record<string, unknown> {
  return raw !== null && typeof raw==="object" && !Array.isArray(raw) ? raw as Record<string,unknown> : {};
}
function string(raw: unknown): string | null {
  return typeof raw==="string" && raw.length>0 ? raw : null;
}
function workflow(raw: unknown): WorkflowEvidence | null {
  const row=object(raw);
  const id=row.id;
  const url=string(row.html_url);
  if(typeof id!=="number"||!Number.isSafeInteger(id)||id<1||
    !url||!url.startsWith(sourceUrl+"/runs/")) return null;
  return {id, name:string(row.name)??"Unnamed workflow",branch:string(row.head_branch)??"Unknown",
    status:string(row.status)??"unknown",conclusion:string(row.conclusion),
    startedAt:string(row.run_started_at)??string(row.created_at),
    updatedAt:string(row.updated_at),url,job:null,step:null,jobStatus:null,stepCoverage:"NOT_CHECKED",
    workflowPath:string(row.path),event:string(row.event)};
}
export function readWorkflowRows(raw:unknown, desired: "in_progress"|"queued"|"recent"):WorkflowEvidence[] {
  const rows=object(raw).workflow_runs;
  if(!Array.isArray(rows))throw Error("Invalid GitHub Actions API response");
  const parsed=rows.map(workflow).filter((value):value is WorkflowEvidence=>value!==null);
  return parsed.filter(item=>desired==="recent"?item.status==="completed":
    desired==="in_progress"?item.status==="in_progress":
    ["queued","pending","requested","waiting"].includes(item.status));
}
export function readJobStep(raw:unknown):{job:string|null;step:string|null;jobStatus:string|null} {
  const jobs=object(raw).jobs;
  if(!Array.isArray(jobs))throw Error("Invalid GitHub Actions job response");
  const running=jobs.map(object).find(j=>j.status==="in_progress");
  const pending=jobs.map(object).find(j=>j.status==="queued"||j.status==="waiting");
  const job=running??pending;
  const steps=job?.steps;
  const step=Array.isArray(steps) ? steps.map(object).find(s=>s.status==="in_progress") : null;
  return {job:string(job?.name),step:string(step?.name),jobStatus:string(job?.status)};
}
/**
 * An exact running GitHub job+step is the only authority for an active mapped
 * installation check. Never map arbitrary workflow names, queued jobs or
 * completed runs to a live task. The master checklist remains independently
 * unaccepted until full acceptance evidence exists.
 */
export function verifyInstallationStep(
 run:WorkflowEvidence,rawJobs:unknown,checkedAt:string,
 desired:"RUNNING"|"LATEST"="RUNNING"
):VerifiedTaskExecution|null{
 if(run.workflowPath!==trackedWorkflowPath||run.branch!=="main"||
  !run.event||!validEvents.has(run.event))return null;
 if(desired==="RUNNING"&&run.status!=="in_progress")return null;
 if(desired==="LATEST"&&run.status!=="completed")return null;
 const jobs=object(rawJobs).jobs;
 if(!Array.isArray(jobs))return null;
 const eligible=jobs.map(object).filter(job=>
  job.name===trackedJobName &&
  (desired==="RUNNING"?job.status==="in_progress":job.status==="completed"));
 if(eligible.length!==1)return null;
 const job=eligible[0];
 if(!Array.isArray(job.steps))return null;
 const found=job.steps.map(object).filter(step=>
  typeof step.name==="string"&&Object.hasOwn(taskStepContracts,step.name)&&
  (desired==="RUNNING"?step.status==="in_progress":step.status==="completed"&&
    ["success","failure"].includes(String(step.conclusion))));
 if(!found.length)return null;
 // The latest completed mapped step is a checkpoint, never current execution.
 const step=desired==="RUNNING"?found[0]:found[found.length-1];
 const contract=taskStepContracts[String(step.name)];
 return {
  taskId:contract.id,label:contract.label,
  state:desired==="RUNNING"?"RUNNING":step.conclusion==="success"?"SUCCEEDED":"FAILED",
  runId:run.id,runUrl:run.url,job:trackedJobName,step:String(step.name),
  source:"GITHUB_ACTIONS_STEP",observedAt:checkedAt,
  stepStartedAt:string(step.started_at),stepCompletedAt:string(step.completed_at),
  acceptanceGranted:false
 };
}

export async function fetchLiveGithubActions(
  token:string|undefined,checkedAt:string,
  fetcher:typeof fetch=fetch
):Promise<LiveGithubEvidence>{
  const unavailable=(state:LiveGithubEvidence["state"],note:string):LiveGithubEvidence=>({
    state,checkedAt,sourceUrl,running:[],queued:[],recent:[],taskExecution:null,lastTaskExecution:null,
    scope:"GitHub Actions execution only, not an authenticated Codex task heartbeat or scientific grade",
    note
  });
  if(!token)return unavailable("UNAVAILABLE","GitHub read credential not configured; execution status cannot be verified.");
  const headers={Authorization:"Bearer "+token,Accept:"application/vnd.github+json",
    "X-GitHub-Api-Version":"2022-11-28","User-Agent":"PDUFA-Installation-Live-Readback"};
  async function request(path:string):Promise<unknown>{
    const response=await fetcher(restBase+path,{headers,cache:"no-store",signal:AbortSignal.timeout(6500)});
    if(!response.ok)throw Error("GitHub Actions API HTTP "+response.status);
    return response.json();
  }
  const statuses=await Promise.allSettled([
    request("/actions/runs?status=in_progress&per_page=50"),
    request("/actions/runs?status=queued&per_page=50"),
    request("/actions/runs?per_page=20")
  ]);
  const [runningResult,queuedResult,recentResult]=statuses;
  if(runningResult.status==="rejected")return unavailable("UNAVAILABLE",
    "GitHub running-workflow lookup failed; cannot confirm what is executing.");
  let running:WorkflowEvidence[];
  try{running=readWorkflowRows(runningResult.value,"in_progress");}
  catch{return unavailable("UNAVAILABLE","GitHub running-workflow data could not be verified.");}
  let queued:WorkflowEvidence[]=[];
  let recent:WorkflowEvidence[]=[];
  let partial=false;
  try{
    if(queuedResult.status==="fulfilled")queued=readWorkflowRows(queuedResult.value,"queued");
    else partial=true;
    if(recentResult.status==="fulfilled")recent=readWorkflowRows(recentResult.value,"recent").slice(0,5);
    else partial=true;
  }catch{partial=true;}
  // Read up to eight actual running jobs. An exact *step* match with a known
  // source-workflow path is required to set the installation cursor.
  const jobLookups=await Promise.allSettled(running.slice(0,8).map(item=>
    request("/actions/runs/"+item.id+"/jobs?per_page=100")));
  let taskExecution:VerifiedTaskExecution|null=null;
  running=running.map((item,index)=>{
    if(index>=8)return item;
    const jobResult=jobLookups[index];
    if(jobResult.status!=="fulfilled")return {...item,stepCoverage:"UNAVAILABLE"};
    try{
      const step=readJobStep(jobResult.value);
      const verified=verifyInstallationStep(item,jobResult.value,checkedAt);
      if(verified&&(!taskExecution||verified.runId>taskExecution.runId))
       taskExecution=verified;
      return {...item,...step,stepCoverage:"OBSERVED"};
    }catch{return {...item,stepCoverage:"UNAVAILABLE"};}
  });
  // Read one source-workflow-specific completed run for an honest last-known
  // task-step checkpoint; never report it as RUNNING.
  let lastTaskExecution:VerifiedTaskExecution|null=null;
  try{
    const history=await request("/actions/workflows/pdufa-installation-smoke.yml/runs?status=completed&per_page=3");
    const historyRows=readWorkflowRows(history,"recent").filter(item=>
      item.workflowPath===trackedWorkflowPath&&item.branch==="main");
    if(historyRows.length){
      const recentRun=historyRows[0];
      const jobHistory=await request("/actions/runs/"+recentRun.id+"/jobs?per_page=100");
      lastTaskExecution=verifyInstallationStep(recentRun,jobHistory,checkedAt,"LATEST");
    }
  }catch{partial=true;}
  if(running.length>=50 || running.length>8 || running.some(item=>item.stepCoverage==="UNAVAILABLE"))partial=true;
  const note=partial
    ?"GitHub supplied verified observations, but at least one execution list was partial or capped. No full absence claim is possible."
    :"GitHub Actions status checked directly. This does not establish Codex task identity or scientific review completion.";
  return {state:partial?"PARTIAL":"VERIFIED",checkedAt,sourceUrl,running,queued,recent,
    scope:"GitHub Actions workflow/job execution; only exact installation-smoke job+step maps to a checklist task. No Codex heartbeat or independent task acceptance.",
    note,taskExecution,lastTaskExecution};
}
