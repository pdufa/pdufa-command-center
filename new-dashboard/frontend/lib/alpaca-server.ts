// Import from Next.js server components / server actions only.
// Never use NEXT_PUBLIC_* for the backend token or Alpaca credentials.
import "server-only";

type Operation = "status" | "test" | "quotes" | "bars" | "technicals";

export async function alpacaRequest(
  operation: Operation,
  params: Record<string, string | number> = {},
): Promise<unknown> {
  const base = process.env.ALPACA_BACKEND_URL;
  const token = process.env.DASHBOARD_API_TOKEN;
  if (!base || !token) throw new Error("Alpaca backend is not configured.");

  const url = new URL(`/api/alpaca/${operation}`, base);
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, String(value)));
  const response = await fetch(url.toString(), {
    headers: { "x-dashboard-token": token },
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    // Do not pass upstream server details or any credentials to the browser.
    throw new Error(`Alpaca data request failed (HTTP ${response.status})`);
  }
  return response.json();
}
