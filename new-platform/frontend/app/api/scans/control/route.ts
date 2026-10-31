import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

// Operator-triggered bridge to the EXISTING GitHub Actions collectors.
// This staging application must not create a second nightly clock or write source data.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const REPO = "pdufa/pdufa-command-center";
const CONTROL = "pdufa-scan-control.yml";
const OVERNIGHT = "pdufa-overnight-sequential.yml";
const GMAIL = "pdufa-gmail-section-audit.yml";
const GMAIL_REPAIR = "pdufa-gmail-repair-cleanup.yml";
const GMAIL_SECTIONS = ["ALL", "INBOX", "SENT_MAIL", "PDUFA", "SCAN_START", "SCAN_END", "SCAN_ERROR", "DAILY_REPORT", "WEEKLY_REPORT"] as const;
const ACTIONS = ["VERIFY_ALL", "REVERIFY_PARTIAL", "RESCAN_ALL"] as const;
const SCANS = ["ALL", "PIPELINE", "PHASE3_RESULTS"] as const;
const ACTIVE = new Set(["queued", "in_progress", "waiting", "requested", "pending"]);
const WORKFLOW_URL = "https://github.com/" + REPO + "/actions/workflows/" + CONTROL;
type Run = { id: number; status: string; conclusion: string | null; created_at: string; html_url: string };

function json(payload: unknown, status = 200) {
  return NextResponse.json(payload, { status, headers: { "Cache-Control": "private, no-store" } });
}

function authenticated(req: NextRequest): boolean {
  return authConfigured() && hasSession(req.cookies.get(COOKIE_NAME)?.value);
}

async function github(path: string, init: RequestInit = {}) {
  const token = process.env.PDUFA_GITHUB_TOKEN?.trim();
  const response = await fetch("https://api.github.com/repos/" + REPO + path, {
    ...init,
    headers: {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "pdufa-new-platform-operator-scans",
      ...(token ? { Authorization: "Bearer " + token } : {}),
      ...(init.headers || {}),
    },
    cache: "no-store",
    signal: AbortSignal.timeout(12000),
  });
  return response;
}

async function recent(workflow: string): Promise<Run[]> {
  const response = await github("/actions/workflows/" + workflow + "/runs?branch=main&per_page=10");
  if (!response.ok) throw new Error("GitHub scan status unavailable");
  const payload: unknown = await response.json();
  if (!payload || typeof payload !== "object" || !("workflow_runs" in payload)) {
    throw new Error("GitHub scan status malformed");
  }
  const data = payload as { workflow_runs?: unknown };
  if (!Array.isArray(data.workflow_runs)) throw new Error("GitHub scan runs malformed");
  return data.workflow_runs.slice(0, 10).filter((x): x is Run =>
    Boolean(x) && typeof x.id === "number" && typeof x.status === "string" &&
    typeof x.html_url === "string" && x.html_url.startsWith("https://github.com/" + REPO + "/actions/runs/")
  ).map(x => ({
    id: x.id, status: x.status, conclusion: x.conclusion || null,
    created_at: String(x.created_at || ""), html_url: x.html_url,
  }));
}

export async function GET(req: NextRequest) {
  if (!authenticated(req)) return json({ error: "Authentication required" }, 401);
  try {
    const [manual, overnight, gmail, gmailRepair] = await Promise.all([recent(CONTROL), recent(OVERNIGHT), recent(GMAIL), recent(GMAIL_REPAIR)]);
    return json({
      dispatchEnabled: Boolean(process.env.PDUFA_GITHUB_TOKEN?.trim()),
      manual: manual.slice(0, 5), overnight: overnight.slice(0, 5), gmail: gmail.slice(0, 5), gmailRepair: gmailRepair.slice(0, 5),
      workflowUrl: WORKFLOW_URL,
    });
  } catch {
    return json({
      error: "GitHub Actions status unavailable; no scan was started",
      dispatchEnabled: Boolean(process.env.PDUFA_GITHUB_TOKEN?.trim()),
      workflowUrl: WORKFLOW_URL,
    }, 503);
  }
}

export async function POST(req: NextRequest) {
  if (!authenticated(req)) return json({ error: "Authentication required" }, 401);
  // A same-origin, password-session POST is required; never expose the Actions token to the browser.
  if (req.headers.get("origin") !== req.nextUrl.origin) return json({ error: "Origin not allowed" }, 403);
  if (!process.env.PDUFA_GITHUB_TOKEN?.trim()) {
    return json({ error: "GitHub scan-control token is not configured on the new dashboard" }, 503);
  }
  if (!req.headers.get("content-type")?.toLowerCase().startsWith("application/json")) {
    return json({ error: "JSON request required" }, 415);
  }
  if (Number(req.headers.get("content-length") || "0") > 2048) return json({ error: "Request too large" }, 413);
  const input: unknown = await req.json().catch(() => null);
  if (!input || typeof input !== "object" || Array.isArray(input)) return json({ error: "Invalid scan request" }, 422);
  const { action, scan, section } = input as Record<string, unknown>;
  const isGmail = (action === "GMAIL_AUDIT" || action === "GMAIL_REPAIR_CLEANUP") && typeof section === "string" &&
    GMAIL_SECTIONS.includes(section as typeof GMAIL_SECTIONS[number]);
  const isScan = typeof action === "string" && ACTIONS.includes(action as typeof ACTIONS[number]) &&
    typeof scan === "string" && SCANS.includes(scan as typeof SCANS[number]);
  if (!isGmail && !isScan) {
    return json({ error: "Unrecognized scan action or stage" }, 422);
  }
  try {
    // Fail closed on uncertainty: do not create a second overnight/interactive chain.
    const [manual, overnight, gmail, gmailRepair] = await Promise.all([recent(CONTROL), recent(OVERNIGHT), recent(GMAIL), recent(GMAIL_REPAIR)]);
    const active = [...manual, ...overnight, ...gmail, ...gmailRepair].find(run => ACTIVE.has(run.status));
    if (active) {
      return json({
        error: "An existing scan is queued or running; another scan was not started",
        activeRunUrl: active.html_url,
      }, 409);
    }
    const workflow = action === "GMAIL_REPAIR_CLEANUP" ? GMAIL_REPAIR : isGmail ? GMAIL : CONTROL;
    const inputs = isGmail ? { section } : { action, scan };
    const response = await github("/actions/workflows/" + workflow + "/dispatches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ref: "main", inputs }),
    });
    if (response.status !== 204) {
      return json({ error: "GitHub did not accept the scan request. Verify token Actions permissions." }, 502);
    }
    return json({
      accepted: true, action, scan: isScan ? scan : undefined, section: isGmail ? section : undefined,
      workflowUrl: isGmail ? "https://github.com/" + REPO + "/actions/workflows/" + workflow : WORKFLOW_URL,
      message: action === "GMAIL_REPAIR_CLEANUP" ? "Safe-repair and resolved-notice cleanup requested. Only the exact failed GitHub run successfully retried may have its failure notice moved to Trash; unresolved messages remain. Review job summary." :
        isGmail ? "Read-only Gmail header audit accepted, not yet completed. Review the GitHub run summary and retained aggregate artifact." :
        "Scan request accepted by GitHub Actions, not yet completed. Review the run and published evidence before relying on its output.",
    }, 202);
  } catch {
    return json({ error: "Could not verify existing scan activity or dispatch; no confirmed new scan" }, 503);
  }
}
