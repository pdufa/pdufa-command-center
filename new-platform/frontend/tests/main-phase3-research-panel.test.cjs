const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {act,create}=require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file
);
require.extensions[".css"]=mod=>{mod.exports=new Proxy({}, {get:(_obj,key)=>String(key)});};
const pinned=require("../data/main-phase3-qualification-snapshot-20261026.json");
const {parsePinnedResearchSnapshot}=require("../lib/main-phase3-research-snapshot.ts");
const MainPhase3ResearchPanel=require("../app/MainPhase3ResearchPanel.tsx").default;
const mutate=(fn)=>{const x=structuredClone(pinned);fn(x);return x;};

test("pinned original GitHub run has a complete but non-qualifying nine-gate research snapshot",()=>{
  const x=parsePinnedResearchSnapshot(pinned);
  assert.equal(x.captureMode,"PINNED_VERIFIED_GITHUB_ACTIONS_RUN_NOT_LIVE");
  assert.equal(x.sourceRunId,40387212933);
  assert.equal(x.historicalTrialCount,741);
  assert.equal(x.issuerResearchPointerCount,130);
  assert.equal(x.mandatoryGates.length,9);
  assert.equal(x.gateChecksDenominator,6669);
  assert.equal(x.gateChecksPass,741);
  assert.equal(x.gateChecksReview,5928);
  assert.equal(x.rightsReviewChecklistSlots,4446);
  assert.equal(x.rightsSlotsWithSubmissions,0);
  assert.equal(x.independentlyVerifiedCurrentRightsTrials,0);
  assert.equal(x.qualifiedPipelineCount,null);
});

test("missing, forged, reordered or promoted research source figures are rejected",()=>{
  const bad=[
    x=>{x.sourceRunId=40387212934;},
    x=>{x.sourceRunUrl="https://example.org/unverified";},
    x=>{x.sourceBranchHead="0".repeat(40);},
    x=>{x.captureMode="LIVE";},
    x=>{x.historicalTrialCount=742;},
    x=>{x.issuerResearchPointerCount=131;},
    x=>{x.gateChecksPass=742;},
    x=>{x.gateChecksReview=5927;},
    x=>{x.mandatoryGates[1].pass=1;x.mandatoryGates[1].review=740;},
    x=>{x.mandatoryGates[1].gate="verified_pdufa";},
    x=>{x.rightsSlotsWithSubmissions=100;},
    x=>{x.secPrimaryDocumentsAttempted=20;},
    x=>{x.independentlyVerifiedCurrentRightsTrials=1;},
    x=>{x.qualifiedPipelineCount=0;},
    x=>{x.mandatoryGates.pop();},
    x=>{x.fakeLiveTradingSignal=true;},
  ];
  for(const fn of bad)assert.throws(()=>parsePinnedResearchSnapshot(mutate(fn)));
});

test("MAIN site card prominently separates research history from live membership",async()=>{
  let renderer;
  try{
    await act(async()=>{renderer=create(React.createElement(MainPhase3ResearchPanel));});
    const output=JSON.stringify(renderer.toJSON());
    assert.match(output,/MAIN · Phase 3 historical research/);
    assert.match(output,/NOT LIVE/);
    assert.match(output,/741 historical NCT study records/);
    assert.match(output,/741\/741/);
    assert.match(output,/741\/6,669/);
    assert.match(output,/5,928\/6,669/);
    assert.match(output,/0\/4,446/);
    assert.match(output,/UNKNOWN \(not zero\)/);
    assert.match(output,/40387212933/);
    assert.match(output,/SEC_USER_AGENT/);
    assert.doesNotMatch(output,/FDA approved|approval probability|automatically qualified/);
    const summaries=renderer.root.findAllByType("summary");
    assert.equal(summaries.length,2);
    assert.match(summaries[0].props.children,/All nine mandatory/);
    assert.match(summaries[1].props.children,/Secondary source coverage/);
    const rows=renderer.root.findAllByType("tr");
    assert.equal(rows.length,10); // 1 header + all 9 mandatory gates
    const links=renderer.root.findAllByType("a");
    assert.ok(links.length>=2);
    assert.equal(links[0].props.href,pinned.sourceRunUrl);
    assert.equal(links[0].props.target,"_blank");
    assert.ok(links.some(link=>String(link.props.href).includes(
      "/actions/workflows/main-phase3-evidence-qualification.yml")));
    const status=renderer.root.findAllByProps({role:"status"});
    assert.ok(status.some(entry=>JSON.stringify(entry.props.children).includes(
      "Scheduled scan status cannot be verified from GitHub")));
  }finally{if(renderer)await act(async()=>renderer.unmount());}
});

test("research panel appears only within PDUFA Pipeline and does not change stage memberships",()=>{
  const source=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
  assert.match(source,/import MainPhase3ResearchPanel from "\.\/MainPhase3ResearchPanel";/);
  assert.match(source,/\{top==="PDUFA" && nav==="PIPELINE" && <MainPhase3ResearchPanel \/>}/);
  assert.doesNotMatch(source,/setPipeline.*main.phase3|setGem.*main.phase3/i);
  const css=fs.readFileSync(path.join(__dirname,"../app/MainPhase3ResearchPanel.module.css"),"utf8");
  assert.match(css,/@media\(max-width:540px\)/);
  assert.match(css,/@media\(max-width:840px\)/);
  assert.match(css,/overflow:auto/);
});
