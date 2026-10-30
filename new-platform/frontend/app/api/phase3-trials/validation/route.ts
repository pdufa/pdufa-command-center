import { NextRequest } from "next/server";
import { relayPhase3Catalog } from "../../../../lib/phase3-trials";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  return relayPhase3Catalog(req, true);
}
