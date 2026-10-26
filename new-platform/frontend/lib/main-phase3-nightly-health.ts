/** Read-only GitHub Actions MAIN nightly status.
 * An actual source scan differs from DST skip, canceled jobs, and a
 * completed workflow whose research artifact is missing or expired.
 * Never updates the historical pinned qualification snapshot.
 */
export type NightlyHealthState =
  | "FULL_SCAN_CONFIRMED"
  | "FULL_SCAN_STALE"
  | "FULL_SCAN_FAILED"
  | "FULL_SCAN_RUNNING"
  | "REPORT_ARTIFACT_MISSING"
  | "NO_FULL_SCHEDULED_RUN_YET"
  | "SOURCE_UNAVAILABLE";

export type NightlyHealth = {
  schemaVersion: 1;
  state: NightlyHealthState;
  checkedAtUtc: string;
  runId: number | null;
  runUrl: string | null;
  runStartedAtUtc: string | null;
  jobCompletedAtUtc: string | null;
  latestScheduleObservedAtUtc: string | null;
  intentionallySkippedAlternates: number;
  artifactConfirmed: boolean;
  scope: "SCHEDULED_MAIN_RESEARCH_LEDGER_ONLY_NO_MEMBERSHIP_CHANGES";
};

export const WORKFLOW_HISTORY_URL =
  "https://github.com/pdufa/pdufa-command-center/actions/workflows/main-phase3-evidence-qualification.yml";
const API = "https://api.github.com/repos/pdufa/pdufa-command-center";
const RUNS_ENDPOINT = API + "/actions/workflows/main-phase3-evidence-qualification.yml/runs?event=schedule&branch=main&per_page=25";
const REQUIRED_ARTIFACT = "main-phase3-evidence-qualification-research-only";
const MAX_JOB_QUERIES = 12;
const STALE_MILLIS = 36 * 60 * 60 * 1000;

type Row = Record<string, unknown>;
const obj = (v:unknown):v is Row=>v!==null && typeof v==="object" && !Array.isArray(v);
const positiveId = (v:unknown):v is number => typeof v==="number" && Number.isSafeInteger(v) && v>0;
const utc = (s:unknown):s is string => typeof s==="string" &&
  /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(s) &&
  Number.isFinite(Date.parse(s));
const runUrl = (id:number)=>"https://github.com/pdufa/pdufa-command-center/actions/runs/"+id;

function emptyHealth(now:Date):NightlyHealth {
  return {
    schemaVersion:1, state:"NO_FULL_SCHEDULED_RUN_YET",
    checkedAtUtc:now.toISOString(),
    runId:null,runUrl:null,runStartedAtUtc:null,jobCompletedAtUtc:null,
    latestScheduleObservedAtUtc:null,intentionallySkippedAlternates:0,
    artifactConfirmed:false,
    scope:"SCHEDULED_MAIN_RESEARCH_LEDGER_ONLY_NO_MEMBERSHIP_CHANGES",
  };
}
export function unavailableNightlyHealth(now:Date=new Date()):NightlyHealth {
  return {...emptyHealth(now), state:"SOURCE_UNAVAILABLE"};
}

export async function readNightlyHealth(
  fetchJson:(url:string)=>Promise<unknown>,now:Date=new Date()
):Promise<NightlyHealth> {
  if(!Number.isFinite(now.getTime()))throw new Error("Invalid observation clock");
  const listing=await fetchJson(RUNS_ENDPOINT);
  if(!obj(listing)||!Array.isArray(listing.workflow_runs)||
    listing.workflow_runs.length>25)throw new Error("GitHub workflow listing unavailable");
  const scheduleRuns=listing.workflow_runs.filter((v):v is Row=>
    obj(v)&&v.event==="schedule"&&v.head_branch==="main"&&
    positiveId(v.id)&&utc(v.created_at)&&
    typeof v.path==="string"&&v.path.includes("/main-phase3-evidence-qualification.yml")
  ).sort((a,b)=>Date.parse(b.created_at as string)-Date.parse(a.created_at as string));

  const output=emptyHealth(now);
  if(scheduleRuns[0])output.latestScheduleObservedAtUtc=scheduleRuns[0].created_at as string;
  for(const run of scheduleRuns.slice(0,MAX_JOB_QUERIES)){
    const id=run.id as number;
    const jobsPayload=await fetchJson(API+"/actions/runs/"+id+"/jobs?per_page=100");
    if(!obj(jobsPayload)||!Array.isArray(jobsPayload.jobs)||
      jobsPayload.jobs.length>100)throw new Error("Scheduled research job status unavailable");
    const jobs=jobsPayload.jobs.filter(obj);
    const ledger=jobs.find(x=>x.name==="research-ledger");
    const gate=jobs.find(x=>x.name==="pacific-nightly-gate");
    if(!gate)throw new Error("Scheduled gate job is not identified");
    const started=run.created_at as string;
    const update=(state:NightlyHealthState,date:string|null,confirmed=false):NightlyHealth=>({
      ...output,state,runId:id,runUrl:runUrl(id),
      runStartedAtUtc:started,jobCompletedAtUtc:date,
      artifactConfirmed:confirmed,
    });
    if(gate.conclusion==="failure"||gate.conclusion==="cancelled"||
      gate.conclusion==="timed_out")return update("FULL_SCAN_FAILED",null);
    if(!ledger){
      if(run.status!=="completed")return update("FULL_SCAN_RUNNING",null);
      throw new Error("Completed scheduled workflow is missing its research-ledger job");
    }
    if(ledger.conclusion==="skipped"){
      if(gate.conclusion!=="success")
        throw new Error("Unconfirmed DST-alternate skip; full scan cannot be inferred");
      output.intentionallySkippedAlternates++;
      continue;
    }
    if(gate.conclusion!=="success"||ledger.status!=="completed"||ledger.conclusion===null){
      return update("FULL_SCAN_RUNNING",null);
    }
    const done=utc(ledger.completed_at)?ledger.completed_at as string:null;
    if(ledger.conclusion!=="success"){
      return update("FULL_SCAN_FAILED",done);
    }
    const artifacts=await fetchJson(API+"/actions/runs/"+id+"/artifacts?per_page=100");
    if(!obj(artifacts)||!Array.isArray(artifacts.artifacts)||
      artifacts.artifacts.length>100)throw new Error("Research artifact verification unavailable");
    const found=artifacts.artifacts.some(x=>obj(x)&&
      x.name===REQUIRED_ARTIFACT&&x.expired===false&&
      typeof x.size_in_bytes==="number"&&x.size_in_bytes>0&&
      (!obj(x.workflow_run)||x.workflow_run.id===id));
    if(!found)return update("REPORT_ARTIFACT_MISSING",done);
    if(!done||Date.parse(done)>now.getTime()+300000)
      throw new Error("Successful research run lacks a trustworthy completion timestamp");
    return update(now.getTime()-Date.parse(done)>STALE_MILLIS ?
      "FULL_SCAN_STALE":"FULL_SCAN_CONFIRMED",done,true);
  }
  return output;
}

export function parseNightlyHealth(value:unknown):NightlyHealth {
  const states:NightlyHealthState[]=[
    "FULL_SCAN_CONFIRMED","FULL_SCAN_STALE","FULL_SCAN_FAILED",
    "FULL_SCAN_RUNNING","REPORT_ARTIFACT_MISSING",
    "NO_FULL_SCHEDULED_RUN_YET","SOURCE_UNAVAILABLE"
  ];
  if(!obj(value)||value.schemaVersion!==1||!states.includes(value.state as NightlyHealthState)||
    !utc(value.checkedAtUtc)||!Number.isSafeInteger(value.intentionallySkippedAlternates)||
    (value.intentionallySkippedAlternates as number)<0||
    value.scope!=="SCHEDULED_MAIN_RESEARCH_LEDGER_ONLY_NO_MEMBERSHIP_CHANGES"||
    typeof value.artifactConfirmed!=="boolean")throw new Error("Invalid nightly research status");
  if(value.runId===null){
    if(value.runUrl!==null||value.runStartedAtUtc!==null||value.jobCompletedAtUtc!==null||
      value.artifactConfirmed||!["NO_FULL_SCHEDULED_RUN_YET","SOURCE_UNAVAILABLE"].includes(value.state as string))
      throw new Error("Unsubstantiated successful scheduled run");
  }else{
    if(!positiveId(value.runId)||value.runUrl!==runUrl(value.runId)||
       !utc(value.runStartedAtUtc)||
       (value.jobCompletedAtUtc!==null&&!utc(value.jobCompletedAtUtc))||
       ["NO_FULL_SCHEDULED_RUN_YET","SOURCE_UNAVAILABLE"].includes(value.state as string))
      throw new Error("Malformed scheduled run identity");
    if(value.artifactConfirmed !==
      ["FULL_SCAN_CONFIRMED","FULL_SCAN_STALE"].includes(value.state as string))
      throw new Error("Artifact-dependent success status is unsupported");
  }
  if(value.latestScheduleObservedAtUtc!==null&&!utc(value.latestScheduleObservedAtUtc))
    throw new Error("Invalid last scheduled trigger");
  return value as NightlyHealth;
}
