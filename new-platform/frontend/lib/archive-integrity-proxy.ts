import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "./auth";

type ArchiveResource = "archive-health" | "archive-manifest" | "archive-scope";
const headers = { "Cache-Control": "private, no-store" };

/** Relay existing read-only reports. This does not initiate an integrity audit. */
export async function relayArchiveIntegrity(req: NextRequest, resource: ArchiveResource) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers });
  }
  const unavailable = () => NextResponse.json({ error: "Archive verification unavailable" }, { status: 503, headers });
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  const base = process.env.PDUFA_API_BASE_URL;
  if (!base || !key) return unavailable();
  try {
    const origin = new URL(base);
    if (origin.protocol !== "https:" || origin.username || origin.password) return unavailable();
    const upstream = await fetch(new URL("/api/" + resource, origin).toString(), {
      method: "GET", cache: "no-store", redirect: "error",
      headers: { "X-Pdufa-Internal-Key": key, Accept: "application/json" },
      signal: AbortSignal.timeout(25000),
    });
    if (!upstream.ok || !(upstream.headers.get("content-type") || "").toLowerCase().includes("application/json")) return unavailable();
    const report: unknown = await upstream.json();
    if (!report || typeof report !== "object" || Array.isArray(report)) return unavailable();
    // Never relay an internal credential even if an upstream diagnostic echoes it.
    if (JSON.stringify(report).includes(key)) return unavailable();
    return NextResponse.json(report, { headers });
  } catch {
    return unavailable();
  }
}
