#!/usr/bin/env python3
"""Read-only signed-in acceptance of the exact-commit FOCUS 29/23 research board.

The test secret is supplied only through protected CI. No cookies or source
content are logged. No reviewer writes or production alias changes.
"""
from __future__ import annotations
from html.parser import HTMLParser
import http.cookiejar,json,os,re,sys
from urllib.error import HTTPError,URLError
from urllib.request import HTTPCookieProcessor,HTTPRedirectHandler,Request,build_opener

SITE="https://pdufa-new-dashboard-moztc7ekg-pdufa.vercel.app"
ROSTER="/api/predictions/focus-preliminary"
URL="/predictions"
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError("UNEXPECTED_EXTERNAL_AUTH_REDIRECT")
class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)
def get(client,path,accept):
    req=Request(SITE+path,headers={
        "Accept":accept,"User-Agent":"PDUFA-FOCUS-R39-signed-in-readback/1"
    })
    try:response=client.open(req,timeout=35)
    except HTTPError as e:response=e
    with response:
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError("PREVIEW_RESPONSE_SIZE_EXCEEDED")
        return response.code,response.headers.get("content-type",""),raw
def check(ok,code):
    if not ok:raise ValueError(code)
def main():
    password=os.environ.get("DASHBOARD_PASSWORD")
    check(bool(password),"MISSING_AUTHORIZED_PREVIEW_SECRET")
    client=build_opener(NoRedirect(),HTTPCookieProcessor(http.cookiejar.CookieJar()))
    request=Request(SITE+"/api/auth",data=json.dumps({"password":password}).encode(),
        headers={"Accept":"application/json","Content-Type":"application/json",
                 "Origin":SITE,"User-Agent":"PDUFA-FOCUS-R39-auth/1"})
    try:auth=client.open(request,timeout=35)
    except HTTPError as e:auth=e
    with auth:
        check(auth.code==200,"NORMAL_DASHBOARD_LOGIN_UNAVAILABLE_HTTP_"+str(auth.code))
    print(json.dumps({"stage":"NORMAL_DASHBOARD_LOGIN","status":"PASS"}),flush=True)
    code,kind,raw=get(client,URL,"text/html")
    check(code==200 and "text/html" in kind,"PREDICTIONS_HTML_NOT_AVAILABLE")
    parser=Visible();parser.feed(raw.decode("utf8","replace"))
    rendered=re.sub(r"\s+"," "," ".join(parser.parts))
    for value in [
        "29 FOCUS trials / 23 provisional FDA application assessments",
        "29-trial roster and application linkage",
        "23 application-specific evidence judgments",
        "Download the complete dated 29-trial / 23-application research record",
        "Approval-lean research","CRL-lean research","Research abstains",
        "Observed FDA approval","Official FDA prediction",
        "Review delay/extension prediction",
        "November 9 2026",
    ]:
        check(value.lower() in rendered.lower(),"FOCUS_RENDER_MISSING_"+re.sub(r"\W+","_",value).upper())
    print(json.dumps({"stage":"FOCUS_29_23_SIGNED_IN_HTML","status":"PASS",
        "researchOnly":True,"futureModelStatus":"ABSTAIN"}),flush=True)
    code,kind,raw=get(client,ROSTER,"application/json")
    check(code==200 and "json" in kind,"RESEARCH_JSON_NOT_AVAILABLE")
    r=json.loads(raw)
    summary=r.get("summary",{})
    trials=r.get("trials",[])
    apps=r.get("applications",[])
    check(r.get("schema")=="MAIN_FOCUS_29_23_APP_RESEARCH_V1" and
        r.get("asOf")=="2026-11-09" and
        len(trials)==29 and len(apps)==23 and
        len({x["nct"] for x in trials})==29 and
        len({x["id"] for x in apps})==23 and
        summary.get("researchLeanApprovals")==5 and
        summary.get("researchLeanCrls")==1 and
        summary.get("abstainResearchCalls")==16 and
        summary.get("observedPastApprovals")==1 and
        summary.get("independentlyValidatedFDAForecasts")==0 and
        summary.get("qualifiedIndependentClinicalReviews")==0 and
        summary.get("verifiedHistoricalBacktests")==0,
        "FOCUS_RESEARCH_ROSTER_SAFETY_SCHEMA_MISMATCH")
    check(all(x.get("numericalFDAProbability") is None and
              x.get("calibratedAccuracy") is None and
              x.get("qualifiedReviewerSignoff") is False and
              x.get("reviewDelayOrExtensionPrediction") in
                ("ABSTAIN","NOT_APPLICABLE_ALREADY_OBSERVED")
              for x in apps),
         "UNVALIDATED_FDA_PROBABILITY_OR_TIMING_RELEASED")
    observed=[x for x in apps if x.get("observedAction")]
    check(len(observed)==1 and observed[0]["id"]=="cytk-aficamten-ohcm" and
       observed[0]["observedAction"]=="FDA_APPROVED_2025_12_19" and
       all(x["releasedRegulatoryPrediction"]=="ABSTAIN" for x in apps if not x.get("observedAction")),
       "OBSERVED_ACTION_MISCLASSIFIED_AS_FUTURE_FORECAST")
    check(all(x["applicationCycleIds"] and
          all(any(a["id"]==id and x["nct"] in a["ncts"] for a in apps)
              for id in x["applicationCycleIds"]) for x in trials),
          "FOCUS_NCT_APPLICATION_MEMBERSHIP_CORRUPTED")
    print(json.dumps({"stage":"FOCUS_29_23_SIGNED_IN_JSON","status":"PASS",
        "trials":len(trials),"applications":len(apps),
        "researchApprovalLeans":5,"researchCrlLeans":1,
        "researchAbstains":16,"observedApprovals":1,
        "qualifiedClinicalGrades":0,"validatedForecasts":0,
        "historicalBacktests":0,"futureFdaForecasts":"ABSTAIN",
        "readOnly":True}),flush=True)

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,URLError) as e:
        print(json.dumps({"status":"BLOCKED",
            "code":"FOCUS_PRELIMINARY_SIGNED_IN_ACCEPTANCE_FAILED",
            "errorType":type(e).__name__,
            "safeReason":str(e) if isinstance(e,ValueError) else "ERROR_REDACTED"}),flush=True)
        sys.exit(1)
