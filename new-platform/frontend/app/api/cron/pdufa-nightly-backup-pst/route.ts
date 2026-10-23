// 04:15 UTC backup clock for 8:15 PM Pacific during standard time.
// Any duplicate or daylight-time invocation is rejected by shared admission.
export { GET } from "../pdufa-nightly-backup/route";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
