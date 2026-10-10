// Headless audit of the ACTUAL public Streamlit deployment, not local AppTest.
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");
const URL = "https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/";
const outDir = path.join(process.cwd(), "live-audit-artifacts");
fs.mkdirSync(outDir, { recursive: true });
const result = { url: URL, date: new Date().toISOString(), checks: {}, errors: [], notes: [], navigation: [], tabs: [] };
let browser;
async function audit() {
  const chrome = process.env.CHROME_PATH || "/usr/bin/google-chrome";
  browser = await chromium.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const page = await browser.newPage({viewport:{width: 1440, height: 900}, deviceScaleFactor:1});
  const browserErrors = [];
  page.on("pageerror", err => browserErrors.push(String(err.message || err).slice(0,350)));
  const response = await page.goto(URL, {waitUntil:"domcontentloaded",timeout:60000});
  result.http = response ? response.status() : null;
  result.finalUrl = page.url();
  // Streamlit may be waking from hibernation. Check rendered UI, not HTML shell.
  try {
    await page.waitForFunction(() => {
      const t = document.body ? document.body.innerText : "";
      return t.includes("BIO PDUFA COMMAND CENTER") || t.includes("Sign in") ||
        t.includes("This app has encountered an error") || t.includes("Your app is in the oven");
    }, { timeout: 160000 });
  } catch (_) { result.notes.push("Expected app header did not render before browser timeout."); }
  await page.waitForTimeout(2000);
  const initial = await page.locator("body").innerText();
  result.visibleStart = initial.slice(0,1200);
  result.checks.pdufaHeader = initial.includes("BIO PDUFA COMMAND CENTER");
  result.checks.newBuildLabel = initial.includes("NAVIGATION V12");
  result.checks.scriptError = !/This app has encountered an error|TypeError:|Traceback \(most recent call last\)/i.test(initial);
  result.checks.loginRequired = /Sign in to Streamlit|Log in to Streamlit|Continue with Google/i.test(initial);
  result.navigation = (await page.locator('[data-testid="stRadio"] label').allInnerTexts()).map(s => s.trim()).filter(Boolean);
  const distinct = [...new Set(result.navigation)];
  result.navigation = distinct;
  result.checks.noTodayNavigation = !distinct.some(s => s === "TODAY");
  result.checks.pipelineNavigation = distinct.includes("PIPELINE");
  result.tabs = (await page.getByRole("tab").allInnerTexts()).map(s=>s.trim());
  result.checks.threePipelineTabs = ["TRIALS & DATES","PDUFA WORKBENCH","PHASE 3 DAILY"].every(t=>result.tabs.some(s=>s.includes(t)));
  await page.screenshot({ path: path.join(outDir,"streamlit-home.png"), fullPage:false });
  if(result.checks.pdufaHeader && result.checks.threePipelineTabs){
    const stage = await page.getByText("STAGES", {exact:true}).count();
    const dates = await page.getByText("DATES", {exact:true}).count();
    result.checks.stageAndDateControls = stage>0 && dates>0;
    await page.getByRole("tab",{name:"PHASE 3 DAILY"}).click({timeout:15000});
    const toggle=page.getByText("SHOW PHASE 3 DAILY REPORT", {exact:false}).first();
    result.checks.dailyReportToggle=await toggle.count()>0;
    if(result.checks.dailyReportToggle){
      await toggle.click({timeout:10000});
      try{await page.getByText("Yesterday: source-linked posts").first().waitFor({timeout:65000});result.checks.dailyReportLoads=true;}
      catch(err){result.checks.dailyReportLoads=false;result.notes.push("Expanded report did not show counts: "+String(err.message).slice(0,180));}
      await page.screenshot({path:path.join(outDir,"streamlit-phase3-daily.png"),fullPage:false});
    }
  }
  result.browserPageErrors=browserErrors;
  if(result.http !== 200) result.errors.push("App HTTP response not 200.");
  if(!result.checks.pdufaHeader) result.errors.push("PDUFA app did not render in public browser.");
  if(result.checks.pdufaHeader && !result.checks.newBuildLabel) result.errors.push("DEPLOYMENT STALE OR WRONG ENTRYPOINT: NAVIGATION V12 marker missing.");
  if(result.checks.pdufaHeader && !result.checks.noTodayNavigation) result.errors.push("Standalone TODAY still appears as navigation.");
  if(result.checks.pdufaHeader && !result.checks.threePipelineTabs) result.errors.push("Three expected Pipeline tabs are missing.");
  if(result.checks.pdufaHeader && !result.checks.scriptError) result.errors.push("Visible application exception.");
  if(result.checks.dailyReportLoads === false) result.errors.push("Expanded Phase 3 Daily report failed to load.");
}
audit().catch(err=>result.errors.push(String(err.stack||err).slice(0,1000))).finally(async()=>{
  if(browser) await browser.close();
  fs.writeFileSync(path.join(outDir,"live-audit.json"),JSON.stringify(result,null,2));
  process.stdout.write("LIVE STREAMLIT AUDIT\n"+JSON.stringify(result,null,2)+"\n");
  process.exitCode = result.errors.length ? 1 : 0;
});
