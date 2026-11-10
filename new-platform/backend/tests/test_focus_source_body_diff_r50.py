"""R50: original raw byte proof distinguishes SEC delivery variations and real source edits."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.compare_original_focus_source_bodies_r50 import compare
from scripts.refresh_focus_public_sources_r40 import (
    ROSTER,APPS,_read_json,build_manifest
)

def sec(tag):
    sensor="487029093" if tag=="1d077bdb" else "717730921"
    head=(f'<script >bazadebezolkohpepadr="{sensor}"</script>'
          f'<script type="text/javascript" src="https://www.sec.gov/akam/13/{tag}"  defer></script>')
    tail=(f'<noscript><img src="https://www.sec.gov/akam/13/pixel_{tag}?a=YmFzZTY0" '
          f'style="visibility: hidden; position: absolute; left: -999px; top: -999px;" /></noscript>')
    return ("<html><head>"+head+"</head><body><h1>Original Phase 3 disclosure</h1>"
       +"<p>Same efficacy statement and endpoint data.</p>"+tail+"</body></html>").encode()

SEC_URL="https://www.sec.gov/Archives/edgar/data/1000000/0000001/one.htm"
PH_URL="https://ir.pharvaris.com/news-releases/example"

def fixture(tmp_path):
    old=tmp_path/"old";new=tmp_path/"new";old.mkdir();new.mkdir()
    groups=build_manifest(_read_json(ROSTER),_read_json(APPS))["applicationGroups"]
    def receipt(url,data):
        return {"url":url,"status":"FETCHED","sha256":hashlib.sha256(data).hexdigest(),
        "bytes":len(data),"contentType":"text/html",
        "rawArtifact":hashlib.sha256(url.encode()).hexdigest()+".body"}
    inputs=[
      (SEC_URL,sec("1d077bdb"),sec("2ac7b634")),
      (PH_URL,b"<html><script>var edge=1</script><main>Clinical endpoint stated</main></html>",
         b"<html><script>var edge=2</script><main>Clinical endpoint stated</main></html>")
    ]
    for url,o,n in inputs:
        name=hashlib.sha256(url.encode()).hexdigest()+".body"
        (old/name).write_bytes(o);(new/name).write_bytes(n)
    docs=[]
    for which in (0,1):
        rows=[]
        for i,g in enumerate(groups):
            url,o,n=inputs[0 if i<2 else 1]
            data=o if which==0 else n
            rows.append({"cycleId":g["cycleId"],"applicationSource":receipt(url,data),
             "alternateOfficialSecSource":None,"additionalOfficialFdaSources":[]})
        docs.append({"schema":"MAIN_FOCUS_PUBLIC_SOURCE_RECAPTURE_R40",
            "trialRoster":29,"provisionalApplicationGroups":23,
            "modelTrainingAuthorized":False,"noClinicalOrProductionWrites":True,
            "applicationGroups":rows})
    return docs[0],docs[1],old,new

def test_raw_sec_injection_is_not_medically_material_and_shared_url_is_once(tmp_path):
    before,after,o,n=fixture(tmp_path)
    report=compare(before,after,o,n,"123456")
    assert report["classifiedSourceUrls"]==2
    assert report["differenceClasses"]["SEC_AKAMAI_SCRIPT_AND_PIXEL_ONLY_FILING_MARKUP_IDENTICAL"]==1
    assert report["differenceClasses"]["SCRIPT_BYTES_CHANGED_NON_SCRIPT_HTML_IDENTICAL_REVIEW_REQUIRED"]==1
    assert report["scientificMaterialityVerified"]==0
    assert report["newValidatedFdaOutcomePredictions"]==0
    assert report["numericalAccuracy"] is None
    sec_row=next(r for r in report["sourceComparisons"] if r["url"]==SEC_URL)
    assert len(sec_row["affectedApplicationResearchIds"])==2
    assert sec_row["originalFilingMarkupUnchangedAfterNarrowSECInjectionRemoval"] is True
    assert sec_row["materialScientificImpactIndependentlyAdjudicated"] is False
    pharma_row=next(r for r in report["sourceComparisons"] if r["url"]==PH_URL)
    assert pharma_row["wholeNonScriptMarkupUnchanged"] is True
    assert pharma_row["originalFilingMarkupUnchangedAfterNarrowSECInjectionRemoval"] is False

def test_actual_non_script_source_edit_remains_review_not_dismissed(tmp_path):
    before,after,o,n=fixture(tmp_path)
    src=after["applicationGroups"][2]["applicationSource"]
    name=src["rawArtifact"];updated=(n/name).read_bytes().replace(b"Clinical endpoint stated",b"Different endpoint reported")
    (n/name).write_bytes(updated)
    src["sha256"]=hashlib.sha256(updated).hexdigest()
    src["bytes"]=len(updated)
    for row in after["applicationGroups"][3:]:row["applicationSource"]=deepcopy(src)
    r=compare(before,after,o,n,"123456")
    changed=next(x for x in r["sourceComparisons"] if x["url"]==PH_URL)
    assert changed["differenceClassification"]=="NON_SCRIPT_OR_OTHER_ORIGINAL_HTML_BYTES_CHANGED_REVIEW_REQUIRED"
    assert changed["materialScientificImpactIndependentlyAdjudicated"] is False

def test_markup_changed_but_html_text_nodes_same_remains_review_required(tmp_path):
    before,after,o,n=fixture(tmp_path)
    src=after["applicationGroups"][2]["applicationSource"]
    name=src["rawArtifact"]
    original=(n/name).read_bytes()
    newer=original.replace(b"<main>Clinical endpoint stated</main>",
                           b'<main data-runtime="2026-11-09">Clinical endpoint stated</main>')
    assert newer!=original
    (n/name).write_bytes(newer)
    src["sha256"]=hashlib.sha256(newer).hexdigest()
    src["bytes"]=len(newer)
    for row in after["applicationGroups"][3:]:
        row["applicationSource"]=deepcopy(src)
    outcome=compare(before,after,o,n,"123456")
    item=next(x for x in outcome["sourceComparisons"] if x["url"]==PH_URL)
    assert item["differenceClassification"]=="HTML_TEXT_NODES_IDENTICAL_OTHER_MARKUP_CHANGED_REVIEW_REQUIRED"
    assert item["htmlTextNodesUnchangedOtherMarkupReviewRequired"] is True
    assert item["materialScientificImpactIndependentlyAdjudicated"] is False
    assert outcome["newValidatedFdaOutcomePredictions"]==0

def test_tampered_raw_sha_archive_cannot_be_classified(tmp_path):
    before,after,o,n=fixture(tmp_path)
    sec_url=after["applicationGroups"][0]["applicationSource"]
    (n/sec_url["rawArtifact"]).write_bytes(b"<html>spoofed</html>")
    with pytest.raises(ValueError,match="INTEGRITY_FAILED"):
        compare(before,after,o,n,"123456")

def test_missing_old_source_archive_does_not_silently_create_history(tmp_path):
    before,after,o,n=fixture(tmp_path)
    with pytest.raises(ValueError,match="PREVIOUS_RAW_SOURCE_ARCHIVE_REQUIRED"):
        compare(before,after,None,n,"123456")
    r=compare(None,after,None,n,"123456")
    assert r["hasOriginalPreviousCapture"] is False
    assert r["differenceClasses"]=={"SOURCE_URL_ADDED_OR_REMOVED_REVIEW_REQUIRED":2}

@pytest.mark.parametrize("mutation",[
 lambda x:x.update(modelTrainingAuthorized=True),
 lambda x:x.update(provisionalApplicationGroups=22),
 lambda x:x["applicationGroups"].pop(),
 lambda x:x["applicationGroups"][0].update(cycleId="fabricated-identity"),
 lambda x:x["applicationGroups"][0]["applicationSource"].update(url="https://evil.example/file.html"),
 lambda x:x["applicationGroups"][0]["applicationSource"].update(rawArtifact="../../steal.body"),
 lambda x:x["applicationGroups"][0]["applicationSource"].update(sha256="0"*64),
])
def test_source_roster_and_archive_integrity_tamper_fails_closed(tmp_path,mutation):
    before,after,o,n=fixture(tmp_path)
    mutation(after)
    with pytest.raises(ValueError):compare(before,after,o,n,"123456")
