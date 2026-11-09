import {FOCUS_R40_SOURCE_STATUS} from "../../../../lib/focus-r40-source-readiness";
/** Dated source-access metadata, NOT medical truth or an FDA model output.
 * Rev39 app/trial research judgments remain immutable and separate.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
export function GET():Response {
  if(!FOCUS_R40_SOURCE_STATUS)
    return Response.json({status:"SOURCE_RECEIPT_IDENTITY_UNVERIFIED"},
      {status:503,headers:{"Cache-Control":"private, no-store"}});
  return Response.json(FOCUS_R40_SOURCE_STATUS,{
    headers:{
      "Cache-Control":"private, no-store",
      "X-Content-Type-Options":"nosniff",
      "Content-Disposition":'attachment; filename="focus-r40-public-source-coverage-2026-11-09.json"'
    }
  });
}
