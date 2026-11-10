const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const get = (...parts)=>fs.readFileSync(path.join(__dirname,"..",...parts),"utf8");

test("CAL COMPANY NEWS are direct destinations and synchronized UI panels",()=>{
 const nav=get("app","GlobalNavigation.tsx");
 for(const [label,href] of [["CAL","/cal"],["COMPANY","/company"],["NEWS","/news"]]){
   assert.ok(nav.includes('label:"'+label+'",href:"'+href+'"'));
   assert.match(get("app",href.slice(1),"page.tsx"),/IntelligenceHub/);
 }
 const hub=get("app","IntelligenceHub.tsx");
 assert.match(hub,/cycleId/);
 assert.match(hub,/onSelectCompany/);
 assert.match(hub,/showModal\(\)/);
 assert.match(hub,/newsFilter/);
 assert.match(hub,/automation\?\.state/);
 assert.match(hub,/jumpFromNews/);
 assert.match(hub,/focusDate=\{focusDate\}/);
 assert.match(hub,/goCal/);
 assert.match(get("app","CalCalendar.tsx"),/onSelectCompany\?\.\(ticker,eventId\)/);
});
test("NEWS distinguishes official news from recorded document leads",()=>{
 const route=get("app","api","news","route.ts");
 for(const marker of ["OFFICIAL_FDA_PUBLICATION","SOURCE_LINK_RECORDED","UNREVIEWED_EXACT_DRUG_MENTION","CYCLE_SOURCE_RECORD","FDA_RSS_UNAVAILABLE"])
  assert.ok(route.includes(marker),marker);
 assert.match(route,/\["www\.fda\.gov","fda\.gov"\]\.includes\(url\.hostname\)/);
 assert.match(route,/url\.protocol="https:"/);
 assert.match(route,/impact:"NOT_ASSESSED"/);
 assert.doesNotMatch(route,/approvalProbability\s*:/);
});
test("No public auto-run endpoint, and medical status is read-only and authenticated",()=>{
 const api=get("app","api","news-automation-status","route.ts");
 assert.match(api,/hasSession/);
 assert.match(api,/export async function GET/);
 assert.doesNotMatch(api,/export async function POST/);
 assert.match(api,/SOURCE_COLLECTION_ONLY/);
});
