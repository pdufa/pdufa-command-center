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
    await page.goto(base+"/tools",{waitUntil:"domcontentloaded",timeout:45000});
    assert.match(await page.title(),/TOOLS/);
    await page.getByRole("heading",{name:"POOL",exact:true}).waitFor({timeout:15000});
    await page.getByRole("button",{name:/Find Phase 3 \+ Orphan Drug trials/}).waitFor();
    assert.match(await page.locator("body").innerText(),/0 matching trials/);
    assert.doesNotMatch(await page.locator("body").innerText(),/Calculating matching trial records from saved sources/);
    await screenshot("01-no-selections");
  });
  await check("stage-only",async()=>{
    await page.locator("details").filter({has:page.getByText("Select clinical trial stages")}).locator("summary").click();
    await page.getByRole("checkbox",{name:/^Phase 2(?!\/)/}).check();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("3,269"),{timeout:100000});
    const count=await page.locator(".nonexistent").count();
    const selected=await page.getByRole("checkbox",{name:/^Phase 2(?!\/)/}).isChecked();
    assert.equal(selected,true);
    await screenshot("02-stage-Phase-2");
    return {selected,count};
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
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("4 documented linked trial matches"),{timeout:100000});
    assert.equal(await page.getByRole("checkbox",{name:/^Orphan Drug Designation/}).isChecked(),true);
    await screenshot("03-orphan-only");
  });
  await check("one-tap-combined",async()=>{
    await page.getByRole("button",{name:"Find Phase 3 + Orphan Drug trials"}).click();
    await page.getByRole("checkbox",{name:/^Phase 3(?! Results)/}).waitFor();
    assert.equal(await page.getByRole("checkbox",{name:/^Phase 3(?! Results)/}).isChecked(),true);
    assert.equal(await page.getByRole("checkbox",{name:/^Orphan Drug Designation/}).isChecked(),true);
    await page.waitForFunction(()=>!document.body.innerText.includes("Calculating matching trial records from saved sources") &&
      !document.body.innerText.includes("Calculating matching trials…"),{timeout:100000});
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
    await page.getByRole("button",{name:"Find Phase 3 + Orphan Drug trials"}).click();
    await page.getByRole("checkbox",{name:/^Phase 3(?! Results)/}).uncheck();
    await page.getByRole("checkbox",{name:/^Phase 2(?!\/)/}).check();
    await page.getByRole("checkbox",{name:/^Orphan Drug Designation/}).uncheck();
    await page.getByRole("checkbox",{name:/^Priority Review/}).check();
    await page.waitForFunction(()=>document.querySelector("section[aria-label='Selected filters and matching clinical trials spreadsheet']")?.textContent?.includes("1 documented linked trial matches"),{timeout:100000});
    const summary=await page.locator("section[aria-label='Selected filters and matching clinical trials spreadsheet']").innerText();
    assert.match(summary,/NCT\d{8}/);
    await screenshot("05-phase-2-and-priority");
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
