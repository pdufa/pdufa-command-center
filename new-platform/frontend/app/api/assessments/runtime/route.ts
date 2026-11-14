import {NextRequest,NextResponse} from 'next/server';
import {authConfigured,COOKIE_NAME,hasSession} from '../../../../lib/auth';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=60;
const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
const json=(body:unknown,status=200)=>NextResponse.json(body,{status,headers});
const authorized=(req:NextRequest)=>authConfigured()&&hasSession(req.cookies.get(COOKIE_NAME)?.value);
const nct=(value:string|null)=>!!value&&/^NCT\d{8}$/.test(value);
async function relay(req:NextRequest,path:string,body?:unknown){
 const base=process.env.PDUFA_API_BASE_URL?.replace(/\/$/,''),key=process.env.PDUFA_INTERNAL_API_KEY;
 if(!base?.startsWith('https://')||!key)return json({error:'Persistent assessment backend is not configured'},503);
 try{
  const response=await fetch(base+'/api/assessment-runtime'+path,{method:body?'POST':'GET',cache:'no-store',headers:{'Content-Type':'application/json','X-Pdufa-Internal-Key':key},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.any([req.signal,AbortSignal.timeout(45000)])});
  if(!response.headers.get('content-type')?.includes('application/json'))return json({error:'Assessment backend unavailable'},503);
  const data=await response.json();
  if(!response.ok)return json({error:typeof data.detail==='string'?data.detail:'Assessment backend rejected this request'},[401,403,404,409,422].includes(response.status)?response.status:503);
  return json(data,response.status);
 }catch{return json({error:'Assessment backend could not be reached; no completion confirmed'},503);}
}
export async function GET(req:NextRequest){
 if(!authorized(req))return json({error:'Sign in to access assessments'},401);
 const q=req.nextUrl.searchParams;
 if(q.has('population')){
  const population=q.get('population'),term=q.get('q')||'';
  if(!['POOL','FOCUS','HISTORICAL'].includes(population||'')||term.length>100)return json({error:'Invalid population search'},422);
  return relay(req,'/trials?'+new URLSearchParams({population:population!,q:term}));
 }
 const id=q.get('nct'),run=q.get('runId'),level=q.get('level');
 if(!nct(id)||(level!==null&&!/^[1-6]$/.test(level))||(run!==null&&!/^[a-f0-9-]{36}$/.test(run)))return json({error:'Exact NCT, optional run UUID and level 1–6 required'},422);
 return relay(req,run?'/runs/'+id+'/'+run:'/history/'+id+(level?'?level='+level:''));
}
export async function POST(req:NextRequest){
 if(!authorized(req))return json({error:'Sign in to run assessments'},401);
 if(req.headers.get('origin')!==req.nextUrl.origin)return json({error:'Same-origin action required'},403);
 if(!req.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return json({error:'JSON required'},415);
 if(!req.body)return json({error:'Assessment request required'},422);
 let data:Record<string,unknown>;
 try{
  const reader=req.body.getReader(),chunks:Uint8Array[]=[];let size=0;
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>1024){await reader.cancel();return json({error:'Request too large'},413);}chunks.push(value);}
  data=JSON.parse(Buffer.concat(chunks).toString('utf8'));
 }catch{return json({error:'Invalid JSON'},422);}
 if(!data||typeof data!=='object'||Array.isArray(data)||Object.keys(data).some(k=>!['nct','level','mode','cutoffDate'].includes(k))||typeof data.nct!=='string'||!nct(data.nct)||!Number.isInteger(data.level)||Number(data.level)<1||Number(data.level)>6||!['CURRENT_EVIDENCE','BLIND_HISTORICAL'].includes(String(data.mode)))return json({error:'Exact NCT, selected level 1–6 and assessment mode required; no caller evidence or scoring claims allowed'},422);
 if(data.mode==='CURRENT_EVIDENCE'&&'cutoffDate' in data)return json({error:'Current mode does not accept historical cutoff'},422);
 if(data.mode==='BLIND_HISTORICAL'&&(typeof data.cutoffDate!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(data.cutoffDate)||!Number.isFinite(Date.parse(data.cutoffDate+'T00:00:00Z'))||new Date(data.cutoffDate+'T00:00:00Z').toISOString().slice(0,10)!==data.cutoffDate||data.cutoffDate>=new Date().toISOString().slice(0,10)))return json({error:'Valid past historical cutoff required'},422);
 return relay(req,'/runs',data);
}
