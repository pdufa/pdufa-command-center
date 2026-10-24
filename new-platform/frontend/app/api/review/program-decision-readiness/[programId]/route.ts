import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../../lib/auth";
import { researchReadiness } from "../../../../../lib/research-readiness";
import { researchBackendBase } from "../../../../../lib/research-backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Existing isolated review only: no fallback, assessment writes, or orders. */
export async function GET(req: NextRequest, context: { params: Promise<{ programId: string }> }) {
  const reply = (data: unknown, status: number) => NextResponse.json(data, {
    status, headers: { "Cache-Control": "private, no-store" },
  });
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return reply({ error: "Authentication required" }, 401);
  }
  const { programId } = await context.params;
  const stage = req.nextUrl.searchParams.get("stage");
  const identity = req.nextUrl.searchParams.get("identity") || "";
  if (!/^PDUFA-[0-9]{6,}$/.test(programId) || !identity.trim() || identity.length > 512
      || (stage !== "GEM_JR" && stage !== "GEM")) {
    return reply({ error: "Exact program identity and GEM assessment stage required" }, 422);
  }
  const base = researchBackendBase();
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !/^https:\/\//.test(base) || !key) {
    return reply({ error: "Research readiness unavailable" }, 503);
  }
  try {
    const response = await fetch(base + "/api/review/program-decision-readiness/" + encodeURIComponent(programId)
      + "?stage=" + encodeURIComponent(stage), {
      headers: { "x-pdufa-internal-key": key }, cache: "no-store", redirect: "error",
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) return reply({ error: "Research readiness unavailable" }, response.status === 404 ? 404 : 503);
    const data = researchReadiness(await response.json(), programId, identity, stage);
    return reply(data, 200);
  } catch {
    return reply({ error: "Research readiness unavailable" }, 503);
  }
}
