import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "./auth";
import { NCT_PATTERN, RUN_PATTERN } from "./nct-live-stream";

const privateHeaders = { "Cache-Control": "private, no-store" };
function error(message: string, status: number) {
  return NextResponse.json({ error: message }, { status, headers: privateHeaders });
}
export async function relayNctRun(req: NextRequest, nct: string, run?: string, events = false, integrity = false) {
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)) return error("Authentication required", 401);
  if (!NCT_PATTERN.test(nct) || (run !== undefined && !RUN_PATTERN.test(run))) return error("Invalid trial or processing run", 422);
  const create = run === undefined;
  if (create && (req.method !== "POST" || req.headers.get("origin") !== req.nextUrl.origin)) return error("Same-origin POST required", 403);
  const base = process.env.PDUFA_API_BASE_URL?.replace(/\/$/, "");
  const key = process.env.PDUFA_INTERNAL_API_KEY;
  if (!base?.startsWith("https://") || !key) return error("Processing backend is not configured", 503);
  let path = "/api/nct-stream/" + encodeURIComponent(nct) + "/runs";
  let body: string | undefined;
  if (create) {
    if (Number(req.headers.get("content-length") || 0) > 1000) return error("Request is too large", 413);
    const raw = await req.text();
    if (raw.length > 1000) return error("Request is too large", 413);
    let data: unknown;
    try { data = JSON.parse(raw); } catch { return error("Invalid request JSON", 422); }
    const requestKey = data && typeof data === "object" ? (data as Record<string, unknown>).request_key : null;
    if (typeof requestKey !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(requestKey)) return error("A request UUID is required", 422);
    const reuseExisting = (data as Record<string, unknown>).reuse_existing;
    if (reuseExisting !== undefined && typeof reuseExisting !== "boolean") return error("Invalid saved-run option", 422);
    body = JSON.stringify({ request_key: requestKey, ...(reuseExisting === true ? { reuse_existing: true } : {}) });
  } else {
    path += "/" + encodeURIComponent(run!);
    if (integrity) path += "/dossier-integrity";
    if (events) {
      path += "/events";
      const after = req.nextUrl.searchParams.get("after");
      if (after !== null) {
        if (!/^(0|[1-9][0-9]{0,14})$/.test(after)) return error("Invalid processing cursor", 422);
        path += "?after=" + after;
      }
    }
  }
  const cursor = req.headers.get("last-event-id");
  if (events && cursor && !new RegExp("^" + run + ":(?:0|[1-9][0-9]{0,14})$").test(cursor)) return error("Processing cursor identity mismatch", 422);
  try {
    const upstream = await fetch(base + path, {
      method: create ? "POST" : "GET", cache: "no-store", body,
      headers: { "X-Pdufa-Internal-Key": key, Accept: events ? "text/event-stream" : "application/json",
        ...(create ? { "Content-Type": "application/json" } : {}), ...(events && cursor ? { "Last-Event-ID": cursor } : {}) },
      signal: AbortSignal.any([req.signal, AbortSignal.timeout(events ? 55000 : 25000)]),
    });
    if (!upstream.ok) return error("Processing request unavailable", [404, 409, 422, 429].includes(upstream.status) ? upstream.status : 503);
    const type = upstream.headers.get("content-type") || "";
    if (events) {
      if (!type.toLowerCase().startsWith("text/event-stream") || !upstream.body) return error("Processing backend did not return an event stream", 502);
      return new Response(upstream.body, { headers: { ...privateHeaders, "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "private, no-store, no-transform", "X-Accel-Buffering": "no" } });
    }
    if (!type.toLowerCase().startsWith("application/json")) return error("Processing backend returned an unexpected response", 502);
    return NextResponse.json(await upstream.json(), { status: upstream.status, headers: privateHeaders });
  } catch { return error("Processing backend is unavailable", 503); }
}
