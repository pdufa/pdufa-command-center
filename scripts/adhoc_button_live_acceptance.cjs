// Inspect the live SCANS navigation and ad hoc button; never submit a scan.
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
    const deadline = Date.now()+145000;
    let frame=null;
    while(Date.now()<deadline){
      frame=await appFrame(page);
      if(frame && await frame.getByText("5. SCANS",{exact:true}).count())break;
      await sleep(1500);
    }
    if(!frame)throw Error("Streamlit app navigation did not render");
    await frame.getByText("5. SCANS",{exact:true}).click({timeout:10000});
    let scanBody = "", buttons = 0, links=0, pin=0;
    while(Date.now()<deadline){
      frame=await appFrame(page);
      if(!frame){await sleep(1000);continue;}
      scanBody=await frame.locator("body").innerText({timeout:8000});
      if(/This app has encountered an error|Traceback \(most recent call last\)/i.test(scanBody))
        throw Error("Streamlit application exception: "+scanBody.slice(-650));
      buttons=await frame.getByRole("button",{name:"▶ RUN AD HOC GMAIL + GITHUB ERROR CHECK",exact:true}).count();
      links=await frame.getByText("OPEN AD HOC ERROR CHECK / RESULTS IN GITHUB",{exact:true}).count();
      pin=await frame.getByText("Ad hoc check PIN",{exact:false}).count();
      if(buttons && links && pin)break;
      await sleep(1250);
    }
    result.setup = scanBody.includes("Direct one-click dispatch is locked until")
      ? "STREAMLIT_TOKEN_OR_PIN_MISSING"
      : scanBody.includes("Enter your scan-control PIN to enable the on-demand check.")
        ? "READY_PIN_REQUIRED"
        : "CREDENTIAL_STATUS_UNKNOWN";
    if(result.setup === "STREAMLIT_TOKEN_OR_PIN_MISSING")
      result.errors.push("Streamlit lacks the required GitHub token or scan PIN");
    result.checks.scansPage = scanBody.includes("5. SCANS — FIND CHANGES & NEW EVIDENCE");
    result.checks.adhocButton = buttons===1;
    result.checks.adhocPin = pin>0;
    result.checks.githubResultLink = links>0;
    result.checks.noApplicationException = !/This app has encountered an error|Traceback \(most recent call last\)/i.test(scanBody);
    if(buttons===1)result.checks.lockedBeforePin = await frame.getByRole("button",{name:"▶ RUN AD HOC GMAIL + GITHUB ERROR CHECK"}).isDisabled();
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
