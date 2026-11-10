"use strict";
/** R71 actual local Chromium source-review controls at desktop/390px mobile.
 * Does not interact with external medical papers or sign clinical reviews.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const {chromium}=require("playwright");
const OUT=process.env.RECEIPT_DIR||"/tmp/r71-source-review-browser";
const cases=[
 {name:"desktop",width:1365,height:850,mobile:false},
 {name:"iphone-390px",width:390,height:844,mobile:true}
];
const receipts=[];
async function profile(browser,config){
 const ctx=await browser.newContext({
  viewport:{width:config.width,height:config.height},
  isMobile:config.mobile,hasTouch:config.mobile,
  deviceScaleFactor:config.mobile?2:1});
 const page=await ctx.newPage(),errors=[];
 page.on("pageerror",e=>errors.push(String(e)));
 try{
  const response=await page.goto("http://127.0.0.1:3157/predictions/evidence-gaps",
     {waitUntil:"domcontentloaded",timeout:30000});
  assert.equal(response?.status(),200);
  const board=page.locator('section[aria-label="R68 scientific evidence recovery board"]');
  await board.waitFor({state:"visible",timeout:18000});
  const find=board.getByRole("searchbox",{name:"Search source recovery trials"});
  const cases=()=>board.locator('details[aria-label^="R68 evidence for"]');
  async function inspect(nct){
   await find.fill(nct);
   assert.equal(await cases().count(),1,"exact NCT filtering");
   await cases().first().locator("summary").first().click();
   const panel=board.locator('section[aria-label="R71 pivotal source method intake for '+nct+'"]');
   await panel.waitFor({state:"visible",timeout:12000});
   assert.match(await panel.innerText(),/ABSTAIN/);
   assert.match(await panel.innerText(),/unassessed/i);
   // Visible safeguards must survive rendering, not merely exist in source data.
   assert.match(await panel.innerText(),/Qualified scientific reviews:\s*0/);
   assert.match(await panel.innerText(),/Future FDA decision:\s*ABSTAIN/);
   assert.match(await panel.innerText(),/independently replicated/);
   const sourceCount=await panel.locator("details").count();
   assert.equal(sourceCount,2,"source method and study-specific review accordions");
   await panel.locator("details").first().locator("summary").click();
   assert.equal(await panel.locator("article").count(),8);
   assert.equal(await panel.locator("article").filter({hasText:"UNASSESSED"}).count(),8);
   await panel.locator("details").nth(1).locator("summary").click();
   return panel;
  }
  let p=await inspect("NCT06153693");
  assert.match(await p.innerText(),/1000-imputation/);
  assert.match(await p.innerText(),/MAR\/MNAR/);
  assert.match(await p.innerText(),/protocol versions 2.1, 3.0 and 3.1/);
  assert.equal(await p.getByRole("link",{name:"Publisher protocol and supplemental materials listing"}).getAttribute("href"),
    "https://jamanetwork.com/journals/jama/fullarticle/2835763");
  const sapIndex=board.locator('section[aria-label="R73 Launch-HTN published protocol and SAP document index"]');
  await sapIndex.waitFor({state:"visible",timeout:12000});
  const sapText=await sapIndex.innerText();
  assert.match(sapText,/0\/7/);
  assert.match(sapText,/ABSTAIN/);
  assert.match(sapText,/NOT/);
  assert.equal(await sapIndex.getByRole("link",{name:"Open original public JAMA supplement index"}).getAttribute("href"),
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/");
  await sapIndex.locator("details").first().locator("summary").click();
  const links=sapIndex.locator('a[href*="/articles/instance/12210145/bin/jama-e259413-s"]');
  assert.equal(await links.count(),7,"exact original indexed protocol and SAP document links");
  for(let i=1;i<=7;i++){
    const expected="https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/jama-e259413-s"+
      String(i).padStart(3,"0")+".pdf";
    assert.equal(await links.nth(i-1).getAttribute("href"),expected);
  }
  const methods=board.locator('section[aria-label="R77 Launch-HTN original H1 H7 published methods"]');
  await methods.waitFor({state:"visible",timeout:12000});
  const methodsText=await methods.innerText();
  assert.match(methodsText,/7 .* 1 primary/);
  assert.match(methodsText,/8 .* no alpha replay/);
  assert.match(methodsText,/ABSTAIN/);
  assert.match(methodsText,/UNASSESSED/);
  assert.match(methodsText,/0\/23/);
  await methods.locator("details").first().locator("summary").click();
  assert.equal(await methods.locator("details").first().locator("article").count(),7);
  assert.equal(await methods.locator("details").first().locator("li").count(),8);
  assert.match(await methods.innerText(),/WITHIN-PARTICIPANT ANALYSIS/);
  await methods.locator("details").nth(2).locator("summary").click();
  assert.match(await methods.innerText(),/11 \/ 14 \/ 4/);
  assert.match(await methods.innerText(),/29 \/ 38 \/ 3/);
  await methods.scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(OUT,config.name+"-launch-htn-r77-method-gates.png"),fullPage:false});
  await page.screenshot({path:path.join(OUT,config.name+"-launch-htn-r73-seven-documents.png"),fullPage:false});
  const publicChronology=board.locator('section[aria-label="R78 Launch-HTN public readout and FDA review chronology"]');
  await publicChronology.waitFor({state:"visible",timeout:12000});
  const chronologyText=await publicChronology.innerText();
  assert.match(chronologyText,/2025-03-10/);
  assert.match(chronologyText,/2026-12-22/);
  assert.match(chronologyText,/database lock/);
  assert.match(chronologyText,/0\/23/);
  assert.match(chronologyText,/ABSTAIN/);
  await publicChronology.locator("details").first().locator("summary").click();
  assert.equal(await publicChronology.locator("details").first().locator("li").count(),9);
  const originalPublicLinks=publicChronology.locator('details').first().locator('a[href^="https://"]');
  assert.equal(await originalPublicLinks.count(),9);
  assert.equal(await originalPublicLinks.nth(5).getAttribute("href"),
    "https://ir.mineralystx.com/sec-filings/all-sec-filings/content/0001628280-25-011459/mlys-20250310.htm");
  assert.equal(await originalPublicLinks.nth(8).getAttribute("href"),
    "https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm");
  await publicChronology.scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(OUT,config.name+"-launch-htn-r78-public-chronology.png"),fullPage:false});
  const authenticity=board.locator('section[aria-label="R79 Launch-HTN SAP and unblinding evidence authentication"]');
  await authenticity.waitFor({state:"visible",timeout:12000});
  let authText=await authenticity.innerText();
  assert.match(authText,/Original proof requirements authenticated/);
  assert.match(authText,/0 \/ 7/);
  assert.match(authText,/none configured/);
  assert.match(authText,/ABSTAIN/);
  assert.match(authText,/0\/23/);
  assert.match(authText,/first unblinding|first unblinded|unblinding/i);
  await authenticity.locator("details").first().locator("summary").click();
  assert.equal(await authenticity.locator("details").first().locator("li").count(),7,
    "exact seven original source-authentication requirements");
  await authenticity.locator("details").nth(1).locator("summary").click();
  assert.equal(await authenticity.locator("details").nth(1).locator('a[href^="https://"]').count(),2,
    "original FDA/ICH E9 and E6R3 standards remain clickable");
  await authenticity.scrollIntoViewIfNeeded();
  if(config.mobile){
   const rect=await authenticity.evaluate(el=>({width:el.getBoundingClientRect().width,
     viewport:document.documentElement.clientWidth}));
   assert.ok(rect.width<=rect.viewport+2,"R79 original-proof gate must fit iPhone-sized viewport");
  }
  await page.screenshot({path:path.join(OUT,config.name+"-launch-htn-r79-authentication-gate.png"),fullPage:false});

  await page.screenshot({path:path.join(OUT,config.name+"-launch-htn-research.png"),fullPage:false});
  p=await inspect("NCT06081894");
  assert.match(await p.innerText(),/Two primary endpoints/);
  assert.match(await p.innerText(),/10.5% vs 0.8%/);
  p=await inspect("NCT05126758");
  assert.match(await p.innerText(),/4.55% in PUL2.0 percentage change/);
  const caprFda=board.locator('section[aria-label="R72 original FDA and issuer conflict for NCT05126758"]');
  await caprFda.waitFor({state:"visible",timeout:12000});
  const caprText=await caprFda.innerText();
  assert.match(caprText,/FDA vs applicant analysis/);
  assert.match(caprText,/p=0[.]24/);
  assert.match(caprText,/p=0[.]029/);
  assert.match(caprText,/incompatible endpoint scales/);
  assert.match(caprText,/2026-11-22/);
  assert.match(caprText,/ABSTAIN/);
  assert.match(caprText,/UNKNOWN/);
  assert.equal(await caprFda.locator("details").first().locator("article").count(),3);
  assert.equal(await caprFda.getByRole("link",{name:/Original FDA July 29 briefing/}).getAttribute("href"),
    "https://www.fda.gov/media/193839/download");
  await page.screenshot({path:path.join(OUT,config.name+"-capr-fda-conflict.png"),fullPage:false});
  assert.equal(await p.getByRole("link",{name:"Open original article / PubMed source"}).getAttribute("href"),
    "https://pubmed.ncbi.nlm.nih.gov/42526472/");
  p=await inspect("NCT05662241");
  assert.match(await p.innerText(),/Hazard ratio 0.44/);
  p=await inspect("NCT06343779");
  assert.match(await p.innerText(),/1.28 h with deucrictibant/);
  await find.fill("NCT04871282");
  assert.equal(await cases().count(),1);
  await cases().first().locator("summary").first().click();
  assert.equal(await board.locator('section[aria-label="R71 pivotal source method intake for NCT04871282"]').count(),0,
    "RINGSIDE Phase 2 article must not be counted as Phase 3 main report");
  await find.fill("");
  assert.equal(await cases().count(),29);
  if(config.mobile){
   const x=await board.evaluate(el=>({
    width:el.getBoundingClientRect().width,
    viewport:document.documentElement.clientWidth
   }));
   assert.ok(x.width<=x.viewport+2,"R71 scientific intake must fit iPhone-sized screen");
  }
  assert.equal(errors.length,0,"no browser JS exceptions");
  receipts.push({profile:config.name,viewport:[config.width,config.height],
   originalTrials:29,exactArticleCases:5,sourceDomainsPerCase:8,
   signedScientificScores:0,validatedFDAForecasts:0,
   studySpecificReviewOpeningPassed:true,physicalIPhoneTested:false,
   browserErrors:errors});
 }finally{await ctx.close()}
}
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
  for(const c of cases)await profile(browser,c);
  fs.writeFileSync(path.join(OUT,"R71_SOURCE_REVIEW_BROWSER.json"),
   JSON.stringify({schema:"MAIN_R71_FIVE_MAIN_REPORTS_SOURCE_ONLY_LOCAL_CHROMIUM",
    profiles:receipts,originalSAPsSigned:0,clinicalScoreRelease:false,
    futureFDAOutcome:"ABSTAIN",productionWrites:false},null,2)+"\n");
  console.log(JSON.stringify({status:"PASS",profiles:receipts.map(x=>x.profile),
    fiveTrialSourceCases:5,originalMethodReviewSlots:40,
    clinicalGradesSigned:0,fdaFutureOutcome:"ABSTAIN"}));
 }finally{await browser.close()}
})().catch(e=>{console.error("MAIN_R71_BROWSER_FAILED:",e);process.exitCode=1;});
