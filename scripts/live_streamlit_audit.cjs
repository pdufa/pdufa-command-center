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
function navigationChoice(frame,name){
  return frame.locator('[data-testid="stRadio"]').filter({has:
    frame.getByRole("radio",{name:"PDUFA",exact:true})}).getByText(name,{exact:true});
}
async function waitForRender(page,frame,accepts,timeout=180000){
  const deadline=Date.now()+timeout;
  let text="",stableSince=null;
  while(Date.now()<deadline){
    try{
      if(frame.isDetached()){
        const current=(await inspectFrames(page)).find(x=>x.text.includes("BIO PDUFA COMMAND CENTER"));
        if(current)frame=current.frame;
        else{await sleep(1000);continue;}
      }
      text=await frame.locator("body").innerText({timeout:9000});
      if(/This app has encountered an error|Traceback \(most recent call last\)/i.test(text))
        throw Error("Streamlit displays an application exception: "+text.slice(-650));
      if(await accepts(text,frame)){
        stableSince??=Date.now();
        // Timed fragments can keep the global Running indicator active even
        // after the target controls render. Require a stable target screen;
        // background refresh activity is not proof that this screen is partial.
        if(Date.now()-stableSince>=1200)return {frame,text};
      }else stableSince=null;
    }catch(err){
      if(!/detached|Execution context was destroyed/i.test(String(err)))throw err;
      stableSince=null;
    }
    await sleep(700);
  }
  throw Error("Streamlit render did not complete: "+text.slice(-900));
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
    const ready=await waitForRender(page,appFrame,text=>
      text.includes("PDUFA — CLINICAL AND REGULATORY STAGES")
      && text.includes("STAGE COUNTS") && text.includes("DATE TRIAL COUNTS")
      && text.includes("PIPELINE — PDUFA COUNTDOWN, WATCHLIST & ANALYSIS"));
    appFrame=ready.frame;initial=ready.text;
  }
  result.visibleStart=initial.slice(0,1100);
  result.checks.pdufaHeader=initial.includes("BIO PDUFA COMMAND CENTER");
  result.checks.newBuildLabel=initial.includes("PDUFA PIPELINE PRIMARY") && initial.includes("MATCH VALIDATION IN PREDICTION ENGINE");
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
    result.checks.pdufaNavigation=result.navigation.includes("PDUFA");
    result.checks.oldPipelineNavigationAbsent=!result.navigation.includes("PIPELINE");
    result.checks.matchOptimizerNavigationRemoved=!result.navigation.includes("10. MATCH OPTIMIZER");
    result.checks.pdufaMainNavigationFirst=result.navigation.filter(x=>x!=="Navigation")[0]==="PDUFA";
    result.tabs=(await appFrame.getByRole("tab").allInnerTexts()).map(x=>x.trim());
    result.checks.prePhase3MainNavAbsent=!result.navigation.includes("PRE PHASE 3");
    result.checks.threePdufaTabs=["PIPELINE","PRE PHASE 3","POST PHASE 3"].every(x=>result.tabs.includes(x));
    result.checks.workbenchSubtabRemoved=!result.tabs.includes("PDUFA WORKBENCH");
    result.checks.pipelineDefaultActive=await appFrame.getByRole("tab",{name:"PIPELINE"}).getAttribute("aria-selected")==="true";
    if(!result.checks.matchOptimizerNavigationRemoved || !result.checks.pdufaMainNavigationFirst || !result.checks.pipelineDefaultActive)
      result.errors.push("PDUFA must open with PIPELINE primary; Match Optimizer must not be a main navigation item.");
    result.checks.researchInsidePipeline=await appFrame.getByText("PIPELINE — PDUFA COUNTDOWN, WATCHLIST & ANALYSIS",{exact:false}).count()>0;
    result.checks.stageAndDateControls=(await appFrame.locator('[data-testid="stMultiSelect"]').count())>=2;
    result.checks.stageCountChart=await appFrame.getByText("STAGE COUNTS",{exact:true}).count()>0;
    result.checks.dateCountChart=await appFrame.getByText("DATE TRIAL COUNTS",{exact:true}).count()>0;
    result.checks.noInitialTrials=/Trials \/ programs displayed\s*0/.test(initial);
    if(result.checks.threePdufaTabs){
      await appFrame.getByRole("tab",{name:"POST PHASE 3"}).click({timeout:15000});
      const phase3Ready=await waitForRender(page,appFrame,async(text,frame)=>
        await frame.getByRole("tab",{name:"POST PHASE 3",exact:true}).getAttribute("aria-selected")==="true"
        && text.includes("POST PHASE 3 — TRADING WORKSPACE")
        && text.includes("STAGE 1 — PHASE 3 → FINANCING #2 → GREEN ENTRY")
        && text.includes("1 · Discover & qualify")
        && text.includes("2 · Monitor & exit")
        && text.includes("3 · Historical backtest")
        && text.includes("One combined candidate table")
        && text.includes("Sort combined table")
        && text.includes("Ranked for research")
        && text.includes("TOP 10 — RESEARCH PRIORITY")
        && text.includes("ALL CANDIDATES — STATUS + RANKINGS + EVIDENCE GAPS")
        && !text.includes("No active research candidates match this view"));
      appFrame=phase3Ready.frame;
      result.checks.postPhase3Installed=true;
      result.checks.postPhase3CombinedRatingVisible=phase3Ready.text.includes("One combined candidate table")
        && phase3Ready.text.includes("Sort combined table");
      result.checks.postPhase3ResearchRanksVisible=phase3Ready.text.includes("Ranked for research")
        && phase3Ready.text.includes("TOP 10 — RESEARCH PRIORITY")
        && phase3Ready.text.includes("ALL CANDIDATES — STATUS + RANKINGS + EVIDENCE GAPS")
        && !phase3Ready.text.includes("No active research candidates match this view");
      if(!result.checks.postPhase3CombinedRatingVisible)
        result.errors.push("POST PHASE 3 combined eligibility and rating sorter is missing.");
      await page.screenshot({path:path.join(outDir,"streamlit-post-phase3-qualification.png"),fullPage:false});
      await appFrame.getByText("2 · Monitor & exit",{exact:true}).first().click({timeout:15000});
      const phase3Hold=await waitForRender(page,appFrame,
        text=>text.includes("STAGE 2 — GREEN ENTRY → YELLOW HOLD → RED EXIT WATCH")
          && text.includes("No actual positions have been supplied."));
      appFrame=phase3Hold.frame;
      result.checks.postPhase3Stage2Visible=true;
      result.checks.noPhantomPositions=true;
      await page.screenshot({path:path.join(outDir,"streamlit-post-phase3-positions.png"),fullPage:false});
      await appFrame.getByText("3 · Historical backtest",{exact:true}).first().click({timeout:15000});
      const phase3History=await waitForRender(page,appFrame,
        text=>text.includes("STAGE 3 — HISTORICAL ENTRY / EXIT RESEARCH")
          && text.includes("Historical research leads")
          && text.includes("BACKTEST NOT READY"));
      appFrame=phase3History.frame;
      result.checks.postPhase3Stage3Visible=true;
      result.checks.noInventedTradeReturns=phase3History.text.includes("Simulated trade scenarios")
        && phase3History.text.includes("BACKTEST NOT READY");
      if(!result.checks.noInventedTradeReturns)
        result.errors.push("POST PHASE 3 Stage 3 falsely reports trade returns without evidence.");
      await page.screenshot({path:path.join(outDir,"streamlit-post-phase3-backtesting.png"),fullPage:false});
      await appFrame.getByRole("tab",{name:"PRE PHASE 3"}).click({timeout:15000});
      const preReady=await waitForRender(page,appFrame,(text,frame)=>
        frame.getByRole("tab",{name:"PRE PHASE 3",exact:true}).getAttribute("aria-selected")
          .then(selected=>selected==="true"
            && text.includes("SOURCE HEALTH / LAST VERIFIED CHECK")
            && text.includes("NEXT 10 PHASE 3 CLINICAL SCORING REVIEWS")));
      appFrame=preReady.frame;
      let prePhaseScreen=preReady.text;
      // Confirm the new scoring workflow is actually visible on the deployed
      // PRE PHASE 3 tab, not merely present in the Python source files.
      for(let n=0;n<50;n++){
        try{
          // Streamlit Cloud reruns can detach and recreate the application iframe.
          // Reacquire it instead of failing an otherwise healthy browser audit.
          if(appFrame.isDetached()){
            const candidates=await inspectFrames(page);
            const current=candidates.find(x=>x.text.includes("BIO PDUFA COMMAND CENTER"));
            if(current)appFrame=current.frame;
            else{await sleep(1400);continue;}
          }
          prePhaseScreen=await appFrame.locator("body").innerText({timeout:8500});
          if(prePhaseScreen.includes("NEXT 10 PHASE 3 CLINICAL SCORING REVIEWS")
            && prePhaseScreen.includes("filtered rows have a fully source-reviewed")
            && prePhaseScreen.includes("provisional, source-cited clinical research score(s) /100")
            && prePhaseScreen.includes("DATED CLINICAL RESEARCH PILOT SCORES")
            && prePhaseScreen.includes("TRVI · NCT07671911")
            && prePhaseScreen.includes("LBRX · NCT07363577")
            && prePhaseScreen.includes("80/100")
            && prePhaseScreen.includes("72/100"))break;
          if(/This app has encountered an error|Traceback \(most recent call last\)/i.test(prePhaseScreen))break;
        }catch(err){
          if(/detached|Target closed|Execution context was destroyed/i.test(String(err))){
            const candidates=await inspectFrames(page);
            const current=candidates.find(x=>x.text.includes("BIO PDUFA COMMAND CENTER"));
            if(current)appFrame=current.frame;
          }else throw err;
        }
        await sleep(1400);
      }
      result.checks.prePhase3PilotScoresVisible=
        prePhaseScreen.includes("DATED CLINICAL RESEARCH PILOT SCORES")
        && prePhaseScreen.includes("TRVI · NCT07671911")
        && prePhaseScreen.includes("LBRX · NCT07363577")
        && prePhaseScreen.includes("80/100")
        && prePhaseScreen.includes("72/100");
      if(!result.checks.prePhase3PilotScoresVisible)
        result.errors.push("Live PRE PHASE 3 must display exact TRVI OCEAN-1 and LBRX NOVA-2 numeric scorecards.");
      const prePhaseTabSelected=await appFrame.getByRole("tab",{name:"PRE PHASE 3"}).getAttribute("aria-selected");
      result.checks.prePhase3ScoringWorkflowVisible=prePhaseTabSelected==="true"
        && prePhaseScreen.includes("NEXT 10 PHASE 3 CLINICAL SCORING REVIEWS")
        && prePhaseScreen.includes("filtered rows have a fully source-reviewed")
        && prePhaseScreen.includes("provisional, source-cited clinical research score(s) /100");
      if(!result.checks.prePhase3ScoringWorkflowVisible)
        result.errors.push("Deployed PRE PHASE 3 is missing the score-count caption or the ten-candidate clinical scoring review worklist.");
      result.prePhaseDiagnostic={
        tabSelected:prePhaseTabSelected,
        hasNewHeading:prePhaseScreen.includes("PRE PHASE 3 — LIVE SOURCE MONITOR"),
        textEnd:prePhaseScreen.slice(-3500),
      };
      result.checks.prePhase3Visible=(prePhaseTabSelected==="true")
        && prePhaseScreen.includes("PRE PHASE 3 — LIVE SOURCE MONITOR")
        && prePhaseScreen.includes("SOURCE HEALTH / LAST VERIFIED CHECK")
        && prePhaseScreen.includes("CLINICAL RESEARCH QUEUE")
        && !/This app has encountered an error|Traceback \(most recent call last\)/i.test(prePhaseScreen);
      if(!result.checks.prePhase3Visible)
        result.errors.push("PRE PHASE 3 Step 7 source-health and clinical research tables must be visible.");
      await page.screenshot({path:path.join(outDir,"streamlit-pre-readout.png"),fullPage:false});
      await appFrame.getByRole("tab",{name:"PIPELINE"}).click({timeout:15000});
      const pipelineReady=await waitForRender(page,appFrame,text=>text.includes("WATCHLIST MANAGEMENT"));
      appFrame=pipelineReady.frame;
      result.checks.watchlistInsidePipeline=await appFrame.getByText("WATCHLIST MANAGEMENT",{exact:true}).count()>0;
      await page.screenshot({path:path.join(outDir,"streamlit-pipeline-with-research.png"),fullPage:false});
      await page.setViewportSize({width:390,height:844});
      await sleep(1500);
      await page.screenshot({path:path.join(outDir,"streamlit-iphone-width.png"),fullPage:false});
      // A real phone must reach PLAN without a horizontally hidden navigation option.
      const mobilePlanChoice=navigationChoice(appFrame,"11. PLAN");
      result.checks.mobilePlanNavigationVisible=await mobilePlanChoice.evaluate(el=>{
        const bounds=el.getBoundingClientRect();
        return bounds.width>0 && bounds.left>=0 && bounds.right<=window.innerWidth;
      });
      await mobilePlanChoice.click({timeout:15000});
      const planReady=await waitForRender(page,appFrame,async(text,frame)=>
        await frame.getByRole("radio",{name:"11. PLAN",exact:true}).isChecked()
        && text.includes("11. PLAN — SYSTEM RULES & OPERATING RHYTHM")
        && text.includes("SAVE PLAN CHANGES") && text.includes("DOWNLOAD PLAN BACKUP"));
      appFrame=planReady.frame;
      // Streamlit may paint the PLAN title before its editor/action widgets.
      // Wait for the actual controls, not only the heading, at iPhone width.
      let mobilePlanText="";
      for(let attempt=0;attempt<35;attempt++){
        mobilePlanText=await appFrame.locator("body").innerText({timeout:9000});
        if(mobilePlanText.includes("Edit plan")
          && mobilePlanText.includes("SAVE PLAN CHANGES")
          && mobilePlanText.includes("DOWNLOAD PLAN BACKUP"))break;
        await sleep(1000);
      }
      result.checks.mobilePlanOpens=mobilePlanText.includes("Edit plan")
        && mobilePlanText.includes("SAVE PLAN CHANGES")
        && mobilePlanText.includes("DOWNLOAD PLAN BACKUP")
        && !/This app has encountered an error|Traceback \(most recent call\)/i.test(mobilePlanText);
      if(!result.checks.mobilePlanOpens)
        result.notes.push("Mobile PLAN render incomplete: "+mobilePlanText.slice(-650));
      await page.screenshot({path:path.join(outDir,"streamlit-iphone-plan.png"),fullPage:false});
      if(!result.checks.mobilePlanNavigationVisible || !result.checks.mobilePlanOpens)
        result.errors.push("11. PLAN is not reachable and usable on mobile.");
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
      ["11. PLAN","11. PLAN — SYSTEM RULES"],
    ];
    result.pages=[];
    for(const [name, expectedHeading] of pages){
      const entry={name, expectedHeading};
      try{
        // PLAN content can repeat navigation names. Select the actual radio
        // rather than a same-text paragraph elsewhere on the page.
        // React Aria clips the native input inside a 1px span. Force-checking
        // that input can hit another radio and silently leave the old page.
        // Click the visible label within the actual navigation group instead.
        const choice=navigationChoice(appFrame,name);
        await choice.click({timeout:15000});
        const ready=await waitForRender(page,appFrame,async(text,frame)=>
          await frame.getByRole("radio",{name,exact:true}).isChecked()
          && text.includes(expectedHeading));
        appFrame=ready.frame;
        for(let n=0;n<45;n++){
          const titles=await appFrame.locator("h1,h2,h3").allInnerTexts();
          entry.headings=titles.slice(0,8);
          const selected=await appFrame.getByRole("radio",{name,exact:true}).isChecked();
          if(selected && titles.some(t=>t.includes(expectedHeading)))break;
          await sleep(1000);
        }
        const visible=await appFrame.locator("body").innerText({timeout:9000});
        entry.navigationSelected=await appFrame.getByRole("radio",{name,exact:true}).isChecked();
        entry.headingFound=entry.navigationSelected && (entry.headings||[]).some(t=>t.includes(expectedHeading));
        entry.noVisibleException=!visible.includes("This app has encountered an error")
          && !visible.includes("Traceback (most recent call last)");
        entry.passed=entry.headingFound&&entry.noVisibleException;
        if(name==="9. PREDICTION ENGINE" && entry.passed){
          const tabs=await appFrame.getByRole("tab").allInnerTexts();
          result.checks.predictionContainsBothViews=["PREDICTIONS","HISTORICAL MATCH VALIDATION"]
            .every(label=>tabs.includes(label));
          const validationTab=appFrame.getByRole("tab",{name:"HISTORICAL MATCH VALIDATION"});
          await validationTab.click({timeout:15000});
          try{
            await appFrame.getByText("HISTORICAL MATCH VALIDATION — MODEL IMPROVEMENT",{exact:false})
              .first().waitFor({timeout:65000});
            let validatorText="";
            for(let n=0;n<45;n++){
              validatorText=await appFrame.locator("body").innerText({timeout:9000});
              if(validatorText.includes("STEP 3 — Tune the high-confidence F gate")
                && (validatorText.includes("STEP 5 — Lock thresholds and test the untouched holdout")
                  || validatorText.includes("No threshold pair meets the current minimum coverage/call requirements.")))break;
              if(validatorText.includes("This app has encountered an error"))break;
              await sleep(1200);
            }
            const eligibleThreshold=validatorText.includes("STEP 5 — Lock thresholds and test the untouched holdout")
              || validatorText.includes("No threshold pair meets the current minimum coverage/call requirements.");
            result.optimizerDiagnostic={
              benchmark:validatorText.includes("FDA-V3 decision-safe benchmark"),
              tuneGate:validatorText.includes("STEP 3 — Tune the high-confidence F gate"),
              tuneYear:validatorText.includes("Tune year"),
              holdoutYear:validatorText.includes("Holdout year"),
              thresholdOrReview:eligibleThreshold,
              lastText:validatorText.slice(-900),
            };
            // These controls establish that the former Match Optimizer is installed.
            // A pending optimization result is a separate data/compute state, not
            // evidence that the controls have been removed from the UI.
            result.checks.historicalOptimizerPreserved=result.optimizerDiagnostic.benchmark
              && result.optimizerDiagnostic.tuneGate
              && result.optimizerDiagnostic.tuneYear
              && result.optimizerDiagnostic.holdoutYear;
            result.checks.optimizerOutcomeResolved=result.optimizerDiagnostic.thresholdOrReview;
            if(result.checks.historicalOptimizerPreserved&&!result.checks.optimizerOutcomeResolved)
              result.notes.push("Prediction Engine historical controls are visible; a final tuned threshold or no-valid-threshold message was not observed during this audit.");
          }catch(err){
            result.checks.historicalOptimizerPreserved=false;
            result.notes.push("Prediction Engine historical validation not accessible: "+String(err.message).slice(0,180));
          }
          if(!result.checks.predictionContainsBothViews || !result.checks.historicalOptimizerPreserved)
            result.errors.push("Prediction Engine is missing former Match Optimizer controls.");
        }
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
  for(const k of ["noTodayNavigation","pdufaNavigation","oldPipelineNavigationAbsent","prePhase3MainNavAbsent","threePdufaTabs","workbenchSubtabRemoved","researchInsidePipeline","watchlistInsidePipeline","stageAndDateControls",
                   "stageCountChart","dateCountChart","dailyReportToggle","dailyReportLoads",
                   "prePhase3Visible",
                   "workbenchSubtabRemoved","prePhase3ScoringWorkflowVisible","prePhase3PilotScoresVisible"]){
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
