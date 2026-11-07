/** This old 762-trial cohort export is retired; use P3 POST-DATA instead. */
export const dynamic="force-dynamic";
export function GET(){
 return Response.json({error:"RETIRED_COHORT",currentPage:"/p3-post-data",detail:"Historical Phase 3 research is preserved; the 762-trial cohort is not a live candidate list."},
  {status:410,headers:{"Cache-Control":"no-store"}});
}
