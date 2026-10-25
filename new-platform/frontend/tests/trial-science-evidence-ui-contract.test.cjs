const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const React = require("react");
const { act, create } = require("react-test-renderer");

global.IS_REACT_ACT_ENVIRONMENT = true;
for (const ext of [".ts", ".tsx"]) {
  require.extensions[ext] = (mod, file) => mod._compile(
    ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true,
      },
    }).outputText,
    file,
  );
}
require.extensions[".css"] = mod => {
  mod.exports = new Proxy({}, { get: (_, key) => String(key) });
};

const {
  PILOT_NCT, SCIENCE_DOMAIN_LABELS, validTrialSciencePilot, safePilotSource,
} = require("../lib/trial-science-pilot.ts");
const { default: TrialSciencePilot } = require("../app/TrialSciencePilot.tsx");

const domains = Object.keys(SCIENCE_DOMAIN_LABELS);

function fixture() {
  const source = (analysis_id, pmid, effects = {}, outcomes = {}) => ({
    analysis_id,
    nct_id: PILOT_NCT,
    source_id: pmid,
    source_url: "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/",
    publication_date: "2021-04-19",
    report_type: analysis_id,
    source_evidence_status: "published_reported_not_independently_reanalyzed",
    effects, outcomes, methodological_caveats: ["Interpretation requires source appraisal"],
  });
  return {
    pilot: {
      nct_id: PILOT_NCT, trial_name: "KEYNOTE-024", phase: "PHASE3",
      enrollment: 305, program: "Pembrolizumab versus chemotherapy",
      condition: "PD-L1-high metastatic NSCLC",
      domains: Object.fromEntries(domains.map(domain => [domain, { status: "pending_review" }])),
    },
    dossier: {
      nct_id: PILOT_NCT,
      exact_program_id: "TRIAL|" + PILOT_NCT,
      source_sha256: "a".repeat(64),
      source_url: "https://clinicaltrials.gov/study/" + PILOT_NCT,
      domains: Object.fromEntries(domains.map(domain => [domain, {
        status: "not_assessed", score: null, claims: [],
      }])),
      overall_score: null, fda_approval_probability: null, read_only: true,
    },
    publishedResults: {
      nct_id: PILOT_NCT, randomized_population: 305,
      analysis_snapshots: [
        source("keynote024_initial_2016", "27718847", {
          progression_free_survival: {
            metric: "median_months", pembrolizumab: 10.3,
            chemotherapy: 6, hazard_ratio: 0.5,
            hazard_ratio_95pct_ci: [0.37, 0.68],
            p_value: "<0.001", analysis_role: "prespecified_primary",
          },
        }),
        source("keynote024_pros_2017", "29129441", {}, {
          quality_of_life_week15_change: {
            between_group_difference: 7.8,
            difference_95pct_ci: [2.9, 12.8],
            nominal_p_value: "0.0020", analysis_role: "prespecified_exploratory",
          },
        }),
        source("keynote024_five_year_2021", "33872070", {
          overall_survival: {
            metric: "median_months", pembrolizumab: 26.3, chemotherapy: 13.4,
            hazard_ratio: 0.62, hazard_ratio_95pct_ci: [0.48, 0.81],
            five_year_kaplan_meier_survival_percent: {
              pembrolizumab: 31.9, chemotherapy: 16.3,
            },
          },
        }),
      ],
      corroborating_sources: [
        { source_type: "national_cancer_institute_scientific_summary",
          source_url: "https://www.cancer.gov/types/lung/research/pembrolizumab-nsclc-keynote-024",
          supported_observation: "Study results from NCI",
          scope_note: "Independent reanalysis not performed",
        },
      ],
      domain_scores: Object.fromEntries(domains.map(d => [d, null])),
      overall_score: null, fda_approval_probability: null, read_only: true,
      trading_actions_enabled: false,
      scientific_review_status: "source_reported_requires_independent_appraisal",
      unresolved_tasks: ["Confirm prespecified statistical-analysis plan and interim rules"],
    },
    assessmentStatus: "source_reported_requires_independent_appraisal",
    scoringModified: false,
    qualificationPresetsModified: false,
    researchOnly: true,
  };
}

test("exact historical pilot fixture retains all eight domains, without scores", () => {
  const pilot = fixture();
  assert.equal(validTrialSciencePilot(pilot), true);
  assert.equal(domains.length, 8);
  assert.equal(pilot.publishedResults.analysis_snapshots.length, 3);
  assert.equal(pilot.publishedResults.overall_score, null);
});

test("rejects cross-trial or scored payload, unsafe sources and duplicate analyses", () => {
  const changes = [
    x => { x.pilot.nct_id = "NCT87654321"; },
    x => { x.dossier.exact_program_id = "TRIAL|NCT87654321"; },
    x => { x.dossier.domains.clinical_results.score = 90; },
    x => { x.publishedResults.domain_scores.clinical_results = 90; },
    x => { x.publishedResults.fda_approval_probability = 0.94; },
    x => { x.scoringModified = true; },
    x => { x.qualificationPresetsModified = true; },
    x => { x.publishedResults.analysis_snapshots[1].analysis_id = "keynote024_initial_2016"; },
    x => { x.publishedResults.analysis_snapshots[0].source_url = "https://evil.example/fake"; },
    x => { x.publishedResults.analysis_snapshots[0].source_id = "99999999"; x.publishedResults.analysis_snapshots[0].source_url = "https://pubmed.ncbi.nlm.nih.gov/99999999/"; },
    x => { x.publishedResults.corroborating_sources[0].source_url = "javascript:alert(1)"; },
    x => { delete x.dossier.domains.advanced_inference; },
  ];
  for (const alter of changes) {
    const changed = fixture();
    alter(changed);
    assert.equal(validTrialSciencePilot(changed), false, String(alter));
  }
  assert.equal(safePilotSource("https://pubmed.ncbi.nlm.nih.gov/27718847/"), true);
  assert.equal(safePilotSource("https://pubmed.ncbi.nlm.nih.gov.evil.example/27718847/"), false);
  assert.equal(safePilotSource("https://evil.example/"), false);
});

test("pilot panel remains unloaded until user clicks, then shows separate source dates", async () => {
  const previous = global.fetch;
  let calls = 0;
  let requested = "";
  let renderer;
  try {
    global.fetch = async (url, options) => {
      calls += 1; requested = String(url);
      assert.equal(options.cache, "no-store");
      return { ok: true, json: async () => fixture() };
    };
    await act(async () => { renderer = create(React.createElement(TrialSciencePilot)); });
    assert.equal(calls, 0);
    assert.match(JSON.stringify(renderer.toJSON()), /KEYNOTE-024/);
    const button = renderer.root.findAllByType("button")[0];
    await act(async () => { await button.props.onClick(); });
    assert.equal(calls, 1);
    assert.equal(requested, "/api/scientific-assessment/pilot/keynote024");
    const rendered = JSON.stringify(renderer.toJSON());
    assert.match(rendered, /Eight scientific research domains/);
    assert.match(rendered, /2016|keynote024_initial_2016/);
    assert.match(rendered, /2021|keynote024_five_year_2021/);
    assert.match(rendered, /prespecified primary/);
    assert.match(rendered, /0.50/);
    assert.match(rendered, /0.62/);
    assert.match(rendered, /score not assigned/);
    assert.match(rendered, /trading/);
    const links = renderer.root.findAllByType("a");
    assert.ok(links.some(link => String(link.props.href).endsWith("/27718847/")));
    assert.ok(links.some(link => String(link.props.href).endsWith("/33872070/")));
  } finally {
    if (renderer) await act(async () => renderer.unmount());
    global.fetch = previous;
  }
});

test("bad pilot response fails closed instead of displaying partial scientific results", async () => {
  const previous = global.fetch;
  let renderer;
  try {
    const altered = fixture();
    altered.dossier.overall_score = 97;
    global.fetch = async () => ({ ok: true, json: async () => altered });
    await act(async () => { renderer = create(React.createElement(TrialSciencePilot)); });
    await act(async () => { await renderer.root.findAllByType("button")[0].props.onClick(); });
    const output = JSON.stringify(renderer.toJSON());
    assert.match(output, /failed trial identity, provenance or unscored-state validation/);
    assert.doesNotMatch(output, /Eight scientific research domains/);
  } finally {
    if (renderer) await act(async () => renderer.unmount());
    global.fetch = previous;
  }
});

test("trial sheet embeds pilot only on the exact NCT, not across all candidate trials", () => {
  const file = fs.readFileSync(
    path.join(__dirname, "../app/trial/[nctId]/page.tsx"), "utf8",
  );
  assert.match(file, /TrialSciencePilot/);
  assert.match(file, /import \{ PILOT_NCT \} from/);
  assert.equal(PILOT_NCT, "NCT02142738");
  assert.match(file, /nct\s*===\s*(?:"NCT02142738"|PILOT_NCT)/);
});
