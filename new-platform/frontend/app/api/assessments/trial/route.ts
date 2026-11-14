import {NextRequest,NextResponse} from 'next/server';
import {authConfigured,COOKIE_NAME,hasSession} from '../../../../lib/auth';
import {AssessmentError,executeTrial,NCT,parseTrialRequest} from '../../../../lib/trial-level-assessment';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=60;
const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
const json=(body:unknown,status=200)=>NextResponse.json(body,{status,headers});
const authorized=(req:NextRequest)=>authConfigured()&&hasSession(req.cookies.get(COOKIE_NAME)?.value);
function backend(){const base=process.env.PDUFA_API_BASE_URL?.replace(/\/$/,''),key=process.env.PDUFA_INTERNAL_API_KEY;if(!base?.startsWith('https://')||!key)throw new AssessmentError('Persistent assessment backend is not configured. No run was started.',503);return {base,key};}
async function relay(path:string,req:NextRequest,body?:unknown){
 const {base,key}=backend();
 const response=await fetch(base+'/api/assessments/trial/history'+path,{method:body?'POST':'GET',cache:'no-store',headers:{Accept:'application/json','Content-Type':'application/json','X-Pdufa-Internal-Key':key},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.any([req.signal,AbortSignal.timeout(20000)])});
 if(!response.ok)throw new AssessmentError(body?'Assessment was not confirmed saved. No completed result is shown.':'Assessment history could not be retrieved',response.status===409?409:503);
 const data=await response.json();
 if(body&&(data.runId!==(body as {runId:string}).runId||data.savedToDatabase!==true))throw new AssessmentError('Persistence acknowledgement is invalid',502);
 return data;
}
export async function GET(req:NextRequest){
 if(!authorized(req))return json({error:'Sign in to view assessment history'},401);
 const nct=req.nextUrl.searchParams.get('nct'),level=req.nextUrl.searchParams.get('level');
 if(!nct||!NCT.test(nct)||(level!==null&&!/^[1-6]$/.test(level)))return json({error:'Exact NCT and optional level 1–6 required'},422);
 try{return json(await relay('?nct='+nct+(level?'&level='+level:''),req));}catch(e){return failure(e);}
}
function failure(e:unknown){return json({error:e instanceof AssessmentError?e.message:'Assessment service unavailable; no completion confirmed'},e instanceof AssessmentError?e.status:503);}
export async function POST(req:NextRequest){
 if(!authorized(req))return json({error:'Sign in to run assessments'},401);
 if(req.headers.get('origin')!==req.nextUrl.origin)return json({error:'Same-origin action required'},403);
 if(!req.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return json({error:'JSON required'},415);
 try{
  if(!req.body)throw new AssessmentError('Assessment request required',422);
  const reader=req.body.getReader(),chunks:Uint8Array[]=[];let size=0;
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>1024){await reader.cancel();throw new AssessmentError('Request too large',413);}chunks.push(value);}
  let value:unknown;try{value=JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw new AssessmentError('Invalid JSON',422);}
  const request=parseTrialRequest(value);backend();
  const report=await executeTrial(request,req.signal);
  return json(await relay('',req,report));
 }catch(e){return failure(e);}
}
