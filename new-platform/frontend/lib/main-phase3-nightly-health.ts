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
  | "REPORT_INTEGRITY_UNVERIFIED"
  | "NO_FULL_SCHEDULED_RUN_YET"
  | "SCHEDULED_SCAN_OVERDUE"
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
  overduePacificDate: string | null;
  intentionallySkippedAlternates: number;
  artifactConfirmed: boolean;
  integrityStepConfirmed: boolean;
  scope: "SCHEDULED_MAIN_RESEARCH_LEDGER_ONLY_NO_MEMBERSHIP_CHANGES";
};

export const WORKFLOW_HISTORY_URL =
  "https://github.com/pdufa/pdufa-command-center/actions/workflows/main-phase3-evidence-qualification.yml";
const API = "https://api.github.com/repos/pdufa/pdufa-command-center";
const RUNS_ENDPOINT = API + "/actions/workflows/main-phase3-evidence-qualification.yml/runs?event=schedule&branch=main&per_page=25";
const REQUIRED_ARTIFACT = "main-phase3-evidence-qualification-research-only";
// Stable GitHub Actions job-step API contract; never encode changing file count.
export const INTEGRITY_STEP = "Verify MAIN Phase 3 research integrity manifest [nightly-integrity-v1]";
const MAX_JOB_QUERIES = 12;
const STALE_MILLIS = 36 * 60 * 60 * 1000;
// PR #471 installed the first nominal Pacific nightly schedule on Oct 26.
const FIRST_NOMINAL_PACIFIC_SCAN = "2026-10-26";
const DEADLINE_PACIFIC_MINUTES = 22 * 60 + 30; // 10:30 PM grace includes both UTC cron triggers.

type PacificClock = {day:string; minutes:number};
function pacificClock(instant:Date):PacificClock {
  const fields=new Intl.DateTimeFormat("en-US",{
    timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit",
    hour:"2-digit",minute:"2-digit",hourCycle:"h23"
  }).formatToParts(instant);
  const get=(key:string)=>fields.find(x=>x.type===key)?.value;
  const year=get("year"),month=get("month"),day=get("day"),
    hour=Number(get("hour")),minute=Number(get("minute"));
  if(!year||!month||!day||!Number.isInteger(hour)||!Number.isInteger(minute)||
    hour<0||hour>23||minute<0||minute>59)throw new Error("Invalid Pacific clock");
  return {day:year+"-"+month+"-"+day,minutes:hour*60+minute};
}
function previousPacificDay(day:string):string {
  const previous=new Date(Date.parse(day+"T12:00:00Z")-86400000);
  if(!Number.isFinite(previous.getTime()))throw new Error("Invalid Pacific day");
  return previous.toISOString().slice(0,10);
}
/** Nightly schedule overdue only after 10:30 PM Pacific, with a grace period.
 * Until 10:30 PM the previous night's completed run is still the expected
 * observation; after that the next nightly research run is expected.
 */
export function overdueNominalPacificDate(now:Date):string|null {
  if(!Number.isFinite(now.getTime()))throw new Error("Invalid Pacific clock instant");
  const local=pacificClock(now);
  const due=local.minutes>=DEADLINE_PACIFIC_MINUTES?
    local.day:previousPacificDay(local.day);
  return due>=FIRST_NOMINAL_PACIFIC_SCAN?due:null;
}
/** GitHub cron might start many hours late the next day. Until the
 * 7 PM Pacific schedule window, a scheduled run belongs to the prior night.
 */
function runPacificNight(started:string):string {
  const local=pacificClock(new Date(started));
  return local.minutes<19*60?previousPacificDay(local.day):local.day;
}

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
    latestScheduleObservedAtUtc:null,overduePacificDate:null,intentionallySkippedAlternates:0,
    artifactConfirmed:false,integrityStepConfirmed:false,
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
  const expectedNight=overdueNominalPacificDate(now);
  const late=():NightlyHealth=>({
    ...output,state:"SCHEDULED_SCAN_OVERDUE",overduePacificDate:expectedNight
  });
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
    const update=(state:NightlyHealthState,date:string|null,confirmed=false,integrity=false):NightlyHealth=>({
      ...output,state,runId:id,runUrl:runUrl(id),
      runStartedAtUtc:started,jobCompletedAtUtc:date,
      artifactConfirmed:confirmed,integrityStepConfirmed:integrity,
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
    // Never show yesterday's confirmed job as satisfying a missing new night.
    // Delayed starts before the next 7 PM Pacific window belong to the prior night.
    if(expectedNight&&runPacificNight(started)<expectedNight)return late();
    if(gate.conclusion!=="success"||ledger.status!=="completed"||ledger.conclusion===null){
      return update("FULL_SCAN_RUNNING",null);
    }
    const done=utc(ledger.completed_at)?ledger.completed_at as string:null;
    if(ledger.conclusion!=="success"){
      return update("FULL_SCAN_FAILED",done);
    }
    // GitHub uploads partial forensic artifacts via if: always(). A green job
    // and a ZIP alone are not proof that its 14 source files reconciled.
    // The exact named pre-upload integrity step must have succeeded as well.
    if(!Array.isArray(ledger.steps)||ledger.steps.length>100)
      return update("REPORT_INTEGRITY_UNVERIFIED",done);
    const matchingSteps=ledger.steps.filter(x=>obj(x)&&x.name===INTEGRITY_STEP);
    if(matchingSteps.length!==1||
      matchingSteps[0].status!=="completed"||
      matchingSteps[0].conclusion!=="success")
      return update("REPORT_INTEGRITY_UNVERIFIED",done);
    const artifacts=await fetchJson(API+"/actions/runs/"+id+"/artifacts?per_page=100");
    if(!obj(artifacts)||!Array.isArray(artifacts.artifacts)||
      artifacts.artifacts.length>100)throw new Error("Research artifact verification unavailable");
    const found=artifacts.artifacts.some(x=>obj(x)&&
      x.name===REQUIRED_ARTIFACT&&x.expired===false&&
      typeof x.size_in_bytes==="number"&&x.size_in_bytes>0&&
      (!obj(x.workflow_run)||x.workflow_run.id===id));
    if(!found)return update("REPORT_ARTIFACT_MISSING",done,false,true);
    if(!done||Date.parse(done)>now.getTime()+300000)
      throw new Error("Successful research run lacks a trustworthy completion timestamp");
    return update(now.getTime()-Date.parse(done)>STALE_MILLIS ?
      "FULL_SCAN_STALE":"FULL_SCAN_CONFIRMED",done,true,true);
  }
  return expectedNight?late():output;
}

export function parseNightlyHealth(value:unknown):NightlyHealth {
  const states:NightlyHealthState[]=[
    "FULL_SCAN_CONFIRMED","FULL_SCAN_STALE","FULL_SCAN_FAILED",
    "FULL_SCAN_RUNNING","REPORT_ARTIFACT_MISSING",
    "REPORT_INTEGRITY_UNVERIFIED",
    "NO_FULL_SCHEDULED_RUN_YET","SCHEDULED_SCAN_OVERDUE","SOURCE_UNAVAILABLE"
  ];
  if(!obj(value)||value.schemaVersion!==1||!states.includes(value.state as NightlyHealthState)||
    !utc(value.checkedAtUtc)||!Number.isSafeInteger(value.intentionallySkippedAlternates)||
    (value.intentionallySkippedAlternates as number)<0||
    value.scope!=="SCHEDULED_MAIN_RESEARCH_LEDGER_ONLY_NO_MEMBERSHIP_CHANGES"||
    typeof value.artifactConfirmed!=="boolean"||
    typeof value.integrityStepConfirmed!=="boolean"||
    (value.overduePacificDate!==null &&
      (typeof value.overduePacificDate!=="string" ||
        !/^\d{4}-\d{2}-\d{2}$/.test(value.overduePacificDate))))
    throw new Error("Invalid nightly research status");
  if(value.runId===null){
    if(value.runUrl!==null||value.runStartedAtUtc!==null||value.jobCompletedAtUtc!==null||
      value.artifactConfirmed||value.integrityStepConfirmed||
      !["NO_FULL_SCHEDULED_RUN_YET","SCHEDULED_SCAN_OVERDUE","SOURCE_UNAVAILABLE"].includes(value.state as string))
      throw new Error("Unsubstantiated successful scheduled run");
  }else{
    if(!positiveId(value.runId)||value.runUrl!==runUrl(value.runId)||
       !utc(value.runStartedAtUtc)||
       (value.jobCompletedAtUtc!==null&&!utc(value.jobCompletedAtUtc))||
       ["NO_FULL_SCHEDULED_RUN_YET","SCHEDULED_SCAN_OVERDUE","SOURCE_UNAVAILABLE"].includes(value.state as string))
      throw new Error("Malformed scheduled run identity");
    if(value.artifactConfirmed !==
      ["FULL_SCAN_CONFIRMED","FULL_SCAN_STALE"].includes(value.state as string))
      throw new Error("Artifact-dependent success status is unsupported");
    if(value.integrityStepConfirmed !==
      ["FULL_SCAN_CONFIRMED","FULL_SCAN_STALE","REPORT_ARTIFACT_MISSING"].includes(value.state as string))
      throw new Error("Pre-upload integrity validation status is unsupported");
  }
  if((value.state==="SCHEDULED_SCAN_OVERDUE")!==Boolean(value.overduePacificDate))
    throw new Error("Overdue alert date must match unverified scheduled status");
  if(value.latestScheduleObservedAtUtc!==null&&!utc(value.latestScheduleObservedAtUtc))
    throw new Error("Invalid last scheduled trigger");
  return value as NightlyHealth;
}
