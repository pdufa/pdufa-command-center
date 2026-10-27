import { inflateRawSync } from "node:zlib";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const repo = "pdufa/pdufa-command-center";
const workflow = "pdufa-daily-research-safety.yml";
const artifactName = "historical-drugsatfda-ingestion-status";

type IngestionReport = {
  status?: string; candidate_count?: number | null;
  with_source_documents?: number | null; without_source_documents?: number | null;
  with_action_descriptions?: number | null; submission_types?: Record<string, number>;
  evidence_coverage_by_submission_type?: Record<string, unknown>;
  readiness?: string;
};
function readStatusZip(buffer: Buffer): IngestionReport {
  if (buffer.length > 2_000_000) throw new Error("ZIP too large");
  // Locate the ZIP central directory and require the exact expected JSON filename.
  let end = -1;
  for (let i = buffer.length - 22; i >= Math.max(0, buffer.length - 65557); i--) {
    if (buffer.readUInt32LE(i) === 0x06054b50) { end = i; break; }
  }
  if (end < 0) throw new Error("ZIP directory missing");
  const count = buffer.readUInt16LE(end + 10);
  let pos = buffer.readUInt32LE(end + 16);
  for (let n = 0; n < Math.min(count, 20); n++) {
    if (pos + 46 > buffer.length || buffer.readUInt32LE(pos) !== 0x02014b50) throw new Error("Invalid ZIP entry");
    const method = buffer.readUInt16LE(pos + 10);
    const compressed = buffer.readUInt32LE(pos + 20);
    const uncompressed = buffer.readUInt32LE(pos + 24);
    const nameLength = buffer.readUInt16LE(pos + 28);
    const extraLength = buffer.readUInt16LE(pos + 30);
    const commentLength = buffer.readUInt16LE(pos + 32);
    const offset = buffer.readUInt32LE(pos + 42);
    const name = buffer.toString("utf8", pos + 46, pos + 46 + nameLength);
    pos += 46 + nameLength + extraLength + commentLength;
    if (name !== "historical_drugsatfda_ingestion_status.json") continue;
    if (uncompressed > 100_000 || compressed > 100_000 || offset + 30 > buffer.length || buffer.readUInt32LE(offset) !== 0x04034b50) throw new Error("Unsafe ZIP entry");
    const start = offset + 30 + buffer.readUInt16LE(offset + 26) + buffer.readUInt16LE(offset + 28);
    if (start + compressed > buffer.length) throw new Error("Truncated ZIP");
    const payload = buffer.subarray(start, start + compressed);
    const raw = method === 0 ? payload : method === 8 ? inflateRawSync(payload, { maxOutputLength: 100_000 }) : null;
    if (!raw || raw.length !== uncompressed) throw new Error("Invalid ZIP payload");
    const parsed: unknown = JSON.parse(raw.toString("utf8"));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Invalid status JSON");
    return parsed as IngestionReport;
  }
  throw new Error("Status JSON not in artifact");
}

export async function GET() {
  const token = process.env.PDUFA_GITHUB_TOKEN || process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
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
    const successfulRuns = body.workflow_runs?.filter(r => r.conclusion === "success") ?? [];
    if (!successfulRuns.length) return unavailable("No successful historical workflow run");
    let selected: { run: (typeof successfulRuns)[number]; artifact: { name: string; expired: boolean; html_url: string } } | null = null;
    for (const run of successfulRuns.slice(0, 5)) {
      const response = await fetch(`https://api.github.com/repos/${repo}/actions/runs/${run.id}/artifacts?per_page=100`, { headers, cache: "no-store", signal: AbortSignal.timeout(8000) });
      if (!response.ok) continue;
      const data = await response.json() as { artifacts?: Array<{ name: string; expired: boolean; html_url: string; id: number }> };
      const artifact = data.artifacts?.find(a => a.name === artifactName && !a.expired);
      if (artifact) { selected = { run, artifact }; break; }
    }
    if (!selected) return unavailable("Historical ingestion status artifact not published in the last five successful runs");
    const { run, artifact } = selected;
    const archive = await fetch(`https://api.github.com/repos/${repo}/actions/artifacts/${artifact.id}/zip`, {
      headers, redirect: "manual", cache: "no-store", signal: AbortSignal.timeout(8000),
    });
    const signedUrl = archive.headers.get("location");
    if (archive.status !== 302 || !signedUrl || !signedUrl.startsWith("https://")) return unavailable("FDA status artifact download unavailable");
    const download = await fetch(signedUrl, { cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (!download.ok || Number(download.headers.get("content-length") || 0) > 2_000_000) return unavailable("FDA status artifact could not be downloaded");
    const report = readStatusZip(Buffer.from(await download.arrayBuffer()));
    if (report.status !== "SUCCEEDED") return unavailable("Latest available FDA ingestion did not succeed");
    return NextResponse.json({
      status: "INGESTION_REPORTED", run_id: run.id, run_created_at: run.created_at,
      artifact_url: artifact.html_url,
      candidate_count: typeof report.candidate_count === "number" ? report.candidate_count : null,
      with_source_documents: typeof report.with_source_documents === "number" ? report.with_source_documents : null,
      without_source_documents: typeof report.without_source_documents === "number" ? report.without_source_documents : null,
      with_action_descriptions: typeof report.with_action_descriptions === "number" ? report.with_action_descriptions : null,
      submission_types: report.submission_types ?? null,
      evidence_coverage_by_submission_type: report.evidence_coverage_by_submission_type ?? null,
      readiness: report.readiness ?? "SOURCE_REVIEW_REQUIRED",
      historical_outcomes_independently_verified: false,
      prediction_model_validated: false, model_ready: false,
      note: "Staged submission counts are not independently verified FDA PASS/FAIL decisions.",
    }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return unavailable("Historical workflow status could not be retrieved");
  }
}
