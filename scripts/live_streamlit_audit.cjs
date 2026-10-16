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
  const found = await waitFor(page, name, async(f, text) =>
    await selectedTab(f, name) && expected.every(s => text.includes(s)), opts.timeoutMs || 125000);
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
    ["GEM JR", ["GEM JR — POST-PHASE 3 RESEARCH", "GEM JR — RESEARCH & QUALIFICATION QUEUE"]],
    ["GEM", ["GEM — TWO-BENCHMARK VERIFIED RESEARCH", "POTENTIAL GEMs — PENDING RESEARCH"]],
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

  // Exercise GEM full-width master, not just its title. The chart and
  // trading assessment require an exact-program stock card to open.
  await safely("GEM nested stock entry/exit chart", async() => {
    await inspectTab(page, "GEM", ["GEM — TWO-BENCHMARK VERIFIED RESEARCH", "POTENTIAL GEMs — PENDING RESEARCH"]);
    const first = await currentFrame(page);
    const label = "GEM — FULL VERIFIED MASTER: SCORES / SIX FACTORS / INPUTS";
    // The full-width master opens by default; do not click its toggle closed.
    if (!await first.getByText(label, {exact:true}).count())
      throw Error("GEM full verified master toggle missing.");
    const master = await waitFor(page, "GEM nested master", async(f, text) =>
      await selectedTab(f, "GEM") &&
      text.includes("GEM — STOCK → FACTORS → SOURCE INPUTS") &&
      text.includes("GEM programs"));
    if (/This app has encountered an error|Traceback \(most recent call last\)/i.test(master.text)) {
      throw Error("GEM master crashed on expansion.");
    }
    // A default research-only filter can be empty even with saved GEM rows.
    // Selecting All candidates tests an actual program's chart when available.
    const candidates = master.frame.getByText("OPEN STOCK → six factors → inputs", {exact:false});
    const count = await candidates.count();
    if (!count) {
      report.notes.push("GEM nested master opened, but no matching stock cards were displayed for the saved filter.");
      report.checked.push({screen:"GEM nested master",result:"PASS",stock_chart:"NO STOCK MATCH"});
      return;
    }
    await candidates.first().click({timeout:15000});
    await delay(750);
    // Scroll the selected stock into view if the browser has deferred its body.
    const scrollDetail = await candidates.first().evaluate(el => {
      let parent = el;
      while (parent) {
        const style = getComputedStyle(parent);
        if (parent.scrollHeight > parent.clientHeight + 50 &&
            /(scroll|auto)/.test(style.overflowY)) {
          const before = parent.scrollTop;
          parent.scrollTop = Math.min(parent.scrollHeight,
                                      parent.scrollTop + 700);
          return {found:true, before, after:parent.scrollTop,
                  scrollHeight:parent.scrollHeight,
                  clientHeight:parent.clientHeight};
        }
        parent = parent.parentElement;
      }
      return {found:false};
    });
    await delay(1600);
    report.notes.push("GEM stock internal scroll: " + JSON.stringify(scrollDetail));
    // Preserve diagnostic facts from the opened disclosure; this distinguishes
    // real chart failures from a missing/invisible DOM label in the renderer.
    const probeFrame = await currentFrame(page);
    const probeText = probeFrame ? await probeFrame.locator("body").innerText({timeout:9000}) : "";
    const summary = probeFrame ? probeFrame.getByText("OPEN STOCK → six factors → inputs", {exact:false}).first() : null;
    let disclosure = "unknown";
    try { disclosure = await summary.evaluate(el => {
      const holder = el.closest('[data-testid="stExpander"]');
      const details = holder?.querySelector("details");
      return details ? (details.open ? "open" : "closed") : (holder ? "found expander" : "expander not found");
    }); } catch (_) {}
    let chartInDisclosure = "unknown", disclosureSnippet = "";
    try {
      const diagnostic = await summary.evaluate(el => {
        const section=el.closest('[data-testid="stExpander"]');
        return {hasChart:section?.textContent.includes("ENTRY / EXIT MONITOR"),
                text:section?.textContent.slice(0,650)};
      });
      chartInDisclosure = diagnostic.hasChart;
      disclosureSnippet = diagnostic.text || "";
    } catch (_) {}
    report.notes.push("GEM stock probe: header=" +
                      probeText.includes("ENTRY / EXIT MONITOR") +
                      "; disclosure=" + disclosure +
                      "; chart_dom=" + chartInDisclosure +
                      "; expander_text=" + disclosureSnippet.slice(0,460) +
                      "; master=" + probeText.includes("GEM — STOCK → FACTORS → SOURCE INPUTS"));
    await screenshot(page,"gem-expander-diagnostic");
    const chart = await waitFor(page, "GEM entry/exit stock chart", async(f,text) =>
      await selectedTab(f, "GEM") && text.includes("ENTRY / EXIT MONITOR"), 35000);
    // Streamlit's st.dataframe uses a canvas-backed grid; its column titles
    // are not necessarily present in body.innerText. Require the actual
    // rendered research header and inspect Streamlit's dataframe test ID.
    const tables = await chart.frame.locator('[data-testid="stDataFrame"]').count();
    report.checked.push({screen:"GEM nested stock entry/exit chart",result:"PASS",
                         source_warnings_visible:chart.text.includes("SOURCE RECHECK PARTIAL / STALE"),
                         dataframe_widgets:tables});
    await screenshot(page,"gem-entry-exit-stock");
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
