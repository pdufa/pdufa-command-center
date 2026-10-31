import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function checkAuth(req: NextRequest) {
  return authConfigured() && hasSession(req.cookies.get(COOKIE_NAME)?.value);
}

function upstreamUrl(req: NextRequest): string | null {
  const programId = req.nextUrl.searchParams.get("programId") || "";
  const stage = (req.nextUrl.searchParams.get("stage") || "").toUpperCase();
  if (!/^PDUFA-[0-9]{6,}$/.test(programId) || stage !== "PIPELINE") return null;
  const base = process.env.PDUFA_API_BASE_URL;
  if (!base || !base.startsWith("http://backend:") && !base.startsWith("http://localhost:") && !base.startsWith("https://")) return null;
  return base.replace(/\/$/, "") + "/api/program-checklists/" + encodeURIComponent(programId) + "/" + stage;
}

async function relay(req: NextRequest, method: "GET" | "PUT") {
  if (!checkAuth(req)) return NextResponse.json({ error: "Unauthorized or not configured" }, { status: 401 });
  if (method === "PUT") {
    const origin = req.headers.get("origin");
    if (origin && origin !== req.nextUrl.origin) {
      return NextResponse.json({ error: "Origin not allowed" }, { status: 403 });
    }
  }
  const url = upstreamUrl(req);
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!url || !key) return NextResponse.json({ error: "Backend not configured" }, { status: 503 });
  let data: string | undefined;
  if (method === "PUT") {
    data = await req.text();
    if (data.length > 16000) return NextResponse.json({ error: "Payload too large" }, { status: 413 });
  }
  try {
    const upstream = await fetch(url, {
      method, cache: "no-store",
      headers: { "X-PDUFA-Internal-Key": key, ...(data ? { "Content-Type": "application/json" } : {}) },
      body: data,
      signal: AbortSignal.timeout(15000)
    });
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" }
    });
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 502 });
  }
}

export async function GET(req: NextRequest) { return relay(req, "GET"); }
export async function PUT(req: NextRequest) { return relay(req, "PUT"); }
