import {FOCUS_PRELIMINARY_R39} from "../../../../lib/focus-preliminary-application-research";
/** Dated, versioned *research* snapshot for 29 exact NCTs and 23 candidate applications.
 * No scoring writes or live FDA inference. Never promote to signed clinical claims.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
export function GET():Response{
  return Response.json(FOCUS_PRELIMINARY_R39,{
    headers:{
      "Cache-Control":"private, no-store",
      "X-Content-Type-Options":"nosniff",
      "Content-Disposition":'attachment; filename="focus-29-23-preliminary-2026-11-09-research-only.json"'
    }
  });
}
