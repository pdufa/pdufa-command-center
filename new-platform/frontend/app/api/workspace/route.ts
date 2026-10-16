import { NextRequest, NextResponse } from "next/server";
import snapshot from "../../../data/stageSnapshot.json";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, {
      status: 401, headers: { "Cache-Control": "no-store" }
    });
  }
  return NextResponse.json(snapshot, { headers: { "Cache-Control": "private, no-store" } });
}
