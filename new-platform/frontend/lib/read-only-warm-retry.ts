/** A single, bounded recovery attempt for authenticated read-only backend GETs.
 * Never repeat writes, auth failures, version conflicts, or malformed requests.
 * Reuses the caller's single request timeout so both calls share one deadline.
 */
export async function fetchReadOnlyWithWarmRetry(
  url: string,
  init: RequestInit,
  options: {
    fetcher?: typeof fetch;
    pause?: () => Promise<void>;
  } = {},
): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();
  if (method !== "GET") throw new Error("Only GET requests may be retried");
  const fetcher = options.fetcher ?? fetch;
  const request: RequestInit = { ...init, method: "GET" };
  const first = await fetcher(url, request);
  if (first.status !== 502 && first.status !== 503) return first;
  const pause = options.pause ?? (() => new Promise<void>(resolve => setTimeout(resolve, 1200)));
  await pause();
  if (init.signal?.aborted) throw new Error("Read-only request deadline exceeded");
  return fetcher(url, request);
}
