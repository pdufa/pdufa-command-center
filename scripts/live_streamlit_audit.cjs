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
const EXPECTED_TABS = ["GEM", "PIPELINE", "PRE PHASE 3", "POST PHASE 3", "SCANS", "WT"];
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
        throw Error(label + ": Streamlit application exception.");
      }
      if (recent.includes("Source integration failed.") && label === "PRE PHASE 3") {
        throw Error("PRE PHASE 3 source cache failed validation in deployed app.");
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
    ["GEM", ["#1-GEM", "GEM — TWO BENCHMARKS VERIFIED"]],
    ["SCANS", ["GEMS — GITHUB SCAN LOGS", "GEM — MASTER STOCK LIST", "NIGHTLY SCAN REPORT"]],
    ["PRE PHASE 3", ["PRE PHASE 3 — LIVE SOURCE MONITOR", "SOURCE HEALTH / LAST VERIFIED CHECK"]],
    ["POST PHASE 3", ["POST PHASE 3 — TRADING WORKSPACE", "STAGE 3 — HISTORICAL ENTRY / EXIT RESEARCH"]],
    // WT chart/widget content lives in a nested components iframe.
    ["WT", []]
  ];
  for (const [name, labels] of tabs) {
    await safely("PDUFA tab " + name, () => inspectTab(page, name, labels));
  }
  // Exercise the collapsed GEM master UI, not just its title. The chart and
  // trading assessment require a stock card to open before their code runs.
  await safely("GEM nested stock entry/exit chart", async() => {
    await inspectTab(page, "GEM", ["#1-GEM", "GEM — TWO BENCHMARKS VERIFIED"]);
    const first = await currentFrame(page);
    const label = "#1 GEM — THREE-LEVEL NESTED MASTER LIST (show / hide)";
    await first.getByText(label, {exact:true}).click({timeout:15000});
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
    const chart = await waitFor(page, "GEM entry/exit stock chart", async(f,text) =>
      await selectedTab(f, "GEM") && text.includes("ENTRY / EXIT MONITOR —") &&
      text.includes("Trading metric"), 90000);
    report.checked.push({screen:"GEM nested stock entry/exit chart",result:"PASS",
                         source_warnings_visible:chart.text.includes("SOURCE RECHECK PARTIAL / STALE")});
    await screenshot(page,"gem-entry-exit-stock");
  });
  // The embedded watchlist is hosted in its own components iframe.
  await safely("WT embedded watchlist", async() => {
    const selected = await waitFor(page, "WT", (frame) => selectedTab(frame, "WT"));
    const inner = [];
    for (const frame of page.frames()) {
      if (frame === selected.frame) continue;
      try { inner.push(await frame.locator("body").innerText({timeout:2500})); } catch (_) {}
    }
    if (!inner.some(text => text.includes("WATCHLIST") && text.includes("TRADING"))) {
      throw Error("Watchlist/Trading iframe absent or incomplete.");
    }
    report.checked.push({screen:"WT embedded Watchlist and Trading",result:"PASS"});
  });

  await safely("Main SCANS", async() => {
    await inspectRadio(page,"SCANS",["SCANS — LIVE ACTIVITY & HISTORY"]);
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
