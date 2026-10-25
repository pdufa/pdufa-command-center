import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME, authConfigured, hasSession } from "../../../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../../../lib/read-only-warm-retry";
import { ARCHIVE_NCT_PATTERN, isExactArchivedDossier } from "../../../../../lib/archived-science-dossier";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const PRIVATE = { "Cache-Control": "private, no-store" };

/**
 * Proxy a read-only, checksum-verified registry dossier for one selected NCT.
 * Reject arbitrary IDs before upstream calls. No import, PubMed search,
 * scheduler, scoring, trading, or write operation may be invoked.
 */
export async function GET(
  req: NextRequest,
  context: { params: Promise<{ nctId: string }> },
) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, {
      status: 401, headers: PRIVATE,
    });
  }
  const { nctId } = await context.params;
  if (!ARCHIVE_NCT_PATTERN.test(nctId)) {
    return NextResponse.json({ error: "Exact NCT######## trial identity required" }, {
      status: 422, headers: PRIVATE,
    });
  }

  const base = process.env.PDUFA_SCIENTIFIC_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_SCIENTIFIC_PREVIEW_READ_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ error: "Scientific review service unavailable" }, {
      status: 503, headers: PRIVATE,
    });
  }
  try {
    const exactId = "TRIAL|" + nctId;
    const upstream = await fetchReadOnlyWithWarmRetry(
      base + "/api/scientific-assessment/dossier?exact_id=" + encodeURIComponent(exactId),
      {
        headers: { "x-pdufa-internal-key": key },
        cache: "no-store",
        signal: AbortSignal.timeout(45000),
      },
    );
    if (upstream.status === 404) {
      return NextResponse.json({
        error: "No verified archive for this trial yet. Source review is not available.",
      }, { status: 404, headers: PRIVATE });
    }
    if (!upstream.ok) {
      return NextResponse.json({ error: "Archived scientific evidence unavailable" }, {
        status: 503, headers: PRIVATE,
      });
    }
    const data: unknown = await upstream.json();
    if (!isExactArchivedDossier(data, nctId)) {
      return NextResponse.json({
        error: "Archive trial identity, score state, or evidence provenance failed validation",
      }, { status: 503, headers: PRIVATE });
    }
    return NextResponse.json(data, { headers: PRIVATE });
  } catch {
    return NextResponse.json({ error: "Archived scientific evidence could not be read" }, {
      status: 503, headers: PRIVATE,
    });
  }
}
