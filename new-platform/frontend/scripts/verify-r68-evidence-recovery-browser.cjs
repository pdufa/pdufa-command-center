"use strict";
/** MAIN R68 actual LOCAL Chromium evidence-recovery interactive acceptance:
 * desktop and 390px emulated touch viewport, never actual signed-in iPhone.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const {chromium}=require("playwright");
const BASE="http://127.0.0.1:3157/predictions/evidence-gaps";
const OUT=process.env.RECEIPT_DIR||"/tmp/main-r68-browser";
const profiles=[
 {name:"desktop",width:1365,height:850,mobile:false},
 {name:"iphone-390px",width:390,height:844,mobile:true}
];
const receipts=[];
async function verify(browser,profile){
 const context=await browser.newContext({
  viewport:{width:profile.width,height:profile.height},
  isMobile:profile.mobile,hasTouch:profile.mobile,
  deviceScaleFactor:profile.mobile?2:1,
 });
 const page=await context.newPage(),errors=[];
 page.on("pageerror",e=>errors.push(String(e)));
 try{
  const response=await page.goto(BASE,{waitUntil:"domcontentloaded",timeout:30000});
  assert.equal(response?.status(),200);
  const board=page.locator('section[aria-label="R68 scientific evidence recovery board"]');
  await board.waitFor({state:"visible",timeout:15000});
  await board.getByRole("heading",{name:"Scientific evidence recovery · 29 FOCUS trials"}).waitFor();
  assert.equal(await board.locator('details[aria-label^="R68 evidence for"]').count(),29);
  assert.match(await board.innerText(),/Source availability/);
  assert.match(await board.innerText(),/ABSTAIN/);
  assert.match(await board.innerText(),/NOT CALIBRATED/);
  const query=board.getByRole("searchbox",{name:"Search source recovery trials"});
  const filter=board.getByRole("combobox",{name:"Filter source recovery trials"});
  for(const kind of ["PRIMARY","SAFETY","METHODS"]){
   await filter.selectOption(kind);
   assert.equal(await board.locator('details[aria-label^="R68 evidence for"]').count(),17,
    "17 exact trial source-recovery cases in each missing category "+kind);
  }
  await filter.selectOption("ALL");
  await query.fill("SVRA");
  assert.equal(await board.locator('details[aria-label^="R68 evidence for"]').count(),1);
  const savara=board.locator('details[aria-label^="R68 evidence for"]').first();
  await savara.locator("summary").first().click();
  assert.equal(await savara.evaluate(el=>el.open),true);
  assert.equal(await savara.locator("ol li").count(),5);
  assert.equal(await savara.getByRole("link",{name:"Open complete scientific assessment"}).getAttribute("href"),
   "/predictions/assessment?nct=NCT04544293");
  assert.equal(await savara.getByRole("link",{name:"Original ClinicalTrials.gov record"}).getAttribute("href"),
   "https://clinicaltrials.gov/study/NCT04544293");
  await page.screenshot({path:path.join(OUT,profile.name+"-savara-recovery.png"),fullPage:false});
  await query.fill("NCT05126758");
  assert.equal(await board.locator('details[aria-label^="R68 evidence for"]').count(),1);
  const capr=board.locator('details[aria-label^="R68 evidence for"]').first();
  await capr.locator("summary").first().click();
  assert.match(await capr.innerText(),/Recover original primary endpoint results/);
  assert.match(await capr.innerText(),/Recover original protocol and statistical-analysis-plan PDFs/);
  assert.equal(await capr.getByRole("link",{name:"Open original PDF page leads"}).getAttribute("href"),
   "/predictions/assessment?nct=NCT05126758#original-methods-r64");
  await query.fill("");
  assert.equal(await board.locator('details[aria-label^="R68 evidence for"]').count(),29);
  if(profile.mobile){
   const rect=await board.evaluate(el=>({
    width:el.getBoundingClientRect().width,
    viewport:document.documentElement.clientWidth
   }));
   assert.ok(rect.width<=rect.viewport+2,"recovery dashboard must fit iPhone width");
  }
  assert.equal(errors.length,0,"no browser JavaScript errors");
  receipts.push({profile:profile.name,viewport:[profile.width,profile.height],
   renderedExactNcts:29,eachMissingCategory:17,
   filtersReactive:true,searchReactive:true,
   originalSourceLinksExact:true,expandCollapse:true,
   signedClinicalScores:0,validatedFDAForecasts:0,
   physicalIPhoneTested:false,browserErrors:errors});
 }finally{await context.close()}
}
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
  for(const p of profiles)await verify(browser,p);
  fs.writeFileSync(path.join(OUT,"R68_BROWSER_RESULTS.json"),
   JSON.stringify({schema:"MAIN_R68_EVIDENCE_RECOVERY_LOCAL_BROWSER",
     profiles:receipts,productionWrites:false,forecastRelease:false},null,2)+"\n");
  console.log(JSON.stringify({status:"PASS",profiles:receipts.map(x=>x.profile),
   exactTrials:29,reviewSignoffs:0,verifiedFDAForecasts:0}));
 }finally{await browser.close()}
})().catch(e=>{console.error("MAIN_R68_BROWSER_FAILED",e);process.exitCode=1;});
