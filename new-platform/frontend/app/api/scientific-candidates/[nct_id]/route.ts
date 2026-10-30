import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { object } from "../../../../lib/scientific-candidates";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
const headers = { "Cache-Control": "private, no-store" };

export async function GET(req: NextRequest, context: { params: Promise<{ nct_id: string }> }) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers });
  }
  const { nct_id } = await context.params;
  if (!/^NCT[0-9]{8}$/.test(nct_id)) return NextResponse.json({ error: "An exact NCT identifier is required" }, { status: 422, headers });
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) return NextResponse.json({ error: "Scientific evidence backend is not configured" }, { status: 503, headers });
  try {
    const response = await fetch(base + "/api/scientific-candidates/" + nct_id, {
      headers: { "x-pdufa-internal-key": key }, cache: "no-store", signal: AbortSignal.timeout(25000),
    });
    if (response.status === 404) return NextResponse.json({ error: "No persisted dossier for this candidate" }, { status: 404, headers });
    if (!response.ok) throw new Error("Scientific dossier unavailable");
    const data: unknown = await response.json();
    if (!object(data)) throw new Error("Invalid dossier");
    return NextResponse.json(data, { headers });
  } catch {
    return NextResponse.json({ error: "Scientific candidate dossier unavailable; no evidence inferred" }, { status: 503, headers });
  }
}
