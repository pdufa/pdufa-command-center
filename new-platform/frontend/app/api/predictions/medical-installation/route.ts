import {NextRequest, NextResponse} from "next/server";
import {authConfigured, COOKIE_NAME, hasSession} from "../../../../lib/auth";
import {isolatedMedicalBackend} from "../../../../lib/medical-review-matrix";
import {validateMedicalInstallation} from "../../../../lib/medical-installation-status";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"};
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error: "Authentication required"}, {status: 401, headers});
  const base = isolatedMedicalBackend(process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL);
  // This existing monitor endpoint accepts the ordinary internal key only.
  // It is sent solely to the explicitly selected isolated medical origin.
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !key) return NextResponse.json({error: "Isolated medical installation monitoring is not configured"}, {status: 503, headers});
  try {
    const response = await fetch(base + "/api/internal/installation-monitor", {
      headers: {"x-pdufa-internal-key": key}, redirect: "error", cache: "no-store", signal: AbortSignal.timeout(15000)
    });
    if (!response.ok || !response.headers.get("content-type")?.includes("json")) throw Error("MONITOR_UNAVAILABLE");
    const body = await response.text();
    if (body.length > 1_000_000) throw Error("MONITOR_TOO_LARGE");
    return NextResponse.json(validateMedicalInstallation(JSON.parse(body) as unknown), {headers});
  } catch {
    return NextResponse.json({error: "Isolated medical installation observations could not be verified. Completion remains unknown."}, {status: 503, headers});
  }
}
