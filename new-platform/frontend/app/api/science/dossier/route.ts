import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { assessScienceReadiness, SCIENCE_SCHEMA_VERSION, type ScienceDossier } from "../../../../lib/science-evidence";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store" };
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers });
  const programId = req.nextUrl.searchParams.get("programId") || "";
  const list = req.nextUrl.searchParams.get("list") || "";
  if (!/^PDUFA-[0-9]{6,}$/.test(programId) || !["GEM_JR", "GEM", "WT"].includes(list))
    return NextResponse.json({ error: "Invalid scientific dossier identity" }, { status: 422, headers });
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key)
    return NextResponse.json({ error: "Scientific backend not configured" }, { status: 503, headers });
  try {
    const upstream = await fetch(base + "/api/science/dossier?programId=" + encodeURIComponent(programId) + "&list=" + encodeURIComponent(list), {
      headers: { "x-pdufa-internal-key": key }, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(15000),
    });
    if (!upstream.ok) return NextResponse.json({ error: "Scientific dossier unavailable" }, { status: upstream.status === 404 ? 404 : 503, headers });
    const data: unknown = await upstream.json();
    if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("Invalid dossier");
    const dossier = data as ScienceDossier;
    if (dossier.schemaVersion !== SCIENCE_SCHEMA_VERSION || dossier.programId !== programId || dossier.list !== list ||
      !Array.isArray(dossier.assessments) || dossier.assessments.some(a => !a || !Array.isArray(a.evidence) || !Array.isArray(a.missingEvidence)))
      throw new Error("Mismatched dossier");
    return NextResponse.json({ ...dossier, readiness: assessScienceReadiness(dossier), approvalProbability: null }, { headers });
  } catch {
    return NextResponse.json({ error: "Scientific evidence could not be verified" }, { status: 503, headers });
  }
}
