'use strict';
const {chromium,webkit}=require('playwright');
const fs=require('node:fs');
const BASE='https://pdufa-new-dashboard.vercel.app';
const result={started_at:new Date().toISOString(),commit:process.env.GITHUB_SHA,run_id:process.env.GITHUB_RUN_ID,status:'INCOMPLETE',checks:{},counts:{}};
function check(value,code){result.checks[code]=Boolean(value);if(!value)throw Error(code);}
async function json(context,path){const response=await context.request.get(BASE+path,{timeout:65000});check(response.status()===200,'protected_api_http200');return response.json();}
async function authenticate(page){await page.goto(BASE,{waitUntil:'domcontentloaded'});await page.locator('#password').fill(process.env.DASHBOARD_PASSWORD);const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/auth'&&r.request().method()==='POST');await page.getByRole('button',{name:'Sign in',exact:true}).click();check((await response).status()===200,'normal_password_authentication');await page.getByRole('button',{name:'Sign out',exact:true}).waitFor();}
async function run(browser,mobile=false){
 const context=await browser.newContext(mobile?{viewport:{width:375,height:812},isMobile:true,hasTouch:true}:{viewport:{width:1440,height:1000}});
 let errors=0,mutations=0;
 await context.route('**/*',route=>{const r=route.request(),u=new URL(r.url());if(!['GET','HEAD','OPTIONS'].includes(r.method())&&!(u.origin===BASE&&u.pathname==='/api/auth'&&r.method()==='POST')){mutations++;return route.abort();}return route.continue();});
 const page=await context.newPage();page.on('pageerror',()=>errors++);
 const anonymous=await context.request.get(BASE+'/api/pipeline-research/export?limit=200');check(anonymous.status()===401,'export_requires_authentication');
 await authenticate(page);
 await page.goto(BASE+'/pipeline',{waitUntil:'domcontentloaded'});
 await page.getByRole('tablist',{name:'Pipeline display mode'}).waitFor({timeout:65000});
 await page.getByRole('table',{name:'Twenty ranked assessment overview'}).waitFor({timeout:180000});
 const headings=await page.getByRole('table',{name:'Twenty ranked assessment overview'}).locator('thead th').allTextContents();
 check(headings.filter(x=>/^#\d+ /.test(x)).length===20,(mobile?'mobile_':'desktop_')+'all20_primary_columns');
 for(const text of ['Public Phase 3 release','Days since release','Verified PDUFA date','Days until PDUFA'])check(headings.includes(text),'identity_timeline_columns_separate');
 const rows=await page.getByRole('table',{name:'Twenty ranked assessment overview'}).locator('tbody tr').count();check(rows>0,'real_research_rows_render');
 const label=mobile?'mobile':'desktop';
 for(const name of ['Cards + Dossier','Research Workflow','Compare + Analytics','Advanced Table']){await page.getByRole('tab',{name:new RegExp(name.replace('+','\\+'))}).click();check(await page.getByRole('tabpanel').isVisible(),label+'_view_'+name.split(' ')[0].toLowerCase());}
 await page.getByRole('button',{name:'Expand',exact:true}).first().click();
 const dossier=page.getByRole('region',{name:/Detailed trial dossier/});
 check(await dossier.isVisible(),label+'_exact_trial_dossier_opens');
 check(await dossier.locator('details').count()>=20,'nested_collapsed_assessments');
 if(mobile)check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+3),'iphone_no_document_overflow');
 else{
  let offset=0,version=null,total=null,seen=new Set(),findings=0,unassessed=0,competitors=0;
  do{const p=await json(context,'/api/pipeline-research/export?limit=200&offset='+offset);
   if(version===null){version=p.datasetVersion;total=p.total;result.deployed_frontend_commit=p.deploymentCommit||null;}
   check(p.datasetVersion===version&&p.total===total,'canonical_version_stable');
   for(const record of p.records){check(!seen.has(record.nctId),'no_duplicate_trials');seen.add(record.nctId);check(record.fields.length===38&&record.assessments.length===20,'all_records_preserve38_and20');findings+=record.assessments.reduce((n,a)=>n+a.verified,0);unassessed+=record.assessments.filter(a=>a.state==='NOT_ASSESSED').length;competitors+=record.competitors.length;}
   if(p.nextOffset===null)break;check(p.nextOffset>offset,'pagination_advances');offset=p.nextOffset;
  }while(true);
  check(seen.size===total,'complete_canonical_retrieval');result.counts={research_trials:total,verified_assessment_inputs:findings,unassessed_assessments:unassessed,documented_competitors:competitors};
  const pool=await json(context,'/api/scope-funnel?view=pool&limit=50');result.counts.published_pool_records=pool.total;result.counts.qualified_programs=pool.overview.qualifiedPrograms;
  const archive=await json(context,'/api/archive-scope');result.archive_scope={expected_records:archive.expected_records??archive.original_scope_records??null,physical_records:archive.physical_records??archive.archive_records??null,status:archive.status??null};
 }
 check(errors===0,label+'_no_page_exceptions');check(mutations===0,label+'_no_production_mutations');await context.close();
}
(async()=>{let desktop,mobile;try{check(Boolean(process.env.DASHBOARD_PASSWORD),'authorized_secret_available');desktop=await chromium.launch();await run(desktop);mobile=await webkit.launch();await run(mobile,true);result.status='PASS';}catch(error){result.failure_code=/^[a-z0-9_]+$/.test(error.message)?error.message:'browser_execution_failed';}finally{if(desktop)await desktop.close();if(mobile)await mobile.close();result.finished_at=new Date().toISOString();console.log('PDUFA_PIPELINE_RESEARCH_BROWSER '+JSON.stringify(result));if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,JSON.stringify(result,null,2));if(result.status!=='PASS')process.exitCode=1;}})();
