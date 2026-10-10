// Browser-level check of the deployed Streamlit site. Community Cloud may
// embed the live app in an iframe; all checks must inspect the frame DOM.
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");
const URL = "https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/";
const outDir = path.join(process.cwd(), "live-audit-artifacts");
fs.mkdirSync(outDir, { recursive: true });
const result = {url:URL,date:new Date().toISOString(),checks:{},errors:[],notes:[],navigation:[],tabs:[],frames:[]};
let browser;
const sleep = ms => new Promise(resolve=>setTimeout(resolve,ms));
async function inspectFrames(page) {
  const frames = [];
  for(const frame of page.frames()){
    let text = "";
    try { text = await frame.locator("body").innerText({timeout:3500}); } catch (_) {}
    frames.push({frame, url:frame.url(), text});
  }
  return frames;
}
async function audit(){
  browser = await chromium.launch({executablePath:process.env.CHROME_PATH||"/usr/bin/google-chrome",
    headless:true,args:["--no-sandbox","--disable-dev-shm-usage"]});
  const page = await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
  const browserErrors=[], failedRequests=[];
  page.on("pageerror",err=>browserErrors.push(String(err.message||err).slice(0,300)));
  page.on("requestfailed",req=>{if(failedRequests.length<25)failedRequests.push({url:req.url().slice(0,160),error:req.failure()?.errorText});});
  const response=await page.goto(URL,{waitUntil:"domcontentloaded",timeout:60000});
  result.http=response?.status()??null;
  result.finalUrl=page.url();
  let appFrame=null, initial="";
  for(let attempt=0;attempt<80;attempt++){
    const observations=await inspectFrames(page);
    result.frames=observations.map(x=>({url:x.url,textLength:x.text.length,textStart:x.text.slice(0,130)}));
    const matched=observations.find(x=>x.text.includes("BIO PDUFA COMMAND CENTER"));
    if(matched){appFrame=matched.frame;initial=matched.text;break;}
    if(observations.some(x=>/Sign in|This app has encountered an error/i.test(x.text))){
      result.notes.push("App shows sign-in or a visible exception.");
      initial=observations.map(x=>x.text).join("\n");
      break;
    }
    await sleep(2000);
  }
  // A Streamlit iframe paints the header before completing its Python rerun.
  // Wait for the actual filter labels, charts and navigation before auditing.
  if(appFrame){
    for(let readyAttempt=0;readyAttempt<80;readyAttempt++){
      try{
        const updated=await appFrame.locator("body").innerText({timeout:5000});
        initial=updated;
        if(updated.includes("PIPELINE — CLINICAL AND REGULATORY STAGES")
          && updated.includes("STAGE COUNTS") && updated.includes("DATE TRIAL COUNTS")
          && updated.includes("PDUFA WORKBENCH"))break;
      }catch(_){}
      await sleep(2000);
    }
  }
  result.visibleStart=initial.slice(0,1100);
  result.checks.pdufaHeader=initial.includes("BIO PDUFA COMMAND CENTER");
  result.checks.newBuildLabel=initial.includes("NAVIGATION V12");
  result.checks.loginRequired=/Sign in to Streamlit|Continue with Google/i.test(initial);
  result.checks.scriptError=!/This app has encountered an error|Traceback \(most recent call last\)/i.test(initial);
  await page.screenshot({path:path.join(outDir,"streamlit-home.png"),fullPage:false});
  if(appFrame){
    result.appFrameUrl=appFrame.url();
    const nav=(await appFrame.locator('[data-testid="stRadio"] label').allInnerTexts()).map(x=>x.trim()).filter(Boolean);
    result.navigation=[...new Set(nav)];
    if(!result.navigation.length){
      // Fallback: Streamlit's BaseWeb radio labels may not carry stRadio.
      const radioItems=await appFrame.locator('input[type="radio"]').count();
      const labels=await appFrame.locator('input[type="radio"]').evaluateAll(nodes=>
        nodes.map(x=>x.parentElement?.innerText||x.getAttribute("aria-label")||"").map(x=>x.trim()).filter(Boolean));
      if(labels.length)result.navigation=[...new Set(labels)];
      result.radioInputCount=radioItems;
    }
    result.checks.noTodayNavigation=!result.navigation.includes("TODAY");
    result.checks.pipelineNavigation=result.navigation.includes("PIPELINE");
    result.tabs=(await appFrame.getByRole("tab").allInnerTexts()).map(x=>x.trim());
    result.checks.threePipelineTabs=["TRIALS & DATES","PDUFA WORKBENCH","PHASE 3 DAILY"].every(x=>result.tabs.some(t=>t.includes(x)));
    result.checks.stageAndDateControls=await appFrame.getByText("STAGES",{exact:true}).count()>0 &&
      await appFrame.getByText("DATES",{exact:true}).count()>0;
    result.checks.stageCountChart=await appFrame.getByText("STAGE COUNTS",{exact:true}).count()>0;
    result.checks.dateCountChart=await appFrame.getByText("DATE TRIAL COUNTS",{exact:true}).count()>0;
    result.checks.noInitialTrials=/Trials \/ programs displayed\s*0/.test(initial);
    if(result.checks.threePipelineTabs){
      await appFrame.getByRole("tab",{name:"PHASE 3 DAILY"}).click({timeout:15000});
      const toggle=appFrame.getByText("SHOW PHASE 3 DAILY REPORT",{exact:false}).first();
      try{
        await toggle.waitFor({state:"visible",timeout:65000});
        result.checks.dailyReportToggle=true;
      }catch(err){
        result.checks.dailyReportToggle=false;
        const dailyText=await appFrame.locator("body").innerText({timeout:9000});
        result.notes.push("PHASE 3 DAILY toggle missing after wait: "+dailyText.slice(-650));
      }
      await page.screenshot({path:path.join(outDir,"streamlit-phase3-before-toggle.png"),fullPage:false});
      if(result.checks.dailyReportToggle){
        await toggle.click({timeout:15000});
        try{
          await appFrame.getByText("Yesterday: source-linked posts").first().waitFor({timeout:110000});
          result.checks.dailyReportLoads=true;
        }catch(err){
          result.checks.dailyReportLoads=false;
          result.notes.push("Daily report did not show result metrics: "+String(err.message).slice(0,170));
        }
        await page.screenshot({path:path.join(outDir,"streamlit-phase3-daily.png"),fullPage:false});
      }
      await appFrame.getByRole("tab",{name:"PDUFA WORKBENCH"}).click({timeout:15000});
      await sleep(1500);
      result.checks.workbenchVisible=await appFrame.getByText("WATCHLIST — PROGRAM REVIEW THROUGH FDA DECISION",{exact:false}).count()>0;
      await page.screenshot({path:path.join(outDir,"streamlit-workbench.png"),fullPage:false});
      await appFrame.getByRole("tab",{name:"TRIALS & DATES"}).click({timeout:15000});
      await page.setViewportSize({width:390,height:844});
      await sleep(1500);
      await page.screenshot({path:path.join(outDir,"streamlit-iphone-width.png"),fullPage:false});
    }
    // Walk each independent main navigation page in the deployed browser.
    // This catches runtime exceptions outside Pipeline, which unit tests
    // and startup import checks do not exercise.
    await page.setViewportSize({width:1440,height:900});
    const pages=[
      ["DISEASE & MARKET HORIZON","DISEASE & MARKET HORIZON"],
      ["STRATEGY","STRATEGY — NESTED DISEASE"],
      ["2. PDUFA CALENDAR","2. PDUFA CALENDAR"],
      ["4. DECISION","4. DECISION — FDA OUTCOMES"],
      ["5. SCANS","5. SCANS — FIND CHANGES"],
      ["6. RECHECK","6. RECHECK — VERIFY"],
      ["9. PREDICTION ENGINE","9. PREDICTION ENGINE"],
      ["10. MATCH OPTIMIZER","10. MATCH OPTIMIZER"],
      ["11. PLAN","11. PLAN — SYSTEM RULES"],
    ];
    result.pages=[];
    for(const [name, expectedHeading] of pages){
      const entry={name, expectedHeading};
      try{
        await appFrame.getByRole("radio",{name,exact:true}).check({timeout:15000});
        for(let n=0;n<45;n++){
          const titles=await appFrame.locator("h1,h2,h3").allInnerTexts();
          entry.headings=titles.slice(0,8);
          if(titles.some(t=>t.includes(expectedHeading)))break;
          await sleep(1000);
        }
        const visible=await appFrame.locator("body").innerText({timeout:9000});
        entry.headingFound=(entry.headings||[]).some(t=>t.includes(expectedHeading));
        entry.noVisibleException=!visible.includes("This app has encountered an error")
          && !visible.includes("Traceback (most recent call last)");
        entry.passed=entry.headingFound&&entry.noVisibleException;
        if(!entry.passed)result.errors.push("Navigation page failed live audit: "+name);
        if(!entry.passed)await page.screenshot({path:path.join(outDir,
          "page-error-"+name.replace(/[^a-z0-9]+/gi,"-")+".png"),fullPage:false});
      }catch(err){
        entry.passed=false;
        entry.error=String(err.message||err).slice(0,220);
        result.errors.push("Could not audit navigation page: "+name);
      }
      result.pages.push(entry);
    }
  }
  result.failedRequests=failedRequests;
  result.browserPageErrors=browserErrors;
  if(result.http!==200) result.errors.push("Site HTTP status is not 200.");
  if(!result.checks.pdufaHeader) result.errors.push("App did not render in an inspected browser frame.");
  if(result.checks.pdufaHeader&&!result.checks.newBuildLabel) result.errors.push("Live app is an outdated or different build.");
  for(const k of ["noTodayNavigation","pipelineNavigation","threePipelineTabs","stageAndDateControls",
                   "stageCountChart","dateCountChart","dailyReportToggle","dailyReportLoads","workbenchVisible"]){
    if(result.checks.pdufaHeader&&result.checks[k]===false) result.errors.push("Live UI check failed: "+k);
  }
  if(!result.checks.scriptError)result.errors.push("Live app displays an exception.");
}
audit().catch(err=>result.errors.push(String(err.stack||err).slice(0,1500))).finally(async()=>{
  if(browser)await browser.close();
  fs.writeFileSync(path.join(outDir,"live-audit.json"),JSON.stringify(result,null,2));
  console.log("LIVE STREAMLIT AUDIT\n"+JSON.stringify(result,null,2));
  process.exitCode=result.errors.length?1:0;
});
