/**
 * Strict, public-safe descriptions for the authenticated OUTCOME diagnostic.
 * Never pass arbitrary upstream response text or secret configuration to UI.
 * This is a connection reason, NOT FDA source or model verification.
 */
export type HopSourceReason =
  | "SOURCE_AUTHENTICATION_FAILED"
  | "SOURCE_UNREACHABLE"
  | "SOURCE_ROUTE_MISSING"
  | "SOURCE_HTTP_ERROR"
  | "SOURCE_INVALID_RESPONSE";

const REASONS: Record<HopSourceReason, string> = {
  SOURCE_AUTHENTICATION_FAILED:
    "OUTCOME source refused the server-to-server credential. Reconcile the dedicated HOP credential in production with the Render HOP source, without sharing or logging key values.",
  SOURCE_UNREACHABLE:
    "OUTCOME source could not be reached. Check the existing read-only Render service and retry once it is available.",
  SOURCE_ROUTE_MISSING:
    "OUTCOME source does not offer the expected read-only readiness route. Verify the source deployment/version; do not use another backend as a fallback.",
  SOURCE_HTTP_ERROR:
    "OUTCOME source returned an unexpected status. Review the Render service health and route logs.",
  SOURCE_INVALID_RESPONSE:
    "OUTCOME response failed strict source validation. Its historical counts and model status remain withheld.",
};

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Accept ONLY the proxy's sanctioned reason enum for an actual HTTP 503.
 * Treat any other content as untrusted; never display JSON/error messages
 * verbatim, even if a proxy or source unexpectedly returns credentials.
 */
export function safeHopDiagnostic(status: number, payload: unknown): string {
  if (status === 401) return "Sign in to the dashboard to check protected OUTCOME evidence.";
  if (status === 403) return "You do not have permission to view protected OUTCOME evidence.";
  if (status !== 503 || !object(payload)) {
    return "OUTCOME evidence is currently unavailable (HTTP "
      + (Number.isSafeInteger(status) && status >= 100 && status <= 599 ? status : "unknown")
      + "). Historical counts remain withheld.";
  }
  const reason = payload.reason;
  if (typeof reason === "string"
      && Object.prototype.hasOwnProperty.call(REASONS, reason)) {
    return REASONS[reason as HopSourceReason]
      + " Source connection remains NOT VERIFIED; no FDA prediction is enabled.";
  }
  return "OUTCOME source connection is not verified. Historical counts and FDA probabilities remain withheld.";
}
