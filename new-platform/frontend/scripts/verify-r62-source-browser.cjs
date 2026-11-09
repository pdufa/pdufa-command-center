"use strict";

/** MAIN R62: local, real-Chromium desktop + iPhone-sized source UI acceptance.
 * Does not authenticate to a live application or change any deployed service.
 * Does not browse source links (only checks exact original-source hrefs).
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {chromium} = require("playwright");

const BASE = "http://127.0.0.1:3157/predictions";
const OUT = process.env.RECEIPT_DIR || "/tmp/main-r62-browser";
const PROFILES = [
  {label:"desktop",width:1365,height:850,mobile:false},
  {label:"iphone-390px",width:390,height:844,mobile:true},
];
const RESULTS = [];

async function verifyProfile(browser, profile) {
  const context = await browser.newContext({
    viewport:{width:profile.width,height:profile.height},
    isMobile:profile.mobile,
    hasTouch:profile.mobile,
    deviceScaleFactor:profile.mobile?2:1,
  });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", err=>pageErrors.push(String(err).slice(0,400)));
  try{
    const response = await page.goto(BASE,{waitUntil:"domcontentloaded",timeout:30000});
    assert.equal(response?.status(),200,"development page must respond 200");
    await page.getByRole("heading",{name:"FDA Outcome Predictions"}).waitFor({timeout:20000});
    const panel = page.locator('section[aria-label="R60 source-verified trial findings"]');
    await panel.waitFor({state:"visible",timeout:20000});
    await panel.getByRole("heading",{name:"Expandable scientific source findings · 29 FOCUS trials"}).waitFor();
    assert.equal(await panel.locator("details").count(),29,"29 distinct original NCT cards");
    assert.match(await panel.innerText(),/Validated forecasts\s*0/);

    // Hydration and actual React-driven state changes are required; this is
    // stronger than checking static server-side HTML.
    const search = panel.getByRole("searchbox",{name:"Search original source trial findings"});
    const filter = panel.getByRole("combobox",{name:"Filter original source findings"});
    await panel.getByRole("button",{name:"Expand all findings"}).click();
    await panel.getByRole("button",{name:"Collapse all findings"}).waitFor();
    assert.equal(await panel.locator("details[open]").count(),29,"expand all is live");
    await panel.getByRole("button",{name:"Collapse all findings"}).click();
    assert.equal(await panel.locator("details[open]").count(),0,"collapse all is live");

    await filter.selectOption("POSTED");
    assert.equal(await panel.locator("details").count(),12,
      "12 current originally posted primary-result trial cards");
    await filter.selectOption("RECOVERY");
    assert.equal(await panel.locator("details").count(),17,
      "17 current registry primary-source recovery tasks");
    await filter.selectOption("EXCEPTION");
    const flagged = await panel.locator("details").count();
    assert.ok(flagged>=17&&flagged<=29,"original exception filter must not infer clinical failure");
    await filter.selectOption("ALL");

    await search.fill("SVRA");
    assert.equal(await panel.locator("details").count(),1,"ticker filter must identify one exact NCT");
    const savara = panel.locator("details").first();
    await savara.locator("summary").click();
    await savara.getByText("14/81",{exact:true}).waitFor({state:"visible"});
    await savara.getByText("20/83",{exact:true}).waitFor({state:"visible"});
    assert.ok((await savara.innerText()).includes("0.0007"),"source-only p-value retained");
    assert.ok((await savara.innerText()).includes("6.0"),"source-only effect retained");
    const clinicalLink = savara.getByRole("link",{name:"Original ClinicalTrials.gov record"});
    assert.equal(await clinicalLink.getAttribute("href"),
      "https://clinicaltrials.gov/study/NCT04544293");
    assert.equal(await savara.getByRole("link",{name:"Scientific method matrix"}).getAttribute("href"),
      "/predictions/assessment?nct=NCT04544293");

    await page.screenshot({path:path.join(OUT,profile.label+"-savara-source.png"),fullPage:false});

    await search.fill("NCT05126758");
    assert.equal(await panel.locator("details").count(),1,"exact NCT search works");
    const missing = panel.locator("details").first();
    await missing.locator("summary").click();
    assert.match(await missing.innerText(),
      /No primary outcome result table in this archived current registry copy/);
    assert.match(await missing.innerText(),/Check original Phase 3 sponsor, journal and regulatory records/);
    assert.equal(await missing.getByRole("link",{name:"Original ClinicalTrials.gov record"}).getAttribute("href"),
      "https://clinicaltrials.gov/study/NCT05126758");

    await search.fill("");
    assert.equal(await panel.locator("details").count(),29);
    const ncts = await panel.locator("details summary strong").allTextContents();
    assert.equal(new Set(ncts.map(s=>s.match(/NCT\d{8}/)?.[0])).size,29);

    // The independent R62 application source-review section is a distinct
    // 23-cycle worklist. Test its actual client-side filtering and exact
    // registry-to-application crosswalk without treating it as an FDA forecast.
    const applications = page.locator(
      'section[aria-label="R62 provisional application source review"]');
    await applications.waitFor({state:"visible"});
    assert.equal(await applications.locator("details").count(),23,
      "23 provisional application groups must render exactly once");
    assert.match(await applications.innerText(),/Validated FDA forecasts\\s*0/);
    const applicationSearch=applications.getByRole("searchbox",{
      name:"Find application source evidence"});
    const applicationFilter=applications.getByRole("combobox",{
      name:"Filter application source evidence"});
    await applicationFilter.selectOption("POSTED");
    const appPosted=await applications.locator("details").count();
    assert.ok(appPosted>0&&appPosted<23,
      "application posted-primary filter changes actual rendered rows");
    await applicationFilter.selectOption("RECOVERY");
    const appRecovery=await applications.locator("details").count();
    assert.ok(appRecovery>0&&appRecovery<=23);
    await applicationFilter.selectOption("ALL");
    await applicationSearch.fill("SVRA");
    assert.equal(await applications.locator("details").count(),1,
      "SVRA must identify one exact provisional application cycle");
    const savaraApplication=applications.locator("details").first();
    await savaraApplication.locator("summary").click();
    await savaraApplication.getByText("NCT04544293",{exact:true}).waitFor();
    assert.equal(await savaraApplication.getByRole("link",{name:"Original trial record"}).getAttribute("href"),
      "https://clinicaltrials.gov/study/NCT04544293");
    assert.equal(await savaraApplication.getByRole("link",{name:"Scientific assessment"}).getAttribute("href"),
      "/predictions/assessment?nct=NCT04544293&cycle=svra-molgramostim");
    await page.screenshot({path:path.join(OUT,profile.label+"-application-evidence.png"),
      fullPage:false});
    await applicationSearch.fill("");
    assert.equal(await applications.locator("details").count(),23);
    await applicationFilter.selectOption("EXCEPTIONS");
    assert.ok(await applications.locator("details").count()>0);
    await applicationFilter.selectOption("ALL");

    const fullText=await page.locator("main").innerText();
    assert.match(fullText,/NOT CALIBRATED/);
    assert.match(fullText,/ABSTAIN/);
    assert.match(fullText,/No numerical forecast has been independently validated or released/);
    assert.equal(pageErrors.length,0,"no browser JavaScript exceptions");

    if(profile.mobile){
      const widths = await panel.evaluate(el=>({
        outer:el.getBoundingClientRect().width,
        inner:el.scrollWidth, viewport:document.documentElement.clientWidth,
      }));
      assert.ok(widths.outer<=widths.viewport+2,
        "research panel must fit iPhone-sized viewport");
    }

    RESULTS.push({
      profile:profile.label,viewport:[profile.width,profile.height],
      pageHttpStatus:response.status(),nctRows:29,postedRows:12,recoveryRows:17,applicationRows:23,
      originalSourceLinksExact:true,reactiveSearchAndExpand:true,applicationCrosswalkInteractions:true,
      independentClinicalSignoffs:0,validatedFDAForecasts:0,
      browserPageErrors:pageErrors,
    });
  }finally{
    await context.close();
  }
}

(async()=>{
  fs.mkdirSync(OUT,{recursive:true});
  const browser=await chromium.launch({headless:true});
  try{
    for(const profile of PROFILES)await verifyProfile(browser,profile);
    fs.writeFileSync(path.join(OUT,"R62_BROWSER_RESULTS.json"),
      JSON.stringify({schema:"MAIN_R62_SOURCE_BROWSER_RESPONSIVE_ACCEPTANCE",
        environment:"LOCAL_NEXT_SERVER_NOT_LIVE_SIGNED_IN",
        evidence:RESULTS,
        productionWrites:false,fdaForecastRelease:false},null,2)+"\n");
    console.log(JSON.stringify({status:"PASS",profiles:RESULTS.map(x=>x.profile),
      exactNcts:29,applicationGroups:23,realBrowserInteractions:true,
      signedInLiveBrowserVerified:false,productionWrites:false}));
  }finally{await browser.close();}
})().catch(error=>{console.error("MAIN_R62_SOURCE_BROWSER_FAILURE:",error);process.exitCode=1;});
