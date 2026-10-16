// Live browser audit for CURRENT PDUFA Command Center navigation.
// Checks actual rendered UI rather than retired labels or hypothetical trades.
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");

const SITE = "https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/";
const DIR = path.join(process.cwd(), "live-audit-artifacts");
fs.mkdirSync(DIR, { recursive: true });

const report = {
  url: SITE,
  checked_at_utc: new Date().toISOString(),
  http_status: null,
  checked: [],
  failures: [],
  source_warnings: [],
  notes: [
    "Live browser verification; successful rendering does not prove clinical, SEC or market accuracy.",
    "No broker orders, private accounts or trade-performance claims are inspected."
  ]
};
const EXPECTED_TABS = ["PIPELINE", "GEM JR", "GEM", "SCANS", "WT"];
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let browser;

async function currentFrame(page) {
  for (const frame of page.frames()) {
    try {
      const text = await frame.locator("body").innerText({timeout: 2500});
      if (text.includes("BIO PDUFA COMMAND CENTER")) return frame;
    } catch (_) {}
  }
  return null;
}

async function waitFor(page, label, matches, timeoutMs=125000) {
  const end = Date.now() + timeoutMs;
  let recent = "";
  while (Date.now() < end) {
    const frame = await currentFrame(page);
    if (!frame) { await delay(1200); continue; }
    try {
      recent = await frame.locator("body").innerText({timeout: 6000});
      if (/This app has encountered an error|Traceback \(most recent call last\)/i.test(recent)) {
        try { await screenshot(page, "exception-" + label.toLowerCase().replace(/[^a-z0-9]+/g, "-")); } catch (_) {}
        throw Error(label + ": Streamlit application exception. Visible text: " + recent.slice(-2800));
      }
      if (recent.includes("Source integration failed.") && label === "PIPELINE") {
        throw Error("PIPELINE clinical source cache failed validation in deployed app.");
      }
      if (await matches(frame, recent)) {
        await delay(800);
        return {frame, text: recent};
      }
    } catch (error) {
      const message = String(error?.message || error);
      if (!/detached|Execution context was destroyed|Target closed/i.test(message)) throw error;
    }
    await delay(850);
  }
  throw Error(label + ": live screen failed to render expected controls. Recent text: " + recent.slice(-450));
}

async function screenshot(page, name) {
  try {
    await page.screenshot({path: path.join(DIR, name + ".png"), fullPage: false});
  } catch (error) {
    report.notes.push("Screenshot unavailable for " + name + ": " + String(error?.message || error).slice(0,140));
  }
}

async function selectedTab(frame, label) {
  const control = frame.getByRole("tab", {name: label, exact: true});
  return await control.getAttribute("aria-selected") === "true";
}

async function inspectTab(page, name, expected, opts={}) {
  const frame = await currentFrame(page);
  if (!frame) throw Error(name + ": app iframe not found.");
  await frame.getByRole("tab", {name, exact: true}).click({timeout: 15000});
  const found = await waitFor(page, name, async(f, text) => {
    if (!await selectedTab(f, name)) return false;
    if (name === "GEM JR" || name === "GEM") {
      const dashboard = page.frames().find(x => x.url().includes("gem_reference_dashboard"));
      if (!dashboard) return false;
      const content = await dashboard.locator("body").innerText({timeout:5000});
      return expected.every(s => content.includes(s));
    }
    return expected.every(s => text.includes(s));
  }, opts.timeoutMs || 125000);
  const warning = [];
  if (found.text.includes("SOURCE SNAPSHOT STALE")) warning.push("GEM source snapshot stale");
  if (found.text.includes("SEC FINANCING RECHECK PARTIAL/STALE")) warning.push("SEC financing recheck partial or stale");
  if (found.text.includes("No source-cleared two-benchmark GEMs")) warning.push("No verified two-benchmark GEM entries");
  if (found.text.includes("BACKTEST NOT READY")) warning.push("Post-Phase-3 backtest incomplete");
  if (found.text.includes("Source integration failed.")) warning.push("Source integration failed");
  report.source_warnings.push(...warning.filter(s => !report.source_warnings.includes(s)));
  report.checked.push({screen:name, result:"PASS", required_labels:expected, warnings:warning});
  await screenshot(page, "pdufa-" + name.toLowerCase().replace(/[^a-z0-9]+/g, "-"));
  return found;
}

async function inspectRadio(page, name, expected) {
  const frame = await currentFrame(page);
  if (!frame) throw Error(name + ": app frame not found.");
  // BaseWeb native radio is visually clipped. Click the visible text label
  // inside the owning stRadio group instead of using force on the input.
  const group = frame.locator('[data-testid="stRadio"]').filter({
    has: frame.getByRole("radio", {name, exact:true})
  });
  await group.getByText(name, {exact:true}).click({timeout:15000});
  const found = await waitFor(page, "Main navigation " + name,
    async(f, text) => await f.getByRole("radio", {name, exact:true}).isChecked()
      && expected.every(s => text.includes(s)), 120000);
  report.checked.push({screen:"Main navigation: " + name, result:"PASS", required_labels:expected});
  await screenshot(page, "nav-" + name.toLowerCase().replace(/[^a-z0-9]+/g, "-"));
  return found;
}

async function safely(label, fn) {
  try {
    await fn();
  } catch (error) {
    report.failures.push({screen:label, error:String(error?.message || error).slice(0,1000)});
  }
}

async function audit() {
  browser = await chromium.launch({
    executablePath:process.env.CHROME_PATH || "/usr/bin/google-chrome",
    headless:true, args:["--no-sandbox","--disable-dev-shm-usage"]
  });
  const page = await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
  const jsErrors = [], failedRequests = [];
  page.on("pageerror", e => jsErrors.push(String(e?.message || e).slice(0,220)));
  page.on("requestfailed", request => {
    if (failedRequests.length < 12) failedRequests.push({
      url:request.url().slice(0,160), error:request.failure()?.errorText
    });
  });
  const response = await page.goto(SITE, {waitUntil:"domcontentloaded",timeout:60000});
  report.http_status = response?.status() ?? null;
  if (report.http_status !== 200) report.failures.push({screen:"Site HTTP",error:"HTTP " + report.http_status});

  await safely("PDUFA / PIPELINE", async() => {
    const found = await waitFor(page, "PDUFA / PIPELINE", async(f,text) =>
      await selectedTab(f, "PIPELINE")
        && text.includes("PDUFA — CLINICAL AND REGULATORY STAGES")
        && text.includes("STAGE COUNTS")
        && text.includes("DATE TRIAL COUNTS")
        && text.includes("PIPELINE — PDUFA COUNTDOWN, WATCHLIST & ANALYSIS"));
    const tabs = (await found.frame.getByRole("tablist").first().getByRole("tab").allInnerTexts()).map(s=>s.trim());
    report.pdufa_tabs = tabs;
    const missing = EXPECTED_TABS.filter(x => !tabs.includes(x));
    if (missing.length) throw Error("Missing current PDUFA tabs: " + missing.join(", "));
    report.checked.push({screen:"PDUFA / PIPELINE", result:"PASS", tabs:tabs});
    await screenshot(page,"pdufa-pipeline");
  });

  // Inspect every current subtab. A failed tab does not stop unrelated tabs.
  const tabs = [
    ["GEM JR", ["GEM JR Candidates", "Trial Structure (3-Level View)", "Entry Checklist (GEM JR)", "Exit Checklist (GEM JR)"]],
    ["GEM", ["GEM Candidates", "GEM Qualification Rules", "Two-Financing Verification", "Hard Stop / PDUFA Exit Policy"]],
    ["SCANS", ["GEMS — GITHUB SCAN LOGS", "GEM — MASTER STOCK LIST", "NIGHTLY SCAN REPORT"]],
    // WT chart/widget content lives in a nested components iframe.
    ["WT", []]
  ];
  for (const [name, labels] of tabs) {
    await safely("PDUFA tab " + name, () => inspectTab(page, name, labels));
  }
  // Production acceptance: the three SEC/FDA baseline counts must be the
  // same Pipeline record IDs after STAGES, DATES and search filtering.
  // Amendments/missing-evidence are claims/filings, not additional trials.
  await safely("Pipeline SEC FDA live count parity", async() => {
    const found = await inspectTab(page, "SCANS", [
      "SEC & FDA SCAN CONTROLS",
      "SEC FINANCING",
      "FDA FILINGS",
      "MISSING EVIDENCE",
      "PIPELINE ↔ SEC / FDA — TRIAL RECONCILIATION",
      "SEC Base details", "SEC Amendment details",
      "FDA Base details", "FDA Amendment details",
      "SEC MISSING EVIDENCE", "FDA MISSING EVIDENCE",
    ]);
    // Image-contract acceptance: four independent stacked agency cards
    // followed by one joint missing-evidence card and a progress legend.
    const cardClasses = [
      "pdufa_sec_base_card", "pdufa_sec_amend_card",
      "pdufa_fda_base_card", "pdufa_fda_amend_card",
      "pdufa_missing_evidence_card", "pdufa_scan_progress",
    ];
    for (const key of cardClasses) {
      if (await found.frame.locator(".st-key-" + key).count() !== 1) {
        throw Error("Expected one stacked SEC/FDA survey card: " + key);
      }
    }
    const sections = ["SEC FINANCING", "FDA FILINGS", "MISSING EVIDENCE"];
    const offsets = sections.map(s => found.text.indexOf(s));
    if (offsets.some(x => x < 0) || offsets[0] >= offsets[1] || offsets[1] >= offsets[2]) {
      throw Error("SEC financing / FDA filings / missing evidence are not in visual order.");
    }
    for (const key of cardClasses.slice(0, 4)) {
      const count = await found.frame.locator(".st-key-" + key)
        .getByRole("button", {name:"▶ Scan this section",exact:true}).count();
      if (count !== 1) throw Error("Expected section scan control inside " + key);
    }
    const metrics = await found.frame.locator('[data-testid="stMetric"]').allInnerTexts();
    const readCount = label => {
      const matches = metrics.filter(value => value.includes(label));
      if (matches.length !== 1) throw Error(label + ": expected one metric, found " + matches.length);
      const numbers = matches[0].match(/\b\d[\d,]*\b/g) || [];
      if (numbers.length !== 1) throw Error(label + ": ambiguous count " + matches[0]);
      return Number(numbers[0].replace(/,/g, ""));
    };
    const pipeline = readCount("Pipeline filtered total");
    const sec = readCount("SEC baseline rows");
    const fda = readCount("FDA baseline rows");
    if (pipeline !== sec || pipeline !== fda) {
      throw Error("Pipeline/SEC/FDA trial count mismatch: " +
                  JSON.stringify({pipeline, sec, fda}));
    }
    const scanButtons = found.frame.getByRole("button", {name:"▶ Scan this section",exact:true});
    if (await scanButtons.count() !== 4) throw Error("Expected four agency-specific manual scan buttons.");
    report.checked.push({
      screen:"Stacked SEC FDA controls and Pipeline count parity", result:"PASS",
      pipeline_trial_records:pipeline, sec_baseline_rows:sec, fda_baseline_rows:fda,
      scan_buttons:4, dropdowns:6
    });
    await screenshot(page, "pipeline-sec-fda-count-parity");
  });

  // The reference dashboard is the only GEM view. Check the actual component,
  // selected program, nested trials and chart controls rather than retired UI.
  await safely("GEM reference dashboard interaction", async() => {
    await inspectTab(page, "GEM", ["GEM Candidates", "GEM Qualification Rules"]);
    const dashboard = page.frames().find(x => x.url().includes("gem_reference_dashboard"));
    if (!dashboard) throw Error("GEM reference component missing");
    const details = dashboard.locator('.candidate-table button[data-action="select"]');
    const count = await details.count();
    if (count) {
      await details.first().click();
      await dashboard.getByRole("tab", {name:"Trial structure · 3 levels", exact:true}).click();
      if (!await dashboard.locator('.tree details[data-tree="company"]').count())
        throw Error("Company > drug > trial hierarchy missing for selected program");
      await dashboard.getByRole("button", {name:"1M",exact:true}).click();
      if (!await dashboard.getByRole("heading", {name:/1M Trading Chart/}).count())
        throw Error("Chart timeframe did not update");
    }
    if (!await dashboard.getByRole("heading", {name:"Entry Checklist (GEM)",exact:true}).count())
      throw Error("Entry checklist missing");
    if (!await dashboard.getByRole("heading", {name:"Exit Checklist (GEM)",exact:true}).count())
      throw Error("Exit checklist missing");
    report.checked.push({screen:"GEM reference dashboard", result:"PASS", candidate_controls:count});
    await screenshot(page,"gem-reference-dashboard");
  });
  // The embedded watchlist is hosted in its own components iframe.
  await safely("WT embedded watchlist", async() => {
    // Previous checks navigate away from WT; deliberately re-open it rather
    // than assuming the tab left selected at the end of the preceding loop.
    const selected = await inspectTab(page, "WT", []);
    let inner = [];
    // Streamlit custom HTML renders in a separate iframe AFTER the tab itself
    // reports selected. Allow time for that iframe to mount and populate.
    for (let attempt=0;attempt<20;attempt++) {
      inner = [];
      for (const frame of page.frames()) {
        if (frame === selected.frame) continue;
        try { inner.push(await frame.locator("body").innerText({timeout:2500})); } catch (_) {}
      }
      if (inner.some(text => text.includes("WATCHLIST") && text.includes("TRADING"))) break;
      await delay(900);
    }
    if (!inner.some(text => text.includes("WATCHLIST") && text.includes("TRADING"))) {
      throw Error("Watchlist/Trading iframe absent or incomplete after 20 checks; frames="+page.frames().length);
    }
    report.checked.push({screen:"WT embedded Watchlist and Trading",result:"PASS"});
  });

  // Exactly one SCANS destination: the PDUFA subtab. The former global
  // SCANS radio is intentionally removed; its read-only activity history
  // is now a toggle in the richer PDUFA evidence/controls screen.
  await safely("Unified PDUFA SCANS", async() => {
    const frame = await currentFrame(page);
    if (!frame) throw Error("Unified SCANS: app iframe missing.");
    if (await frame.getByRole("radio", {name:"SCANS", exact:true}).count() !== 0) {
      throw Error("Obsolete duplicate top-level SCANS navigation is still visible.");
    }
    const found = await inspectTab(page, "SCANS", [
      "SEC & FDA SCAN CONTROLS",
      "SHOW LIVE ACTIVITY & HISTORY",
      "GEMS — GITHUB SCAN LOGS",
      "NIGHTLY SCAN REPORT",
    ]);
    report.checked.push({screen:"One consolidated SCANS navigation",result:"PASS",
                         live_activity_toggle:found.text.includes("SHOW LIVE ACTIVITY & HISTORY")});
  });
  await safely("PDUFA CALENDAR", async() => {
    await inspectRadio(page,"2. PDUFA CALENDAR",["2. PDUFA CALENDAR — UPCOMING CATALYSTS"]);
  });
  await safely("Mobile width", async() => {
    await page.setViewportSize({width:390,height:844});
    const before = await currentFrame(page);
    if (!before) throw Error("PDUFA iframe is missing at iPhone width.");
    const nav = before.getByRole("radio",{name:"PDUFA",exact:true});
    if (!(await nav.isChecked())) {
      const group = before.locator('[data-testid="stRadio"]').filter({has:nav});
      await group.getByText("PDUFA",{exact:true}).click({timeout:15000});
    }
    // Wait for the actual PDUFA rerun. The global title appears before the
    // tabs, so relying on the title alone creates a false mobile failure.
    const found = await waitFor(page,"Mobile PDUFA tabs",async(f,text) =>
      await f.getByRole("radio",{name:"PDUFA",exact:true}).isChecked()
      && text.includes("PDUFA — CLINICAL AND REGULATORY STAGES")
      && await f.getByRole("tab",{name:"SCANS",exact:true}).count()===1,120000);
    const scans = found.frame.getByRole("tab",{name:"SCANS",exact:true});
    await scans.scrollIntoViewIfNeeded({timeout:15000});
    await scans.click({timeout:15000});
    await waitFor(page,"Mobile SCANS content",async(f,text) =>
      await selectedTab(f,"SCANS") &&
      text.includes("NIGHTLY SCAN REPORT") &&
      text.includes("GEM — MASTER STOCK LIST"),120000);
    report.checked.push({screen:"Mobile SCANS opens at 390px",result:"PASS"});
    await screenshot(page,"iphone-390-scans");
  });
  report.browser_js_errors = jsErrors.slice(0,12);
  report.failed_requests = failedRequests;
  if(jsErrors.length) report.notes.push("Browser errors observed; review browser_js_errors.");
  if(failedRequests.length) report.notes.push("Network requests failed; review failed_requests for blocked third-party feeds.");
}

audit().catch(error => {
  report.failures.push({screen:"Audit runner",error:String(error?.stack || error).slice(0,1400)});
}).finally(async() => {
  if (browser) await browser.close();
  report.ok = report.failures.length === 0;
  fs.writeFileSync(path.join(DIR,"live-audit.json"),JSON.stringify(report,null,2));
  process.stdout.write("LIVE STREAMLIT AUDIT\n" + JSON.stringify(report,null,2) + "\n");
  process.exitCode = report.ok ? 0 : 1;
});
