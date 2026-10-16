import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function allowed(req: NextRequest) {
  return authConfigured() && hasSession(req.cookies.get(COOKIE_NAME)?.value);
}
async function upstream(req: NextRequest, method: "GET" | "PUT") {
  if (!allowed(req)) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (method === "PUT" && req.headers.get("origin") && req.headers.get("origin") !== req.nextUrl.origin) {
    return NextResponse.json({ error: "Invalid origin" }, { status: 403 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !/^https:\/\//.test(base) || !key) return NextResponse.json({ error: "Backend not configured" }, { status: 503 });
  let body: string | undefined;
  if (method === "PUT") {
    const data = await req.json().catch(() => null);
    if (!data || !Array.isArray(data.watch) || !Array.isArray(data.trade)
       || data.watch.length > 500 || data.trade.length > 500 || !Number.isSafeInteger(data.version)) {
      return NextResponse.json({ error: "Invalid Watch/Trade selection" }, { status: 422 });
    }
    body = JSON.stringify(data);
  }
  try {
    const response = await fetch(base + "/api/watch-trade", {
      method, cache: "no-store",
      headers: { "x-pdufa-internal-key": key, "content-type": "application/json" },
      body, signal: AbortSignal.timeout(15000)
    });
    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status, headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Watch/Trade storage temporarily unreachable" }, { status: 503 });
  }
}
export async function GET(req: NextRequest) { return upstream(req, "GET"); }
export async function PUT(req: NextRequest) { return upstream(req, "PUT"); }
