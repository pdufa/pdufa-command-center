"use strict";
/** R70 real LOCAL Chromium source-role acceptance, desktop and 390px mobile.
 * Not physical iPhone Safari or independent signed medical full-text review.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const {chromium}=require("playwright");
const OUT=process.env.RECEIPT_DIR||"/tmp/main-r70-browser";
const cases=[
 {name:"desktop",width:1365,height:850,mobile:false},
 {name:"iphone-390px",width:390,height:844,mobile:true}
];
const checked=[];
async function profile(browser,config){
 const context=await browser.newContext({
  viewport:{width:config.width,height:config.height},
  isMobile:config.mobile,hasTouch:config.mobile,
  deviceScaleFactor:config.mobile?2:1
 });
 const page=await context.newPage(),errors=[];
 page.on("pageerror",e=>errors.push(String(e)));
 try{
  const response=await page.goto(
   "http://127.0.0.1:3157/predictions/evidence-gaps",
   {waitUntil:"domcontentloaded",timeout:30000});
  assert.equal(response?.status(),200);
  const board=page.locator('section[aria-label="R68 scientific evidence recovery board"]');
  await board.waitFor({state:"visible",timeout:20000});
  const coverage=board.locator('[aria-label="R70 publication abstract role counts"]');
  await coverage.waitFor({state:"visible",timeout:10000});
  assert.match(await coverage.innerText(),/Phase 3 primary result candidates/);
  assert.match(await coverage.innerText(),/5/);
  assert.match(await coverage.innerText(),/None has passed independent full-text/);
  const search=board.getByRole("searchbox",{name:"Search source recovery trials"});
  const selected=()=>board.locator('details[aria-label^="R68 evidence for"]');
  async function inspect(nct){
   await search.fill(nct);
   assert.equal(await selected().count(),1,"exact NCT search should resolve one trial");
   await selected().first().locator("summary").first().click();
   const panel=board.locator('section[aria-label="R70 publication role classification for '+nct+'"]');
   await panel.waitFor({state:"visible",timeout:10000});
   return panel;
  }

  let panel=await inspect("NCT06081894");
  assert.equal(await panel.locator("div[class*='entry']").count(),3);
  const desc=await panel.innerText();
  assert.match(desc,/Primary Phase 3 results described in abstract/);
  assert.match(desc,/Additional analysis of the same trial/);
  assert.match(desc,/ACACIA-HCM aficamten original Phase 3 report/);
  assert.match(desc,/not a signed scientific assessment/);
  assert.equal(await panel.getByRole("link",{name:"PubMed 42663312 · Inspect source abstract"}).getAttribute("href"),
    "https://pubmed.ncbi.nlm.nih.gov/42663312/");
  await page.screenshot({path:path.join(OUT,config.name+"-acacia-paper-triage.png"),
    fullPage:false});

  panel=await inspect("NCT04871282");
  assert.match(await panel.innerText(),/Phase 2 component, not Phase 3 results/);
  assert.doesNotMatch(await panel.innerText(),/Primary Phase 3 results described in abstract/);

  panel=await inspect("NCT02500381");
  assert.match(await panel.innerText(),/Earlier-phase cohort, not pivotal trial outcome/);
  assert.match(await panel.innerText(),/Background\/reference study, not pivotal trial outcome/);
  assert.doesNotMatch(await panel.innerText(),/Primary Phase 3 results described in abstract/);

  panel=await inspect("NCT05126758");
  assert.match(await panel.innerText(),/HOPE-3 deramiocel Phase 3 trial/);
  assert.match(await panel.innerText(),/Independently signed grades: 0/);

  await search.fill("NCT05059223");
  assert.equal(await selected().count(),1);
  await selected().first().locator("summary").first().click();
  assert.equal(await board.locator('section[aria-label="R70 publication role classification for NCT05059223"]').count(),0);
  assert.match(await board.innerText(),/No PubMed reference is listed in this retained registry copy/);
  await search.fill("");
  assert.equal(await selected().count(),29);
  assert.match(await board.innerText(),/ABSTAIN/);
  if(config.mobile){
   const rect=await board.evaluate(el=>({
    width:el.getBoundingClientRect().width,
    viewport:document.documentElement.clientWidth
   }));
   assert.ok(rect.width<=rect.viewport+2,"R70 summary and source roles fit 390px viewport");
  }
  assert.equal(errors.length,0,"no browser runtime exceptions");
  checked.push({profile:config.name,width:config.width,height:config.height,
   totalSourcePubmedLeads:11,
   candidatePrimaryAbstractReports:5,
   originalTrialRecords:29,
   browserRoleFilterExpandPassed:true,
   fullScientificAdjudications:0,
   calibratedFdaApprovalForecasts:0,
   physicalIPhoneTested:false,
   browserErrors:errors});
 }finally{await context.close()}
}
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
  for(const config of cases)await profile(browser,config);
  fs.writeFileSync(path.join(OUT,"R70_BROWSER_RESULTS.json"),
   JSON.stringify({schema:"MAIN_R70_ABSTRACT_ROLE_LOCAL_BROWSER",
    checked,clinicalMethodGradesReleased:false,
    officialFDAOutcome:"ABSTAIN",productionWrites:false},null,2)+"\n");
  console.log(JSON.stringify({status:"PASS",profiles:checked.map(x=>x.profile),
    publicationReferences:11,primaryAbstractCandidates:5,
    qualifiedClinicalSignoffs:0}));
 }finally{await browser.close()}
})().catch(e=>{console.error("MAIN_R70_BROWSER_FAILED:",e);process.exitCode=1;});
