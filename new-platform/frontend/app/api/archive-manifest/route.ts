import { NextRequest } from "next/server";
import { relayArchiveIntegrity } from "../../../lib/archive-integrity-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  return relayArchiveIntegrity(req, "archive-manifest");
}
