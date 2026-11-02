import assert from "node:assert/strict";
import fs from "node:fs/promises";
import {webkit} from "playwright";

const base="https://pdufa-new-dashboard.vercel.app";
const password=process.env.DASHBOARD_PASSWORD;
if(!password)throw Error("DASHBOARD_PASSWORD must be configured for authenticated TOOLS smoke tests");
const directory="test-results/tools-rating-production";
await fs.mkdir(directory,{recursive:true});
const browser=await webkit.launch({headless:true});
const devices=[
  {label:"desktop",width:1440,height:900,mobile:false},
  {label:"iphone",width:390,height:844,mobile:true}
];
function check(expression,message){assert.ok(expression,message);}
async function ratingTest(page,label){
  const supplementary=page.locator("main > details").nth(2);
  await supplementary.locator(":scope > summary").click();
  const root=page.locator("#tools-phase3-registry-tables");
  const before=root.locator('section[aria-label="Top unposted registry results trial spreadsheet"]');
  const after=root.locator('section[aria-label="Bottom posted registry results trial spreadsheet"]');
  await before.waitFor({state:"visible",timeout:90000});
  await after.waitFor({state:"visible",timeout:90000});
  const beforeRows=before.locator("tbody tr");
  const afterRows=after.locator("tbody tr");
  await before.locator('tbody tr:first-child td:nth-child(3) a').first().waitFor({timeout:60000});
  const nct=(await before.locator('tbody tr:first-child td:nth-child(3) a').first().innerText()).trim();
  assert.match(nct,/^NCT\d{8}$/,"Before table needs real source-linked NCT trial rows");
  const afterCount=await afterRows.count();
  check(afterCount>0,"Past table must contain source-linked trial rows");
  const beforeExpand=before.locator('button[aria-label^="Expand Before M "]');
  await beforeExpand.click();
  check((await before.locator('thead tr:first-child th[data-rating-ingredient="VER"]').count())===1,
    "Before M must reveal VER ingredient immediately to the right");
  check((await after.locator('thead tr:first-child th[data-rating-ingredient="VER"]').count())===0,
    "Past section must stay independently collapsed");
  const structure=await before.locator("thead tr:first-child").evaluate(row=>{
    const cells=[...row.querySelectorAll("th")];
    const index=cells.findIndex(el=>el.dataset.ratingGroup==="M");
    return cells.slice(index,index+5).map(el=>el.dataset.ratingGroup||el.dataset.ratingIngredient);
  });
  assert.deepEqual(structure,["M","VER","MOD","MISS","CRIT"],"M ingredients must expand HORIZONTALLY");
  const borders=await before.locator("thead").evaluate(head=>{
    const g=head.querySelector('tr:nth-child(2) th[data-rating-group="M"]');
    const last=head.querySelector('tr:nth-child(2) th[data-rating-ingredient="CRIT"]');
    const title=head.querySelector('tr:first-child th[data-rating-group="M"]');
    return {
      headingLeft:Number.parseFloat(getComputedStyle(title).borderLeftWidth),
      filterLeft:Number.parseFloat(getComputedStyle(g).borderLeftWidth),
      filterRight:Number.parseFloat(getComputedStyle(last).borderRightWidth)
    };
  });
  check(borders.headingLeft>=2&&borders.filterLeft>=2&&borders.filterRight>=2,
    "Expanded M outline must remain continuous through the filter row: "+JSON.stringify(borders));
  await after.locator('button[aria-label^="Expand Past M "]').click();
  check((await after.locator('thead tr:first-child th[data-rating-ingredient="CRIT"]').count())===1,
    "Past M independently reveals its ingredients");
  const query=before.locator('input[aria-label="Before filter NCT"]');
  await query.fill(nct);
  await page.waitForFunction(()=>{
    const s=document.querySelector('section[aria-label="Top unposted registry results trial spreadsheet"]');
    return s?.querySelectorAll("tbody tr").length===1;
  },null,{timeout:15000});
  check((await afterRows.count())===afterCount,"Before NCT filter must not alter the Past spreadsheet");
  check((await before.locator("tbody tr:first-child").innerText()).includes(nct),
    "Exact NCT filtering must retain the correct trial");
  await query.fill("");
  check(await beforeRows.count()>1,"Clearing the NCT filter must restore source rows");
  console.log("PASS",label,"registry ratings expand right; selected border continuous; filters isolated");
}
async function finalSurveyTest(page,label){
  const readout=page.locator("main > details").nth(1);
  await readout.locator(":scope > summary").click();
  for(const [bucket,caption] of [["pre","Top pre-release spreadsheet"],["post","Bottom post-release spreadsheet"]]){
    const sheet=page.locator('section[aria-label="'+caption+'"]');
    await sheet.waitFor({state:"visible",timeout:90000});
    await sheet.locator(":scope > details > summary").click();
    await sheet.getByRole("button",{name:/Trial rows/}).click();
    const open=sheet.locator('button[aria-label^="Open SURVEY combined assessment for"]').first();
    await open.waitFor({state:"visible",timeout:60000});
    await open.click();
    const dialog=page.getByRole("dialog",{name:/SURVEY synthesis for/});
    await dialog.waitFor({state:"visible",timeout:15000});
    const audit=dialog.getByRole("region",{name:"Final SURVEY readiness and reluctant evidence grade"});
    await audit.waitFor({state:"visible",timeout:15000});
    let body=await audit.innerText();
    assert.match(body,/Grade 1 · Full analysis readiness/);
    assert.match(body,/Grade 2 · Reluctant evidence-coverage grade/);
    assert.match(body,/FDA decision forecast:\s*ABSTAIN/);
    check(body.includes("Source-verified coverage:"),"Source coverage has to be visible");
    const scientific=dialog.locator('details[aria-label="Phase 3 scientific evidence verification checklist"]');
    await scientific.locator(":scope > summary").click();
    const scientificText=await scientific.innerText();
    check(scientificText.includes("Scientific validation checkpoints"),
      "Scientific verification must be visible for each trial");
    check(scientificText.includes("Independent clinical data adjudication"),
      "Source presence must not falsely imply independent clinical review");
    check(scientificText.includes("FDA decision evidence"),
      "FDA decision evidence must remain explicitly unverified");
    const arithmetic=scientific.locator('details[aria-label="Exact-trial published effect-size arithmetic"]');
    await arithmetic.locator(":scope > summary").click();
    const arithmeticText=await arithmetic.innerText();
    if(bucket==="pre"){
      check(arithmeticText.includes("No exact-NCT, fully reconciled placebo comparison"),
        "Pre-readout evidence must not contain an invented treatment difference");
    }else{
      check(/Week 12 UAS7 extra mean reduction versus placebo/.test(arithmeticText),
        "Source-matched EMBARQ study must have explicit arithmetic instead of a clinical grade");
      check(/Week 24 complete-response difference/.test(arithmeticText),
        "Longer-term response difference must be distinguishable from continuous durability");
      check(arithmeticText.includes("SEC-filed copy of the same company release"),
        "Company SEC filing is corroboration of a disclosure, not independent clinical review");
      check(/No NNT, CI/.test(arithmeticText),"Missing arm denominators forbid fake NNT or CI");
    }
    await arithmetic.locator(":scope > summary").click();
    await scientific.locator(":scope > summary").click();
    const matrix=dialog.locator('details[aria-label="Twenty survey evidence coverage matrix"]');
    await matrix.locator(":scope > summary").click();
    const items=matrix.locator("tbody tr[data-final-survey-number]");
    assert.equal(await items.count(),20,"Final SURVEY must contain exactly 20 original assessments");
    for(let index=1;index<=20;index++)
      assert.equal(await items.nth(index-1).getAttribute("data-final-survey-number"),String(index));
    check((await items.first().innerText()).includes("Not assessed")||
      (await items.first().innerText()).includes("verified"),
      "An unverified survey must never be treated as a clinical failure");
    await matrix.getByRole("button",{name:"Inspect scoring protocol for survey 3"}).click();
    const method=matrix.getByRole("region",{name:"Selected survey scoring method"});
    await method.waitFor({state:"visible"});
    const text=await method.innerText();
    check(text.includes("Survey 3")&&text.includes("Evidence basis:")&&
      text.includes("Required comparison:")&&text.includes("Interpretation method:"),
      "Survey 3 must show its distinct scientific scoring method to the right");
    check(text.includes("Not calibrated")&&text.includes("no numerical score assigned"),
      "Source completeness must not fabricate a scientific or FDA outcome score");
    if(bucket==="pre")check(text.includes("Public results not documented as checked"),
      "Pre-readout clinical scoring should not infer published outcome evidence");
    const rowStyle=await matrix.locator('tr[data-final-survey-number="3"]').evaluate(el=>({
      selected:el.querySelector("button")?.getAttribute("aria-pressed"),
      border:getComputedStyle(el.querySelector("th")).borderLeftWidth
    }));
    assert.equal(rowStyle.selected,"true","The right-hand panel must track the selected survey");
    check(Number.parseFloat(rowStyle.border)>=2,"Selected survey row requires a visible outline");
    await matrix.getByRole("button",{name:"Inspect scoring protocol for survey 8"}).click();
    check((await method.innerText()).includes("Survey 8"),
      "Selecting another survey must update the right-hand methodology panel");
    await matrix.locator(":scope > summary").click();
    const actions=dialog.locator('details[aria-label="Final SURVEY prioritized research actions"]');
    await actions.waitFor({state:"visible",timeout:15000});
    await actions.locator(":scope > summary").click();
    check((await actions.innerText()).includes("Question verification remaining:"),
      "Trial SURVEY must tell the user how many questions still need verification");
    const exactTrial=actions.locator('a[href^="https://clinicaltrials.gov/study/"]');
    assert.equal(await exactTrial.count(),1,"Source-first actions must link to the exact NCT trial");
    check((await actions.innerText()).includes("research checklist, not a medical failure list"),
      "Missing evidence must not be presented as a failed trial");
    await actions.locator(":scope > summary").click();
    if(bucket==="post"){
      await page.waitForFunction(()=>{
        const p=document.querySelector('[aria-label="Final SURVEY readiness and reluctant evidence grade"]');
        return !!p&&/Source-verified coverage:\s*\d+ of 38/.test(p.textContent||"");
      },null,{timeout:45000});
      const loaded=await audit.innerText();
      check(/Source-verified coverage:\s*[25] of 38/.test(loaded),
        "POST readout must display source-verified issuer trial observations, not empty placeholders");
      check(loaded.includes("FDA decision forecast: ABSTAIN"),
        "Sponsor topline findings must not create a probability or FDA verdict");
    }
    await page.waitForFunction(()=>{
      const panel=document.querySelector('[aria-label="Final SURVEY readiness and reluctant evidence grade"]');
      return !!panel&&!panel.textContent.includes("Checking sources");
    },null,{timeout:45000});
    body=await audit.innerText();
    check(/NOT READY|NOT ASSESSED|READY — 38\/38 VERIFIED/.test(body),
      "Full analysis grade must be explicit even for sparse trials");
    check(!/\b(?:APPROVAL PROBABILITY|CRL PROBABILITY)\b/i.test(body),
      "Coverage grade must not assert an FDA outcome likelihood");
    await dialog.getByRole("button",{name:/Close/}).click();
    console.log("PASS",label,bucket,"two-grade SURVEY audit with no implied FDA prediction");
  }
}
async function liveTrialTest(page){
  const pool=page.locator("main > details").first();
  await pool.locator(":scope > summary").click();
  const selectors=pool.locator('details[data-pool-segment="selectors"]');
  await selectors.locator(":scope > summary").click();
  await page.locator('[aria-controls="tools-first-phase"]').click();
  const phase3=page.locator("#tools-first-phase label").filter({hasText:/Phase 3/}).first().locator('input[type="checkbox"]');
  await phase3.waitFor({state:"visible",timeout:90000});
  await phase3.check();
  const live=pool.locator('details[data-pool-segment="live-trials"]');
  await live.locator(":scope > summary").click();
  const grid=page.locator("#tools-final-trial-spreadsheet");
  await grid.waitFor({state:"visible",timeout:90000});
  const target=grid.locator('tbody a[href^="https://clinicaltrials.gov/study/"]').first();
  await target.waitFor({state:"visible",timeout:90000});
  const nct=(await target.innerText()).trim();
  assert.match(nct,/^NCT\d{8}$/,"Live grid must contain an exact source-linked NCT");
  const input=grid.locator('input[aria-label="Filter NCT Trial ID"]');
  await input.fill(nct);
  await page.waitForFunction(()=>{
    const element=document.querySelector('#tools-final-trial-spreadsheet');
    return !!element&&element.querySelectorAll("tbody tr").length===1;
  },null,{timeout:15000});
  check((await grid.locator("tbody tr").first().innerText()).includes(nct),
    "Filtered live grid must preserve the selected NCT");
  const label=await grid.locator(".trialColumnFilterBar").innerText();
  check(label.includes("loaded trial rows"),"Live filters must be explicitly page-scoped");
  await input.fill("");
  console.log("PASS desktop live trial NCT filter, Phase selector and page-scoped count");
}
try{
  for(const device of devices){
    const context=await browser.newContext({
      viewport:{width:device.width,height:device.height},
      deviceScaleFactor:device.mobile?3:1,
      isMobile:device.mobile,hasTouch:device.mobile,locale:"en-US"
    });
    const page=await context.newPage();
    const browserErrors=[];
    page.on("pageerror",err=>browserErrors.push(err.message));
    try{
      const auth=await context.request.post(base+"/api/auth",{
        data:{password},headers:{Origin:base},timeout:45000
      });
      assert.equal(auth.status(),200,"Authenticated browser session is required");
      const response=await page.goto(base+"/tools",{waitUntil:"domcontentloaded",timeout:45000});
      assert.equal(response?.status(),200,"Production /tools should return HTTP 200");
      const issuer=await context.request.get(base+"/api/phase3-readout-survey");
      assert.equal(issuer.status(),200,"Authenticated issuer-specific survey feed must be accessible");
      const published=await issuer.json();
      assert.deepEqual(published.records.map(row=>row.nctId),
        ["NCT06445023","NCT06455202","NCT06641076"]);
      check(!!published.records[0].facts.durability&&!!published.records[1].facts.durability,
        "Separate CSU trials must each carry a source-backed Week 24 field");
      check(published.records[2].facts.durability===undefined,
        "The blinded IZAR-1 topline must not fabricate longer-term durability");
      assert.equal(published.records[2].facts.clinicalBenefit,undefined,
        "Blinded MLTX placebo comparator must never generate synthetic benefit");
      await ratingTest(page,device.label);
      await finalSurveyTest(page,device.label);
      if(!device.mobile)await liveTrialTest(page);
      console.log("PASS",device.label,"production TOOLS browser smoke; page errors",browserErrors.length);
      if(browserErrors.length)console.log("BROWSER_ERRORS",browserErrors.slice(0,4));
    }catch(error){
      console.error("TOOLS_PRODUCTION_BROWSER_FAILURE",device.label,error);
      try{await page.screenshot({path:directory+"/"+device.label+"-failure.png",fullPage:true,timeout:20000});}catch{}
      throw error;
    }finally{await context.close();}
  }
}finally{await browser.close();}
