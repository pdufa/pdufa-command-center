import {activePhase3Cohorts} from "../../../lib/phase3-active-cohorts";
export const dynamic="force-dynamic";
export async function GET(){
 const data=activePhase3Cohorts.snapshot;
 return Response.json(data,{headers:{"Cache-Control":"no-store"}});
}
