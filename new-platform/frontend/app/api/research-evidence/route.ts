import {NextRequest, NextResponse} from "next/server";
import {authConfigured, COOKIE_NAME, hasSession} from "../../../lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Research-only same-origin boundary; no browser-provided identity is trusted. */
export async function GET(req:NextRequest) {
  const headers = {"Cache-Control":"private, no-store"};
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  const programId=req.nextUrl.searchParams.get("program_id");
  if (!programId || programId.length>256 || !/^[A-Za-z0-9_|.:-]+$/.test(programId))
    return NextResponse.json({error:"Invalid program identity"},{status:400,headers});
  // A browser session alone does NOT establish evidence-reader role or
  // per-program authorization. No backend proxy until a trusted mapping exists.
  return NextResponse.json({error:"Research evidence authorization backend not configured",
    readiness:"NOT_READY",decision:"ABSTAIN"},{status:503,headers});
}
