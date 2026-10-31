import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { clinicalHealth, count, emailHealth, record, savedCheck, scoringHealth, sourceHealth, type HealthCheck } from "../../../lib/site-health";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
const REPO = "https://api.github.com/repos/pdufa/pdufa-command-center";
const DATA = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/";

async function json(url: string, headers?: Record<string, string>, cached = false) {
  try {
    const response = await fetch(url, { headers, signal: AbortSignal.timeout(15000),
      ...(cached ? { next: { revalidate: 60 } } : { cache: "no-store" as const }) });
    return response.ok ? record(await response.json()) : null;
  } catch { return null; }
}

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401,
      headers: { "Cache-Control": "private, no-store" } });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const internalKey = process.env.PDUFA_INTERNAL_API_KEY;
  const backendConfigured = !!base && /^https:\/\//.test(base) && !!internalKey;
  const sha = process.env.VERCEL_GIT_COMMIT_SHA;
  const token = process.env.PDUFA_GITHUB_TOKEN || process.env.GITHUB_TOKEN;
  const headers: Record<string, string> = { Accept: "application/vnd.github+json", "User-Agent": "pdufa-site-health" };
  if (token) headers.Authorization = "Bearer " + token;
  const [backend, lists, clinical, sources, scoring, email, deployment] = await Promise.all([
    backendConfigured ? json(base + "/health") : null,
    backendConfigured ? json(base + "/api/workspace/summary", { "x-pdufa-internal-key": internalKey! }) : null,
    json(DATA + "nightly_scan_report.json", undefined, true),
    json(DATA + "pdufa_source_report.json", undefined, true),
    json(DATA + "nightly_scoring_audit.json", undefined, true),
    json(DATA + "pdufa_mail_count.json", undefined, true),
    sha && /^[a-f0-9]{40}$/i.test(sha) ? json(REPO + "/commits/" + sha + "/status", headers, true) : null,
  ]);
  const checkedAt = new Date().toISOString();
  const now = Date.parse(checkedAt);
  const checks: HealthCheck[] = [];
  const add = (id: string, label: string, state: HealthCheck["state"], summary: string, detail: string) =>
    checks.push({ id, label, state, summary, detail, checkedAt });
  add("website", "Website & sign-in", "good", "Connected", "This authenticated health request reached the website successfully.");
  const statusRows = Array.isArray(deployment?.statuses) ? deployment.statuses.map(record) : [];
  const vercel = statusRows.find(row => row?.context === "Vercel");
  const deployState = vercel?.state;
  add("deployment", "Deployment", deployState === "success" ? "good" :
    ["failure", "error"].includes(String(deployState)) ? "failed" : deployState === "pending" ? "warning" : "unknown",
    deployState === "success" ? "Published successfully" : deployState === "pending" ? "Deploying" : deployState ? "Deployment failed" : "Unverified",
    "GitHub's Vercel status for the exact serving commit" + (sha ? " " + sha.slice(0, 7) : "") + ". It does not verify every page control.");
  const backendValid = backend?.service === "pdufa-new-backend";
  add("backend", "Backend & database", backendValid && backend.storage_ready === true && backend.status === "ok" ? "good" : "failed",
    !backendConfigured ? "Not configured" : !backendValid ? "Unavailable" : backend.storage_ready === true ? "Connected" : "Database unavailable",
    backendValid ? "Backend responded. Persistent storage " + (backend.storage_ready === true ? "is ready." : "is not ready.") : "The configured backend could not be verified. No save or scan was started.");
  const listCounts = lists && count(lists.pipeline);
  add("lists", "POOL source inventory", listCounts ? "good" : "unknown",
    listCounts ? Number(lists.pipeline).toLocaleString("en-US") : "Unverified",
    "Published combined backend records, not the independently qualified post–Phase 3 Pipeline count. No historical stage membership is an eligibility requirement.");
  checks.push(savedCheck("scans", "Clinical scan collection", clinical, now, clinicalHealth));
  checks.push(savedCheck("sources", "Source verification", sources, now, sourceHealth));
  checks.push(savedCheck("scoring", "Scoring data", scoring, now, scoringHealth));
  add("controls", "Restrictions, buttons & popups", "unknown", "Not independently tested",
    "An HTTP success does not prove every control works. Original independent FS/FA restrictions are unchanged by this health display.");
  add("screens", "iPhone & desktop display", "unknown", "Not independently tested",
    "A visual and interaction check on both screen sizes is needed before this check can pass.");
  checks.push(savedCheck("email", "PDUFA email count", email, now, emailHealth));
  return NextResponse.json({ checkedAt, checks }, { headers: { "Cache-Control": "private, no-store" } });
}
