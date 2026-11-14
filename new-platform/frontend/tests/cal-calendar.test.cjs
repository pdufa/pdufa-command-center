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

const research = JSON.parse(readFileSync(join(__dirname,"..","data",
  "calFocusResearchOverlay20261110.json"),"utf8"));
const roster = JSON.parse(readFileSync(join(__dirname,"..","data",
  "p3PostDataActive.json"),"utf8"));

test("CAL shows source-linked future FDA-cycle research and preserves independent forecasts",()=>{
  const api=fromApp("api","cal","route.ts");
  const ui=fromApp("CalCalendar.tsx");
  assert.match(api,/calFocusResearchOverlay20261110\.json/);
  assert.match(api,/matchedCycleIds/);
  assert.match(api,/e\.ncts\.includes\(n\)/);
  assert.match(api,/c\.reportedPdufaGoal === e\.date/);
  assert.match(api,/c\.call === "ALREADY_APPROVED"/);
  assert.match(api,/GOAL_NOT_IN_PUBLISHED_CALENDAR_REQUIRES_VERIFICATION/);
  assert.match(api,/No substitute data is displayed|no substitute data is displayed/);
  assert.match(ui,/shortCall\(event\.prediction\.call\)/);
  assert.match(ui,/PredictionSummary prediction=\{event\.prediction\}/);
  assert.match(ui,/awaiting a published FDA goal date/);
  assert.match(ui,/independently reviewed FDA forecast/);
  assert.match(ui,/ALREADY_APPROVED/);
});

test("provisional research is frozen, application-cycle exact and never a validated probability",()=>{
  assert.equal(research.kind,"CAL_FOCUS_LEVEL3_STYLE_RESEARCH_FREEZE_NOT_VALIDATED_FDA_FORECAST");
  assert.equal(research.cycles.length,23);
  assert.equal(roster.records.length,32);
  assert.equal(research.policy.independentScientificSignoff,false);
  assert.equal(research.policy.numericalProbabilities,null);
  assert.equal(research.policy.notActivePredictionEngine,true);
  assert.equal(research.summary.approvalLeans,12);
  assert.equal(research.summary.crlLeans,5);
  assert.equal(research.summary.abstentions,5);
  assert.equal(research.summary.alreadyApproved,1);
  const byNct=new Map(roster.records.map(x=>[x.nct,x]));
  assert.equal(new Set(research.cycles.map(x=>x.cycleId)).size,23);
  for(const c of research.cycles){
    assert.equal(c.level,3);
    assert.equal(c.independentSignoff,false);
    assert.equal(c.calibratedProbability,null);
    assert.ok(["APPROVAL_LEAN","CRL_LEAN","ABSTAIN","ALREADY_APPROVED"].includes(c.call));
    assert.ok(c.associatedNcts.length>0);
    for(const n of c.associatedNcts) assert.equal(byNct.get(n)?.ticker,c.ticker);
  }
});

test("future dated calendar events map by cycle, not just ticker",()=>{
  const dated=new Map();
  const unmapped=new Set(["NCT05031780","NCT06747468","NCT06553768"]);
  const exceptions=new Set();
  for(const e of source.events){
    const joined=research.cycles.filter(c=>c.ticker===e.ticker &&
      c.associatedNcts.some(n=>e.ncts.includes(n)) &&
      (c.reportedPdufaGoal===e.date || c.call==="ALREADY_APPROVED"));
    dated.set(e.id,joined);
    if(e.ncts.every(n=>unmapped.has(n))){
      assert.equal(joined.length,0,"Unmapped trials must not acquire invented cycles");
      e.ncts.forEach(n=>exceptions.add(n));
    }else assert.ok(joined.length>0,"Mapped entry without matching cycle: "+e.id);
  }
  assert.deepEqual([...exceptions].sort(),["NCT05031780"],"Only this unmapped trial has a dated entry in the frozen calendar");
  assert.ok([...unmapped].every(n=>research.cycles.every(c=>!c.associatedNcts.includes(n))),"None of the three exceptions may acquire an invented cycle");
  assert.equal(dated.get("focus-srpt-nct02500381").length,2,
    "two Sarepta products require two FDA-cycle predictions");
  const cy=dated.get("focus-cytk-nct05767346");
  assert.equal(cy.length,1);
  assert.equal(cy[0].call,"ALREADY_APPROVED");
  assert.equal(cy[0].reportedPdufaGoal,null,
    "already approved cycle cannot be treated as a current pending PDUFA");
  const mapped=new Set([...dated.values()].flat().map(c=>c.cycleId));
  assert.equal(mapped.size,16);
  const undated=research.cycles.filter(c=>!mapped.has(c.cycleId)&&c.call!=="ALREADY_APPROVED");
  assert.equal(undated.length,7);
  assert.ok(undated.every(c=>c.reportedPdufaGoal===null),
    "do not invent dates for planned applications");
});
