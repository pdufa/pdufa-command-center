import {NextRequest, NextResponse} from "next/server";
import {authConfigured, COOKIE_NAME, hasSession} from "../../../../lib/auth";
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE} from "../../../../lib/focus-specialty-assessment";
import {assertMatrixPhaseSnapshot, isolatedMedicalBackend, validateCatalogMatrix, validateReviewMatrix} from "../../../../lib/medical-review-matrix";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"};
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error: "Authentication required"}, {status: 401, headers});
  const nct = req.nextUrl.searchParams.get("nct");
  const selection = req.nextUrl.searchParams.get("assessmentIndex");
  const index = selection === null ? undefined : Number(selection);
  if (!nct || !/^NCT\d{8}$/.test(nct) || !FOCUS_SPECIALTY_ASSESSMENT_QUEUE.some(t => t.nct === nct) ||
      (index !== undefined && (!/^([1-9]|[1-3][0-9]|40)$/.test(selection!) || !Number.isInteger(index))))
    return NextResponse.json({error: "Select an exact FOCUS NCT and assessment 1–40"}, {status: 422, headers});
  // Deliberately no fallback to the ordinary storage/production backend.
  const base = isolatedMedicalBackend(process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL);
  const key = process.env.PDUFA_MEDICAL_INTERNAL_API_KEY ?? process.env.PDUFA_INTERNAL_API_KEY;
  if (!base || !key) return NextResponse.json({error: "Isolated medical review backend is not configured"}, {status: 503, headers});
  try {
    const init: RequestInit = {headers: {"x-pdufa-internal-key": key}, redirect: "error", cache: "no-store", signal: AbortSignal.timeout(20000)};
    const paths = ["/api/internal/medical-assessments/" + nct + "/matrix" + (index === undefined ? "" : "?assessmentIndex=" + index)];
    if (index === undefined) paths.push("/api/internal/medical-phase-matrix/" + nct);
    const responses = await Promise.all(paths.map(path => fetch(base + path, init)));
    if (responses.some(r => !r.ok || !r.headers.get("content-type")?.includes("json"))) throw Error("SOURCE_UNAVAILABLE");
    const documents = await Promise.all(responses.map(async r => {
      const body = await r.text();
      if (body.length > 5_000_000) throw Error("SOURCE_TOO_LARGE");
      return JSON.parse(body) as unknown;
    }));
    const review = validateReviewMatrix(documents[0], nct, index);
    const catalog = index === undefined ? validateCatalogMatrix(documents[1], nct) : null;
    if (catalog) assertMatrixPhaseSnapshot(catalog, review);
    return NextResponse.json({review, catalog}, {headers});
  } catch {
    return NextResponse.json({error: "Scientific review ledger could not be verified. Counts and grades are withheld."}, {status: 503, headers});
  }
}
