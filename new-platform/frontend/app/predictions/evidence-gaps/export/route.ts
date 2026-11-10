import {buildR83EvidenceGapChecklist} from "../../../../lib/focus-r83-evidence-gap-export";

/** Server-generated, read-only research checklist. No clinical grade or FDA advice. */
export const dynamic = "force-dynamic";
export function GET():Response {
  const csv=buildR83EvidenceGapChecklist();
  if(csv===null) {
    return new Response("The exact-NCT source snapshot failed integrity validation.",{
      status:503,headers:{"Content-Type":"text/plain; charset=utf-8",
        "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}
    });
  }
  return new Response("\uFEFF"+csv,{
    status:200,
    headers:{
      "Content-Type":"text/csv; charset=utf-8",
      "Content-Disposition":'attachment; filename="focus-29-source-evidence-gaps-r83.csv"',
      "Cache-Control":"no-store",
      "X-Content-Type-Options":"nosniff"
    }
  });
}
