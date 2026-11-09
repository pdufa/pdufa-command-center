#!/usr/bin/env python3
"""R50 compare exact archived public source bodies, not just changing raw hashes.

A known SEC Akamai script + tracking pixel can vary per HTTP response without
modifying a filing's remaining original HTML bytes. A non-SEC page can change
only its script bytes without changing non-script markup; unlike the narrowly
matched SEC case this still requires manual embedded-data review. Neither case
certifies clinical correctness, original first-public date, CMC or FDA outcomes.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from collections import defaultdict,Counter
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from scripts.refresh_focus_public_sources_r40 import (
    ALLOWED_HOSTS,ROSTER,APPS,_read_json,build_manifest
)

SEC_SCRIPT=re.compile(
    rb'<script\s*>bazadebezolkohpepadr="[0-9]+"</script>'
    rb'<script type="text/javascript" src="https://www\.sec\.gov/akam/[A-Za-z0-9/]+"\s+defer></script>',
    re.I
)
SEC_PIXEL=re.compile(
    rb'<noscript><img src="https://www\.sec\.gov/akam/13/pixel_[a-f0-9]{8}\?a=[A-Za-z0-9+/=]+"'
    rb' style="visibility: hidden; position: absolute; left: -999px; top: -999px;"\s*/></noscript>',
    re.I
)
HTML_SCRIPT=re.compile(rb"<script\b[^>]*>.*?</script\s*>",re.I|re.S)
HEX=re.compile(r"[0-9a-f]{64}\Z")
MAX_FILE=50_000_000

class _NonScriptTextNodes(HTMLParser):
    # Text-node comparison is a research signal only; HTML attributes, metadata,
    # data-* links, structured results and script-generated pages are not proved
    # equivalent by this extractor.
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_noncontent=0
        self.nodes=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","svg"):self.in_noncontent+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg"):
            self.in_noncontent=max(0,self.in_noncontent-1)
    def handle_data(self,text):
        if self.in_noncontent==0:
            value=" ".join(text.split())
            if value:self.nodes.append(value)

def _text_nodes_digest(raw:bytes)->str|None:
    # Large filings need source-by-source review; do not silently fast-match.
    if len(raw)>6_000_000:return None
    parser=_NonScriptTextNodes()
    try:parser.feed(raw.decode("utf-8","replace"))
    except (ValueError,AssertionError,UnicodeError):return None
    return hashlib.sha256(" ".join(parser.nodes).encode()).hexdigest()

def _parent_ids():
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    if len(manifest["applicationGroups"])!=23 or manifest["trialCount"]!=29:
        raise ValueError("CANONICAL_FOCUS_APPLICATION_ROSTER_CHANGED")
    return {g["cycleId"] for g in manifest["applicationGroups"]}

def _url(source):
    if not isinstance(source,dict) or not isinstance(source.get("url"),str):
        raise ValueError("SOURCE_URL_NOT_A_KNOWN_STRING")
    value=source["url"]
    try: p=urlsplit(value)
    except ValueError:raise ValueError("INVALID_ORIGINAL_PUBLIC_SOURCE_URL")
    if (p.scheme!="https" or p.hostname not in ALLOWED_HOSTS or
        p.username or p.password or p.port not in (None,443) or
        not p.path.strip("/") or p.fragment or len(value)>2048):
        raise ValueError("UNTRUSTED_ORIGINAL_SOURCE_HOST_OR_URL")
    return value

def index(capture:dict,allowed_ids:set[str]):
    if (not isinstance(capture,dict) or
        capture.get("schema")!="MAIN_FOCUS_PUBLIC_SOURCE_RECAPTURE_R40" or
        capture.get("trialRoster")!=29 or
        capture.get("provisionalApplicationGroups")!=23 or
        capture.get("noClinicalOrProductionWrites") is not True or
        capture.get("modelTrainingAuthorized") is not False):
        raise ValueError("FOCUS_CAPTURE_NOT_RESEARCH_ONLY_ORIGINAL_ROSTER")
    groups=capture.get("applicationGroups")
    if not isinstance(groups,list) or len(groups)!=23 or {
        g.get("cycleId") for g in groups if isinstance(g,dict)
    }!=allowed_ids:
        raise ValueError("EXACT_APPLICATION_MEMBERSHIP_NOT_PRESERVED")
    indexed={}
    refs=defaultdict(set)
    for group in groups:
        cid=group["cycleId"]
        sources=[group.get("applicationSource"),group.get("alternateOfficialSecSource")]
        additional=group.get("additionalOfficialFdaSources",[])
        if not isinstance(additional,list):raise ValueError("INVALID_FDA_SOURCE_ADDENDA")
        sources.extend(additional)
        for item in sources:
            if item is None:continue
            url=_url(item)
            if url in indexed and indexed[url]!=item:
                raise ValueError("CONFLICTING_ORIGINAL_SAME_URL_RECEIPT")
            indexed[url]=item
            refs[url].add(cid)
    if not indexed:raise ValueError("NO_ORIGINAL_APPLICATION_SOURCE_CAPTURE")
    return indexed,refs

def _read_verified_source(root:Path,source:dict)->bytes|None:
    if source.get("status")!="FETCHED":
        return None
    raw_name=source.get("rawArtifact")
    url=source["url"]
    required=hashlib.sha256(url.encode()).hexdigest()+".body"
    if raw_name!=required or not HEX.fullmatch(source.get("sha256","")):
        raise ValueError("ORIGINAL_SOURCE_ARTIFACT_OR_SHA_MISMATCH")
    if (not root.is_dir() or root.is_symlink() or
        root.resolve()==Path("/") or
        not isinstance(raw_name,str)):
        raise ValueError("INVALID_ARCHIVED_SOURCE_DIRECTORY")
    path=root/raw_name
    if (not path.is_file() or path.is_symlink() or
        not path.resolve().is_relative_to(root.resolve()) or
        path.stat().st_size>MAX_FILE):
        raise ValueError("ARCHIVED_RAW_SOURCE_BYTES_MISSING_OR_UNSAFE")
    data=path.read_bytes()
    if (len(data)!=source.get("bytes") or
        hashlib.sha256(data).hexdigest()!=source["sha256"]):
        raise ValueError("ORIGINAL_PUBLIC_SOURCE_BYTE_INTEGRITY_FAILED")
    return data

def _kind(url:str,a:dict,b:dict,x:bytes|None,y:bytes|None):
    if a.get("status")!="FETCHED" or b.get("status")!="FETCHED":
        return "SOURCE_ACCESS_OR_AVAILABILITY_CHANGED_NOT_CONTENT_VERIFIED"
    if x is None or y is None:
        raise ValueError("RAW_FETCHED_BODY_REQUIRED")
    if x==y:return "RAW_SOURCE_BYTES_UNCHANGED"
    if (a.get("contentType")!="text/html" or b.get("contentType")!="text/html"):
        return "NON_HTML_ORIGINAL_CONTENT_BYTES_CHANGED_REVIEW_REQUIRED"
    host=urlsplit(url).hostname
    if host=="www.sec.gov":
        if (len(SEC_SCRIPT.findall(x))==len(SEC_SCRIPT.findall(y))==1 and
            len(SEC_PIXEL.findall(x))==len(SEC_PIXEL.findall(y))==1):
            old=SEC_PIXEL.sub(b"",SEC_SCRIPT.sub(b"",x))
            new=SEC_PIXEL.sub(b"",SEC_SCRIPT.sub(b"",y))
            if old==new:
                return "SEC_AKAMAI_SCRIPT_AND_PIXEL_ONLY_FILING_MARKUP_IDENTICAL"
    old_without=HTML_SCRIPT.sub(b"",x)
    new_without=HTML_SCRIPT.sub(b"",y)
    if (old_without==new_without and old_without!=x and new_without!=y):
        return "SCRIPT_BYTES_CHANGED_NON_SCRIPT_HTML_IDENTICAL_REVIEW_REQUIRED"
    old_text=_text_nodes_digest(x)
    new_text=_text_nodes_digest(y)
    if old_text is not None and old_text==new_text:
        return "HTML_TEXT_NODES_IDENTICAL_OTHER_MARKUP_CHANGED_REVIEW_REQUIRED"
    return "NON_SCRIPT_OR_OTHER_ORIGINAL_HTML_BYTES_CHANGED_REVIEW_REQUIRED"

def compare(previous:dict|None,current:dict,previous_root:Path|None,
            current_root:Path,run_id:str):
    if not isinstance(run_id,str) or not run_id.isdigit():
        raise ValueError("REAL_WORKFLOW_RUN_REQUIRED")
    allowed=_parent_ids()
    cur,cur_refs=index(current,allowed)
    if previous is not None:
        prev,prev_refs=index(previous,allowed)
        if previous_root is None:raise ValueError("PREVIOUS_RAW_SOURCE_ARCHIVE_REQUIRED")
    else:prev,prev_refs={},{}
    output=[];classes=Counter()
    for url in sorted(set(prev)|set(cur)):
        old=prev.get(url)
        new=cur.get(url)
        original_data=_read_verified_source(previous_root,old) if old is not None else None
        current_data=_read_verified_source(current_root,new) if new is not None else None
        if old is None or new is None:
            status="SOURCE_URL_ADDED_OR_REMOVED_REVIEW_REQUIRED"
        elif old.get("sha256")==new.get("sha256") and old.get("status")==new.get("status"):
            status="RAW_SOURCE_BYTES_UNCHANGED"
        else:
            status=_kind(url,old,new,original_data,current_data)
        classes[status]+=1
        output.append({
          "url":url,
          "affectedApplicationResearchIds":sorted(prev_refs.get(url,set())|cur_refs.get(url,set())),
          "priorSha256":old.get("sha256") if old else None,
          "currentSha256":new.get("sha256") if new else None,
          "priorStatus":old.get("status") if old else None,
          "currentStatus":new.get("status") if new else None,
          "differenceClassification":status,
          "originalFilingMarkupUnchangedAfterNarrowSECInjectionRemoval":
            status=="SEC_AKAMAI_SCRIPT_AND_PIXEL_ONLY_FILING_MARKUP_IDENTICAL",
          "wholeNonScriptMarkupUnchanged":
            status in ("SEC_AKAMAI_SCRIPT_AND_PIXEL_ONLY_FILING_MARKUP_IDENTICAL",
              "SCRIPT_BYTES_CHANGED_NON_SCRIPT_HTML_IDENTICAL_REVIEW_REQUIRED"),
          "htmlTextNodesUnchangedOtherMarkupReviewRequired":
            status=="HTML_TEXT_NODES_IDENTICAL_OTHER_MARKUP_CHANGED_REVIEW_REQUIRED",
          "materialScientificImpactIndependentlyAdjudicated":False,
          "automatedPredictionChangeAuthorized":False
        })
    return {
      "schema":"MAIN_R50_ORIGINAL_APPLICATION_BODY_COMPARISON",
      "runId":run_id,"capturedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "exactFocusTrialCount":29,"applicationCycleCount":23,
      "hasOriginalPreviousCapture":previous is not None,
      "previousApplicationSourceUrls":len(prev),
      "currentApplicationSourceUrls":len(cur),
      "classifiedSourceUrls":len(output),
      "differenceClasses":dict(sorted(classes.items())),
      "sourceComparisons":output,
      "affectedApplicationResearchIds":sorted({
        cid for row in output if row["differenceClassification"]!="RAW_SOURCE_BYTES_UNCHANGED"
        for cid in row["affectedApplicationResearchIds"]
      }),
      "scientificMaterialityVerified":0,"newValidatedFdaOutcomePredictions":0,
      "historicalFdaBacktestsCompleted":0,"numericalAccuracy":None,
      "sourceReviewOnly":True,
      "sourceBodiesNotRewritten":True,
      "modelTrainingAuthorized":False,"productionWriteAuthorized":False,
      "predictionWriteAuthorized":False,
      "caution":"An Akamai response injection or page script variation is not a verified clinical development. Other source changes require original-text review. This is not source first-publication proof or independent scientific adjudication."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--current",required=True,type=Path)
    p.add_argument("--current-source-dir",required=True,type=Path)
    p.add_argument("--previous",type=Path)
    p.add_argument("--previous-source-dir",type=Path)
    p.add_argument("--run-id",required=True)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("WRITE_ONCE_RESEARCH_COMPARISON_REQUIRED")
    if (a.previous is None)!=(a.previous_source_dir is None):
        raise ValueError("PREVIOUS_SOURCE_RECEIPT_AND_ORIGINAL_BYTES_MUST_BOTH_EXIST")
    def load(path):
        if (not path.is_file() or path.is_symlink() or path.stat().st_size>10_000_000):
            raise ValueError("UNSAFE_ORIGINAL_CAPTURE_RECEIPT")
        return json.loads(path.read_bytes())
    out=compare(load(a.previous) if a.previous else None,load(a.current),
      a.previous_source_dir,a.current_source_dir,a.run_id)
    a.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:out[k] for k in (
      "exactFocusTrialCount","applicationCycleCount","hasOriginalPreviousCapture",
      "classifiedSourceUrls","differenceClasses","scientificMaterialityVerified",
      "newValidatedFdaOutcomePredictions"
    )},sort_keys=True),flush=True)
if __name__=="__main__":main()
