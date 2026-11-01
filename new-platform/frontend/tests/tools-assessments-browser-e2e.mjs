import assert from "node:assert/strict";
import fs from "node:fs/promises";
import {webkit} from "playwright";

// Authenticated production smoke-check for the 20-assessment TOOLS page.
// This validates real WebKit layout and selectors; no clinical findings are fabricated.
const base="https://pdufa-new-dashboard.vercel.app";
const password=process.env.DASHBOARD_PASSWORD;
if(!password)throw Error("Configured dashboard test credential unavailable");
const out="test-results/tools-assessments-browser";
await fs.mkdir(out,{recursive:true});
const browser=await webkit.launch({headless:true});
const errors=[];
async function openAuthenticated(viewport,isMobile){
  const context=await browser.newContext({viewport,deviceScaleFactor:isMobile?3:1,isMobile,hasTouch:isMobile});
  const auth=await context.request.post(base+"/api/auth",{
    data:{password},headers:{Origin:base},
  });
  assert.equal(auth.status(),200,"Dashboard authentication failed");
  const page=await context.newPage();
  page.on("pageerror",e=>errors.push(e.message));
  await page.goto(base+"/tools",{waitUntil:"domcontentloaded",timeout:50000});
  await page.locator("#tools-benefit-assessments").waitFor({timeout:45000});
  return {context,page};
}
async function populate(page){
  const chooser=page.locator("details").filter({has:page.getByText("Select clinical trial stages")}).locator("summary");
  await chooser.click();
  await page.getByRole("button",{name:"Select all",exact:true}).click();
  await page.waitForFunction(()=>{
    const s=document.querySelector("#tools-benefit-assessments");
    const picker=document.querySelector("#benefit-trial-picker");
    return s && picker && picker.options.length>0 &&
      !s.textContent.includes("Loading source-matched resultant trials");
  },null,{timeout:100000});
}
try {
  const mobile=await openAuthenticated({width:390,height:844},true);
  const page=mobile.page;
  const funnel=page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]');
  const cards=await Promise.all(["POOL","PIPELINE","TRIALS"].map(async name=>
    funnel.getByRole("heading",{name,exact:true}).boundingBox()));
  assert.ok(cards.every(Boolean),"Every funnel stage must exist");
  assert.ok(cards[0].x<cards[1].x && cards[1].x<cards[2].x,"iPhone funnel cards must be horizontal");
  assert.ok(Math.abs(cards[0].y-cards[1].y)<12 && Math.abs(cards[1].y-cards[2].y)<12,
    "iPhone funnel headings must stay on the same line");
  // Verify real authenticated research intake, not just a rendered empty table.
  const researchResponse=await page.request.get(base+"/api/benefit-assessments",{timeout:110000});
  assert.equal(researchResponse.status(),200,
    "TOOLS must retrieve the reconciled Pipeline research feed rather than an empty or failing stub");
  const benefitFeed=await researchResponse.json();
  assert.equal(benefitFeed.schemaVersion,1);
  assert.match(benefitFeed.sourceAsOf,/^\d{4}-\d{2}-\d{2}$/);
  assert.ok(Array.isArray(benefitFeed.records),"Source-backed benefit research records missing");
  assert.ok(benefitFeed.records.every(r=>/^NCT\d{8}$/.test(r.nctId)&&r.ticker&&r.drug&&r.indication),
    "Benefit research cannot contain orphaned NCT identities");
  const groupSelect=page.locator("#benefit-group-picker");
  assert.equal(await groupSelect.locator("option").count(),20);
  const emptyResponse=await page.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&offset=0&limit=50");
  assert.equal(emptyResponse.status(),200);
  const empty=await emptyResponse.json();
  assert.equal(empty.pipelineResearch?.screenedTrials,346,"PIPELINE retains the dated source-screened 346");
  assert.equal(empty.total,0,"API must never return default candidates without a selected filter");
  assert.deepEqual(empty.rows,[]);
  assert.deepEqual(empty.spreadsheetRows,[]);
  const retired=await page.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&offset=0&limit=50&baseline=1");
  assert.equal(retired.status(),422,"Deprecated implicit baseline bypass must be rejected");
  const pipelineCard=funnel.getByRole("heading",{name:"PIPELINE",exact:true}).locator("../..");
  await pipelineCard.getByText("346",{exact:true}).waitFor({timeout:100000});
  const trialsCard=funnel.getByRole("heading",{name:"TRIALS",exact:true}).locator("../..");
  assert.equal((await trialsCard.locator('[role="status"]').first().innerText()).trim(),"0",
    "Unchecked clinical stages and FDA designations MUST show 0 trials");
  assert.equal(await page.locator("#benefit-trial-picker").count(),0,
    "No trial selector or assessment rows without checked filters");
  assert.match(await page.locator("#tools-benefit-assessments").innerText(),/0 matching trials/);
  const csv=page.locator("a").filter({hasText:"Export all matches (CSV)"});
  assert.equal(await csv.getAttribute("aria-disabled"),"true",
    "No-selection state must disable trial export");
  await populate(page);
  const benefitBox=await page.locator("#tools-benefit-assessments").boundingBox();
  const totalsBox=await page.getByRole("heading",{name:"Selected selectors & individual trial totals"}).boundingBox();
  assert.ok(benefitBox&&totalsBox&&benefitBox.y<totalsBox.y,
    "Benefit matrix must appear before the long individual selector totals table on iPhone");
  const trialSelect=page.locator("#benefit-trial-picker");
  assert.ok(await trialSelect.isVisible(),"Mobile resultant-trial picker must be visible");
  assert.ok(await trialSelect.locator("option").count()>0);
  // Verify a genuine primary registry lookup for the selected screened NCT.
  const selectedNct=await trialSelect.inputValue();
  assert.match(selectedNct,/^NCT\d{8}$/);
  const sourceResponse=await page.request.get(base+"/api/registry-benefit-research?nct="+selectedNct,{timeout:50000});
  assert.equal(sourceResponse.status(),200,"Primary-source registry evidence endpoint must work for screened NCT");
  const sourcePacket=await sourceResponse.json();
  assert.equal(sourcePacket.nctId,selectedNct);
  assert.equal(sourcePacket.sourceUrl,"https://clinicaltrials.gov/study/"+selectedNct);
  assert.equal(sourcePacket.comparisonVerified,false);
  assert.equal(sourcePacket.benefitRank,null);
  assert.equal(sourcePacket.fdaDecisionVerified,false);
  assert.ok(Array.isArray(sourcePacket.primary));
  assert.ok(Array.isArray(sourcePacket.seriousAdverseEvents));
  const evidenceDetail=page.locator("#tools-benefit-assessments details[aria-label='Independent ClinicalTrials.gov source evidence "+selectedNct+"']");
  assert.ok(await evidenceDetail.isVisible(),"Primary-source evidence panel must be visible on iPhone");
  await evidenceDetail.locator("summary").click();
  await evidenceDetail.getByText("Open exact ClinicalTrials.gov study").waitFor({timeout:40000});
  await groupSelect.selectOption("3");
  assert.match(await page.locator("#tools-benefit-assessments h4").innerText(),/^#3 — Clinical Benefit$/);
  assert.ok(await page.getByText("Competitive advantages · strongest first",{exact:true}).isVisible());
  await page.locator("#tools-benefit-assessments").getByRole("button",{name:/Next/}).click();
  assert.match(await page.locator("#tools-benefit-assessments h4").innerText(),/^#4 — Survival Benefit$/);
  await page.screenshot({path:out+"/01-iphone-390.png",fullPage:true});
  await page.getByRole("button",{name:"Clear all filters"}).click();
  await page.getByText("0 selected · 0 matching trials.",{exact:false}).waitFor({timeout:90000});
  assert.equal((await trialsCard.locator('[role="status"]').first().innerText()).trim(),"0",
    "Removing the last selected criterion restores zero trials, not 346");
  assert.equal(await page.locator("#benefit-trial-picker").count(),0);
  await page.screenshot({path:out+"/03-iphone-empty-selections.png",fullPage:true});
  await mobile.context.close();

  const desktop=await openAuthenticated({width:1440,height:900},false);
  const desk=desktop.page;
  await desk.getByText("0 selected · 0 matching trials.",{exact:false}).waitFor({timeout:90000});
  assert.equal(await desk.locator("#benefit-trial-picker").count(),0);
  await populate(desk);
  const table=desk.locator('[aria-label="Desktop horizontally scrollable 20-assessment spreadsheet"] table');
  assert.ok(await table.isVisible(),"Desktop matrix must be displayed");
  const parent=table.locator("thead tr").first().locator("th");
  assert.equal(await parent.count(),21,"20 parent assessment headings plus identity group");
  const subheader=table.locator("thead tr").nth(1).locator("th");
  const firstSpan=Number(await parent.nth(1).getAttribute("colspan"));
  assert.ok(firstSpan>1,"Expanded assessment #1 should span its subcolumns");
  await desk.locator("#benefit-group-picker").selectOption("3");
  const threeSpan=Number(await parent.nth(3).getAttribute("colspan"));
  assert.equal(threeSpan,8,"Clinical Benefit has 6 mapped subcolumns plus rank/status");
  assert.equal(await parent.nth(1).getAttribute("colspan"),"1");
  assert.equal(await subheader.count(),4+20-1+8,"Subcolumn count matches 20 parent groups");
  await desk.screenshot({path:out+"/02-desktop-1440.png",fullPage:true});
  await desktop.context.close();
  assert.deepEqual(errors,[],"No browser JavaScript runtime errors");
  console.log("PASS: live WebKit iPhone 390px funnel, 20 group navigation, filtered trials, desktop grouped headings");
} catch(e) {
  console.error("LIVE_TOOLS_BENEFIT_BROWSER_FAILURE",e);
  throw e;
} finally {
  await browser.close();
}
