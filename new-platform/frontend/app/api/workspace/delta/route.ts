import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !/^https:\/\//.test(base) || !key) {
    return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  }
  const since = req.nextUrl.searchParams.get("since") || "";
  if (!/^[a-f0-9]{64}$/.test(since)) {
    return NextResponse.json({ error: "A valid workspace version is required" }, { status: 400 });
  }
  try {
    const response = await fetch(base + "/api/workspace/delta?since=" + since, {
      headers: { "x-pdufa-internal-key": key },
      cache: "no-store",
      signal: AbortSignal.timeout(45000),
    });
    if (!response.ok) {
      return NextResponse.json({ error: "Workspace delta unavailable; use full refresh" },
        { status: 503, headers: { "Cache-Control": "private, no-store" } });
    }
    const data = await response.json();
    if (typeof data.version !== "string" || typeof data.reset !== "boolean") {
      throw new Error("Malformed delta response");
    }
    return NextResponse.json(data, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Workspace delta unavailable; use full refresh" },
      { status: 503, headers: { "Cache-Control": "private, no-store" } });
  }
}
