import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "./auth";

const privateHeaders = { "Cache-Control": "private, no-store" };
const SORTS = new Set(["company", "ticker", "drug", "indication", "trial_title", "nct_id", "phase3_status", "last_verified", "completion_date", "decision", "pdufa_date", "scientific_readiness"]);
const DECISIONS = new Set(["ALL", "APPROVED", "CRL", "EXTENDED", "PENDING"]);
function error(message: string, status: number) {
  return NextResponse.json({ error: message }, { status, headers: privateHeaders });
}

export function catalogQuery(search: URLSearchParams): URLSearchParams | null {
  const period = search.get("period") || "CURRENT";
  const query = search.get("q") ?? search.get("search") ?? "";
  const decision = search.get("decision") || "ALL";
  const sort = search.get("sort") || "last_verified";
  const direction = search.get("dir") || "desc";
  const page = search.get("page") || "1";
  const size = search.get("page_size") || "25";
  if (!["CURRENT", "PREVIOUS"].includes(period) || query.length > 200 || !DECISIONS.has(decision) || !SORTS.has(sort) ||
      !["asc", "desc"].includes(direction) || !/^[1-9][0-9]{0,8}$/.test(page) || !/^[1-9][0-9]{0,2}$/.test(size) || Number(size) > 100) return null;
  return new URLSearchParams({ period, q: query, decision, sort, dir: direction, page, page_size: size });
}

export async function relayPhase3Catalog(req: NextRequest, validation = false) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) return error("Authentication required", 401);
  const query = validation ? new URLSearchParams() : catalogQuery(req.nextUrl.searchParams);
  if (!query) return error("Invalid trial catalog filters", 422);
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) return error("Trial catalog backend is not configured", 503);
  try {
    const response = await fetch(base + "/api/phase3-trials" + (validation ? "/validation" : "?" + query.toString()), {
      cache: "no-store", headers: { Accept: "application/json", "X-Pdufa-Internal-Key": key },
      signal: AbortSignal.any([req.signal, AbortSignal.timeout(25000)]),
    });
    if (!response.ok) return error("Verified trial catalog is unavailable", [404, 409, 422, 429].includes(response.status) ? response.status : 503);
    if (!(response.headers.get("content-type") || "").toLowerCase().startsWith("application/json")) return error("Trial catalog returned an unexpected response", 502);
    return NextResponse.json(await response.json(), { headers: privateHeaders });
  } catch { return error("Trial catalog backend is unavailable", 503); }
}
