/** Resolve the isolated read-only research backend independently of the
 * production program-storage backend. Never route writes or ordinary scans here.
 * Credentials continue to be supplied server-side by the authenticated proxy.
 */
export function researchBackendBase(): string | null {
  const selected = process.env.PDUFA_RESEARCH_API_BASE_URL?.trim() || process.env.PDUFA_API_BASE_URL?.trim();
  if (!selected) return null;
  try {
    const url = new URL(selected);
    if (url.protocol !== "https:" || !url.hostname || url.username || url.password
        || url.pathname !== "/" || url.search || url.hash) return null;
    return url.origin;
  } catch {
    return null;
  }
}
