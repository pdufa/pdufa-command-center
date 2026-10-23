// 03:15 UTC backup clock for 8:15 PM Pacific during daylight time.
// Authorization and local-time/DST admission remain in the single shared handler.
export { GET } from "../pdufa-nightly-backup/route";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
