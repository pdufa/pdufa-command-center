import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function handle(
  req: NextRequest,
  context: { params: Promise<{ programId: string }> },
  method: "GET" | "PUT"
) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Sign in to the PDUFA dashboard to edit markers" }, { status: 401 });
  }
  const { programId } = await context.params;
  if (!/^PDUFA-[0-9]{6,}$/.test(programId)) {
    return NextResponse.json({ error: "Invalid permanent Program ID" }, { status: 422 });
  }
  if (method === "PUT" && req.headers.get("origin") && req.headers.get("origin") !== req.nextUrl.origin) {
    return NextResponse.json({ error: "Invalid request origin" }, { status: 403 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !base.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Persistent backend unavailable" }, { status: 503 });
  }
  let body: string | undefined;
  if (method === "PUT") {
    const obj: unknown = await req.json().catch(() => null);
    if (!obj || typeof obj !== "object" ||
      !("version" in obj) || !Number.isSafeInteger(obj.version) ||
      !("markers" in obj) || !Array.isArray(obj.markers) || obj.markers.length > 40) {
      return NextResponse.json({ error: "Invalid custom markers" }, { status: 422 });
    }
    body = JSON.stringify(obj);
    if (body.length > 32000) return NextResponse.json({ error: "Overlay too large" }, { status: 413 });
  }
  try {
    const response = await fetch(base + "/api/fda-overlay/" + encodeURIComponent(programId), {
      method, body,
      headers: { "x-pdufa-internal-key": key, "content-type": "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, {
      status: response.status,
      headers: { "Cache-Control": "private, no-store" },
    });
  } catch {
    return NextResponse.json({ error: "FDA marker storage temporarily unavailable" }, { status: 503 });
  }
}
export async function GET(req: NextRequest, context: { params: Promise<{ programId: string }> }) {
  return handle(req, context, "GET");
}
export async function PUT(req: NextRequest, context: { params: Promise<{ programId: string }> }) {
  return handle(req, context, "PUT");
}
