"use strict";
/** MAIN R65 — local Chromium verification for independent scientific reviewer
 * readiness. Emulates iPhone width/touch, NOT a physical iPhone or authenticated
 * clinical reviewer session. Does not click original PDF links or submit grades.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {chromium}=require("playwright");

const BASE="http://127.0.0.1:3158/predictions/assessment";
const ROOT=process.env.RECEIPT_DIR||"/tmp/main-r65-chromium";
const PROFILES=[
 {name:"desktop-1365",width:1365,height:850,mobile:false},
 {name:"iphone-390",width:390,height:844,mobile:true}
];
const observations=[];

async function checkProfile(browser,profile){
 const context=await browser.newContext({
  viewport:{width:profile.width,height:profile.height},
  deviceScaleFactor:profile.mobile?2:1,
  isMobile:profile.mobile,hasTouch:profile.mobile
 });
 const page=await context.newPage(),errors=[];
 page.on("pageerror",e=>errors.push(String(e)));
 try{
  const response=await page.goto(BASE+"?nct=NCT04544293",
    {waitUntil:"domcontentloaded",timeout:30000});
  assert.equal(response?.status(),200);
  const panel=page.locator('section[aria-label="R65 independent reviewer readiness"]');
  await panel.waitFor({state:"visible",timeout:20000});
  const all=await panel.innerText();
  assert.match(all,/Independent scientific adjudication/);
  assert.match(all,/UNASSESSED · SOURCE ONLY/);
  assert.match(all,/0 \/ 8 domains/);
  assert.match(all,/ABSTAIN · NOT CALIBRATED/);
  assert.match(all,/No independent reviewer has signed/);
  assert.equal(await panel.locator("details").count(),9,
    "eight domain review controls and one required original-evidence record");
  const first=panel.locator("details").first();
  await first.locator("summary").click();
  assert.equal(await first.evaluate(el=>el.open),true);
  const text=await first.innerText();
  assert.match(text,/Verify phase, indication, patient-relevant original endpoint/);
  assert.match(text,/Phase verification: pending/);
  assert.match(text,/Scientific score: not assigned/);
  assert.equal(await first.getByRole("link",{name:"View original source PDFs and page numbers"})
     .getAttribute("href"),"#original-methods-r64");
  await first.locator("summary").click();
  assert.equal(await first.evaluate(el=>el.open),false);
  const fields=panel.locator("details").last();
  await fields.locator("summary").click();
  assert.equal(await fields.locator("li").count(),17,
    "all original reviewer attestation and source-provenance fields displayed");
  assert.match(await fields.innerText(),/second Independent Verifier/i);
  assert.match(await fields.innerText(),/review Event Id/i);
  assert.match(await panel.innerText(),/No signoff fields are filled automatically/);
  await page.screenshot({path:path.join(ROOT,profile.name+"-reviewer-checklist.png"),
    fullPage:false});

  const second=await page.goto(BASE+"?nct=NCT05126758",
    {waitUntil:"domcontentloaded",timeout:30000});
  assert.equal(second?.status(),200);
  const without=page.locator('section[aria-label="R65 independent reviewer readiness"]');
  await without.waitFor({state:"visible",timeout:20000});
  assert.equal(await without.locator("details").count(),9);
  const leadLabels=await without.locator("details").first().locator("summary span").allTextContents();
  assert.ok(leadLabels.some(x=>x.includes("0 archived PDF page leads")));
  assert.match(await without.innerText(),/REVIEW PENDING · SCORE WITHHELD/);
  assert.match(await without.innerText(),/UNASSESSED · SOURCE ONLY/);
  assert.match(await without.innerText(),/ABSTAIN · NOT CALIBRATED/);
  assert.equal(errors.length,0,"no browser JavaScript runtime failures");
  if(profile.mobile){
   const m=await without.evaluate(el=>({
    width:el.getBoundingClientRect().width,
    screen:document.documentElement.clientWidth
   }));
   assert.ok(m.width<=m.screen+2,"review docket fits iPhone-width viewport");
  }
  observations.push({profile:profile.name,width:profile.width,height:profile.height,
    domainChecklists:8,reviewRecordRequiredFields:17,
    ungradedMissingOriginalDocsAllowed:true,
    phaseVerified:false,independentClinicalSignoffs:0,
    FDAOutcome:"ABSTAIN",pageErrors:errors});
 }finally{await context.close();}
}

(async()=>{
 fs.mkdirSync(ROOT,{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
  for(const profile of PROFILES)await checkProfile(browser,profile);
  fs.writeFileSync(path.join(ROOT,"R65_LOCAL_BROWSER_ACCEPTANCE.json"),
   JSON.stringify({schema:"MAIN_R65_LOCAL_REVIEW_READINESS_CHROMIUM",
    observations,physicalIPhoneTested:false,
    signedInClinicalReviewerSessionTested:false,
    clinicalScoresRecorded:0,productionWrites:false},null,2)+"\n");
  console.log(JSON.stringify({status:"PASS",profiles:observations.map(x=>x.profile),
    clinicalScoresRecorded:0,productionWrites:false,
    signedInClinicalReviewerSessionTested:false}));
 }finally{await browser.close();}
})().catch(error=>{console.error("MAIN_R65_REVIEWER_CHROME_FAILED:",error);
 process.exitCode=1;});
