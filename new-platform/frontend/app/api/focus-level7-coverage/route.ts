import {NextResponse} from 'next/server';
import {readFile} from 'node:fs/promises';
import {validateLevel7CoverageReport} from '../../../lib/level7-focus-coverage';

export const dynamic='force-dynamic';
export const runtime='nodejs';
const headers={'Cache-Control':'private, no-store'};

export async function GET(){
 const path=process.env.FOCUS_LEVEL7_COVERAGE_REPORT_PATH;
 if(!path){
  return NextResponse.json({error:'Level 7 evidence report has not been configured; no assessment results available.'},{status:503,headers});
 }
 try{
  const raw=await readFile(path,'utf8');
  const report=validateLevel7CoverageReport(JSON.parse(raw));
  return NextResponse.json(report,{headers});
 }catch{
  return NextResponse.json({error:'Level 7 evidence report unavailable or not reconciled with the current 32-trial FOCUS roster.'},{status:503,headers});
 }
}
