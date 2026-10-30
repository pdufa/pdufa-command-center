import { NextRequest } from "next/server";
import { relayLatestNctRun } from "../../../../../../lib/nct-latest-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, context: { params: Promise<{ nct_id: string }> }) {
  return relayLatestNctRun(req, (await context.params).nct_id);
}
