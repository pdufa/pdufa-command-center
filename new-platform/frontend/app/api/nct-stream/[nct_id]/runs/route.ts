import { NextRequest } from "next/server";
import { relayNctRun } from "../../../../../lib/nct-stream-proxy";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
export async function POST(req: NextRequest, context: { params: Promise<{ nct_id: string }> }) {
  const { nct_id } = await context.params;
  return relayNctRun(req, nct_id);
}
