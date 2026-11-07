const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const base=process.argv[2]||'http://localhost:3000',output=process.argv[3]||'/tmp/bottom-browser';fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 const response=await page.goto(base+'/p3-post-data',{waitUntil:'networkidle'});assert.equal(response.status(),200);
 const active=require('../data/p3PostDataActive.json').records;
 assert.equal(await page.locator('tbody > tr').count(),active.length);
 assert.equal(await page.locator('[data-clinical-nct]').count(),5);
 const list=await (await page.request.get(base+'/api/p3-post-data-research')).json();
 assert.equal(list.rows.length,5);
 for(const row of list.rows){
  assert.ok(active.some(r=>r.nct===row.nctId));
  const detail=await (await page.request.get(base+'/api/p3-post-data-research?nctId='+row.nctId)).json();
  assert.equal(detail.trial.clinicalFullScore,row.clinicalFullScore);
  assert.ok(detail.history.every(h=>h.nctId===row.nctId));
  const cell=page.locator('[data-clinical-nct="'+row.nctId+'"]');
  await cell.locator('button').click();await cell.locator('article').first().waitFor();
  assert.equal(await cell.locator('[role=region] > div > article').count(),5);
  assert.equal(await cell.locator('button').getAttribute('aria-expanded'),'true');
  await cell.locator('summary').filter({hasText:'Exact-NCT score history'}).click();
  assert.ok(await cell.getByText('Saved factor grades and evidence',{exact:true}).count());
  await cell.locator('button').click();
 }
 assert.equal((await page.request.get(base+'/api/p3-post-data-research?nctId=NCT05257408')).status(),404);
 assert.equal((await page.request.get(base+'/api/bottom-only-completion')).status(),404);
 const csv=await (await page.request.get(base+'/api/p3-post-data-research?format=rating-evidence')).text();assert.equal(csv.trim().split('\r\n').length,26);
 const savara=page.locator('[data-clinical-nct="NCT04544293"]');
 await savara.locator('button').click();await savara.locator('article').first().waitFor();await savara.scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(output,'desktop.png')});
 await page.setViewportSize({width:390,height:844});await savara.scrollIntoViewIfNeeded();
 const horizontal=await savara.locator('[role=region]').evaluate(e=>({client:e.clientWidth,scroll:e.scrollWidth}));
 assert.ok(horizontal.scroll>horizontal.client);
 await page.screenshot({path:path.join(output,'mobile.png')});assert.deepEqual(errors,[]);
 const result={base,activeRows:active.length,exactResearchMatches:5,testedClinicalCards:25,historyVerified:true,apiParityVerified:true,activeFilteringVerified:true,retiredEndpointStill404:true,mobileHorizontalExpansion:horizontal,pageErrors:errors};
 fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
