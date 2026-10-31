"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.join(__dirname,"../../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
test("active site top navigation and workbench offer no GEM stage links",()=>{
 const nav=read("new-platform/frontend/app/GlobalNavigation.tsx");
 const workspace=read("new-platform/frontend/app/Workspace.tsx");
 const home=read("new-platform/frontend/app/page.tsx");
 assert.match(nav,/label:"POOL",href:"\/pool"/);
 assert.match(nav,/label:"PIPELINE",href:"\/pipeline"/);
 assert.doesNotMatch(nav,/label:"GEM(?: JR)?"/);
 assert.doesNotMatch(workspace,/\["GEM_JR","GEM JR"\].*\["GEM","GEM"\]/);
 assert.match(workspace,/\(\["PIPELINE"\] as RestrictionPresetStage\[\]\)/);
 assert.doesNotMatch(home,/from "\.\/Workspace"/);
 assert.match(home,/href:"\/pool"/);
 assert.match(home,/href:"\/pipeline"/);
});
test("live source workspace has no GEM membership ledger, inputs or stage qualifiers",()=>{
 const source=read("new-platform/backend/app/source_workspace.py");
 assert.doesNotMatch(source,/sources\["gem_stage_membership\.json"\]/);
 assert.doesNotMatch(source,/sources\["gem_runway_evidence\.json"\]/);
 assert.doesNotMatch(source,/sources\["gem_two_close_recheck\.csv"\]/);
 assert.match(source,/ledger: dict = \{\}/);
 assert.match(source,/"GEM_JR": \{"asOf": "", "rows": \[\], "history": \[\]\}/);
 assert.match(source,/"GEM": \{"asOf": "", "rows": \[\], "history": \[\]\}/);
 assert.match(source,/original_pipeline_universe\(records, now\)/);
});
test("phase3 results scan remains live but GEM qualification and financing are not scheduled",()=>{
 const clinical=read(".github/workflows/pdufa-nightly-clinical.yml");
 const overnight=read(".github/workflows/pdufa-overnight-sequential.yml");
 const starter=read(".github/workflows/pdufa-nightly-pacific-start.yml");
 assert.match(clinical,/phase3_results:/);
 assert.match(clinical,/validate_clinical_snapshot\.py --scan 4/);
 assert.doesNotMatch(clinical,/\n  gem_block:|\n  gem_financing:|\n  gem_jr:/);
 assert.doesNotMatch(overnight,/include_gem:|gem_action:/);
 assert.doesNotMatch(starter,/inputs\[gem_action\]/);
 for(const p of [".github/workflows/gem-jr-gem-pre15-rescan.yml",".github/workflows/gem-research-quality.yml",
   ".github/workflows/gem-financing-full-coverage.yml",".github/workflows/reconcile-730-gem.yml",
   ".github/workflows/phase3-730-unfiltered-gem.yml",
   ".github/workflows/gem-research-diagnostics.yml",".github/workflows/gem-original-qualification-ui.yml",
   ".github/workflows/gem-potential-live-audit.yml",".github/workflows/live-streamlit-audit.yml"]){
  assert.equal(fs.existsSync(path.join(root,p)),false,"retired job must not be registered: "+p);
 }
});
test("active browser scan endpoints cannot dispatch GEM or create new GEM checklists",()=>{
 const route=read("new-platform/frontend/app/api/scans/control/route.ts");
 const checklist=read("new-platform/frontend/app/api/program-state/route.ts");
 assert.match(route,/const SCANS = \["ALL", "PIPELINE", "PHASE3_RESULTS"\]/);
 assert.match(checklist,/stage !== "PIPELINE"/);
});
