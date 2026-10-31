"use client";

import { useEffect, useMemo, useState } from "react";

type RunState = "queued" | "running" | "success" | "failure" | "cancelled" | "skipped" | "completed" | "unknown";
type Step = { name: string; number: number; status: RunState; startedAt: string | null; completedAt: string | null };
type Job = { id: number; name: string; status: RunState; startedAt: string | null; completedAt: string | null; steps: Step[] };
type Report = {
  source?: string; asOf?: string; status?: string; error?: string; note?: string; truncated?: boolean;
  totalJobs?: number;
  run?: {
    id: number; name: string; title: string; workflow: string; status: RunState;
    startedAt: string | null; createdAt: string | null; updatedAt: string | null;
    completedAt: string | null; url: string; event: string | null; attempt: number;
  };
  jobs?: Job[];
};
const FEEDS = [
  ["AUTO", "Latest active / recent scan"],
  ["OVERNIGHT", "Full POOL → PIPELINE → Phase 3 results"],
  ["PIPELINE_GEM_JR", "Clinical POOL / PIPELINE / Phase 3 results"],
  ["SOURCES", "FDA / SEC / Financial / Market / Issuer"],
  ["SCAN_CONTROL", "Manual scan commands"],
  ["GMAIL_AUDIT", "Gmail email audit"],
  ["GMAIL_REPAIR", "Gmail fix & Trash resolved"],
] as const;

const TERMINAL = new Set<RunState>(["success", "failure", "cancelled", "skipped", "completed"]);
const WAIT = new Set<RunState>(["queued", "unknown"]);
const STAGES = [
  { key: "pipeline", label: "PIPELINE", mini: "Trial inventory" },
  { key: "phase3", label: "PHASE 3 RESULTS", mini: "Posted trial evidence" },
  { key: "publish", label: "REPORT", mini: "Published results" },
  { key: "sources", label: "SOURCES", mini: "FDA · SEC · Financial · Market · Issuer" },
  { key: "score", label: "SCORE / REPAIR", mini: "Scoring · Gmail · repair" },
  { key: "final", label: "FINAL", mini: "Result & checks" },
] as const;

function stageForJob(name: string): string | null {
  const n = name.toLowerCase();
  if (/^validate\b/.test(n)) return "validate";
  if (/^clinical\s*\/\s*pipeline\b/.test(n) || /\bpipeline\b/.test(n)) return "pipeline";
  if (/phase.?3 results|phase3_results|clinical\s*\/\s*gem jr\b/.test(n)) return "phase3";
  if (/^report\s*\//.test(n) || /\bpublish\b/.test(n) && !/^sources\s*\//.test(n)) return "publish";
  if (/^sources\s*\//.test(n) || /\b(?:fda|sec|financial|market|issuer)\b/.test(n)) return "sources";
  if (/^scoring-and-repair\s*\//.test(n) || /\bscor(e|ing)\b|\brepair\b/.test(n)) return "score";
  if (/^result\b/.test(n)) return "final";
  return null;
}
function stageStatus(jobs: Job[]): RunState {
  if (!jobs.length) return "unknown";
  if (jobs.some(j => j.status === "running")) return "running";
  if (jobs.some(j => j.status === "failure")) return "failure";
  if (jobs.some(j => WAIT.has(j.status))) return "queued";
  if (jobs.every(j => j.status === "skipped")) return "skipped";
  if (jobs.some(j => j.status === "cancelled")) return "cancelled";
  return jobs.every(j => TERMINAL.has(j.status)) ? "success" : "unknown";
}
function iconFor(status: RunState): string {
  return status === "success" ? "✓" : status === "failure" ? "×" :
    status === "running" ? "●" : status === "skipped" ? "–" :
    status === "cancelled" ? "×" : status === "completed" ? "✓" : "○";
}
function labelFor(status: RunState): string {
  return ({
    success: "Completed", failure: "Failed", cancelled: "Cancelled",
    queued: "Queued", running: "Running", skipped: "Skipped",
    completed: "Finished", unknown: "Not started / unreported",
  })[status];
}
function when(value: string | null | undefined) {
  if (!value || !Number.isFinite(Date.parse(value))) return "Not reported";
  return new Date(value).toLocaleString("en-US", {
    timeZone: "America/Los_Angeles", month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit", second: "2-digit", timeZoneName: "short",
  });
}
function duration(start: string | null | undefined, end: string | null | undefined, now: number): string {
  if (!start || !Number.isFinite(Date.parse(start))) return "Not reported";
  const startTime = Date.parse(start);
  const endTime = end && Number.isFinite(Date.parse(end)) ? Date.parse(end) : now;
  const seconds = Math.max(0, Math.floor((endTime - startTime) / 1000));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h, m, s].map(v => String(v).padStart(2, "0")).join(":");
}
function progress(jobs: Job[], totalJobs: number | undefined, truncated: boolean | undefined) {
  const allSteps = jobs.flatMap(j => j.steps);
  const doneSteps = allSteps.filter(s => TERMINAL.has(s.status)).length;
  const totalSteps = allSteps.length;
  const doneJobs = jobs.filter(j => TERMINAL.has(j.status)).length;
  const knownJobs = totalJobs ?? jobs.length;
// Job completion has a stable denominator; reported step totals can grow as jobs start.
  // Never call skipped or failed work successful — only count that its execution has finished.
  const pct = !truncated && knownJobs > 0 ? Math.round(100 * doneJobs / knownJobs) : null;
  return { doneJobs, knownJobs, doneSteps, totalSteps, pct };
}
function currentTask(jobs: Job[]) {
  const running = jobs.filter(j => j.status === "running");
  const first = running.find(j => j.steps.some(s => s.status === "running")) || running[0];
  const currentStep = first?.steps.find(s => s.status === "running");
  return { first, currentStep, count: running.length };
}

export default function LiveScansProgress() {
  const [feed, setFeed] = useState("AUTO");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [clock, setClock] = useState(0);

  useEffect(() => {
    setClock(Date.now());
    const interval = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    let alive = true;
    async function load() {
      try {
        const r = await fetch("/api/scans/progress?kind=" + encodeURIComponent(feed), {
          cache: "no-store", signal: controller.signal,
        });
        const data: Report = await r.json();
        if (!r.ok) throw Error(data.error || "GitHub execution status unavailable");
        if (!alive) return;
        setReport(data);
        setError("");
      } catch (e) {
        if (!alive) return;
        setReport(null);
        setError(e instanceof Error ? e.message : "Live status unavailable");
      } finally {
        if (alive) setLoading(false);
      }
    }
    setLoading(true);
    void load();
    const timer = setInterval(() => { void load(); }, 60000);
    return () => { alive = false; controller.abort(); clearInterval(timer); };
  }, [feed, refresh]);

  const jobs = useMemo(() => report?.jobs || [], [report?.jobs]);
  const data = progress(jobs, report?.totalJobs, report?.truncated);
  const task = currentTask(jobs);
  const run = report?.run;
  const overallStatus: RunState = run?.status || "unknown";
  const overnight = run?.workflow === "pdufa-overnight-sequential.yml" ||
    run?.workflow === "pdufa-nightly-clinical.yml";
  const stageRows = STAGES.map(s => {
    const items = jobs.filter(j => stageForJob(j.name) === s.key);
    return { ...s, jobs: items, status: stageStatus(items) };
  });
  const keyForNow = task.first ? stageForJob(task.first.name) : null;
  const currentStage = stageRows.find(s => s.key === keyForNow)?.label ||
    (task.first?.name.split("/")[0]?.trim() || "No task running");
  const currentJobDuration = duration(task.first?.startedAt, task.first?.completedAt, clock);
  const currentStepDuration = duration(task.currentStep?.startedAt, task.currentStep?.completedAt, clock);
  const observed = typeof report?.asOf === "string" ? report.asOf : null;

  return <section className="pdufa-progress" aria-label="Live GitHub scan execution progress">
    <header className="pdufa-progress-top">
      <div>
        <div className="pdufa-progress-eyebrow"><span className="pdufa-live-dot" /> LIVE EXECUTION TRACKER</div>
        <h3>What's running — and how far it's progressed</h3>
        <p>Actual GitHub jobs and steps · Pacific time · checks every 60 seconds; server data can lag about 3 minutes without GitHub authorization</p>
      </div>
      <div className="pdufa-progress-controls">
        <label htmlFor="pdufa-progress-feed">Follow workflow
          <select id="pdufa-progress-feed" value={feed} onChange={e => setFeed(e.target.value)}>
            {FEEDS.map(([key, name]) => <option value={key} key={key}>{name}</option>)}
          </select>
        </label>
        <button type="button" onClick={() => setRefresh(n => n + 1)}
                disabled={loading} className="pdufa-progress-refresh">
          {loading ? "Checking…" : "↻ Refresh now"}
        </button>
      </div>
    </header>
    {error && <div className="pdufa-progress-unavailable" role="alert">
      <strong>LIVE TELEMETRY UNAVAILABLE</strong>
      <p>{error}</p>
      <p>The dashboard will not invent progress or elapsed task times. Open <a href="https://github.com/pdufa/pdufa-command-center/actions" target="_blank" rel="noopener noreferrer">GitHub Actions ↗</a> for the source record.</p>
    </div>}
    {!report && !error && <div className="pdufa-progress-unavailable">Connecting to GitHub run telemetry…</div>}
    {report && !run && <div className="pdufa-progress-unavailable">No execution reported for this workflow. Change the selector or start a scan to see real progress.</div>}
    {run && <>
      <div className="pdufa-progress-runline">
        <span className={"pdufa-state pdufa-state-" + overallStatus} aria-live="polite">
          {iconFor(overallStatus)} {labelFor(overallStatus)}
        </span>
        <strong>{run.title}</strong>
        <span className="pdufa-run-meta">#{run.id} · Attempt {run.attempt}</span>
        <a href={run.url} target="_blank" rel="noopener noreferrer">View exact GitHub run ↗</a>
      </div>
      <div className="pdufa-progress-hero">
        <div className="pdufa-progress-gauge">
          <div className="pdufa-gauge-circle" role="img"
               aria-label={data.pct === null ? "Percent unavailable" : data.pct + " percent of reported GitHub jobs finished"}
               style={{ "--meter": (data.pct ?? 0) + "%" } as React.CSSProperties}>
            <div className="pdufa-gauge-middle">
              <b>{data.pct === null ? "—" : data.pct + "%"}</b>
              <small>GitHub jobs finished</small>
            </div>
          </div>
          <div className="pdufa-gauge-bar"><span style={{ width: (data.pct ?? 0) + "%" }} /></div>
          <p><strong>{data.doneJobs}</strong> of <strong>{data.knownJobs}</strong> reported jobs finished</p>
          <p>{data.doneSteps} of {data.totalSteps} reported steps finished · {jobs.filter(j => j.status === "running").length} jobs running</p>
          <small>Exact fraction of currently reported jobs finished; GitHub can add jobs as a workflow advances. Includes skipped/failed jobs as finished, not successful. Does not measure research evidence approval.</small>
        </div>
        <div className="pdufa-current-task">
          <div className="pdufa-current-label">CURRENT TASK</div>
          <div className="pdufa-current-stage">{task.count ? currentStage : overallStatus === "success" ? "Run finished" :
            overallStatus === "failure" ? "Run stopped with a failure" :
            overallStatus === "queued" ? "Waiting for GitHub runner" : "No task currently reported"}</div>
          <div className="pdufa-current-name">{task.first?.name || (overallStatus === "running" ? "Waiting for job-level telemetry" : run.name)}</div>
          <div className="pdufa-current-step">
            <span className={task.currentStep ? "pdufa-step-working" : "pdufa-step-wait"}>
              {task.currentStep ? "● RUNNING STEP" : "STEP STATUS"}
            </span>
            <strong>{task.currentStep?.name || (task.first ? "No individual step reported as running" :
              overallStatus === "success" ? "All reported jobs finished" :
              overallStatus === "failure" ? "Review failed jobs below" : "Awaiting live step telemetry")}</strong>
          </div>
          {task.count > 1 && <p className="pdufa-concurrent">+ {task.count - 1} additional jobs currently running; see the task checklist below.</p>}
          <div className="pdufa-time-block" aria-label="Time on task">
            <h4>TIME ON TASK</h4>
            <div className="pdufa-time-grid">
              <div><small>Run elapsed</small><strong>{duration(run.startedAt, run.completedAt, clock)}</strong></div>
              <div><small>Current job time</small><strong>{task.first ? currentJobDuration : "—"}</strong></div>
              <div><small>Current step time</small><strong>{task.currentStep ? currentStepDuration : "—"}</strong></div>
              <div><small>Started (Pacific)</small><strong>{when(run.startedAt)}</strong></div>
            </div>
            <p>No estimated finish time is shown without a validated duration model.</p>
          </div>
        </div>
      </div>
      {overnight ? <>
        <h4 className="pdufa-progress-subheading">LIVE STAGE FLOW</h4>
        <div className="pdufa-stage-flow" aria-label="POOL, Pipeline, Phase 3 results, report, sources, scoring and final stages">
          {stageRows.map((row, i) => <div className="pdufa-stage-cell" key={row.key}>
            <div className={"pdufa-stage-card pdufa-stage-" + row.status}>
              <span className="pdufa-stage-icon">{iconFor(row.status)}</span>
              <strong>{row.label}</strong>
              <small>{row.mini}</small>
              <span className="pdufa-stage-state">{row.jobs.length ?
                labelFor(row.status) + " · " + row.jobs.filter(j => TERMINAL.has(j.status)).length + "/" + row.jobs.length + " jobs"
                : "Not yet reported"}</span>
            </div>
            {i < stageRows.length - 1 && <span className="pdufa-stage-arrow" aria-hidden="true">›</span>}
          </div>)}
        </div>
      </> : <p className="pdufa-progress-note">Workflow-specific jobs are listed below. POOL → PIPELINE → Phase 3 results flow appears for current clinical and overnight runs.</p>}
      <div className="pdufa-progress-footline">
        <span>Last fetched: {when(observed)}</span>
        <span>Job/step state: GitHub Actions</span>
        <span>Source verification and trading eligibility are separate checks.</span>
      </div>
      <div className="pdufa-progress-tasks">
        <div className="pdufa-progress-taskhead">
          <h4>LIVE TASK CHECKLIST</h4>
          <span>{data.doneJobs}/{data.knownJobs} jobs finished · expand a job to inspect its actual steps and timestamps</span>
        </div>
        {jobs.length === 0 ? <p>No jobs have been reported by GitHub yet.</p> :
          jobs.map(job => {
            const ended = job.steps.filter(s => TERMINAL.has(s.status)).length;
            const percent = job.steps.length ? Math.round(ended / job.steps.length * 100) : null;
            return <details key={job.id + "-" + job.name} className={"pdufa-task-row pdufa-task-" + job.status}
                            open={job.status === "running" ? true : undefined}>
              <summary>
                <span className={"pdufa-task-icon pdufa-state-" + job.status}>{iconFor(job.status)}</span>
                <span className="pdufa-task-title">{job.name}</span>
                <span className="pdufa-task-count">{percent == null ? "No steps yet" : percent + "% of " + job.steps.length + " reported steps"}</span>
                <span className={"pdufa-state pdufa-state-" + job.status}>{labelFor(job.status)}</span>
              </summary>
              <div className="pdufa-job-time">Started: {when(job.startedAt)} · Time: {duration(job.startedAt, job.completedAt, clock)}</div>
              {job.steps.length ? <ol className="pdufa-step-list">{job.steps.map((step, index) =>
                <li key={job.id + "-step-" + step.number + "-" + index}>
                  <span className={"pdufa-task-icon pdufa-state-" + step.status}>{iconFor(step.status)}</span>
                  <div className="pdufa-step-info"><b>{step.name}</b>
                    <small>{labelFor(step.status)} · Started {when(step.startedAt)} ·
                      {step.status === "running" ? " Time on step " + duration(step.startedAt, null, clock) :
                       step.startedAt ? " Duration " + duration(step.startedAt, step.completedAt, clock) : " Duration unavailable"}</small>
                  </div>
                </li>)}</ol> : <p className="subtle">GitHub has not supplied individual steps for this job.</p>}
            </details>;
          })}
      </div>
    </>}
  </section>;
}
