import assert from "node:assert/strict";
import fs from "node:fs/promises";
import {webkit} from "playwright";

// Authenticated source-aware WebKit test of the guided first-selection TOOLS UI
// and the same 20 clinical-benefit columns after a real Phase filter is checked.
const base="https://pdufa-new-dashboard.vercel.app";
const password=process.env.DASHBOARD_PASSWORD;
if(!password)throw Error("Configured dashboard test credential unavailable");
const out="test-results/tools-assessments-browser";
await fs.mkdir(out,{recursive:true});
const browser=await webkit.launch({headless:true});
const errors=[];
async function openAuthenticated(viewport,isMobile){
  const context=await browser.newContext({viewport,deviceScaleFactor:isMobile?3:1,isMobile,hasTouch:isMobile});
  const auth=await context.request.post(base+"/api/auth",{data:{password},headers:{Origin:base}});
  assert.equal(auth.status(),200,"Dashboard authentication failed");
  const page=await context.newPage();
  page.on("pageerror",e=>errors.push(e.message));
  await page.goto(base+"/tools",{waitUntil:"domcontentloaded",timeout:50000});
  await page.locator('[aria-controls="tools-first-phase"]').waitFor({timeout:45000});
  assert.equal(await page.locator("#tools-benefit-assessments").count(),0,
    "Benefit matrix must remain hidden until the first Phase/FDA selection");
  const opening=page.locator('section[aria-label="Live trial inventory spreadsheet"]');
  await opening.waitFor({timeout:50000});
  assert.match(await opening.innerText(),/Published POOL/);
  await page.waitForFunction(()=>{
    const table=document.querySelector('section[aria-label="Live trial inventory spreadsheet"] tbody');
    return table&&/NCT\d{8}/.test(table.textContent||"");
  },null,{timeout:60000});
  assert.equal(await page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]').count(),0);
  assert.equal(await page.locator('[aria-controls="tools-first-phase"]').getAttribute("aria-expanded"),"false");
  assert.equal(await page.locator('[aria-controls="tools-first-designation"]').getAttribute("aria-expanded"),"false");
  return {context,page};
}
async function populate(page){
  await page.locator('[aria-controls="tools-first-phase"]').click();
  await page.locator("#tools-first-phase").waitFor({timeout:10000});
  const stageResponse=page.waitForResponse(response=>{
    try{
      const url=new URL(response.url());
      return url.pathname==="/api/scope-funnel"&&url.searchParams.get("tools")==="1"&&
        url.searchParams.has("stages")&&!url.searchParams.has("baseline");
    }catch{return false;}
  },{timeout:120000});
  await page.locator("#tools-first-phase").getByRole("button",{name:"Select all",exact:true}).click();
  const response=await stageResponse;
  assert.equal(response.status(),200,"Phase-filtered source request failed");
  const body=await response.json();
  assert.ok(body.total>0&&Array.isArray(body.spreadsheetRows)&&body.spreadsheetRows.length>0,
    "All 14 stages must populate actual research trial records");
  await page.locator("#tools-benefit-assessments").waitFor({timeout:60000});
  const isMobile=await page.evaluate(()=>window.matchMedia("(max-width:800px)").matches);
  if(isMobile){
    await page.locator("#benefit-trial-picker").waitFor({state:"visible",timeout:60000});
    await page.waitForFunction(()=>{
      const s=document.querySelector("#tools-benefit-assessments");
      const picker=document.querySelector("#benefit-trial-picker");
      return s&&picker&&picker.options.length>0&&!s.textContent.includes("Loading source-matched resultant trials");
    },null,{timeout:60000});
  }else{
    const table=page.locator('[aria-label="Desktop horizontally scrollable 20-assessment spreadsheet"] table');
    await table.waitFor({state:"visible",timeout:60000});
    await page.waitForFunction(()=>{
      const s=document.querySelector("#tools-benefit-assessments");
      const table=document.querySelector('[aria-label="Desktop horizontally scrollable 20-assessment spreadsheet"] table');
      return s&&table&&table.tBodies[0]?.rows.length>0&&!s.textContent.includes("Loading source-matched resultant trials");
    },null,{timeout:60000});
  }
}
try{
  const mobile=await openAuthenticated({width:390,height:844},true);
  const page=mobile.page;
  assert.match(await page.locator('[aria-controls="tools-first-phase"]').innerText(),/1a\/2/);
  assert.match(await page.locator('[aria-controls="tools-first-designation"]').innerText(),/1b\/2/);
  // No implicit candidates from a missing selection.
  const emptyResponse=await page.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&offset=0&limit=50");
  assert.equal(emptyResponse.status(),200);
  const empty=await emptyResponse.json();
  assert.equal(empty.total,0);
  assert.deepEqual(empty.spreadsheetRows,[]);
  const invalid=await page.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&offset=0&limit=50&baseline=1");
  assert.equal(invalid.status(),422);
  await populate(page);
  const funnel=page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]');
  const cards=await Promise.all(["POOL","PIPELINE","TRIALS"].map(async name=>
    funnel.getByRole("heading",{name,exact:true}).boundingBox()));
  assert.ok(cards.every(Boolean));
  assert.ok(cards[0].x<cards[1].x&&cards[1].x<cards[2].x,"The 3 funnel boxes remain horizontal on iPhone");
  assert.ok(Math.abs(cards[0].y-cards[1].y)<12&&Math.abs(cards[1].y-cards[2].y)<12);
  const groupSelect=page.locator("#benefit-group-picker");
  assert.equal(await groupSelect.locator("option").count(),20);
  const feedResponse=await page.request.get(base+"/api/benefit-assessments",{timeout:110000});
  assert.equal(feedResponse.status(),200);
  const feed=await feedResponse.json();
  assert.equal(feed.schemaVersion,1);
  assert.match(feed.sourceAsOf,/^\d{4}-\d{2}-\d{2}$/);
  assert.ok(Array.isArray(feed.records));
  assert.ok(feed.records.every(r=>/^NCT\d{8}$/.test(r.nctId)&&r.ticker&&r.drug&&r.indication));
  const coverage=await page.request.get(base+"/api/registry-benefit-coverage",{timeout:40000});
  assert.equal(coverage.status(),200);
  const packet=await coverage.json();
  assert.equal(packet.scanned,375);
  assert.ok(packet.records.length>0);
  assert.ok(await page.getByText("Official registry research archive:",{exact:false}).isVisible());
  const trialSelect=page.locator("#benefit-trial-picker");
  const selectedNct=await trialSelect.inputValue();
  assert.match(selectedNct,/^NCT\d{8}$/);
  const sourceResponse=await page.request.get(base+"/api/registry-benefit-research?nct="+selectedNct,{timeout:50000});
  assert.ok([200,404].includes(sourceResponse.status()),
    "Registry detail must either supply exact sourced study evidence or report it unavailable");
  const benefit=page.locator("#tools-benefit-assessments");
  if(sourceResponse.status()===200){
    const research=await sourceResponse.json();
    assert.equal(research.nctId,selectedNct);
    assert.equal(research.sourceUrl,"https://clinicaltrials.gov/study/"+selectedNct);
    assert.equal(research.comparisonVerified,false);
    assert.equal(research.benefitRank,null);
    assert.equal(research.fdaDecisionVerified,false);
    const evidence=benefit.locator("details[aria-label='Independent ClinicalTrials.gov source evidence "+selectedNct+"']");
    assert.ok(await evidence.isVisible());
    await evidence.locator("summary").click();
    await evidence.getByText("Open exact ClinicalTrials.gov study").waitFor({timeout:40000});
  }else{
    console.log("REGISTRY_DETAIL_NOT_AVAILABLE_FOR_EXACT_NCT",selectedNct);
    assert.doesNotMatch(await benefit.innerText(),/Source-verified overall drug superiority/,
      "Missing study research must never be displayed as verified superiority");
  }
  await groupSelect.selectOption("3");
  assert.match(await benefit.locator("h4").innerText(),/#3 — Clinical Benefit/);
  await benefit.getByRole("button",{name:/Next/}).click();
  assert.match(await benefit.locator("h4").innerText(),/#4 — Survival Benefit/);
  await page.screenshot({path:out+"/01-iphone-390-guided.png",fullPage:true});
  await page.getByRole("button",{name:"Clear all selections"}).click();
  assert.equal(await benefit.count(),0);
  assert.equal(await funnel.count(),0);
  await page.screenshot({path:out+"/02-iphone-reset.png",fullPage:true});
  await mobile.context.close();

  const desktop=await openAuthenticated({width:1440,height:900},false);
  const desk=desktop.page;
  await populate(desk);
  const table=desk.locator('[aria-label="Desktop horizontally scrollable 20-assessment spreadsheet"] table');
  assert.ok(await table.isVisible());
  const parent=table.locator("thead tr").first().locator("th");
  assert.equal(await parent.count(),21);
  const subheader=table.locator("thead tr").nth(1).locator("th");
  assert.ok(Number(await parent.nth(1).getAttribute("colspan"))>1);
  await desk.locator("#benefit-group-picker").selectOption("3");
  assert.equal(Number(await parent.nth(3).getAttribute("colspan")),8);
  assert.equal(await parent.nth(1).getAttribute("colspan"),"1");
  assert.equal(await subheader.count(),4+20-1+8);
  await desk.screenshot({path:out+"/03-desktop-1440-guided.png",fullPage:true});
  await desktop.context.close();
  assert.deepEqual(errors,[]);
  console.log("PASS: TOOLS guided first choice and 20-assessment data after selection on mobile and desktop");
}catch(error){
  console.error("LIVE_TOOLS_BENEFIT_BROWSER_FAILURE",error);
  throw error;
}finally{
  await browser.close();
}
