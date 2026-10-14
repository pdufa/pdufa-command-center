// Targeted browser validation for #1 GEM: Potential GEMs numbered list.
// Research lead visibility is not a declaration of trade entry eligibility.
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");
const url = "https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/";
const output = path.join(process.cwd(), "gem-potential-live-artifacts");
fs.mkdirSync(output, { recursive: true });
const result = {
  timestamp: new Date().toISOString(), url, checks: {},
  errors: [], evidence: {},
};
let browser;
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
async function framesWithText(page) {
  const out = [];
  for (const frame of page.frames()) {
    try {
      const value = await frame.locator("body").innerText({ timeout: 4000 });
      out.push({ frame, text: value });
    } catch (_) {}
  }
  return out;
}
async function frameWithApp(page) {
  const rows = await framesWithText(page);
  return rows.find(x => x.text.includes("BIO PDUFA COMMAND CENTER")) || null;
}
function errorFrom(text) {
  return /This app has encountered an error|Traceback \(most recent call last\)/i.test(text);
}
async function audit() {
  browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
    headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on("pageerror", e => errors.push(String(e.message || e).slice(0, 350)));
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  result.http = response?.status() ?? null;
  let app = null;
  for (let i = 0; i < 85; i++) {
    app = await frameWithApp(page);
    if (app) break;
    await sleep(1200);
  }
  if (!app) throw new Error("Deployed Streamlit app header did not render");
  result.checks.appLoaded = true;
  let found = false;
  for (let i = 0; i < 85; i++) {
    app = (await frameWithApp(page)) || app;
    if (errorFrom(app.text)) throw new Error("Live Streamlit page reports an application exception");
    try {
      if (await app.frame.getByRole("tab", { name: "GEM", exact: true }).count()) {
        await app.frame.getByRole("tab", { name: "GEM", exact: true })
          .click({ timeout: 12000 });
        found = true;
        break;
      }
    } catch (e) {
      if (!/detached|Execution context was destroyed/i.test(String(e))) {
        result.errors.push("Navigation retry: " + String(e).slice(0, 160));
      }
    }
    await sleep(1200);
  }
  if (!found) throw new Error("GEM tab not available for GEM list check");
  let panelText = "", overview = "";
  for (let i = 0; i < 120; i++) {
    app = (await frameWithApp(page)) || app;
    overview = app.text;
    if (errorFrom(overview)) throw new Error("GEM tab reports an application exception");
    try {
      if (await app.frame.getByRole("tab", { name: "GEM", exact: true })
        .getAttribute("aria-selected") !== "true") {
        await sleep(900);
        continue;
      }
      const panel = app.frame.locator(".st-key-overview_gem_panel").first();
      if (await panel.count()) {
        panelText = await panel.innerText({ timeout: 5000 });
        if (panelText.includes("POTENTIAL GEMs — PENDING RESEARCH") &&
            ((panelText.includes("Why potential:") && panelText.includes("Pending:")) ||
             panelText.includes("No currently active potential GEMs supported by the saved source reviews."))) break;
      }
    } catch (_) {}
    await sleep(1000);
  }
  result.evidence.panelText = panelText.slice(0, 11000);
  result.evidence.overviewExcerpt = overview.slice(0, 1200);
  const counts = panelText.match(/(\d+) active research leads/);
  const activeCount = counts ? Number(counts[1]) : null;
  const hasList = await app.frame.locator(".st-key-overview_gem_panel ol > li").count() >= 1;
  const explicitlyEmpty = panelText.includes(
    "No currently active potential GEMs supported by the saved source reviews.");
  result.evidence.activeResearchLeads = activeCount;
  result.checks.gemPanelPresent = panelText.includes("#1-GEM");
  result.checks.potentialHeading = panelText.includes("POTENTIAL GEMs — PENDING RESEARCH");
  result.checks.countFromSavedSource = activeCount !== null;
  result.checks.potentialReason = activeCount === 0 ? explicitlyEmpty : panelText.includes("Why potential:");
  result.checks.pendingEvidence = activeCount === 0 ? explicitlyEmpty : panelText.includes("Pending:");
  result.checks.numberedCandidates = activeCount === 0 ? explicitlyEmpty : hasList;
  result.checks.separateVerifiedList = panelText.includes("NOT the verified GEM entry list");
  await page.screenshot({
    path: path.join(output, "gem-potential-desktop.png"), fullPage: false,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await sleep(1400);
  await page.screenshot({
    path: path.join(output, "gem-potential-mobile.png"), fullPage: false,
  });
  result.evidence.pageErrors = errors;
  const failed = Object.entries(result.checks).filter(([, value]) => value !== true);
  if (failed.length) throw new Error(
    "Deployed #1 GEM Potential list validation failed: " + failed.map(([key])=>key).join(", "));
}
(async () => {
  try { await audit(); }
  catch (error) {
    result.errors.push(String(error.stack || error));
    process.exitCode = 1;
  } finally {
    try { if (browser) await browser.close(); } catch (_) {}
    fs.writeFileSync(path.join(output, "gem-potential-browser-result.json"),
      JSON.stringify(result, null, 2));
    console.log(JSON.stringify({
      checks: result.checks, http: result.http,
      errors: result.errors.map(x => x.slice(0, 900)),
    }, null, 2));
  }
})();
