import {NextRequest,NextResponse} from 'next/server';
import {authConfigured,COOKIE_NAME,hasSession} from '../../../../lib/auth';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=60;
const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
const json=(body:unknown,status=200)=>NextResponse.json(body,{status,headers});
const authorized=(req:NextRequest)=>authConfigured()&&hasSession(req.cookies.get(COOKIE_NAME)?.value);
const nct=(value:string|null)=>!!value&&/^NCT\d{8}$/.test(value);
const uuid=(value:unknown):value is string=>typeof value==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
const populations=['POOL','FOCUS','HISTORICAL'];
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
 if(q.has('batchId'))return uuid(q.get('batchId'))?relay(req,'/batches/'+q.get('batchId')):json({error:'Valid saved batch UUID required'},422);
 if(q.has('batches')||q.has('inventory')){
  const population=q.get('population')||'FOCUS';
  if(!populations.includes(population))return json({error:'Invalid trial population'},422);
  if(q.has('batches'))return relay(req,'/batches?'+new URLSearchParams({population}));
  const offset=q.get('offset')||'0',limit=q.get('limit')||'50';
  if(!/^\d{1,3}$/.test(offset)||Number(offset)>500||!/^\d{1,3}$/.test(limit)||Number(limit)<1||Number(limit)>100)return json({error:'Invalid inventory page'},422);
  return relay(req,'/cohort-inventory?'+new URLSearchParams({population,offset,limit}));
 }
 if(q.get('focus')==='true')return relay(req,'/focus');
 if(q.get('past')==='true')return relay(req,'/past');
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
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>16384){await reader.cancel();return json({error:'Request too large'},413);}chunks.push(value);}
  data=JSON.parse(Buffer.concat(chunks).toString('utf8'));
 }catch{return json({error:'Invalid JSON'},422);}
 if(data&&data.action==='COHORT_BATCH_RESUME'){
  if(Object.keys(data).some(k=>!['action','batchId'].includes(k))||!uuid(data.batchId))return json({error:'Exact saved batch UUID required'},422);
  return relay(req,'/batches/'+data.batchId+'/resume',{});
 }
 if(data&&data.action==='COHORT_BATCH_CREATE'){
  const {action,...selection}=data;
  if(Object.keys(selection).some(k=>!['requestKey','population','scope','ncts','levels','mode','cutoffDate','inventoryHash'].includes(k))||!uuid(selection.requestKey)||!populations.includes(String(selection.population))||!['selected','all'].includes(String(selection.scope))||!Array.isArray(selection.ncts)||selection.ncts.length>500||selection.ncts.some(value=>typeof value!=='string'||!nct(value))||!Array.isArray(selection.levels)||!selection.levels.length||selection.levels.length>3||selection.levels.some(l=>!Number.isInteger(l)||Number(l)<1||Number(l)>3)||!['CURRENT_EVIDENCE','BLIND_HISTORICAL'].includes(String(selection.mode)))return json({error:'Valid exact-trial or whole-list Levels 1–3 selection required; caller evidence and scores are not accepted'},422);
  if(selection.inventoryHash!==undefined&&(typeof selection.inventoryHash!=='string'||!/^[a-f0-9]{64}$/.test(selection.inventoryHash)))return json({error:'Valid source inventory hash required'},422);
  return relay(req,'/batches',selection);
 }
 if(Buffer.byteLength(JSON.stringify(data))>1024)return json({error:'Request too large'},413);
 if(data&&data.action==='FOCUS_BATCH'&&Object.keys(data).length===1)return relay(req,'/focus/batch',{});
 if(!data||typeof data!=='object'||Array.isArray(data)||Object.keys(data).some(k=>!['nct','level','mode','cutoffDate','contract'].includes(k))||typeof data.nct!=='string'||!nct(data.nct)||!Number.isInteger(data.level)||Number(data.level)<1||Number(data.level)>6||!['CURRENT_EVIDENCE','BLIND_HISTORICAL'].includes(String(data.mode)))return json({error:'Exact NCT, selected level 1–6 and assessment mode required; no caller evidence or scoring claims allowed'},422);
 if('contract' in data&&(!['LEGACY_SOURCE_AUDIT','SCIENTIFIC_1_3'].includes(String(data.contract))||(data.contract==='SCIENTIFIC_1_3'&&Number(data.level)>3)))return json({error:'Scientific contract supports Levels 1–3 only'},422);
 if(data.mode==='CURRENT_EVIDENCE'&&'cutoffDate' in data)return json({error:'Current mode does not accept historical cutoff'},422);
 if(data.mode==='BLIND_HISTORICAL'&&(typeof data.cutoffDate!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(data.cutoffDate)||!Number.isFinite(Date.parse(data.cutoffDate+'T00:00:00Z'))||new Date(data.cutoffDate+'T00:00:00Z').toISOString().slice(0,10)!==data.cutoffDate||data.cutoffDate>=new Date().toISOString().slice(0,10)))return json({error:'Valid past historical cutoff required'},422);
 return relay(req,'/runs',data);
}
