import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(req: NextRequest, context: { params: Promise<{ nct_id: string }> }) {
  const headers = { "Cache-Control": "private, no-store" };
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers });
  const { nct_id } = await context.params;
  if (!/^NCT[0-9]{8}$/.test(nct_id))
    return NextResponse.json({ error: "Invalid NCT identifier" }, { status: 422, headers });
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key)
    return NextResponse.json({ error: "Backend not configured" }, { status: 503, headers });
  try {
    const upstream = await fetch(base + "/api/prediction-events/" + nct_id, {
      headers: { "x-pdufa-internal-key": key, Accept: "text/event-stream" },
      cache: "no-store", signal: AbortSignal.any([req.signal, AbortSignal.timeout(55000)]),
    });
    if (!upstream.ok || !upstream.body)
      return NextResponse.json({ error: "Trial stream unavailable" }, { status: upstream.status === 404 ? 404 : 503, headers });
    return new Response(upstream.body, { headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "private, no-store, no-transform",
      "X-Accel-Buffering": "no",
    } });
  } catch {
    return NextResponse.json({ error: "Trial stream failed" }, { status: 503, headers });
  }
}
