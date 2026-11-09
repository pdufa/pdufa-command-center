"use strict";
/** R67 local Chromium source-only phase panel e2e. Not a physical iPhone,
 * signed clinical reviewer, or a live FDA regulatory source attestation.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const {chromium}=require("playwright");
const BASE="http://127.0.0.1:3157/predictions/assessment?nct=";
const OUT=process.env.RECEIPT_DIR||"/tmp/main-r67-browser";
const profiles=[
 {name:"desktop",width:1365,height:850,mobile:false},
 {name:"iphone-390px",width:390,height:844,mobile:true}
];
const report=[];
async function verify(browser,p){
 const ctx=await browser.newContext({viewport:{width:p.width,height:p.height},
  isMobile:p.mobile,hasTouch:p.mobile,deviceScaleFactor:p.mobile?2:1});
 const page=await ctx.newPage(),errors=[];
 page.on("pageerror",e=>errors.push(String(e)));
 const openCase=async nct=>{
   const resp=await page.goto(BASE+nct,{waitUntil:"domcontentloaded",timeout:30000});
   assert.equal(resp?.status(),200,"development route must render");
   const el=page.locator('section[aria-label="R67 original registry phase source evidence"]');
   await el.waitFor({state:"visible",timeout:15000});
   return el;
 };
 try{
  let panel=await openCase("NCT04544293");
  const copy=await panel.innerText();
  assert.match(copy,/SVRA/);
  assert.match(copy,/Phase 3/);
  assert.match(copy,/ACTIVE NOT RECRUITING/);
  assert.match(copy,/2026-11-03/);
  assert.match(copy,/NOT VERIFIED/);
  assert.match(copy,/UNASSESSED · SOURCE ONLY/);
  assert.match(copy,/ABSTAIN/);
  assert.equal(await panel.getByRole("link",{name:"Open original ClinicalTrials.gov study"}).getAttribute("href"),
   "https://clinicaltrials.gov/study/NCT04544293");
  const boxes=panel.locator("details");
  assert.equal(await boxes.count(),2);
  await boxes.first().locator("summary").click();
  assert.equal(await boxes.first().evaluate(el=>el.open),true);
  assert.match(await boxes.first().innerText(),/164 \(actual\)/);
  assert.match(await boxes.first().innerText(),/2023-11-30 \(actual\)/);
  await boxes.first().locator("summary").click();
  assert.equal(await boxes.first().evaluate(el=>el.open),false);
  await boxes.nth(1).locator("summary").click();
  assert.match(await boxes.nth(1).innerText(),/source requires independent verification/i);
  const phase=await page.locator('section[aria-label="R67 original registry phase source evidence"]').evaluate(el=>el.getBoundingClientRect().y+scrollY);
  const methods=await page.locator('section[aria-label="R64 original method page review"]').evaluate(el=>el.getBoundingClientRect().y+scrollY);
  const reviewers=await page.locator('section[aria-label="R65 independent reviewer readiness"]').evaluate(el=>el.getBoundingClientRect().y+scrollY);
  const outcome=await page.locator('section[aria-label="R67 FDA prediction readiness summary"]').evaluate(el=>el.getBoundingClientRect().y+scrollY);
  assert.ok(phase<methods&&methods<reviewers&&reviewers<outcome,
    "phase-first source and science-review status must be in required order");
  await page.screenshot({path:path.join(OUT,p.name+"-svra-phase.png"),fullPage:false});
  panel=await openCase("NCT04871282");
  assert.match(await panel.innerText(),/Combined Phase 2\/3/);
  await panel.locator("details").nth(1).locator("summary").click();
  assert.match(await panel.innerText(),/Combined Phase 2\/3 designation requires study-design review/);
  panel=await openCase("NCT06331299");
  await panel.locator("details").first().locator("summary").click();
  assert.match(await panel.innerText(),/N\/A \(not randomized\)/);
  await panel.locator("details").nth(1).locator("summary").click();
  assert.match(await panel.innerText(),/allocation N\/A/i);
  assert.equal(errors.length,0,"no uncaught browser errors");
  if(p.mobile){
    const dims=await panel.evaluate(el=>({
      panelWidth:el.getBoundingClientRect().width,
      viewport:document.documentElement.clientWidth}));
    assert.ok(dims.panelWidth<=dims.viewport+2,"source panel must fit phone viewport");
  }
  report.push({profile:p.name,viewport:[p.width,p.height],phasePanelsVerified:3,
    originalLinksVerified:true,phaseFirstOrderVerified:true,
    sourceOnlyNoFDAForecast:true,errors});
 }finally{await ctx.close();}
}
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
  for(const p of profiles)await verify(browser,p);
  fs.writeFileSync(path.join(OUT,"R67_BROWSER_VERIFICATION.json"),
   JSON.stringify({schema:"MAIN_R67_LOCAL_PHASE_FIRST_REAL_BROWSER_ACCEPTANCE",
    sourceReported29Trials:29,independentPhaseReviews:0,
    validatedFutureFDAForecasts:0,productionWrites:false,
    signedInProductionOrPhysicalIPhoneTested:false,profiles:report},null,2)+"\n");
  console.log(JSON.stringify({status:"PASS",profiles:report.map(r=>r.profile),
    phaseStatusSourceOnly:true,officialFdaOutcome:"ABSTAIN"}));
 }finally{await browser.close();}
})().catch(e=>{console.error("MAIN_R67_PHASE_BROWSER_FAILURE",e);process.exitCode=1;});
