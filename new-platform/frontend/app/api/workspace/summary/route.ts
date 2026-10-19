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
  try {
    const response = await fetch(base + "/api/workspace/summary", {
      headers: { "x-pdufa-internal-key": key },
      cache: "no-store",
      signal: AbortSignal.timeout(90000),
    });
    if (!response.ok) {
      return NextResponse.json({ error: "Verified summary unavailable" }, { status: 503 });
    }
    const data: unknown = await response.json();
    if (!data || typeof data !== "object") throw new Error("Invalid summary");
    const summary = data as Record<string, unknown>;
    for (const key of ["pipeline", "gemJr", "gem"]) {
      if (!Number.isSafeInteger(summary[key]) || (summary[key] as number) < 0) {
        throw new Error("Invalid count: " + key);
      }
    }
    return NextResponse.json(summary, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Verified summary unavailable" }, { status: 503 });
  }
}
