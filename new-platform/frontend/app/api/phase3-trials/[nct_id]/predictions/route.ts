import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../../lib/auth";
import { NCT_PATTERN } from "../../../../../lib/nct-live-stream";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, context: { params: Promise<{ nct_id: string }> }) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers: { "Cache-Control": "private, no-store" } });
  }
  const { nct_id } = await context.params;
  if (!NCT_PATTERN.test(nct_id)) {
    return NextResponse.json({ error: "Invalid NCT identifier" }, { status: 422, headers: { "Cache-Control": "private, no-store" } });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Prediction backend is not configured" }, { status: 503, headers: { "Cache-Control": "private, no-store" } });
  }
  try {
    const upstream = await fetch(base + "/api/phase3-trials/" + encodeURIComponent(nct_id) + "/predictions", {
      headers: { "X-Pdufa-Internal-Key": key, Accept: "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(25000),
    });
    if (!upstream.ok) {
      return NextResponse.json({ error: "Prediction lookup unavailable", decision: "ABSTAIN", status: "NOT_READY" }, {
        status: [404, 422].includes(upstream.status) ? upstream.status : 503,
        headers: { "Cache-Control": "private, no-store" },
      });
    }
    if (!(upstream.headers.get("content-type") || "").toLowerCase().includes("application/json")) throw new Error("Unexpected response");
    const data: unknown = await upstream.json();
    if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("Invalid prediction response");
    const record = data as Record<string, unknown>;
    if (record.nct_id !== nct_id) throw new Error("Prediction identity mismatch");
    // READY describes evidence availability. It does not establish independent
    // scientific adjudication or held-out outcome calibration. Preserve saved
    // records verbatim as research history; the operational decision abstains.
    return NextResponse.json({ ...record, decision: "ABSTAIN", status: "NOT_READY",
      validated_decision_available: false,
    }, { headers: { "Cache-Control": "private, no-store" } });
  } catch {
    return NextResponse.json({ error: "Prediction backend unavailable", decision: "ABSTAIN", status: "NOT_READY" }, {
      status: 503, headers: { "Cache-Control": "private, no-store" },
    });
  }
}

