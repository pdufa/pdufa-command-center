import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { validatePipelinePage } from "../../../../lib/workspace-pages";
import { fetchReadOnlyWithWarmRetry } from "../../../../lib/read-only-warm-retry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

/** Authenticated proxy for bounded pipeline pages. No browser-visible backend key. */
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !/^https:\/\//.test(base) || !key) {
    return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  }

  const offsetText = req.nextUrl.searchParams.get("offset") ?? "0";
  const limitText = req.nextUrl.searchParams.get("limit") ?? "50";
  const version = req.nextUrl.searchParams.get("version") ?? "";
  const queryText = req.nextUrl.searchParams.get("query") ?? "";
  if (!/^(0|[1-9]\d{0,8})$/.test(offsetText) ||
      !/^(?:[1-9]|[1-9]\d|100)$/.test(limitText) ||
      (version !== "" && !/^[a-f0-9]{64}$/.test(version)) ||
      queryText.length > 100) {
    return NextResponse.json({ error: "Invalid pagination parameters" }, { status: 400 });
  }
  const query = new URLSearchParams({ offset: offsetText, limit: limitText });
  if (version) query.set("version", version);
  if (queryText.trim()) query.set("query", queryText.trim());
  try {
    const response = await fetchReadOnlyWithWarmRetry(base + "/api/workspace/page?" + query.toString(), {
      headers: { "x-pdufa-internal-key": key },
      cache: "no-store",
      signal: AbortSignal.timeout(45000),
    });
    if (response.status === 409) {
      return NextResponse.json({ error: "Workspace changed; restart pagination" },
        { status: 409, headers: { "Cache-Control": "private, no-store" } });
    }
    if (!response.ok) {
      return NextResponse.json({ error: "Pipeline page unavailable" },
        { status: 503, headers: { "Cache-Control": "private, no-store" } });
    }
    const page = validatePipelinePage(await response.json(), Number(offsetText), Number(limitText), version || undefined);
    const headers: Record<string,string> = { "Cache-Control": "private, no-store" };
    const serverTiming = response.headers.get("server-timing");
    // Preserve backend processing metrics for browser network diagnostics.
    if (serverTiming && /^workspace_page;dur=\d+(?:\.\d+)?$/.test(serverTiming)) {
      headers["Server-Timing"] = serverTiming;
    }
    return NextResponse.json(page, { headers });
  } catch {
    return NextResponse.json({ error: "Pipeline page unavailable" },
      { status: 503, headers: { "Cache-Control": "private, no-store" } });
  }
}
