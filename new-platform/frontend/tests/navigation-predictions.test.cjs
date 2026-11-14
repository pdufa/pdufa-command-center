const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const app=path.resolve(__dirname,"../app");

test("global navigation includes a working FDA prediction destination",()=>{
  const nav=fs.readFileSync(path.join(app,"GlobalNavigation.tsx"),"utf8");
  assert.match(nav,/label:"PREDICTIONS",href:"\/predictions"/);
  const page=fs.readFileSync(path.join(app,"predictions/page.tsx"),"utf8");
  assert.match(page,/FDA Outcome Predictions/);
  for(const label of ["FDA Approval","Complete Response Letter (CRL)","FDA Review Delay / Extension"]){
    assert.ok(page.includes(label),label+" outcome missing");
  }
  assert.match(page,/Deep Clinical Subspecialty Intelligence/);
  assert.match(page,/OWNER-ONLY LEVELS 1–20/);
  assert.match(page,/not yet prospectively calibrated/);
  assert.match(page,/ABSTAIN/);
  assert.match(page,/NOT VALIDATED/);
  assert.doesNotMatch(page,/approvalProbability:\s*(?:\d|0\.)/);
});

test("ASSESMENTS tab opens the existing FOCUS scientific review ledger without claiming scores are complete",()=>{
  const nav=fs.readFileSync(path.join(app,"GlobalNavigation.tsx"),"utf8");
  assert.ok(nav.includes('label:"ASSESMENTS",href:"/predictions/assessment"'));
  assert.ok(nav.indexOf('label:"PREDICTIONS"')<nav.indexOf('label:"ASSESMENTS"'));
  assert.ok(nav.indexOf('label:"ASSESMENTS"')<nav.indexOf('label:"TOOLS"'));
  const page=fs.readFileSync(path.join(app,"predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/FOCUS_SPECIALTY_ASSESSMENT_QUEUE/);
  assert.match(page,/OWNER NOT REVIEWED/);
  assert.match(page,/OWNER-ONLY ASSESSMENTS/);
  assert.match(page,/ABSTAIN/);
});
