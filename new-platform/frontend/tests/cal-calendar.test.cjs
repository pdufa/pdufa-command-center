const test = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");

const fromApp = (...parts) => readFileSync(join(__dirname,"..","app",...parts),"utf8");
const source = JSON.parse(readFileSync(join(__dirname,"..","..","..","data","ios_focus_pdufa_calendar.json"),"utf8"));

test("CAL navigation, route and company popup exist",()=>{
  assert.match(fromApp("GlobalNavigation.tsx"),/label:"CAL",href:"\/cal"/);
  assert.match(fromApp("cal","page.tsx"),/IntelligenceHub/);
  assert.match(fromApp("IntelligenceHub.tsx"),/CalCalendar/);
  const ui = fromApp("CalCalendar.tsx");
  assert.match(ui,/showModal\(\)/);
  assert.match(ui,/dialog/);
  assert.match(ui,/sourceUrl/);
  assert.match(ui,/sequence\.get\(event\.id\)/);
  assert.match(ui,/min=\{-12\}/);
  assert.match(ui,/last-base/);
});
test("CAL reuses published FOCUS source with strict no-fallback behavior",()=>{
  const api = fromApp("api","cal","route.ts");
  assert.match(api,/ios_focus_pdufa_calendar\.json/);
  assert.match(api,/source unavailable or invalid/i);
  assert.match(api,/status:503/);
  assert.match(api,/e\.marketCapUsd < 300000000 \|\| e\.marketCapUsd > 10000000000/);
});
test("currently published candidate identifiers and market caps are valid",()=>{
  assert.equal(source.schemaVersion,1);
  assert.ok(Array.isArray(source.events));
  const ids=new Set();
  for(const event of source.events){
    assert.match(event.date,/^\d{4}-\d{2}-\d{2}$/);
    assert.match(event.ticker,/^[A-Z0-9.-]{1,10}$/);
    assert.ok(event.marketCapUsd>=300000000&&event.marketCapUsd<=10000000000);
    assert.ok(!ids.has(event.id),"duplicate source event id");
    ids.add(event.id);
  }
});
