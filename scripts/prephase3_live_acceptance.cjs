// Focused browser acceptance for PRE PHASE 3 only.
// No POST PHASE 3 report, finance drilldowns or other heavy navigation pages.
const {chromium}=require("playwright-core");
const fs=require("fs");
const path=require("path");
const URL="https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/";
const out=path.join(process.cwd(),"prephase3-acceptance-artifacts");
fs.mkdirSync(out,{recursive:true});
const sleep=(ms)=>new Promise(resolve=>setTimeout(resolve,ms));
const checked={
  asOfUTC:new Date().toISOString(),
  url:URL,
  checks:{},errors:[],notes:[],screenEnd:"",
};

async function findFrame(page){
  for(const frame of page.frames()){
    try{
      const text=await frame.locator("body").innerText({timeout:2500});
      if(text.includes("BIO PDUFA COMMAND CENTER"))
        return {frame,text};
    }catch(err){
      if(!/detached|Execution context was destroyed|closed/i.test(String(err)))throw err;
    }
  }
  return null;
}

async function verify(){
  const browser=await chromium.launch({
    executablePath:process.env.CHROME_PATH||"/usr/bin/google-chrome",
    headless:true,args:["--no-sandbox","--disable-dev-shm-usage"],
  });
  try{
    const page=await browser.newPage({viewport:{width:1440,height:950}});
    const response=await page.goto(URL,{waitUntil:"domcontentloaded",timeout:60000});
    checked.http=response?.status()??null;
    if(checked.http!==200)throw Error("Dashboard HTTP status "+checked.http);
    let match=null;
    let lastFrameTexts=[];
    // Cloud may be waking or redeploying when multiple validation jobs start.
    // Retry one navigation after the warm-up window; keep failure fail-closed.
    for(let n=0;n<130;n++){
      const observed=await findFrame(page);
      if(n%10===0 || n===129){
        lastFrameTexts=[];
        for(const frame of page.frames()){
          try{
            lastFrameTexts.push({
              url:frame.url(),
              text:(await frame.locator("body").innerText({timeout:1500})).slice(0,450),
            });
          }catch(_){lastFrameTexts.push({url:frame.url(),text:"FRAME UNAVAILABLE"});}
        }
      }
      if(observed&&observed.text.includes("PIPELINE")&&observed.text.includes("PRE PHASE 3")){
        match=observed;
        break;
      }
      if(n===65){
        checked.notes.push("Cloud app not ready on first load; retrying navigation.");
        await page.reload({waitUntil:"domcontentloaded",timeout:60000});
      }
      await sleep(1400);
    }
    checked.frameDiagnostics=lastFrameTexts;
    if(!match)throw Error("Live application still unavailable after navigation retry; see frameDiagnostics");
    const tab=match.frame.getByRole("tab",{name:"PRE PHASE 3",exact:true});
    await tab.click({timeout:20000});
    let body="";
    let lastFrame=match.frame;
    // Streamlit may replace the app frame while rerunning the Python script.
    for(let n=0;n<125;n++){
      const current=await findFrame(page);
      if(current){lastFrame=current.frame;body=current.text;}
      if(body.includes("This app has encountered an error")||
         body.includes("Traceback (most recent call last)"))
        throw Error("Deployed Streamlit shows application exception");
      const required=[
        "PRE PHASE 3 — LIVE SOURCE MONITOR",
        "PRE PHASE 3 COMPLETION CHECKLIST",
        "SOURCE HEALTH / LAST VERIFIED CHECK",
        "PRE PHASE 3 CLINICAL RESEARCH QUEUE",
        "ALL-TRIAL REVIEW PRIORITY",
        "Priority score coverage",
        "filtered rows have a review-priority score /100",
        "DATED CLINICAL RESEARCH PILOT SCORES",
        "NEXT 10 PHASE 3 CLINICAL SCORING REVIEWS",
        "provisional, source-cited clinical research score(s) /100",
      ];
      if(required.every(str=>body.includes(str)))break;
      await sleep(1800);
    }
    await page.screenshot({path:path.join(out,"prephase3-live-scorecards.png"),fullPage:false});
    // The two dated pilot examples may legitimately expire or be withheld;
    // their absence is not a broken dashboard and must not be scored as zero.
    const pilotMatch=body.match(/(\d+) provisional, source-cited clinical research score\(s\) \/100/);
    const pilotCount=pilotMatch?Number(pilotMatch[1]):null;
    const pilotCardsVisible=body.includes("PROVISIONAL RESEARCH /100")
      ||body.includes("REVIEWED RESEARCH /100");
    const pilotExplicitlyUnavailable=body.includes("NO CURRENT SOURCE-DATED PILOT SCORES");
    checked.pilotEvidence={reportedCount:pilotCount,pilotCardsVisible,pilotExplicitlyUnavailable};
    const requiredChecks={
      tabSelected:await lastFrame.getByRole("tab",{name:"PRE PHASE 3",exact:true}).getAttribute("aria-selected")==="true",
      sourceHealth:body.includes("SOURCE HEALTH / LAST VERIFIED CHECK"),
      researchTable:body.includes("PRE PHASE 3 CLINICAL RESEARCH QUEUE"),
      allTrialPriority:body.includes("ALL-TRIAL REVIEW PRIORITY")&&body.includes("Priority score coverage"),
      priorityCoverage:body.includes("filtered rows have a review-priority score /100"),
      priorityOrdering:body.includes("Default display is Top Score, with Ticker A–Z available"),
      priorityRubric:body.includes("HOW REVIEW PRIORITY IS CALCULATED"),
      priorityClinicalSeparation:body.includes("it is not a clinical strength score or success probability")&&body.includes("Excluded rows have priority 0 and no rank"),
      completionChecklist:body.includes("PRE PHASE 3 COMPLETION CHECKLIST"),
      sourceReviewedPilot:body.includes("fully source-reviewed PRE PHASE 3 score /100"),
      provisionalCountReported:pilotCount!==null,
      scorecardHeading:body.includes("DATED CLINICAL RESEARCH PILOT SCORES"),
      pilotScoreStateConsistent:pilotCount===0
        ?pilotExplicitlyUnavailable
        :pilotCount>0?pilotCardsVisible:false,
      researchWorklist:body.includes("NEXT 10 PHASE 3 CLINICAL SCORING REVIEWS"),
      noFalsePoS:body.includes("not independently audited clinical scores")&&body.includes("not a Phase 3 success probability"),
    };
    // Separate rendering/contract failures from missing source-reviewed
    // clinical evidence. A truthful NOT COMPLETE state must not be changed to
    // PASS or counted as a broken web application.
    const pending=body.match(/NOT COMPLETE — ([\d,]+)\/([\d,]+) requirements passed/);
    const dataReady=body.includes("PRE PHASE 3 data and scoring gates pass");
    const completed=pending?Number(pending[1].replace(/,/g,"")):null;
    const total=pending?Number(pending[2].replace(/,/g,"")):null;
    requiredChecks.clinicalReadinessReported=Boolean(dataReady||pending)
      && (dataReady||completed<total);
    checked.readiness={
      status:dataReady?"PASS":pending?"INCOMPLETE":"UNKNOWN",
      passed:completed,total,
      detail:dataReady?"All pre-readout data gates reported passing":
        pending?"Source-evidence requirements remain open; not certified entry-ready":
        "No explicit clinical readiness state was rendered",
    };
    checked.checks=requiredChecks;
    checked.screenEnd=body.slice(-3200);
    checked.errors=Object.entries(requiredChecks).filter(([,ok])=>!ok).map(([k])=>k+" failed");
    if(checked.readiness.status==="INCOMPLETE")
      checked.notes.push("Clinical source review incomplete; UI acceptance does not imply clinical readiness.");
    if(pilotCount===0)
      checked.notes.push("No current dated pilot research scores; browser audit does not invent or demand previous TRVI/LBRX values.");

  }finally{
    await browser.close();
  }
}
verify().catch(e=>checked.errors.push(String(e.stack||e).slice(0,1400))).finally(()=>{
  fs.writeFileSync(path.join(out,"prephase3-acceptance.json"),JSON.stringify(checked,null,2));
  process.stdout.write("PRE PHASE 3 BROWSER ACCEPTANCE\n"+JSON.stringify(checked,null,2)+"\n");
  process.exitCode=checked.errors.length?1:0;
});
