/** GitHub Actions execution observations. Never maps a workflow to a Codex/master-build task. */
export type WorkflowEvidence = {
  id: number; name: string; branch: string; status: string; conclusion: string | null;
  startedAt: string | null; updatedAt: string | null; url: string;
  job: string | null; step: string | null; jobStatus: string | null;
  stepCoverage: "OBSERVED" | "NOT_CHECKED" | "UNAVAILABLE";
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
};
const sourceUrl="https://github.com/pdufa/pdufa-command-center/actions";
const restBase="https://api.github.com/repos/pdufa/pdufa-command-center";
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
    updatedAt:string(row.updated_at),url,job:null,step:null,jobStatus:null,stepCoverage:"NOT_CHECKED"};
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
export async function fetchLiveGithubActions(
  token:string|undefined,checkedAt:string,
  fetcher:typeof fetch=fetch
):Promise<LiveGithubEvidence>{
  const unavailable=(state:LiveGithubEvidence["state"],note:string):LiveGithubEvidence=>({
    state,checkedAt,sourceUrl,running:[],queued:[],recent:[],
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
  // Bounded real job/step inspection; do not label a guessed code task as running.
  const jobLookups=await Promise.allSettled(running.slice(0,8).map(item=>
    request("/actions/runs/"+item.id+"/jobs?per_page=100")));
  running=running.map((item,index)=>{
    if(index>=8)return item;
    const jobResult=jobLookups[index];
    if(jobResult.status!=="fulfilled")return {...item,stepCoverage:"UNAVAILABLE"};
    try{
      const step=readJobStep(jobResult.value);
      return {...item,...step,stepCoverage:"OBSERVED"};
    }catch{return {...item,stepCoverage:"UNAVAILABLE"};}
  });
  if(running.length>=50)partial=true;
  const note=partial
    ?"GitHub supplied verified observations, but at least one execution list was partial or capped. No full absence claim is possible."
    :"GitHub Actions status checked directly. This does not establish Codex task identity or scientific review completion.";
  return {state:partial?"PARTIAL":"VERIFIED",checkedAt,sourceUrl,running,queued,recent,
    scope:"GitHub Actions workflow/job execution (repository-wide); no Codex worker or installation task-ID attestation",note};
}
