import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../../lib/read-only-warm-retry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const PRIVATE = { "Cache-Control": "private, no-store" };
const NCT = "NCT02142738"; // Frozen historical pilot; no cross-trial metadata access.

/** Session-protected, read-only isolated source-byte manifest proxy. No PDF bytes. */
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401, headers: PRIVATE });
  }
  if (req.nextUrl.searchParams.get("nct_id") !== NCT
      || [...req.nextUrl.searchParams.keys()].some(key => key !== "nct_id")) {
    return NextResponse.json({ error: "Exact pilot NCT required" }, { status: 422, headers: PRIVATE });
  }
  const base = process.env.PDUFA_SCIENTIFIC_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_SCIENTIFIC_PREVIEW_READ_KEY;
  if (!base || !/^https:\/\/[^/]+$/.test(base) || !key) {
    return NextResponse.json({ error: "Isolated scientific service not configured", reason: "SCIENTIFIC_SERVICE_NOT_CONFIGURED" }, {
      status: 503, headers: PRIVATE,
    });
  }
  try {
    const result = await fetchReadOnlyWithWarmRetry(
      base + "/api/scientific-assessment/captured-source-manifest/" + NCT,
      { headers: { "x-pdufa-internal-key": key }, cache: "no-store", signal: AbortSignal.timeout(20000) },
    );
    if (!result.ok) {
      // Distinguish stale backend code (404) from disabled access (401/403) and downtime.
      // No credentials, network addresses, upstream body or PDF data in response.
      const reason = result.status === 404 ? "CAPTURED_ROUTE_NOT_DEPLOYED"
        : result.status === 401 || result.status === 403 ? "ISOLATED_READ_KEY_REJECTED"
          : "ISOLATED_SCIENTIFIC_SERVICE_UNAVAILABLE";
      return NextResponse.json({ error: "Isolated captured-source contract unavailable", reason }, {
        status: 503, headers: PRIVATE,
      });
    }
    if (result.headers?.get("x-pdufa-scientific-api-contract") !== "science-captured-hashes-v1") {
      return NextResponse.json({
        error: "Isolated captured-source contract unavailable",
        reason: "CAPTURED_ROUTE_NOT_DEPLOYED",
      }, { status: 503, headers: PRIVATE });
    }
    const raw: unknown = await result.json();
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw Error("Invalid manifest");
    const data = raw as Record<string, unknown>;
    if (data.nctId !== NCT || data.allCapturedBytesRehashed !== true
        || data.independentSourceVerificationCompleted !== false
        || data.reviewerIdentityVerified !== false || data.scientificGradePromotionAllowed !== false
        || data.scientificScore !== null || data.fdaApprovalProbability !== null
        || !Number.isSafeInteger(data.sourceDocumentCount)
        || (data.sourceDocumentCount as number) < 0 || (data.sourceDocumentCount as number) > 8
        || !Array.isArray(data.documents)
        || data.documents.length !== data.sourceDocumentCount) {
      throw Error("Invalid manifest");
    }
    const hashes = new Set<string>();
    const ids = new Set<string>();
    const documents = data.documents.map((entry: unknown) => {
      if (!entry || typeof entry !== "object" || Array.isArray(entry)) throw Error("Invalid document");
      const d = entry as Record<string, unknown>;
      if (d.nctId !== NCT || typeof d.documentId !== "string" || !/^[a-f0-9]{32}$/.test(d.documentId)
          || typeof d.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(d.sha256)
          || typeof d.gateId !== "string" || !/^[a-z_]{3,32}$/.test(d.gateId)
          || typeof d.sourceType !== "string" || !/^[a-z_]{3,64}$/.test(d.sourceType)
          || !Number.isSafeInteger(d.byteLength) || (d.byteLength as number) < 32
          || (d.byteLength as number) > 5 * 1024 * 1024
          || d.captureStatus !== "byte_integrity_checked_unverified"
          || d.byteIntegrityChecked !== true || d.sourceAuthorshipVerified !== false
          || d.documentContentScientificallyVerified !== false
          || d.canCountTowardReadiness !== false
          || ids.has(d.documentId) || hashes.has(d.sha256)) throw Error("Invalid document");
      ids.add(d.documentId);
      hashes.add(d.sha256);
      return {
        documentId: d.documentId, gateId: d.gateId, sourceType: d.sourceType,
        sha256: d.sha256, byteLength: d.byteLength,
        captureStatus: "byte_integrity_checked_unverified",
        scientificVerificationComplete: false,
      };
    });
    return NextResponse.json({
      nctId: NCT, sourceDocumentCount: documents.length,
      allCapturedBytesRehashed: true,
      independentSourceVerificationCompleted: false,
      scientificScore: null, fdaApprovalProbability: null,
      documents,
    }, { headers: PRIVATE });
  } catch {
    return NextResponse.json({ error: "Captured source manifest unavailable or invalid", reason: "ARCHIVE_RESPONSE_UNVERIFIED_OR_UNAVAILABLE" }, {
      status: 503, headers: PRIVATE,
    });
  }
}
