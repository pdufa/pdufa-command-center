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
const phase=page.locator('[aria-controls="tools-first-phase"]');
const designation=page.locator('[aria-controls="tools-first-designation"]');
try{
  await check("initial-two-choices",async()=>{
    await page.goto(base+"/tools",{waitUntil:"domcontentloaded",timeout:45000});
    await phase.waitFor({timeout:45000});
    assert.equal(await phase.getAttribute("aria-expanded"),"false");
    assert.equal(await designation.getAttribute("aria-expanded"),"false");
    assert.match(await phase.innerText(),/1a\/2[\s\S]*Phase/);
    assert.match(await designation.innerText(),/1b\/2[\s\S]*Special Designation/);
    assert.equal(await page.locator("#tools-first-phase").count(),0);
    assert.equal(await page.locator("#tools-first-designation").count(),0);
    assert.equal(await page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]').count(),0,
      "The initial screen must not be crowded by the funnel");
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
    assert.equal(await page.locator("#tools-first-phase").count(),1);
    assert.equal(await page.locator("#tools-first-designation").count(),0);
    const categories=page.locator('#tools-first-phase [aria-controls^="tools-stage-group-"]');
    assert.equal(await categories.count(),4);
    assert.match(await categories.first().innerText(),/2a\/4/);
    assert.match(await categories.last().innerText(),/2d\/4/);
    assert.equal(await page.locator('#tools-first-phase input[type="checkbox"]').count(),0);
    await categories.first().click();
    const children=page.locator("#tools-stage-group-0");
    assert.equal(await children.getByRole("checkbox").count(),5);
    assert.match(await children.innerText(),/3a\/5/);
    assert.match(await children.innerText(),/3e\/5/);
    const response=scopeResponse({stage:"Phase 2"});
    await children.getByRole("checkbox",{name:/Phase 2(?!\/)/}).check();
    const filtered=await response;
    assert.equal(filtered.status(),200,"Selected Phase 2 must produce a successful existing filtered API response");
    await page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]').waitFor();
    await page.locator('section[aria-label="Selected filters and matching clinical trials spreadsheet"]').waitFor();
    assert.match(await phase.innerText(),/1 selected/);
    await capture("02-phase-selected");
  });
  await check("designation-cascade-and-independent-phase",async()=>{
    await designation.click();
    assert.equal(await designation.getAttribute("aria-expanded"),"true");
    assert.equal(await phase.getAttribute("aria-expanded"),"false");
    assert.equal(await page.locator("#tools-first-phase").count(),0);
    const fda=page.locator("#tools-first-designation");
    const all=fda.getByRole("group",{name:"FDA special designations and pathways"});
    assert.equal(await all.getByRole("checkbox").count(),13);
    assert.match(await all.innerText(),/2a\/13/);
    assert.match(await all.innerText(),/2m\/13/);
    const orphan=all.getByRole("checkbox",{name:/Orphan Drug Designation/});
    await orphan.waitFor({timeout:45000});
    assert.equal(await orphan.isDisabled(),false,"Orphan designation must be selectable with source coverage");
    const response=scopeResponse({stage:"Phase 2",designation:"orphan_drug"});
    await orphan.check();
    const filtered=await response;
    assert.equal(filtered.status(),200,"Phase AND FDA selection must retain prior filter when switching branches");
    assert.match(await designation.innerText(),/1 selected/);
    assert.match(await phase.innerText(),/1 selected/);
    await all.locator("label").filter({has:orphan}).locator("xpath=following-sibling::div[1]").waitFor();
    await capture("03-phase-plus-fda");
  });
  await check("switch-back-and-clear",async()=>{
    await phase.click();
    assert.equal(await page.locator("#tools-first-designation").count(),0);
    assert.equal(await page.locator("#tools-first-phase").count(),1);
    const row=page.locator("#tools-stage-group-0").getByRole("checkbox",{name:/Phase 2(?!\/)/});
    await row.waitFor({timeout:15000});
    assert.equal(await row.isChecked(),true);
    await page.getByRole("button",{name:"Clear all selections"}).click();
    assert.equal(await page.locator("#tools-first-phase").count(),0);
    assert.equal(await phase.getAttribute("aria-expanded"),"false");
    assert.equal(await designation.getAttribute("aria-expanded"),"false");
    assert.equal(await page.locator('section[aria-label="POOL to PIPELINE to TRIALS filter flow"]').count(),0);
    assert.equal(await page.locator('section[aria-label="Selected filters and matching clinical trials spreadsheet"]').count(),0);
    await capture("04-cleared-to-start");
  });
  assert.deepEqual(pageErrors,[],"The mobile guided selection flow must not throw browser errors");
  console.log("TOOLS_GUIDED_MOBILE_WEBKIT_PASS");
}finally{
  await context.close();
  await browser.close();
}
