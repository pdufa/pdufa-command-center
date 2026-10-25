/** The installed HOP audit service is independent of program storage and market
 * enrichment. Never fall back to those backends when this source is unavailable.
 * The optional override is server configuration, never a request parameter.
 */
const INSTALLED_HOP_SOURCE = "https://pdufa-hop-readonly-review.onrender.com";

export function hopBackendBase(): string | null {
  const selected = process.env.PDUFA_HOP_API_BASE_URL ?? INSTALLED_HOP_SOURCE;
  try {
    const url = new URL(selected.trim());
    if (url.protocol !== "https:" || !url.hostname || url.username || url.password
        || url.pathname !== "/" || url.search || url.hash) return null;
    return url.origin;
  } catch {
    return null;
  }
}
