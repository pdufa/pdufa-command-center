"use strict";
/** R69: real LOCAL Chromium interaction test; NOT a physical iPhone or
 * authenticated expert review of the linked external publication content.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const {chromium}=require("playwright");
const OUT=process.env.RECEIPT_DIR||"/tmp/main-r69-browser";
const profiles=[
 {name:"desktop",width:1365,height:850,mobile:false},
 {name:"iphone-390px",width:390,height:844,mobile:true}
];
const output=[];
async function verify(browser,profile){
 const context=await browser.newContext({
  viewport:{width:profile.width,height:profile.height},
  isMobile:profile.mobile,hasTouch:profile.mobile,
  deviceScaleFactor:profile.mobile?2:1
 });
 const page=await context.newPage(),errors=[];
 page.on("pageerror",error=>errors.push(String(error)));
 try{
  const response=await page.goto(
   "http://127.0.0.1:3157/predictions/evidence-gaps",
   {waitUntil:"domcontentloaded",timeout:30000});
  assert.equal(response?.status(),200);
  const board=page.locator('section[aria-label="R68 scientific evidence recovery board"]');
  await board.waitFor({state:"visible",timeout:15000});
  assert.match(await board.innerText(),/11/);
  assert.match(await board.innerText(),/unverified references, not accepted exact-NCT trial results/);
  const search=board.getByRole("searchbox",{name:"Search source recovery trials"});
  const cases=board.locator('details[aria-label^="R68 evidence for"]');

  await search.fill("NCT05126758");
  assert.equal(await cases.count(),1);
  await cases.first().locator("summary").first().click();
  let publications=board.locator('section[aria-label="R69 registry publication leads for NCT05126758"]');
  await publications.waitFor({state:"visible"});
  assert.match(await publications.innerText(),/NOT been verified/);
  const paper=publications.getByRole("link",{name:"Open PubMed PMID 42526472"});
  assert.equal(await paper.getAttribute("href"),
   "https://pubmed.ncbi.nlm.nih.gov/42526472/");
  assert.match(await publications.innerText(),/Confirmed exact-trial primary outcomes: 0/);

  await search.fill("NCT06081894");
  assert.equal(await cases.count(),1);
  await cases.first().locator("summary").first().click();
  publications=board.locator('section[aria-label="R69 registry publication leads for NCT06081894"]');
  await publications.waitFor({state:"visible"});
  assert.equal(await publications.getByRole("link",{name:/Open PubMed PMID/}).count(),3);
  await page.screenshot({path:path.join(OUT,profile.name+"-three-original-pubmed-leads.png"),
    fullPage:false});

  await search.fill("NCT05059223");
  assert.equal(await cases.count(),1);
  await cases.first().locator("summary").first().click();
  publications=board.locator('section[aria-label="R69 registry publication leads for NCT05059223"]');
  await publications.waitFor({state:"visible"});
  assert.match(await publications.innerText(),/No PubMed reference is listed in this retained registry copy/);
  assert.equal(await publications.getByRole("link",{name:"Search PubMed for this exact NCT"}).getAttribute("href"),
   "https://pubmed.ncbi.nlm.nih.gov/?term=NCT05059223");
  assert.equal(await publications.getByRole("link",{name:/Open PubMed PMID/}).count(),0);

  await search.fill("");
  assert.equal(await cases.count(),29);
  if(profile.mobile){
   const m=await board.evaluate(el=>({
    width:el.getBoundingClientRect().width,
    viewport:document.documentElement.clientWidth
   }));
   assert.ok(m.width<=m.viewport+2,"research citation panel must fit mobile viewport");
  }
  assert.equal(errors.length,0,"no unexpected browser JavaScript error");
  output.push({profile:profile.name,viewport:[profile.width,profile.height],
   researchNcts:29,missingPrimaryNcts:17,unreviewedPubmedReferences:11,
   originalCitationLinksCorrect:true,exactNctPaperMatchVerified:false,
   localBrowserInteractionPassed:true,physicalIPhoneTested:false,
   clinicalSignoffs:0,validatedFDAForecasts:0,browserErrors:errors});
 }finally{await context.close()}
}
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
  for(const p of profiles)await verify(browser,p);
  fs.writeFileSync(path.join(OUT,"R69_BROWSER_RESULTS.json"),
   JSON.stringify({schema:"MAIN_R69_LOCAL_SOURCE_REFERENCE_BROWSER",
    profiles:output,originalExternalPubmedArticlesNotFetched:true,
    productionWrites:false,modelTraining:false},null,2)+"\n");
  console.log(JSON.stringify({status:"PASS",profiles:output.map(p=>p.profile),
   originalRegistryReferenceLeads:11,
   papersScientificallyVerified:0,fdaForecast:"ABSTAIN"}));
 }finally{await browser.close()}
})().catch(e=>{console.error("MAIN_R69_BROWSER_VERIFICATION_FAILED",e);
 process.exitCode=1;});
