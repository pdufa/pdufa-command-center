import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { isArchiveHealth } from "../../../lib/archive-health";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
const headers = { "Cache-Control": "private, no-store" };

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Archive backend is not configured" }, { status: 503, headers });
  }
  try {
    const response = await fetch(base + "/api/archive-health", {
      headers: { "x-pdufa-internal-key": key }, cache: "no-store", signal: AbortSignal.timeout(25000),
    });
    if (!response.ok) throw new Error("Archive backend unavailable");
    const data: unknown = await response.json();
    if (!isArchiveHealth(data)) throw new Error("Archive report is not verified");
    return NextResponse.json(data, { headers });
  } catch {
    return NextResponse.json({ error: "Archive verification report unavailable; no results inferred" },
      { status: 503, headers });
  }
}
