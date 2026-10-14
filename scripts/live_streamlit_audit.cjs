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
    const found = await inspectRadio(page,"PDUFA",["BIO PDUFA COMMAND CENTER"]);
    const tabLabels = await found.frame.getByRole("tablist").first().getByRole("tab").allInnerTexts();
    if (!tabLabels.some(x=>x.trim()==="SCANS")) throw Error("SCANS tab missing at mobile viewport.");
    report.checked.push({screen:"Mobile tabs at 390px",result:"PASS"});
    await screenshot(page,"iphone-390");
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
