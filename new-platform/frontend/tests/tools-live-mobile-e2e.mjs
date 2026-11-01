import assert from "node:assert/strict";
import fs from "node:fs/promises";
import {webkit} from "playwright";

const base="https://pdufa-new-dashboard.vercel.app";
const password=process.env.DASHBOARD_PASSWORD;
if(!password)throw Error("Production dashboard authentication secret unavailable");
const out="test-results/tools-mobile";
await fs.mkdir(out,{recursive:true});
const browser=await webkit.launch({headless:true});
const context=await browser.newContext({
  viewport:{width:390,height:844},deviceScaleFactor:3,isMobile:true,hasTouch:true,
  locale:"en-US",userAgent:"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
});
const page=await context.newPage();
const pageErrors=[];
page.on("pageerror",error=>pageErrors.push(error.message));
page.on("console",message=>{if(message.type()==="error")console.log("BROWSER_CONSOLE",message.text().slice(0,350));});
const auth=await context.request.post(base+"/api/auth",{
  data:{password},headers:{Origin:base}
});
assert.equal(auth.status(),200,"The TOOLS WebKit test must authenticate before accessing protected data");
async function capture(name){await page.screenshot({path:out+"/"+name+".png",fullPage:true});}
async function check(name,fn){
  console.log("CHECK_START",name);
  try{await fn();console.log("CHECK_OK",name);}
  catch(error){await capture("failure-"+name);throw error;}
}
function scopeResponse({stage,designation}={}){
  return page.waitForResponse(response=>{
    try{
      const u=new URL(response.url());
      return u.pathname==="/api/scope-funnel"&&u.searchParams.get("tools")==="1"&&
        (stage===undefined||u.searchParams.get("stages")?.split(",").includes(stage))&&
        (designation===undefined||u.searchParams.get("designations")?.split(",").includes(designation));
    }catch{return false;}
  },{timeout:120000});
}
async function assertInvertedContrast(locator,label){
 const result=await locator.evaluate(el=>{
  const style=getComputedStyle(el);
  const parse=c=>(c.match(/[\d.]+/g)||[]).slice(0,3).map(Number);
  const light=c=>parse(c).map(v=>{
    const x=v/255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4;
  }).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
  const bg=style.backgroundColor,fg=style.color,l1=light(bg),l2=light(fg);
  const ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
  const small=el.querySelector("small");
  const sub=small?getComputedStyle(small).color:fg;
  const l3=light(sub);
  const subRatio=(Math.max(l1,l3)+.05)/(Math.min(l1,l3)+.05);
  return {bg,fg,ratio,subRatio};
 });
 assert.ok(result.ratio>=4.5,
   label+" text must remain readable against selected background: "+JSON.stringify(result));
 assert.ok(result.subRatio>=4.5,
   label+" secondary text must remain readable: "+JSON.stringify(result));
}

const phase=page.locator('[aria-controls="tools-first-phase"]');
const designation=page.locator('[aria-controls="tools-first-designation"]');
let openingDesignationTotals=null;
let phaseOnlyContextCounts=null;
const categories=["fast_track","breakthrough_therapy","priority_review","accelerated_approval",
  "orphan_drug","rmat","qidp","rare_pediatric_disease","tropical_disease_prv",
  "rare_pediatric_disease_prv","material_threat_mcm_prv","lpad","animal_rule"];
try{
  await check("initial-two-choices",async()=>{
    await page.goto(base+"/tools",{waitUntil:"domcontentloaded",timeout:45000});
    await phase.waitFor({timeout:45000});
    assert.equal(await phase.getAttribute("aria-expanded"),"false");
    assert.equal(await designation.getAttribute("aria-expanded"),"false");
    assert.match(await phase.innerText(),/3a\/2[\s\S]*Phase/);
    assert.match(await designation.innerText(),/3b\/2[\s\S]*Special Designation/);
    assert.equal(await page.locator("#tools-first-phase").count(),0);
    assert.equal(await page.locator("#tools-first-designation").count(),0);
    const globalClear=page.getByRole("button",{name:"Clear all selections throughout TOOLS"});
    assert.equal(await globalClear.count(),1,"Exactly one reset button must be visible at top");
    assert.ok(await globalClear.isVisible());
    const initialInventory=await page.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&inventory=1&offset=0&limit=50");
    assert.equal(initialInventory.status(),200,"Authenticated opening POOL inventory must load");
    const published=await initialInventory.json();
    assert.equal(published.inventoryMode,true);
    assert.ok(published.designationTotals,"Opening source must include cross-reconciled FDA totals");
    openingDesignationTotals=published.designationTotals;
    assert.ok(published.restrictedScope?.originalPoolTrials>=10000,"The original published POOL count stays recorded separately");
    assert.equal(published.restrictedScope?.qualification,"NOT_VERIFIED");
    assert.equal(published.restrictedScope?.scope,"DATED_300M_10B_ISSUER_MARKET_CAP_SCREEN");
    assert.ok(published.restrictedScope?.capAsOf,"Saved cap evidence must be date-stamped");
    assert.equal(published.stageStats.trials,published.total,"The restricted opening grid and stage breakdown share one NCT pool");
    assert.equal(Object.values(published.stageStats.stages).reduce((n,entry)=>n+entry.trials,0),published.total,"All phase buckets must partition the cap-screen trials exactly once");
    assert.equal(published.total,published.restrictedScope.screenedTrials,"Opening grid must be the same restricted research subset as Phase and FDA facets");
    assert.ok(published.total>0,"Issuer $300M–$10B cap screen must include matched NCTs from the full POOL");
    assert.ok(published.spreadsheetRows.length>0);
    assert.match(published.spreadsheetRows[0].nctId,/^NCT\d{8}$/);
    assert.equal(await page.locator("#tools-final-trial-spreadsheet").count(),0,
      "Step 5 must be fully hidden before any Step 3 item is checked");
    assert.equal(await page.locator('section[aria-label="Live trial inventory spreadsheet"]').count(),0,
      "The hidden Step 5 cannot contain a heading or an empty table");
    const invalidMix=await page.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&inventory=1&stages=Phase%203&offset=0&limit=50");
    assert.equal(invalidMix.status(),422,"Inventory cannot misrepresent filtered matching records");
    const funnelAtTop=page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]');
    assert.equal(await funnelAtTop.count(),1,"The POOL → PIPELINE → TRIALS funnel must be visible on the opening screen");
    assert.ok(await funnelAtTop.isVisible());
    assert.ok((await funnelAtTop.boundingBox()).y < (await phase.boundingBox()).y,
      "The funnel must be physically above Step 3 Phase/FDA selectors");
    // The page fetches POOL source counts asynchronously; let it reconcile
    // with the separately fetched published inventory before asserting parity.
    await page.waitForFunction(expected=>{
      const value=document.querySelector('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]')?.textContent||"";
      return value.includes(expected.pool)&&value.includes(expected.screened);
    },{
      pool:published.restrictedScope.originalPoolTrials.toLocaleString("en-US"),
      screened:published.restrictedScope.screenedTrials.toLocaleString("en-US")
    },{timeout:60000});
    const openingFunnelText=await funnelAtTop.innerText();
    assert.match(openingFunnelText,new RegExp(published.restrictedScope.originalPoolTrials.toLocaleString("en-US").replaceAll(",","[,]")));
    assert.match(openingFunnelText,new RegExp(published.restrictedScope.screenedTrials.toLocaleString("en-US").replaceAll(",","[,]")));
    assert.equal(await page.locator('section[aria-label="Selected filters and matching clinical trials spreadsheet"]').count(),0,
      "The initial screen must not show trial tables");
    for(const choice of [phase,designation]){
      const circle=choice.locator('span[aria-hidden="true"]').first();
      const rect=await circle.boundingBox();
      assert.ok(rect&&Math.abs(rect.width-rect.height)<3,"First-step code must be circular");
    }
    await capture("01-first-two-only");
  });
  await check("phase-cascade",async()=>{
    await phase.click();
    assert.equal(await phase.getAttribute("aria-expanded"),"true");
    await assertInvertedContrast(phase,"Selected Phase button");
    assert.equal(await page.locator("#tools-first-phase").count(),1);
    assert.equal(await page.locator("#tools-first-designation").count(),0);
    assert.equal(await page.locator("#tools-final-trial-spreadsheet").count(),0,
      "Opening the Step 3 Phase panel does not yet reveal Step 5");
    const directStages=page.locator("#tools-first-phase").getByRole("group",{name:"Clinical development stages"});
    const phaseBoxes=directStages.getByRole("checkbox");
    assert.equal(await phaseBoxes.count(),14,"Phase should reveal 14 choices immediately like FDA");
    assert.match(await directStages.innerText(),/2a\/14/);
    assert.match(await directStages.innerText(),/2n\/14/);
    assert.equal(await page.locator('#tools-first-phase [aria-controls^="tools-stage-group-"]').count(),0);
    const phase3=directStages.getByRole("checkbox",{name:/^Phase 3(?:\s+[\d,]+)?$/});
    assert.ok(await phase3.isVisible(),"Individual Phase 3 checkbox is directly visible");
    const response=scopeResponse({stage:"Phase 3"});
    await phase3.check();
    await assertInvertedContrast(phase3.locator("xpath=.."),"Checked Phase option");
    const filtered=await response;
    assert.equal(filtered.status(),200,"Restricted Phase 3 must produce a successful filtered API response");
    const selectedGrid=page.locator('section[aria-label="Live trial inventory spreadsheet"]');
    await page.waitForFunction(()=>document.querySelector('section[aria-label="Live trial inventory spreadsheet"]')?.textContent?.includes("Step 5 · Final Trials Spreadsheet"),null,{timeout:45000});
    assert.match(await selectedGrid.innerText(),/Step 5 · Final Trials Spreadsheet — filtered trial matches/);
    await page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]').waitFor();
    const assessments=page.locator('section[id="tools-benefit-assessments"]');
    await assessments.waitFor();
    const modeButtons=page.getByRole("group",{name:"Step 4 organization mode"});
    assert.equal(await modeButtons.getByRole("button").count(),4,
      "Four organization modes must be independently selectable");
    const step4Groups=page.getByRole("group",{name:"Step 4 five assessment groups"});
    assert.equal(await step4Groups.getByRole("button").count(),5,
      "Default Category mode shows all five original assessment groups");
    const metricPicker=page.getByRole("combobox",{name:"Step 4 assessment 4a1 through 4a20"});
    const detail=page.locator("#tools-step4-analysis");
    assert.equal(await detail.getAttribute("open"),null,
      "The large clinical assessment details must be collapsed by default");
    const all20=page.locator("#tools-step4-all20");
    assert.equal(await all20.getAttribute("open"),null,
      "The optional complete 1–20 list must be hidden by default");
    await modeButtons.getByRole("button",{name:"Investment focus"}).click();
    assert.equal(await metricPicker.locator("option").count(),9,
      "Investment research shortlist must preserve nine original metric identities");
    assert.equal(await metricPicker.inputValue(),"3",
      "Investment focus starts with clinical benefit without implying a return forecast");
    assert.match(await assessments.innerText(),/not a proven return forecast/);
    await modeButtons.getByRole("button",{name:"Medical benefits"}).click();
    assert.equal(await metricPicker.locator("option").count(),6,
      "Medical benefits mode shows original metrics 4a3 through 4a8");
    assert.equal(await metricPicker.inputValue(),"3");
    await modeButtons.getByRole("button",{name:"All 20"}).click();
    assert.equal(await metricPicker.locator("option").count(),20,
      "All 20 mode exposes every canonical assessment through one selector");
    await all20.locator(":scope > summary").click();
    const all20Options=page.getByRole("group",{name:"Complete separate Step 4 assessment list 1 through 20"});
    assert.equal(await all20Options.getByRole("button").count(),20,
      "Optional expanded list also contains all twenty assessments");
    await all20Options.getByRole("button",{name:/^Assessment 20 of 20 —/}).click();
    assert.equal(await all20.getAttribute("open"),null,
      "Complete list closes after choosing an assessment");
    assert.equal(await metricPicker.inputValue(),"20",
      "Full numbered list and selector must share the same chosen assessment");
    await modeButtons.getByRole("button",{name:"Categories"}).click();
    assert.equal(await step4Groups.getByRole("button",{name:"4E Stock"}).getAttribute("aria-pressed"),"true",
      "Returning to Category mode must retain the group associated with assessment 20");
    await step4Groups.getByRole("button",{name:"4E Stock"}).click();
    await metricPicker.selectOption("20");
    assert.match(await detail.locator(":scope > summary").innerText(),/4a20 — Shareholder Upside and Risk/);
    await detail.locator(":scope > summary").click();
    assert.match(await assessments.innerText(),/ASSESSMENT 20 OF 20/,
      "View analysis reveals the actual original research fields and their evidence");
    await detail.locator(":scope > summary").click();
    await step4Groups.getByRole("button",{name:"4A Patients"}).click();
    assert.equal(await metricPicker.inputValue(),"1",
      "Choosing another category synchronizes its first original assessment");
    const bottomGrid=page.locator("#tools-final-trial-spreadsheet");
    assert.ok(await bottomGrid.evaluate(el=>{
      const analysis=document.querySelector('section[id="tools-benefit-assessments"]');
      return !!analysis&&!!(analysis.compareDocumentPosition(el)&Node.DOCUMENT_POSITION_FOLLOWING);
    }),"The final trial spreadsheet must follow Step 4 without an intervening audit table");
    assert.ok((await bottomGrid.boundingBox()).y > (await assessments.boundingBox()).y,
      "Step 5 trial grid must be physically below the Step 4 assessment matrix");
    assert.equal(await page.locator("#tools-advanced-research").count(),1,
      "Secondary rankings and source audit must remain behind the advanced disclosure");
    assert.match(await phase.innerText(),/1 selected/);
    const phasePanel=page.locator("#tools-first-phase");
    const clearPhase=phasePanel.getByRole("button",{name:"Clear This Section"});
    assert.equal(await clearPhase.count(),1);
    await clearPhase.click();
    assert.match(await phase.innerText(),/Select clinical stages/);
    assert.equal(await page.locator("#tools-final-trial-spreadsheet").count(),0,
      "Clearing the last checked Phase must hide Step 5 completely");
    assert.equal(await directStages.getByRole("checkbox").count(),14);
    const phase3Again=scopeResponse({stage:"Phase 3"});
    await phase3.check();
    assert.equal((await phase3Again).status(),200);
    await capture("02-phase-selected");
  });
  await check("designation-cascade-and-independent-phase",async()=>{
    await designation.click();
    assert.equal(await designation.getAttribute("aria-expanded"),"true");
    await assertInvertedContrast(designation,"Selected Special Designation button");
    assert.equal(await phase.getAttribute("aria-expanded"),"false");
    assert.equal(await page.locator("#tools-first-phase").count(),0);
    const fda=page.locator("#tools-first-designation");
    const all=fda.getByRole("group",{name:"FDA special designations and pathways"});
    assert.equal(await all.getByRole("checkbox").count(),13);
    assert.match(await all.innerText(),/2a\/13/);
    assert.match(await all.innerText(),/2m\/13/);
    const phaseOnly=await page.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&stages=Phase%203&offset=0&limit=50",{timeout:120000});
    assert.equal(phaseOnly.status(),200);
    const phaseOnlyData=await phaseOnly.json();
    const contextualPhaseCounts=phaseOnlyData.contextualDesignationCounts;
    phaseOnlyContextCounts=contextualPhaseCounts;
    const fdaCounts=fda.locator("strong[class*='toolsFdaRowCount']");
    // FDA source index loads independently of the POOL trial query. Wait for it
    // before asserting badge counts; initial placeholders are not finalized counts.
    await page.waitForFunction(()=>{
      const first=[...document.querySelectorAll('#tools-first-designation label')]
        .find(el=>el.textContent?.includes("Fast Track Designation"));
      const check=first?.querySelector('input[type="checkbox"]');
      return !!check&&!check.disabled;
    },null,{timeout:45000});
    assert.equal(await fdaCounts.count(),13,"All 13 FDA choices must have trial-count labels like the Phase rows");
    assert.ok(await fdaCounts.first().isVisible());
    assert.equal(await fdaCounts.first().evaluate(el=>getComputedStyle(el).textAlign),"right");
    // The main count is the independent all-phase FDA baseline, while a second
    // line shows its intersection with the current Phase 3 selection.
    await page.waitForFunction(expected=>{
      const row=[...document.querySelectorAll('#tools-first-designation label')]
        .find(el=>el.textContent?.includes("Fast Track Designation"));
      return row?.textContent?.includes("all phases · documented NCTs · partial") &&
        row?.textContent?.includes("Within selected Phase/search: "+expected);
    },contextualPhaseCounts?.fast_track?.matchingTrials?.toLocaleString("en-US")??"—",{timeout:45000});
    for(const [i,key] of categories.entries()){
      const scoped=contextualPhaseCounts?.[key]??null;
      const baseline=openingDesignationTotals[key]??null;
      const label=await fdaCounts.nth(i).innerText();
      if(baseline===null)assert.match(label,/Not tracked/);
      else {
        assert.equal(label.split("\n")[0].replaceAll(",",""),String(baseline.linkedNcts),
          "FDA "+key+" primary count must stay independent of selected Phase 3");
        assert.match(label,/all phases · documented NCTs · partial/);
        assert.match(label,/Within selected Phase\/search:/);
        assert.match(label,new RegExp("Within selected Phase/search: "+(scoped===null?"—":scoped.matchingTrials.toLocaleString("en-US"))));
        assert.match(label,/Full FDA total unknown/);
      }
    }
    for(const c of await fdaCounts.all()){
      assert.match(await c.innerText(),/all phases · documented NCTs · partial|count unavailable|Not tracked/,
        "Show source-backed all-phase FDA baseline separately from Phase/search intersection");
    }
    const orphanOnly=await page.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&designations=orphan_drug&offset=0&limit=50",{timeout:120000});
    assert.equal(orphanOnly.status(),200);
    const orphanData=await orphanOnly.json();
    assert.equal(orphanData.selectionSummary.designationUniqueTrials,openingDesignationTotals.orphan_drug.linkedNcts,
      "FDA row count must equal the exact same filter's distinct NCT trial count");
    const orphan=all.getByRole("checkbox",{name:/Orphan Drug Designation/});
    await orphan.waitFor({timeout:45000});
    const response=scopeResponse({stage:"Phase 3",designation:"orphan_drug"});
    await orphan.check({timeout:45000});
    await assertInvertedContrast(orphan.locator("xpath=.."),"Checked FDA option");
    assert.equal(await orphan.isDisabled(),false);
    const filtered=await response;
    assert.equal(filtered.status(),200,"Phase AND FDA selection must retain prior filter when switching branches");
    const filteredData=await filtered.json();
    const contextual=filteredData.contextualDesignationCounts?.orphan_drug;
    const orphanCount=orphan.locator("xpath=..").locator("strong[class*='toolsFdaRowCount']");
    await page.waitForFunction(expected=>{
      const row=[...document.querySelectorAll('section[aria-label="POOL stage and FDA designation tools"] label')]
        .find(el=>el.textContent?.includes("Orphan Drug Designation"));
      const count=row?.querySelector('strong[class*="toolsFdaRowCount"]');
      if(!count)return false;
      return expected===null?count.textContent?.includes("Within selected Phase/search: —")
        :count.textContent?.includes("Within selected Phase/search: "+expected.toLocaleString("en-US"));
    },contextual?.matchingTrials??null,{timeout:45000});
    assert.match(await orphanCount.innerText(),
      contextual===null?/Within selected Phase\/search: —/:new RegExp("Within selected Phase/search: "+contextual.matchingTrials.toLocaleString("en-US")),
      "FDA badge must display the exact Phase/search intersection while keeping the all-phase baseline independent");
    if(contextual)assert.equal(contextual.nctIds.length,Math.min(40,contextual.matchingTrials));
    assert.match(await designation.innerText(),/1 selected/);
    assert.match(await phase.innerText(),/1 selected/);
    await fda.getByText(/source programs/).first().waitFor({timeout:20000});
    assert.match(await fda.innerText(),/documented NCT matches|NCT count unavailable/);
    const clearFda=fda.getByRole("button",{name:"Clear This Section"});
    assert.equal(await clearFda.count(),1);
    await clearFda.click();
    assert.match(await designation.innerText(),/Select FDA categories/);
    assert.match(await phase.innerText(),/1 selected/,"Clearing FDA must preserve Phase criteria");
    const secondResponse=scopeResponse({stage:"Phase 3",designation:"orphan_drug"});
    await orphan.check({timeout:45000});
    assert.equal((await secondResponse).status(),200);
    await capture("03-phase-plus-fda");
  });
  await check("switch-back-and-clear",async()=>{
    await phase.click();
    assert.equal(await page.locator("#tools-first-designation").count(),0);
    assert.equal(await page.locator("#tools-first-phase").count(),1);
    const row=page.locator("#tools-first-phase").getByRole("checkbox",{name:/^Phase 3(?:\s+[\d,]+)?$/});
    await row.waitFor({timeout:15000});
    assert.equal(await row.isChecked(),true);
    const sectionClear=page.locator("#tools-first-phase").getByRole("button",{name:"Clear This Section"});
    const noPhaseResponse=page.waitForResponse(response=>{
      try{const url=new URL(response.url());
        return url.pathname==="/api/scope-funnel" &&
          url.searchParams.get("tools")==="1" &&
          url.searchParams.get("designations")==="orphan_drug" &&
          !url.searchParams.has("stages");
      }catch{return false;}
    },{timeout:60000});
    await sectionClear.click();
    assert.match(await phase.innerText(),/Select clinical stages/);
    assert.match(await designation.innerText(),/1 selected/,"Clearing Phase must preserve FDA choices");
    const withoutPhaseData=await (await noPhaseResponse).json();
    const previewAfterClear=withoutPhaseData.contextualDesignationCounts?.orphan_drug??null;
    assert.ok(previewAfterClear===null||previewAfterClear.matchingTrials>=0);
    const previousScopeCount=phaseOnlyContextCounts?.orphan_drug??null;
    if(previewAfterClear&&previousScopeCount)
      assert.ok(previewAfterClear.matchingTrials>=previousScopeCount.matchingTrials);
    const phaseAgain=scopeResponse({stage:"Phase 3",designation:"orphan_drug"});
    await row.check();
    assert.equal((await phaseAgain).status(),200);
    // Secondary rankings are available in the separate disclosure below Step 5.
    await page.locator("#tools-advanced-research > summary").click();
    const ranking=page.locator('[aria-controls="tools-rank-trials-body"]');
    await ranking.waitFor();
    await ranking.click();
    const rankGroup=page.locator("#tools-rank-trials-body").getByRole("checkbox",{name:/Patient Health & Clinical Benefit/});
    await rankGroup.check();
    await assertInvertedContrast(rankGroup.locator("xpath=.."),"Checked ranking option");
    await page.waitForFunction(()=>{
      try{return JSON.parse(localStorage.getItem("pdufa-tools-ranking-checklists-v1")||"{}").groupIds?.includes(1);}catch{return false;}
    },null,{timeout:15000});
    await page.getByRole("button",{name:"Clear all selections throughout TOOLS"}).click();
    await page.waitForFunction(()=>{
      try{return !JSON.parse(localStorage.getItem("pdufa-tools-ranking-checklists-v1")||"{}").groupIds?.length;}catch{return false;}
    },null,{timeout:15000});
    assert.equal(await page.locator("#tools-first-phase").count(),0);
    assert.equal(await phase.getAttribute("aria-expanded"),"false");
    assert.equal(await designation.getAttribute("aria-expanded"),"false");
    assert.equal(await page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]').count(),1,
      "The top-of-page funnel remains visible even after Clear All Selections");
    assert.equal(await page.locator('section[aria-label="Selected filters and matching clinical trials spreadsheet"]').count(),0);
    assert.equal(await page.locator("#tools-final-trial-spreadsheet").count(),0);
    assert.equal(await page.locator('section[aria-label="Live trial inventory spreadsheet"]').count(),0,
      "Clear All Selections must completely hide Step 5");
    await capture("04-cleared-to-start");
  });
  assert.deepEqual(pageErrors,[],"The mobile guided selection flow must not throw browser errors");
  console.log("TOOLS_GUIDED_MOBILE_WEBKIT_PASS");
}finally{
  await context.close();
  await browser.close();
}
