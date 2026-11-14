'use strict';
// Normal owner login using the existing Actions secret. No credentials, cookies,
// page text, source documents, traces or screenshots are retained in artifacts.
const fs=require('node:fs');
const BASE='https://pdufa-new-dashboard.vercel.app';
const NCT='NCT04576949';
const output=process.env.ASSESSMENT_RESULT_PATH||'/tmp/assessment-production-verification.json';
const result={status:'INCOMPLETE',startedAt:new Date().toISOString(),url:BASE+'/predictions/assessment',nct:NCT,levels:[],blocker:null};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function check(ok,code){if(!ok){const e=Error(code);e.checkId=code;throw e;}}
(async()=>{
 let browser,page,phase='PREFLIGHT';
 try{
  check(process.env.DASHBOARD_PASSWORD,'MISSING_EXISTING_DASHBOARD_PASSWORD_SECRET');
  const {chromium}=require('playwright');browser=await chromium.launch({headless:true});const context=await browser.newContext();
  phase='WAITING_FOR_DEPLOYMENT';let ready=false;
  for(let attempt=0;attempt<60;attempt++){
   const response=await context.request.get(BASE+'/api/assessments/runtime?nct='+NCT);
   if(response.status()===401){ready=true;break;}await sleep(10000);
  }
  check(ready,'FRONTEND_RUNTIME_NOT_DEPLOYED');
  phase='OWNER_LOGIN';const auth=await context.request.post(BASE+'/api/auth',{headers:{Origin:BASE},data:{password:process.env.DASHBOARD_PASSWORD}});check(auth.ok(),'OWNER_LOGIN_FAILED');
  phase='NAVIGATING_TO_ASSESSMENTS';page=await context.newPage();page.on('pageerror',e=>{result.browserErrors=(result.browserErrors||[]).concat({name:e.name,code:(e.message.match(/Minified React error #\d+/)||['UNCLASSIFIED_JS_ERROR'])[0]});});const navigation=await page.goto(BASE+'/predictions/assessment?nct='+NCT,{waitUntil:'domcontentloaded',timeout:60000});result.navigationStatus=navigation?.status();phase='LOCATING_WORKBENCH';
  const workbench=page.getByRole('region',{name:'Assessment workbench'});await workbench.waitFor({timeout:45000});
  phase='EXACT_NCT_CONTROL';check(await workbench.getByLabel('Exact NCT identifier',{exact:true}).inputValue()===NCT,'EXACT_TRIAL_SELECTION');
  for(let level=1;level<=6;level++){
   phase='LEVEL_'+level+'_READING_HISTORY';
   // Reuse only an exact previously verified v2 level result to avoid needless writes.
   const prior=await context.request.get(BASE+'/api/assessments/runtime?nct='+NCT+'&level='+level);
   const old=prior.ok()?await prior.json():{runs:[]};
   const existing=old.runs.find(r=>r.engineVersion===`assessment-evidence-v2.0.1/level-${level}`&&r.mode==='CURRENT_EVIDENCE');
   let report;
   phase='LEVEL_'+level+'_SELECTING_CONTROL';await workbench.getByLabel('Assessment level',{exact:true}).selectOption(String(level));
   if(existing){
    await workbench.getByRole('button',{name:'Load saved assessment history',exact:true}).click();
    await workbench.getByText(/persisted assessment version\(s\) loaded/).waitFor({timeout:30000});
    const boxes=workbench.getByRole('checkbox');
    for(const box of await boxes.all())if(await box.isChecked())await box.uncheck();
    await workbench.getByLabel(`Level ${level} · ${existing.executedAt} · ${existing.mode} · ${existing.engineVersion}`,{exact:true}).check();
    const state=await context.request.get(BASE+'/api/assessments/runtime?nct='+NCT+'&runId='+existing.runId);
    check(state.ok(),'EXISTING_RESULT_RETRIEVAL_LEVEL_'+level);report=(await state.json()).report;
   }else{
    phase='LEVEL_'+level+'_RUNNING_CONTROL';const submitted=page.waitForResponse(r=>r.url()===BASE+'/api/assessments/runtime'&&r.request().method()==='POST');
    await workbench.getByRole('button',{name:'Run Assessment',exact:true}).click();const response=await submitted;
    check(response.status()===202,'OWNER_EXECUTION_LEVEL_'+level);const run=await response.json();
    phase='LEVEL_'+level+'_READING_PROGRESS';for(let i=0;i<150;i++){
     const response=await context.request.get(BASE+'/api/assessments/runtime?nct='+NCT+'&runId='+run.runId);check(response.ok(),'PROGRESS_RETRIEVAL_LEVEL_'+level);const state=await response.json();
     if(state.status==='FAILED')throw Object.assign(Error('EXECUTION_FAILED_LEVEL_'+level),{checkId:'EXECUTION_FAILED_LEVEL_'+level});
     if(state.status==='COMPLETED'){report=state.report;break;}await sleep(1200);
    }
   }
   check(report&&report.nct===NCT&&report.level===level&&report.engineVersion===`assessment-evidence-v2.0.1/level-${level}`,'INTENDED_ENGINE_LEVEL_'+level);
   check(report.savedToDatabase===true&&report.reportHash,'PERSISTENCE_LEVEL_'+level);
   check(report.fdaPrediction.outcome==='ABSTAIN'&&report.fdaPrediction.probability===null,'NO_FABRICATED_PREDICTION_LEVEL_'+level);
   const history=await context.request.get(BASE+'/api/assessments/runtime?nct='+NCT+'&level='+level);check(history.ok()&&(await history.json()).runs.some(r=>r.runId===report.runId),'HISTORY_LEVEL_'+level);
   phase='LEVEL_'+level+'_CHECKING_HISTORICAL_REFUSAL';const blind=await context.request.post(BASE+'/api/assessments/runtime',{headers:{Origin:BASE},data:{nct:NCT,level,mode:'BLIND_HISTORICAL',cutoffDate:'2020-01-01'}});
   check(blind.status()===409,'MISSING_HISTORICAL_SOURCE_REFUSED_LEVEL_'+level);
   result.levels.push({level,runId:report.runId,engineVersion:report.engineVersion,reportHash:report.reportHash,scientificStatus:report.scientificStatus,activationStatus:report.activationStatus,current:'PASSED',historical:'MISSING_PRE_CUTOFF_SOURCE_REFUSAL_VERIFIED_NOT_A_BLIND_ASSESSMENT'});
   // Allow the UI poller to observe completion before changing its disabled selector.
   phase='LEVEL_'+level+'_WAITING_FOR_UI';await workbench.getByRole('button',{name:'Run Assessment',exact:true}).waitFor({state:'visible'});
   await page.waitForFunction(()=>{const s=document.querySelector('section[aria-label="Assessment workbench"]');return s&&Array.from(s.querySelectorAll('button')).some(b=>b.textContent==='Run Assessment'&&!b.matches(':disabled'));},{},{timeout:30000});
   phase='LEVEL_'+level+'_VERIFYING_DISPLAY';await workbench.getByRole('article',{name:`Level ${level} saved assessment`,exact:true}).waitFor({timeout:30000});
  }
  phase='COMPARING_SAVED_RESULTS';await workbench.getByRole('button',{name:'Load saved assessment history',exact:true}).click();
  await workbench.getByText(/persisted assessment version\(s\) loaded/).waitFor({timeout:30000});
  check(await workbench.locator('article').count()>=1,'SAVED_RESULT_DISPLAY');
  // The repository's established historical test record has retained original
  // stream receipts. Use them only if genuinely captured by this past cutoff.
  phase='HISTORICAL_EXECUTION';result.historicalRuns=[];
  const HIST='NCT00116805',CUTOFF='2026-11-13';
  await workbench.getByLabel('Exact NCT identifier',{exact:true}).fill(HIST);
  await workbench.getByLabel('Evidence mode',{exact:true}).selectOption('BLIND_HISTORICAL');
  await workbench.getByLabel('Historical evidence cutoff',{exact:true}).fill(CUTOFF);
  for(let level=1;level<=6;level++){
   await workbench.getByLabel('Assessment level',{exact:true}).selectOption(String(level));
   const submitted=page.waitForResponse(r=>r.url()===BASE+'/api/assessments/runtime'&&r.request().method()==='POST');
   await workbench.getByRole('button',{name:'Run Assessment',exact:true}).click();const response=await submitted;
   if(response.status()===409){result.historicalBlocker='NO_ELIGIBLE_ORIGINAL_PRE_CUTOFF_RECEIPT';break;}
   check(response.status()===202,'HISTORICAL_SUBMISSION_LEVEL_'+level);const created=await response.json();let report;
   for(let i=0;i<60;i++){
    const response=await context.request.get(BASE+'/api/assessments/runtime?nct='+HIST+'&runId='+created.runId);check(response.ok(),'HISTORICAL_RETRIEVAL_LEVEL_'+level);const state=await response.json();
    check(state.status!=='FAILED','HISTORICAL_EXECUTION_LEVEL_'+level);if(state.status==='COMPLETED'){report=state.report;break;}await sleep(1200);
   }
   check(report&&report.level===level&&report.nct===HIST&&report.evidence.captured_at.slice(0,10)<=CUTOFF&&report.evidence.published_at<=CUTOFF,'HISTORICAL_CUTOFF_LEVEL_'+level);
   check(report.fdaPrediction.outcome==='ABSTAIN'&&report.historicalAccuracyEligible===false,'NO_FALSE_BLIND_ACCURACY_LEVEL_'+level);
   await workbench.getByRole('article',{name:`Level ${level} saved assessment`,exact:true}).waitFor({timeout:30000});
   result.historicalRuns.push({level,nct:HIST,cutoff:CUTOFF,runId:report.runId,reportHash:report.reportHash,engineVersion:report.engineVersion,status:'SOURCE_ISOLATION_VERIFIED_NOT_INDEPENDENT_BLIND_ACCURACY'});
   await page.waitForFunction(()=>{const s=document.querySelector('section[aria-label="Assessment workbench"]');return s&&Array.from(s.querySelectorAll('button')).some(b=>b.textContent==='Run Assessment'&&!b.matches(':disabled'));},{},{timeout:30000});
  }
  result.status='CURRENT_EVIDENCE_EXECUTION_VERIFIED_SCIENTIFIC_GAPS_REMAIN';
 }catch(e){result.blocker=e.checkId||phase+'_'+(e.name||'ERROR');result.failedPhase=phase;if(page){result.workbenchElements=await page.locator('section[aria-label="Assessment workbench"]').count().catch(()=>-1);result.passwordInputs=await page.locator('input[type=password]').count().catch(()=>-1);}process.exitCode=1;}
 finally{if(browser)await browser.close();result.finishedAt=new Date().toISOString();fs.writeFileSync(output,JSON.stringify(result,null,2),{mode:0o600});if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,`Assessment production verification: **${result.status}**\n\n${result.blocker||'Six current-evidence engines and persisted histories verified. Historical data/scientific gaps remain.'}\n`);console.log(result.status+(result.blocker?' ['+result.blocker+']':''));}
})();
