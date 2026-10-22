import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  const origin = req.headers.get("origin");
  if (origin && origin !== req.nextUrl.origin) {
    return NextResponse.json({ error: "Origin not allowed" }, { status: 403 });
  }
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Backend is not configured" }, { status: 503 });
  }
  const body = await req.text();
  if (body.length > 2_000_000) {
    return NextResponse.json({ error: "Review package exceeds 2 MB" }, { status: 413 });
  }
  let parsed: unknown;
  try { parsed = JSON.parse(body); } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) ||
      (parsed as {schemaVersion?:unknown}).schemaVersion !== 1 ||
      (parsed as {kind?:unknown}).kind !== "pdufa-reconciliation-review-export" ||
      !Array.isArray((parsed as {records?:unknown}).records)) {
    return NextResponse.json({ error: "Invalid review package" }, { status: 422 });
  }
  try {
    const upstream = await fetch(base + "/api/reconciliation/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-PDUFA-Internal-Key": key },
      body, cache: "no-store", signal: AbortSignal.timeout(45000),
    });
    const result = await upstream.json().catch(() => ({error:"Backend returned an invalid response"}));
    return NextResponse.json(result, {
      status: upstream.status,
      headers: { "Cache-Control": "private, no-store" },
    });
  } catch {
    return NextResponse.json({ error: "Read-only reconciliation validation unavailable" }, { status: 503 });
  }
}
