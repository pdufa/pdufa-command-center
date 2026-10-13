// Inspect PDUFA → SCANS and the protected ad hoc error-check controls; never submit a scan.
const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");

const URL = "https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/";
const outDir = path.join(process.cwd(), "adhoc-button-audit");
fs.mkdirSync(outDir, {recursive:true});
const result = {url: URL, date: new Date().toISOString(), checks:{}, errors:[]};
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let browser;

async function appFrame(page){
  for(const frame of page.frames()){
    try {
      if((await frame.locator("body").innerText({timeout:1200})).includes("BIO PDUFA COMMAND CENTER"))
        return frame;
    } catch(_){}
  }
  return null;
}

(async () => {
  try {
    browser = await chromium.launch({
      executablePath:process.env.CHROME_PATH || "/usr/bin/google-chrome",
      headless:true,args:["--no-sandbox","--disable-dev-shm-usage"]
    });
    const page = await browser.newPage({viewport:{width:1366,height:900}});
    await page.goto(URL,{waitUntil:"domcontentloaded",timeout:60000});
    const deadline = Date.now()+280000; // allow Streamlit Cloud deployment and first-run boot
    let frame=null;
    while(Date.now()<deadline){
      frame=await appFrame(page);
      if(frame && await frame.getByRole("tab",{name:"SCANS",exact:true}).count())break;
      await sleep(1500);
    }
    if(!frame || !(await frame.getByRole("tab",{name:"SCANS",exact:true}).count()))
      throw Error("PDUFA SCANS subtab did not render");
    await frame.getByRole("tab",{name:"SCANS",exact:true}).click({timeout:15000});
    let scanBody = "", buttons = 0, links=0, pin=0, fallback=0;
    let lastReload = Date.now();
    while(Date.now()<deadline){
      frame=await appFrame(page);
      if(!frame){await sleep(1000);continue;}
      scanBody=await frame.locator("body").innerText({timeout:8000});
      // Cloud may temporarily serve an older app revision after GitHub push.
      // Reload to pick up deployment; do not suppress a genuine absence.
      if(Date.now()-lastReload>45000 && !scanBody.includes("AD HOC — GMAIL + GITHUB ERROR CHECK")){
        await page.reload({waitUntil:"domcontentloaded",timeout:60000});
        frame=null;
        let selected=false;
        for(let attempt=0;attempt<20;attempt++){
          frame=await appFrame(page);
          if(frame && await frame.getByRole("tab",{name:"SCANS",exact:true}).count()){
            await frame.getByRole("tab",{name:"SCANS",exact:true}).click({timeout:12000});
            selected=true;
            break;
          }
          await sleep(1000);
        }
        if(!selected)throw Error("SCANS tab missing after refreshed Cloud deployment");
        lastReload=Date.now();
        continue;
      }
      if(/This app has encountered an error|Traceback \(most recent call last\)/i.test(scanBody))
        throw Error("Streamlit application exception: "+scanBody.slice(-650));
      buttons=await frame.getByRole("button",{name:"▶ RUN AD HOC GMAIL + GITHUB ERROR CHECK",exact:true}).count();
      links=await frame.getByText("OPEN AD HOC ERROR CHECK / RESULTS IN GITHUB",{exact:true}).count();
      fallback=await frame.getByText("▶ RUN AD HOC CHECK IN GITHUB",{exact:true}).count();
      pin=await frame.getByText("Ad hoc check PIN",{exact:false}).count();
      if(scanBody.includes("AD HOC — GMAIL + GITHUB ERROR CHECK")
         && ((buttons && links && pin) || (fallback && scanBody.includes("One-click dispatch is not configured"))))break;
      await sleep(1250);
    }
    result.liveSnapshot={
      selectedTab:await frame.getByRole("tab",{name:"SCANS",exact:true}).getAttribute("aria-selected"),
      nightlyReportVisible:scanBody.includes("NIGHTLY SCAN REPORT"),
      adHocHeadingVisible:scanBody.includes("AD HOC — GMAIL + GITHUB ERROR CHECK"),
      cloudLoading:scanBody.includes("Please wait...") || scanBody.includes("Your app is in the oven"),
      buttonCount:buttons,linkCount:links,pinLabelCount:pin,fallbackCount:fallback,
      visibleBodyEnding:scanBody.slice(-1600)
    };
    result.mode = buttons === 1 && links > 0 && pin > 0
      ? "DIRECT_PIN_GATED"
      : fallback === 1 && scanBody.includes("One-click dispatch is not configured")
        ? "GITHUB_MANUAL_RUN_FALLBACK"
        : "NOT_AVAILABLE";
    result.checks.scansPage = scanBody.includes("NIGHTLY SCAN REPORT")
      && scanBody.includes("AD HOC — GMAIL + GITHUB ERROR CHECK")
      && (await frame.getByRole("tab",{name:"SCANS",exact:true}).getAttribute("aria-selected")) === "true";
    result.checks.safeRunPathVisible = result.mode !== "NOT_AVAILABLE";
    result.checks.noApplicationException = !/This app has encountered an error|Traceback \(most recent call last\)/i.test(scanBody);
    result.checks.pinProtected = result.mode==="DIRECT_PIN_GATED"
      ? await frame.getByRole("button",{name:"▶ RUN AD HOC GMAIL + GITHUB ERROR CHECK"}).isDisabled()
      : buttons===0 && fallback===1;
    result.directDispatchReady = result.mode === "DIRECT_PIN_GATED";
    if(!result.directDispatchReady)
      result.notes = ["GitHub manual-run fallback works; set the Streamlit GitHub token and PIN to enable direct dispatch."];
    await page.screenshot({path:path.join(outDir,"scans-adhoc-button.png"),fullPage:false});
    for(const [check,passed] of Object.entries(result.checks))
      if(!passed)result.errors.push(check+" did not pass");
  } catch(err){result.errors.push(String(err).slice(0,1200));}
  finally {
    if(browser)await browser.close();
    fs.writeFileSync(path.join(outDir,"adhoc-button-results.json"),JSON.stringify(result,null,2));
    console.log("AD HOC SCANS BUTTON ACCEPTANCE",JSON.stringify(result,null,2));
    if(result.errors.length)process.exitCode=1;
  }
})();
