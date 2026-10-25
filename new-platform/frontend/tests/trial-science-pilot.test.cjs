const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const React = require("react");
const {act,create} = require("react-test-renderer");

global.IS_REACT_ACT_ENVIRONMENT = true;
for(const ext of [".ts", ".tsx"]) require.extensions[ext] = (mod,file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX,
    esModuleInterop: true,
  }}).outputText, file
);
require.extensions[".css"] = (mod) => {mod.exports = new Proxy({}, {get:(_,key)=>String(key)});};
const {PILOT_NCT, SCIENCE_DOMAIN_LABELS, validTrialSciencePilot, pilotDomainStatus, safePilotSource} =
  require("../lib/trial-science-pilot.ts");
const TrialSciencePilot = require("../app/TrialSciencePilot.tsx").default;
const domains = Object.keys(SCIENCE_DOMAIN_LABELS);
const ref = (id, analysis, date) => ({
  analysis_id: analysis,
  report_type: analysis === "keynote024_initial_2016"
    ? "original_randomized_trial_interim_analysis"
    : analysis === "keynote024_pros_2017"
      ? "prespecified_exploratory_patient_reported_outcomes"
      : "long_term_followup",
  publication_date: date,
  source_id: id,
  source_url: "https://pubmed.ncbi.nlm.nih.gov/" + id + "/",
  nct_id: PILOT_NCT,
  methodological_caveats: ["Independent appraisal pending"],
  source_evidence_status: "published_reported_not_independently_reanalyzed",
});
function payload() {
  return {
    pilot: {
      nct_id:PILOT_NCT,trial_name:"KEYNOTE-024",phase:"PHASE3",enrollment:305,
      program:"Pembrolizumab versus chemotherapy",
      condition:"Advanced non-small-cell lung cancer",
      domains:Object.fromEntries(domains.map(name=>[name,{status:name==="clinical_design"?"registry_metadata_available":"pending_review"}])),
    },
    dossier: {
      exact_program_id:"TRIAL|"+PILOT_NCT,nct_id:PILOT_NCT,
      source_sha256:"a".repeat(64),
      source_url:"https://clinicaltrials.gov/study/"+PILOT_NCT,
      domains:Object.fromEntries(domains.map(name=>[name,{
        status:"not_assessed",score:null,claims:[],
      }])),
      overall_score:null,fda_approval_probability:null,read_only:true,
    },
    publishedResults: {
      nct_id:PILOT_NCT,randomized_population:305,
      analysis_snapshots:[
        {
          ...ref("27718847","keynote024_initial_2016","2016-10-08"),
          data_cutoff_date:"2016-05-09",
          effects:{
            progression_free_survival:{
              metric:"median_months",pembrolizumab:10.3,chemotherapy:6,
              hazard_ratio:0.5,hazard_ratio_95pct_ci:[0.37,0.68],
              analysis_role:"prespecified_primary",p_value:"<0.001",
            },
          },
          safety:{
            treatment_related_adverse_events_grade_3_to_5_percent:{
              pembrolizumab:26.6,chemotherapy:53.3,
            },
          },
        },
        {
          ...ref("29129441","keynote024_pros_2017","2017-11-09"),
          outcomes:{quality_of_life_week15_change:{
            pembrolizumab:6.9,chemotherapy:-0.9,nominal_p_value:"0.0020",
            between_group_difference:7.8,difference_95pct_ci:[2.9,12.8],
          }},
        },
        {
          ...ref("33872070","keynote024_five_year_2021","2021-04-19"),
          data_cutoff_date:"2020-06-01",
          effects:{overall_survival:{
            hazard_ratio:0.62,
            five_year_kaplan_meier_survival_percent:{
              pembrolizumab:31.9,chemotherapy:16.3,
            },
          }},
          effective_crossover_percent_from_chemotherapy:66,
        },
      ],
      corroborating_sources:[{
        source_type:"fda_staff_authored_approval_summary",
        source_url:"https://academic.oup.com/oncolo/article/22/11/1392/6444702",
        supported_observation:"Original endpoint evidence",
        scope_note:"Historical approval review only.",
      }],
      domain_scores:Object.fromEntries(domains.map(name=>[name,null])),
      overall_score:null,fda_approval_probability:null,
      scientific_review_status:"source_reported_requires_independent_appraisal",
      unresolved_tasks:["Verify statistical analysis plan"],
      read_only:true,trading_actions_enabled:false,
    },
    assessmentStatus:"source_reported_requires_independent_appraisal",
    scoringModified:false,qualificationPresetsModified:false,researchOnly:true,
  };
}

test("historical eight-domain pilot permits only source-linked unscored evidence",()=>{
  assert.equal(domains.length,8);
  const good=payload();
  assert.equal(validTrialSciencePilot(good),true);
  assert.equal(pilotDomainStatus("pending_review"),"Not assessed");
  assert.equal(safePilotSource("https://pubmed.ncbi.nlm.nih.gov/27718847/"),true);
  assert.equal(safePilotSource("https://pubmed.ncbi.nlm.nih.gov.attacker.invalid/27718847/"),false);
  assert.equal(safePilotSource("javascript:alert(1)"),false);
  assert.equal(safePilotSource("https://academic.oup.com@attacker.invalid/"),false);
});

test("mismatched, scored, tampered, or unsafe pilot response fails closed",()=>{
  const cases = [
    x=>x.pilot.nct_id="NCT12345678",
    x=>x.dossier.exact_program_id="TRIAL|NCT00000000",
    x=>x.dossier.source_sha256="invalid",
    x=>x.dossier.domains.clinical_results.score=89,
    x=>x.dossier.overall_score=89,
    x=>x.publishedResults.fda_approval_probability=.9,
    x=>x.publishedResults.trading_actions_enabled=true,
    x=>x.publishedResults.domain_scores.advanced_inference=80,
    x=>x.qualificationPresetsModified=true,
    x=>x.publishedResults.analysis_snapshots[0].nct_id="NCT12345678",
    x=>x.publishedResults.analysis_snapshots[0].source_url="https://attacker.invalid",
    x=>x.publishedResults.analysis_snapshots[0].data_cutoff_date="bad",
    x=>x.publishedResults.corroborating_sources[0].source_url="https://pubmed.ncbi.nlm.nih.gov.attacker.invalid/fake",
    x=>x.publishedResults.analysis_snapshots.pop(),
  ];
  for(const mutate of cases){
    const bad=structuredClone(payload());
    mutate(bad);
    assert.equal(validTrialSciencePilot(bad),false,JSON.stringify(bad).slice(0,110));
  }
});

test("pilot is discoverable without changing GOAL/SCANS navigation or triggering bulk operations",()=>{
  const page=fs.readFileSync(path.join(__dirname,"../app/page.tsx"),"utf8");
  assert.match(page,/import TrialSciencePilot from "\.\/TrialSciencePilot"/);
  assert.match(page,/<TrialSciencePilot \/>/);
  assert.match(page,/href="#trial-science-pilot"/);
  const component=fs.readFileSync(path.join(__dirname,"../app/TrialSciencePilot.tsx"),"utf8");
  assert.match(component,/fetch\(PILOT_PATH/);
  assert.doesNotMatch(component,/method:\s*"(?:PUT|POST|DELETE)"|runScan\(|placeOrder\(/);
  const route=fs.readFileSync(path.join(__dirname,
    "../app/api/scientific-assessment/pilot/keynote024/route.ts"),"utf8");
  assert.match(route,/authConfigured\(\)/);
  assert.match(route,/hasSession\(/);
  assert.match(route,/validTrialSciencePilot\(data\)/);
  assert.match(route,/Cache-Control.*private, no-store/);
  assert.doesNotMatch(route,/req\.nextUrl\.searchParams|req\.json\(|method:\s*"(?:POST|PUT|DELETE)"/);
});

test("historical panel loads only on explicit click, preserving cited outcomes and uncertainties",async()=>{
  const oldFetch=global.fetch, calls=[];
  let view;
  try {
    global.fetch=async(url,opts)=>{
      calls.push({url,opts});
      return {ok:true,status:200,json:async()=>payload()};
    };
    await act(async()=>{view=create(React.createElement(TrialSciencePilot));});
    assert.equal(calls.length,0);
    await act(async()=>{view.root.findByType("button").props.onClick();});
    assert.equal(calls.length,1);
    assert.equal(calls[0].url,"/api/scientific-assessment/pilot/keynote024");
    assert.equal(calls[0].opts.cache,"no-store");
    const output=JSON.stringify(view.toJSON());
    assert.match(output,/KEYNOTE-024/);
    assert.match(output, /"26\.6"/);
    assert.match(output, /"53\.3"/);
    assert.match(output,/Progression-free survival/);
    assert.match(output,/6.9 vs -0.9 points/);
    assert.match(output,/Difference 7.8 points/);
    assert.match(output,/data cutoff 2020-06-01/);
    assert.match(output,/2021-04-19/);
    assert.match(output,/33872070/);
    assert.match(output,/Independent appraisal pending/);
    assert.match(output,/No independently validated eight-domain score/);
  } finally{
    if(view)await act(async()=>view.unmount());
    global.fetch=oldFetch;
  }
});

test("pilot failure or unsafe API payload is displayed as error without a fallback score",async()=>{
  const oldFetch=global.fetch;
  let view;
  try{
    global.fetch=async()=>({ok:true,status:200,json:async()=>({...payload(),scoringModified:true})});
    await act(async()=>{view=create(React.createElement(TrialSciencePilot));});
    await act(async()=>{view.root.findByType("button").props.onClick();});
    const output=JSON.stringify(view.toJSON());
    assert.match(output,/failed trial identity, provenance or unscored-state validation/);
    assert.doesNotMatch(output,/Source-reported findings/);
  }finally{
    if(view)await act(async()=>view.unmount());
    global.fetch=oldFetch;
  }
});

test("styles use mobile-first readable evidence grids and scrollable tables",()=>{
  const css=fs.readFileSync(path.join(__dirname,"../app/TrialSciencePilot.module.css"),"utf8");
  assert.match(css,/@media \(max-width: 520px\)/);
  assert.match(css,/overflow-x: auto/);
  assert.match(css,/grid-template-columns: minmax\(0, 1fr\)/);
});
