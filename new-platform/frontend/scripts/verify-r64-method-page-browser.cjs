"use strict";
/** MAIN R64 local real-Chromium verification of read-only method page citations.
 * Desktop and iPhone-sized viewport are test emulations, not a signed-in
 * physical device session. Never navigates the third-party study PDFs.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {chromium}=require("playwright");

const BASE="http://127.0.0.1:3157/predictions/assessment";
const OUT=process.env.RECEIPT_DIR||"/tmp/main-r64-browser";
const PROFILES=[
 {name:"desktop",width:1365,height:850,mobile:false},
 {name:"iphone-390px",width:390,height:844,mobile:true}
];
const result=[];

async function runProfile(browser,profile){
 const ctx=await browser.newContext({
   viewport:{width:profile.width,height:profile.height},
   deviceScaleFactor:profile.mobile?2:1,
   isMobile:profile.mobile,hasTouch:profile.mobile
 });
 const page=await ctx.newPage(),errors=[];
 page.on("pageerror",e=>errors.push(String(e)));
 try{
   const response=await page.goto(BASE+"?nct=NCT04544293",
     {waitUntil:"domcontentloaded",timeout:30000});
   assert.equal(response?.status(),200);
   const panel=page.locator('section[aria-label="R64 original method page review"]');
   await panel.waitFor({state:"visible",timeout:15000});
   await panel.getByRole("heading",{name:/Scientific assessment page references/}).waitFor();
   assert.equal(await panel.locator("details").count(),8,
     "each selected exact-NCT case has precisely eight scientific source domains");
   const banner=await panel.innerText();
   assert.match(banner,/4 · Evidence collection/);
   assert.match(banner,/UNASSESSED · SOURCE ONLY/);
   assert.match(banner,/8 · 0 adjudicated/);
   assert.match(banner,/ABSTAIN · NOT CALIBRATED/);
   assert.match(banner,/47 page references for this NCT/);
   assert.match(banner,/466 page references/);
   const first=panel.locator("details").first();
   await first.locator("summary").click();
   assert.equal(await first.evaluate(el=>el.open),true,
     "native scientific-method accordion must open from click");
   const pdf=first.getByRole("link",{name:/Prot_000.pdf · PDF page 2/});
   await pdf.waitFor({state:"visible",timeout:8000});
   assert.equal(await pdf.getAttribute("href"),
     "https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf#page=2");
   await first.locator("summary").click();
   assert.equal(await first.evaluate(el=>el.open),false,
     "native domain must collapse on second click");
   await panel.locator("details").nth(3).locator("summary").click();
   assert.ok((await panel.innerText()).includes("Scientific grade:"));
   await page.screenshot({path:path.join(OUT,profile.name+"-original-methods.png"),
     fullPage:false});

   const second=await page.goto(BASE+"?nct=NCT05126758",
     {waitUntil:"domcontentloaded",timeout:30000});
   assert.equal(second?.status(),200);
   const missing=page.locator('section[aria-label="R64 original method page review"]');
   await missing.waitFor({state:"visible",timeout:15000});
   assert.equal(await missing.locator("details").count(),8,
     "no current original PDFs must still show eight unassessed review domains");
   assert.match(await missing.innerText(),/0 page references for this NCT/);
   await missing.locator("details").first().locator("summary").click();
   assert.match(await missing.innerText(),
     /No machine-detected page reference from the archived current public documents/);
   assert.match(await missing.innerText(),/do not infer an absent method or negative result/);
   assert.equal(errors.length,0,"no frontend browser JavaScript errors");
   if(profile.mobile){
     const rect=await missing.evaluate(el=>({
       width:el.getBoundingClientRect().width,
       viewport:document.documentElement.clientWidth
     }));
     assert.ok(rect.width<=rect.viewport+2,"research panel fits mobile width");
   }
   result.push({profile:profile.name,viewport:[profile.width,profile.height],
     sourceDomains:8,savaraPdfPageLeadCount:47,
     noCurrentPdfCaseDomains:8,reactiveExpandCollapse:true,
     originalPdfUrlCorrect:true,originalStudyNotGraded:true,
     officialFutureFDAOutcome:"ABSTAIN",browserErrors:errors});
 }finally{await ctx.close();}
}
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
  for(const p of PROFILES)await runProfile(browser,p);
  fs.writeFileSync(path.join(OUT,"R64_BROWSER_VERIFICATION.json"),
    JSON.stringify({schema:"MAIN_R64_LOCAL_METHOD_PAGE_REAL_BROWSER_E2E",
      environments:result,physicalIPhoneTested:false,
      signedInProductionTested:false,productionWrites:false},null,2)+"\n");
  console.log(JSON.stringify({status:"PASS",profiles:result.map(r=>r.profile),
    sourceDomains:8,scientificReviewsSigned:0,
    futureFDAForecast:"ABSTAIN",physicalIPhoneTested:false}));
 }finally{await browser.close();}
})().catch(e=>{console.error("MAIN_R64_METHOD_BROWSER_FAILED:",e);
  process.exitCode=1;});
