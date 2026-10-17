import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

// Read-only Github Actions execution telemetry. Never dispatches a workflow,
// invents a time estimate, or infers source-evidence completeness.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const REPO = "pdufa/pdufa-command-center";
const GH = "https://api.github.com/repos/" + REPO;
const WORKFLOWS = {
  AUTO: null,
  OVERNIGHT: "pdufa-overnight-sequential.yml",
  PIPELINE_GEM_JR: "pdufa-nightly-clinical.yml",
  SOURCES: "pdufa-nightly-missing-sources.yml",
  SCAN_CONTROL: "pdufa-scan-control.yml",
  GEM: "gem-research-quality.yml",
  GMAIL_AUDIT: "pdufa-gmail-section-audit.yml",
  GMAIL_REPAIR: "pdufa-gmail-repair-cleanup.yml",
} as const;
type Kind = keyof typeof WORKFLOWS;
const KNOWN_PATHS = new Set(
  (Object.values(WORKFLOWS).filter(path => path !== null) as string[]),
);
type RawRun = {
  id?: unknown; name?: unknown; display_title?: unknown; status?: unknown; conclusion?: unknown;
  created_at?: unknown; run_started_at?: unknown; updated_at?: unknown; html_url?: unknown;
  event?: unknown; path?: unknown; run_attempt?: unknown;
};
type RawStep = {
  name?: unknown; status?: unknown; conclusion?: unknown; number?: unknown;
  started_at?: unknown; completed_at?: unknown;
};
type RawJob = {
  id?: unknown; name?: unknown; status?: unknown; conclusion?: unknown;
  started_at?: unknown; completed_at?: unknown; steps?: unknown;
};
const text = (value: unknown) => typeof value === "string" ? value : null;
const at = (value: unknown) => {
  const s = text(value);
  return s && Number.isFinite(Date.parse(s)) ? s : null;
};
const state = (status: unknown, conclusion: unknown) => {
  if (status === "completed") {
    if (conclusion === "success") return "success";
    if (conclusion === "skipped") return "skipped";
    if (conclusion === "cancelled") return "cancelled";
    if (conclusion === "failure" || conclusion === "timed_out" || conclusion === "action_required") return "failure";
    return "completed";
  }
  return status === "in_progress" ? "running" :
    status === "queued" || status === "pending" || status === "waiting" || status === "requested"
      ? "queued" : "unknown";
};
const active = (r: RawRun) => ["queued", "pending", "in_progress", "waiting", "requested"].includes(text(r.status) || "");
const validRun = (r: RawRun): r is RawRun & { id: number } =>
  typeof r?.id === "number" && Number.isSafeInteger(r.id) &&
  text(r.html_url) === "https://github.com/" + REPO + "/actions/runs/" + r.id;
const normalizedPath = (path: unknown) => {
  const value = text(path) || "";
  return value.split("/").pop() || "";
};
async function fromGitHub(path: string): Promise<unknown> {
  const token = process.env.PDUFA_GITHUB_TOKEN?.trim();
  const res = await fetch(GH + path, {
    headers: {
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "pdufa-live-scans-progress",
      ...(token ? { "Authorization": "Bearer " + token } : {}),
    },
    // Server-cache shared telemetry to conserve GitHub's unauthenticated limit.
    // This does not cache the authenticated response to our dashboard visitors.
    next: { revalidate: 45 },
    signal: AbortSignal.timeout(12500),
  });
  if (!res.ok) throw new Error("GitHub telemetry HTTP " + res.status);
  return res.json();
}
function cleanJob(raw: RawJob) {
  const steps = Array.isArray(raw.steps) ? raw.steps : [];
  const name = text(raw.name) || "Unnamed job";
  return {
    id: typeof raw.id === "number" ? raw.id : 0,
    name, status: state(raw.status, raw.conclusion),
    startedAt: at(raw.started_at), completedAt: at(raw.completed_at),
    steps: steps.slice(0, 100).map((s: RawStep) => ({
      name: text(s.name) || "Unnamed step",
      number: typeof s.number === "number" ? s.number : 0,
      status: state(s.status, s.conclusion),
      startedAt: at(s.started_at), completedAt: at(s.completed_at),
    })),
  };
}
const response = (obj: unknown, status = 200) =>
  NextResponse.json(obj, { status, headers: { "Cache-Control": "private, no-store" } });

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return response({ error: "Authentication required" }, 401);
  }
  const kindParam = (req.nextUrl.searchParams.get("kind") || "AUTO").toUpperCase();
  if (!(kindParam in WORKFLOWS)) return response({ error: "Unsupported progress source" }, 422);
  const kind = kindParam as Kind;
  try {
    let runs: RawRun[];
    if (kind === "AUTO") {
      // One repository-level request discovers current active workflows, not
      // the latest CI push by mistake. Fall back to overnight run history if
      // 100 recent GitHub runs did not include any tracked collector.
      const listing = await fromGitHub("/actions/runs?branch=main&per_page=100") as { workflow_runs?: unknown };
      if (!Array.isArray(listing.workflow_runs)) throw new Error("Malformed run listing");
      runs = (listing.workflow_runs as RawRun[]).filter(r =>
        KNOWN_PATHS.has(normalizedPath(r.path)) &&
        (r.event === "workflow_dispatch" || r.event === "schedule"));
      if (!runs.length) {
        const history = await fromGitHub(
          "/actions/workflows/pdufa-overnight-sequential.yml/runs?branch=main&per_page=4"
        ) as {workflow_runs?: unknown};
        runs = Array.isArray(history.workflow_runs) ? history.workflow_runs as RawRun[] : [];
      }
    } else {
      const listing = await fromGitHub(
        "/actions/workflows/" + WORKFLOWS[kind] + "/runs?branch=main&per_page=10"
      ) as { workflow_runs?: unknown };
      if (!Array.isArray(listing.workflow_runs)) throw new Error("Malformed run listing");
      runs = listing.workflow_runs as RawRun[];
      // A test/validate-only push is not actual collection. Manual runs get
      // priority, while unconfirmed scopes are not labeled "scanning".
      if (kind === "OVERNIGHT") {
        runs = runs.filter(r => r.event === "workflow_dispatch");
      }
    }
    const valid = runs.filter(validRun).sort((a, b) =>
      String(b.created_at || "").localeCompare(String(a.created_at || "")));
    const picked = valid.find(active) || valid[0];
    if (!picked) return response({
      source: kind, status: "NO_RUN", asOf: new Date().toISOString(),
      error: "No matching run has been reported by GitHub",
    });
    const jobListing = await fromGitHub(
      "/actions/runs/" + picked.id + "/jobs?per_page=100"
    ) as { jobs?: unknown; total_count?: unknown };
    if (!Array.isArray(jobListing.jobs)) throw new Error("Malformed job listing");
    const jobs = (jobListing.jobs as RawJob[]).map(cleanJob);
    const truncated = typeof jobListing.total_count === "number" &&
      jobListing.total_count > jobs.length;
    return response({
      source: kind,
      asOf: new Date().toISOString(),
      run: {
        id: picked.id, name: text(picked.name) || "GitHub workflow",
        title: text(picked.display_title) || text(picked.name) || "GitHub workflow",
        workflow: normalizedPath(picked.path),
        status: state(picked.status, picked.conclusion),
        startedAt: at(picked.run_started_at) || at(picked.created_at),
        createdAt: at(picked.created_at),
        updatedAt: at(picked.updated_at),
        completedAt: picked.status === "completed" ? at(picked.updated_at) : null,
        url: text(picked.html_url), event: text(picked.event),
        attempt: typeof picked.run_attempt === "number" ? picked.run_attempt : 1,
      },
      jobs, totalJobs: typeof jobListing.total_count === "number" ? jobListing.total_count : jobs.length,
      truncated,
      note: "Percentages count observed GitHub workflow jobs/steps, not trials, evidence verification, source success, or time remaining.",
    });
  } catch {
    // Honest failure, never render stale invented execution state.
    return response({
      source: kind, status: "UNAVAILABLE", asOf: new Date().toISOString(),
      error: "Live GitHub job/step telemetry unavailable. Check the GitHub Actions run page. A GitHub token may be required or the API may be rate-limited.",
    }, 503);
  }
}
