import assert from "node:assert/strict";
import fs from "node:fs/promises";
import {webkit} from "playwright";

const base="https://pdufa-new-dashboard.vercel.app";
const pass=process.env.DASHBOARD_PASSWORD;
if(!pass)throw Error("Production dashboard authentication secret unavailable");
const out="test-results/tools-mobile";
await fs.mkdir(out,{recursive:true});
const browser=await webkit.launch({headless:true});
const context=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:3,isMobile:true,hasTouch:true,
  locale:"en-US",userAgent:"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"});
const page=await context.newPage();
const responseEvents=[];
page.on("response",response=>{
  if(response.url().includes("/api/scope-funnel")||response.url().includes("/api/trial-designations")){
    const u=new URL(response.url());
    const item={status:response.status(),path:u.pathname,stages:u.searchParams.get("stages"),
      designations:u.searchParams.get("designations"),query:u.searchParams.get("query")};
    responseEvents.push(item);console.log("LIVE_API",JSON.stringify(item));
  }
});
page.on("pageerror",err=>console.error("BROWSER_PAGE_ERROR",err.message));
page.on("console",msg=>{if(msg.type()==="error")console.error("BROWSER_CONSOLE_ERROR",msg.text().slice(0,400));});
async function screenshot(name){await page.screenshot({path:out+"/"+name+".png",fullPage:true});}
async function check(label,action){
  console.log("CHECK_START",label);
  try{const t=Date.now();const result=await action();console.log("CHECK_OK",label,"ms",Date.now()-t,result===undefined?"":JSON.stringify(result));}
  catch(err){await screenshot("failure-"+label.replaceAll(/[^a-z0-9]+/gi,"-"));console.error("CHECK_FAILED",label,String(err));throw err;}
}
const auth=await context.request.post(base+"/api/auth",{data:{password:pass},headers:{Origin:base}});
assert.equal(auth.status(),200,"Authenticated session POST failed");
assert.deepEqual(await auth.json(),{authenticated:true});
const checkSession=await context.request.get(base+"/api/auth");
assert.equal(checkSession.status(),200);
assert.deepEqual(await checkSession.json(),{authenticated:true});
console.log("AUTHENTICATED_BROWSER_SESSION_READY");
try{
  await check("mobile-load",async()=>{
    const initialResponse=page.waitForResponse(r=>r.url().includes("/api/scope-funnel")&&r.url().includes("tools=1"),{timeout:90000});
    const firstStarted=Date.now();
    await page.goto(base+"/tools",{waitUntil:"domcontentloaded",timeout:45000});
    const loaded=await initialResponse;
    const firstPoolMs=Date.now()-firstStarted;
    console.log("INITIAL_AUTHENTICATED_POOL_LOAD_MS",firstPoolMs,"HTTP",loaded.status());
    assert.equal(loaded.status(),200,"Initial protected POOL request must succeed");
    assert.ok(firstPoolMs<12000,"Initial verified POOL query took "+firstPoolMs+" ms; stale 22-second backend path remains");
    assert.match(await page.title(),/TOOLS/);
    await page.getByRole("heading",{name:"POOL",exact:true}).waitFor({timeout:15000});
    await page.getByText("Find Phase 3 + Orphan Drug trials",{exact:true}).waitFor();
    assert.match(await page.locator("body").innerText(),/0 matching trials/);
    assert.doesNotMatch(await page.locator("body").innerText(),/Calculating matching trial records from saved sources/);
    await screenshot("01-no-selections");
  });
  await check("stage-only",async()=>{
    await page.locator("details").filter({has:page.getByText("Select clinical trial stages")}).locator("summary").click();
    await page.getByRole("checkbox",{name:/^Phase 2(?!\/)/}).check();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("3,269"),null,{timeout:100000});
    const selected=await page.getByRole("checkbox",{name:/^Phase 2(?!\/)/}).isChecked();
    assert.equal(selected,true);
    await screenshot("02-stage-Phase-2");
    return {selected};
  });
  await check("clear-all",async()=>{
    await page.getByRole("button",{name:"Clear all filters"}).click();
    await page.waitForTimeout(200);
    assert.equal(await page.getByRole("checkbox",{name:/^Phase 2(?!\/)/}).isChecked(),false);
    assert.match(await page.locator("body").innerText(),/0 matching trials/);
  });
  await check("designation-only",async()=>{
    await page.locator("details").filter({has:page.getByText("Select FDA designations")}).locator("summary").click();
    await page.getByRole("checkbox",{name:/^Orphan Drug Designation/}).check();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("4 documented linked trial matches"),null,{timeout:100000});
    assert.equal(await page.getByRole("checkbox",{name:/^Orphan Drug Designation/}).isChecked(),true);
    await screenshot("03-orphan-only");
  });
  await check("all-stages-preserve-selected-designation-trial-count",async()=>{
    // "Select all phases" is mathematically the same as an unrestricted stage
    // selection, so the exact-NCT designation count cannot decrease.
    await page.getByRole("button",{name:"Select all",exact:true}).click();
    const checked=page.getByRole("group",{name:"Clinical development stages"})
      .getByRole("checkbox",{checked:true});
    assert.equal(await checked.count(),14);
    await page.getByText(/All-stage check passed: 4 matched trials = 4 linked designation trials/).waitFor({timeout:45000});
    const sameCount=page.locator("section[aria-label='Selected filters and matching clinical trials spreadsheet']");
    assert.match(await sameCount.innerText(),/4 documented linked trial matches/);
    await screenshot("03b-all-phases-orphan-parity");
  });
  await check("accelerated-approval-16-programs-not-false-zero-trials",async()=>{
    await page.getByRole("button",{name:"Clear all filters"}).click();
    const accelerated=page.getByRole("checkbox",{name:/^Accelerated Approval/});
    await accelerated.check();
    await page.waitForFunction(()=>{
      const sheet=document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']");
      return sheet?.textContent?.includes("16 source-backed FDA program records") &&
        sheet?.textContent?.includes("NCT count not established");
    },null,{timeout:60000});
    assert.equal(await accelerated.isChecked(),true);
    assert.match(await page.locator("section[aria-label='POOL to PIPELINE to TRIALS filter flow']").innerText(),/Not established/);
    const before=await page.locator("section[aria-label='Selected filters and matching clinical trials spreadsheet']").innerText();
    assert.match(before,/16 source-backed FDA program records/);
    assert.match(before,/NCT link not established/);
    await page.getByRole("button",{name:"Select all",exact:true}).click();
    await page.waitForFunction(()=>{
      const funnel=document.querySelector("section[aria-label='POOL to PIPELINE to TRIALS filter flow']");
      const sheet=document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']");
      return funnel?.textContent?.includes("Selecting all stages cannot establish the number of clinical trials")
        && sheet?.textContent?.includes("16 source-backed FDA program records")
        && !document.body.textContent?.includes("Calculating matching trial records from saved sources");
    },null,{timeout:60000});
    const allStages=page.getByRole("group",{name:"Clinical development stages"}).getByRole("checkbox",{checked:true});
    assert.equal(await allStages.count(),14);
    const after=await page.locator("section[aria-label='Selected filters and matching clinical trials spreadsheet']").innerText();
    assert.match(after,/16 source-backed FDA program records/);
    assert.match(after,/NCT count not established/);
    assert.doesNotMatch(after,/UNIQUE TRIALS MATCHING COMBINED FILTERS\s+0/);
    const download=page.locator("section[aria-label='Selected filters and matching clinical trials spreadsheet']")
      .getByRole("link",{name:"Export FDA program records (CSV)"});
    await download.waitFor();
    const programs=await context.request.get(base+"/api/scope-funnel?view=pool&recordKind=trials&tools=1&limit=50&offset=0&format=csv&designations=accelerated_approval&stages="+encodeURIComponent(
      ["Early Phase 1","Phase 1","Phase 1/2","Phase 2","Phase 2/3","Phase 3","Phase 3 Results","NDA/BLA Submission","FDA Acceptance","PDUFA Decision","Post-Decision","Phase 4","Not Applicable","Unknown"].join(",")
    ),{timeout:90000});
    assert.equal(programs.status(),200,"FDA program CSV export rejected");
    assert.equal(programs.headers()["x-pdufa-record-type"],"FDA_PROGRAM_EVENT_NOT_NCT");
    const csvText=await programs.text();
    assert.match(csvText,/FDA PROGRAM EVENT — NOT A CLINICAL TRIAL/);
    assert.equal(csvText.trim().split(/\r?\n/).length,17,"16 sourced programs plus one CSV header");
    await screenshot("03c-accelerated-approval-all-stages-unverified");
    await page.getByRole("button",{name:"Clear all filters"}).click();
  });
  await check("one-tap-combined",async()=>{
    await page.getByText("Find Phase 3 + Orphan Drug trials",{exact:true}).click();
    await page.getByRole("checkbox",{name:/^Phase 3(?! Results)/}).waitFor();
    assert.equal(await page.getByRole("checkbox",{name:/^Phase 3(?! Results)/}).isChecked(),true);
    assert.equal(await page.getByRole("checkbox",{name:/^Orphan Drug Designation/}).isChecked(),true);
    await page.waitForFunction(()=>!document.body.innerText.includes("Calculating matching trial records from saved sources") &&
      !document.body.innerText.includes("Calculating matching trials…"),null,{timeout:100000});
    assert.doesNotMatch(await page.locator("body").innerText(),/Results unavailable:/);
    await screenshot("04-phase-3-and-orphan");
  });
  await check("dropdown-counts-and-clear",async()=>{
    const stageCheckbox=page.getByRole("checkbox",{name:/^Phase 3(?! Results)/});
    const orphanCheckbox=page.getByRole("checkbox",{name:/^Orphan Drug Designation/});
    assert.equal(await stageCheckbox.isChecked(),true);
    assert.equal(await orphanCheckbox.isChecked(),true);
    await page.getByRole("button",{name:"Clear all filters"}).click();
    assert.equal(await stageCheckbox.isChecked(),false);
    assert.equal(await orphanCheckbox.isChecked(),false);
    assert.match(await page.locator("body").innerText(),/0 matching trials/);
  });
  await check("mixed-known-positive",async()=>{
    await page.getByText("Find Phase 3 + Orphan Drug trials",{exact:true}).click();
    await page.getByRole("checkbox",{name:/^Phase 3(?! Results)/}).uncheck();
    await page.getByRole("checkbox",{name:/^Phase 2(?!\/)/}).check();
    await page.getByRole("checkbox",{name:/^Orphan Drug Designation/}).uncheck();
    await page.getByRole("checkbox",{name:/^Priority Review/}).check();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("1 documented linked trial matches"),null,{timeout:100000});
    const summary=await page.locator("section[aria-label='Selected filters and matching clinical trials spreadsheet']").innerText();
    assert.match(summary,/NCT\d{8}/);
    await screenshot("05-phase-2-and-priority");
  });
  await check("all-14-clinical-stage-checkboxes",async()=>{
    const allStages=page.getByRole("group",{name:"Clinical development stages"}).getByRole("checkbox");
    assert.equal(await allStages.count(),14);
    await page.getByRole("button",{name:"Clear all filters"}).click();
    await page.getByRole("button",{name:"Select all",exact:true}).click();
    assert.equal(await page.getByRole("group",{name:"Clinical development stages"}).getByRole("checkbox",{checked:true}).count(),14);
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("11,623"),null,{timeout:45000});
    await page.getByRole("button",{name:"Clear all filters"}).click();
    assert.equal(await page.getByRole("group",{name:"Clinical development stages"}).getByRole("checkbox",{checked:true}).count(),0);
  });
  await check("all-13-FDA-checkboxes-available-and-unavailable",async()=>{
    const fda=page.getByRole("group",{name:"FDA special designations and pathways"});
    assert.equal(await fda.getByRole("checkbox").count(),13);
    assert.equal(await fda.locator("input[type=checkbox]:disabled").count(),5);
    await page.getByRole("button",{name:"Select all available"}).click();
    assert.equal(await fda.getByRole("checkbox",{checked:true}).count(),8);
    await page.getByRole("button",{name:"Clear all filters"}).click();
    assert.equal(await fda.getByRole("checkbox",{checked:true}).count(),0);
  });
  await check("search-and-pagination",async()=>{
    await page.getByRole("checkbox",{name:/^Phase 2(?!\/)/}).check();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("3,269"),null,{timeout:45000});
    await page.getByRole("button",{name:"Next 50"}).click();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("Showing 51–100"),null,{timeout:45000});
    await page.getByRole("button",{name:"Previous 50"}).click();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("Showing 1–50"),null,{timeout:45000});
    const search=page.getByRole("searchbox",{name:/Search trial NCT/});
    await search.fill("NO_MATCH_XYZ_2026");
    await page.getByRole("button",{name:"Search results"}).click();
    await page.waitForFunction(()=>document.body.textContent?.includes("No documented NCT links match the selected filters") ||
      document.body.textContent?.includes("No source-linked NCT trials match the selected filters"),null,{timeout:45000});
    await page.getByRole("button",{name:"Clear search"}).click();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("Showing 1–50"),null,{timeout:45000});
    await page.getByRole("button",{name:"Clear all filters"}).click();
  });
  await check("csv-export",async()=>{
    const csvPath="/api/scope-funnel?view=pool&recordKind=trials&tools=1&limit=50&offset=0&format=csv&stages=Phase%202&designations=priority_review";
    const response=await context.request.get(base+csvPath,{timeout:90000});
    assert.equal(response.status(),200,"CSV export rejected");
    assert.match(response.headers()["content-type"],/text\/csv/);
    const data=await response.text();
    assert.match(data,/NCT ID/);
    assert.match(data,/Priority Review/);
    assert.match(data,/NCT\d{8}/);
    return {rows:data.trim().split(/\r?\n/).length-1};
  });
  console.log("LIVE_MOBILE_TOOLS_ALL_CHECKS_PASSED",JSON.stringify(responseEvents));
}finally{
  await browser.close();
}
