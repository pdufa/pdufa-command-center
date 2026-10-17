import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function proxy(req: NextRequest, method: "GET" | "POST") {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const origin = req.headers.get("origin");
  if (method === "POST" && origin && origin !== req.nextUrl.origin) {
    return NextResponse.json({ error: "Origin not allowed" }, { status: 403 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  }
  try {
    const input = method === "POST" ? await req.json().catch(() => ({})) : {};
    const response = await fetch(base + "/api/pipeline-full-records" + (method === "POST" && input.refresh === true ? "?refresh=true" : ""), {
      method, headers: { "x-pdufa-internal-key": key }, cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status, headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Full-record download service is temporarily unavailable" }, { status: 503 });
  }
}

export const GET = (req: NextRequest) => proxy(req, "GET");
export const POST = (req: NextRequest) => proxy(req, "POST");
