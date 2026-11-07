import {bottomOnlyReport} from '../../../lib/bottom-only-completion';
import {bottomExport,bottomSummary,bottomTrialHistory} from '../../../lib/bottom-only-exports';
import activeRoster from '../../../data/p3PostDataActive.json';
export const dynamic='force-dynamic';
const activeNcts=new Set(activeRoster.records.map(t=>t.nct));
export function GET(request:Request){
 const params=new URL(request.url).searchParams;
 const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
 const nct=params.get('nctId'),format=params.get('format');
 if(nct){
  if(!/^NCT\d{8}$/.test(nct))return Response.json({error:'Invalid exact NCT'},{status:422,headers});
  const trial=activeNcts.has(nct)?bottomOnlyReport().trials.find(t=>t.nctId===nct):null;
  if(!trial)return Response.json({error:'No reviewed research for this exact active NCT'},{status:404,headers});
  return Response.json({trial,history:bottomTrialHistory(nct),scope:'EXACT_NCT_ACTIVE_ROSTER_RESEARCH'},{headers});
 }
 if(format){
  if(!['csv','metrics','facts','rating-evidence'].includes(format))return Response.json({error:'Unknown export'},{status:422,headers});
  return new Response(bottomExport(format,activeNcts),{headers:{...headers,'Content-Type':'text/csv; charset=utf-8','Content-Disposition':`attachment; filename="p3-post-data-${format}.csv"`}});
 }
 return Response.json(bottomSummary(activeNcts),{headers});
}
