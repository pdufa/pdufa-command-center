"use strict";
/** MAIN R70. LOCAL Chromium source article UI acceptance (desktop & 390px
 * emulated iPhone touch), not a qualified clinical review or actual Safari.
 */
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const {chromium}=require("playwright");
const OUT=process.env.RECEIPT_DIR||"/tmp/main-r70-browser";
const profiles=[
 {name:"desktop",width:1365,height:850,mobile:false},
 {name:"iphone-390px",width:390,height:844,mobile:true}
];
const successes=[];

async function verifyProfile(browser,profile){
 const context=await browser.newContext({viewport:{
  width:profile.width,height:profile.height},deviceScaleFactor:profile.mobile?2:1,
  isMobile:profile.mobile,hasTouch:profile.mobile});
 const page=await context.newPage(),errors=[];
 page.on("pageerror",err=>errors.push(String(err)));
 try{
  const response=await page.goto(
    "http://127.0.0.1:3157/predictions/evidence-gaps",
    {waitUntil:"domcontentloaded",timeout:30000});
  assert.equal(response?.status(),200);
  const board=page.locator('section[aria-label="R68 scientific evidence recovery board"]');
  await board.waitFor({state:"visible",timeout:15000});
  assert.equal(await board.locator('details[aria-label^="R68 evidence for"]').count(),29);
  assert.match(await board.innerText(),/Revision 70: original PubMed metadata and abstracts retrieved/);
  assert.match(await board.innerText(),/pivotal Phase 3 results independently adjudicated/);
  const search=board.getByRole("searchbox",{name:"Search source recovery trials"});
  const study=()=>board.locator('details[aria-label^="R68 evidence for"]');

  await search.fill("NCT04871282");
  assert.equal(await study().count(),1);
  await study().first().locator("summary").first().click();
  let panel=board.locator('section[aria-label="R70 article metadata for NCT04871282"]');
  await panel.waitFor({state:"visible"});
  assert.equal(await panel.locator("details").count(),1);
  await panel.locator("details").first().locator("summary").click();
  assert.match(await panel.innerText(),/RINGSIDE Phase II/);
  assert.match(await panel.innerText(),/Title identifies Phase 2 component/);
  assert.match(await panel.innerText(),/NOT SCIENTIFICALLY ADJUDICATED/);
  assert.equal(await panel.getByRole("link",{name:"Open original PubMed article PMID 42848980"}).getAttribute("href"),
    "https://pubmed.ncbi.nlm.nih.gov/42848980/");

  await search.fill("NCT02500381");
  assert.equal(await study().count(),1);
  await study().first().locator("summary").first().click();
  panel=board.locator('section[aria-label="R70 article metadata for NCT02500381"]');
  await panel.waitFor({state:"visible"});
  assert.equal(await panel.locator("details").count(),2);
  assert.match(await panel.innerText(),/typically developing children/);
  assert.match(await panel.innerText(),/PubMed databank only/);
  await panel.locator("details").first().locator("summary").click();
  assert.match(await panel.innerText(),/PubMed indexed as Phase I\/II/);

  await search.fill("NCT05126758");
  assert.equal(await study().count(),1);
  await study().first().locator("summary").first().click();
  panel=board.locator('section[aria-label="R70 article metadata for NCT05126758"]');
  await panel.waitFor({state:"visible"});
  assert.match(await panel.innerText(),/HOPE-3/);
  assert.match(await panel.innerText(),/Exact NCT string in article title\/abstract/);
  await panel.locator("details").first().locator("summary").click();
  assert.match(await panel.innerText(),/PubMed indexed Phase III/);
  assert.match(await panel.innerText(),/Independent trial-phase, efficacy, safety/);
  await page.screenshot({path:path.join(OUT,profile.name+"-hope3-pubmed-review.png"),fullPage:false});

  await search.fill("NCT06081894");
  assert.equal(await study().count(),1);
  await study().first().locator("summary").first().click();
  panel=board.locator('section[aria-label="R70 article metadata for NCT06081894"]');
  assert.equal(await panel.locator("details").count(),3);
  assert.match(await panel.innerText(),/NOT SCIENTIFICALLY ADJUDICATED/);

  await search.fill("");
  assert.equal(await study().count(),29);
  if(profile.mobile){
   const dims=await board.evaluate(el=>({
    width:el.getBoundingClientRect().width,
    vw:document.documentElement.clientWidth
   }));
   assert.ok(dims.width<=dims.vw+2,"source article dashboard must fit 390px iPhone-sized width");
  }
  assert.equal(errors.length,0,"no unhandled browser JS errors");
  successes.push({profile:profile.name,viewport:[profile.width,profile.height],
    originalPubmedRecords:11,articleNctMentioned:8,
    onlyPubmedDatabankCrosslinked:3,exactNctSourceLinksTested:true,
    searchAndAccordionsReactive:true,signedClinicalGrades:0,
    validatedFDAFutureOutcomes:0,officialFutureOutcome:"ABSTAIN",
    externalArticlesFullTextNotIndependentlyReviewed:true,
    physicalIphoneSafariTested:false,browserErrors:errors});
 }finally{await context.close();}
}
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const b=await chromium.launch({headless:true});
 try{
  for(const p of profiles)await verifyProfile(b,p);
  fs.writeFileSync(path.join(OUT,"R70_BROWSER_RESULTS.json"),
    JSON.stringify({schema:"MAIN_R70_LOCAL_SOURCE_ARTICLE_BROWSER",
      profiles:successes,noMedicalOrProductionWrites:true},null,2)+"\n");
  console.log(JSON.stringify({status:"PASS",profiles:successes.map(x=>x.profile),
    originalNlmArticleRecords:11,scienceSignoffs:0,validatedFDAForecasts:0}));
 }finally{await b.close()}
})().catch(error=>{
 console.error("MAIN_R70_ORIGINAL_ARTICLE_BROWSER_FAILED",error);
 process.exitCode=1;
});
