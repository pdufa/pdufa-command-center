import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../../lib/auth";
import { fetchReadOnlyWithWarmRetry } from "../../../../lib/read-only-warm-retry";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PRIVATE = { "Cache-Control": "private, no-store" };

/** Diagnostic only: signed-in preview -> isolated scientific backend GET.
 * Does not import, grade, trigger research, change presets, or disclose secrets.
 */
export async function GET(req: NextRequest) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.json({ connection: "authentication_required" }, {
      status: 401, headers: PRIVATE,
    });
  }
  const exactId = req.nextUrl.searchParams.get("exact_id");
  if (!exactId || !/^TRIAL\|NCT[0-9]{8}$/.test(exactId)) {
    return NextResponse.json({ connection: "invalid_exact_trial_id" }, {
      status: 422, headers: PRIVATE,
    });
  }
  const base = process.env.PDUFA_SCIENTIFIC_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_SCIENTIFIC_PREVIEW_READ_KEY;
  if (!base?.startsWith("https://") || !key) {
    return NextResponse.json({ connection: "scientific_backend_not_configured" }, {
      status: 503, headers: PRIVATE,
    });
  }
  try {
    const upstream = await fetchReadOnlyWithWarmRetry(
      base + "/api/scientific-assessment?exact_id=" + encodeURIComponent(exactId), {
        headers: { "x-pdufa-internal-key": key },
        cache: "no-store",
        signal: AbortSignal.timeout(20000),
      },
    );
    if (upstream.status === 401 || upstream.status === 403) {
      return NextResponse.json({ connection: "scientific_backend_authorization_failed" }, {
        status: 502, headers: PRIVATE,
      });
    }
    if (!upstream.ok) {
      return NextResponse.json({ connection: "scientific_backend_unavailable" }, {
        status: 503, headers: PRIVATE,
      });
    }
    if (upstream.headers?.get("x-pdufa-scientific-api-contract") !== "science-integrated-v1") {
      // An older live Render service can answer the same endpoint yet lack the
      // reviewed 20-level and source-adjudication contracts. Treat it as
      // NOT installed; never report a misleading "connected" success.
      return NextResponse.json({ connection: "scientific_backend_contract_mismatch" }, {
        status: 503, headers: PRIVATE,
      });
    }
    const body: unknown = await upstream.json();
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return NextResponse.json({ connection: "scientific_backend_invalid_response" }, {
        status: 503, headers: PRIVATE,
      });
    }
    const data = body as Record<string, unknown>;
    if (data.exactId !== exactId || data.independentOfQualificationPresets !== true
      || !data.assessment || typeof data.assessment !== "object"
      || Array.isArray(data.assessment)) {
      return NextResponse.json({ connection: "scientific_backend_identity_mismatch" }, {
        status: 503, headers: PRIVATE,
      });
    }
    // Connectivity is not source adjudication. Do not return raw upstream
    // evidence, credentials, grades, percentages, or risk signals here.
    return NextResponse.json({
      connection: "connected",
      exactTrialIdentityMatched: true,
      archivedRecordPresent: data.registryEvidence !== null
        && data.registryEvidence !== undefined,
      independentScientificReview: "not_certified_by_connection_test",
      approvalProbability: null,
      scoresAssignedByConnectionTest: false,
    }, { headers: PRIVATE });
  } catch {
    return NextResponse.json({ connection: "scientific_backend_unreachable" }, {
      status: 503, headers: PRIVATE,
    });
  }
}
