import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const repo = "pdufa/pdufa-command-center";
const workflow = "pdufa-daily-research-safety.yml";
const artifactName = "historical-drugsatfda-ingestion-status";

export async function GET() {
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
  const unavailable = (reason: string) => NextResponse.json({
    status: "UNAVAILABLE", reason, candidate_count: null,
    historical_outcomes_independently_verified: false,
    prediction_model_validated: false, model_ready: false,
  }, { status: 200, headers: { "Cache-Control": "no-store" } });
  if (!token) return unavailable("GitHub artifact access not configured");
  const headers = { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28" };
  try {
    const runs = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${workflow}/runs?per_page=10&status=completed`, { headers, cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (!runs.ok) return unavailable("Historical workflow run unavailable");
    const body = await runs.json() as { workflow_runs?: Array<{ id: number; conclusion: string; created_at: string }> };
    const run = body.workflow_runs?.find(r => r.conclusion === "success");
    if (!run) return unavailable("No successful historical workflow run");
    const artifacts = await fetch(`https://api.github.com/repos/${repo}/actions/runs/${run.id}/artifacts?per_page=100`, { headers, cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (!artifacts.ok) return unavailable("Historical artifact index unavailable");
    const data = await artifacts.json() as { artifacts?: Array<{ name: string; expired: boolean; html_url: string }> };
    const artifact = data.artifacts?.find(a => a.name === artifactName && !a.expired);
    if (!artifact) return unavailable("Historical ingestion status artifact not published");
    return NextResponse.json({
      status: "ARTIFACT_AVAILABLE", run_id: run.id, run_created_at: run.created_at,
      artifact_url: artifact.html_url, candidate_count: null,
      historical_outcomes_independently_verified: false,
      prediction_model_validated: false, model_ready: false,
      note: "Artifact exists; contents have not been independently read or verified by this endpoint.",
    }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return unavailable("Historical workflow status could not be retrieved");
  }
}
