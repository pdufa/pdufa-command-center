#!/usr/bin/env python3
"""Capture a bounded, exact-NCT, public-source POOL snapshot for fast TOOLS reads.
The generated file contains only the same public clinical-study metadata used
by the protected dashboard: no session cookie, token, user data or bank data.
Never publish an unverified or stale source inventory.
"""
import csv
import datetime as dt
import gzip
import hashlib
import http.cookiejar
import io
import json
import os
from pathlib import Path
import re
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
BASE="https://pdufa-new-dashboard.vercel.app"
TARGET=ROOT/"new-platform/frontend/data/tools-pool-snapshot.json"
password=os.environ.get("DASHBOARD_PASSWORD")
if not password:
    raise SystemExit("BLOCKED: DASHBOARD_PASSWORD GitHub Action secret not configured")

cookiejar=http.cookiejar.CookieJar()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))
def request(path,post=None):
    headers={"Accept":"application/json","Accept-Encoding":"gzip",
             "User-Agent":"pdufa-verified-tools-static-snapshot/1"}
    body=None
    method="GET"
    if post is not None:
        method="POST"
        body=json.dumps(post).encode()
        headers.update({"Origin":BASE,"Content-Type":"application/json"})
    req=urllib.request.Request(BASE+path,method=method,data=body,headers=headers)
    with opener.open(req,timeout=90) as response:
        data=response.read(45_000_001)
        if len(data)>45_000_000:raise ValueError("Workspace snapshot size exceeds bound")
        if response.headers.get("Content-Encoding","").lower()=="gzip":
            data=gzip.decompress(data)
        return json.loads(data)

if request("/api/auth",{"password":password})!={"authenticated":True}:
    raise ValueError("Authentication refused by production dashboard")
if request("/api/auth")!={"authenticated":True}:
    raise ValueError("Login cookie failed verification")
raw=request("/api/workspace")
rows=raw.get("pipeline")
health=raw.get("sourceHealth") or {}
if not isinstance(rows,list) or not rows or health.get("state")=="STALE":
    raise ValueError("Cannot publish missing or stale source data")
parity=health.get("pipelineSourceParity") or health.get("streamlitPipelineParity") or {}
if parity.get("exactPrograms")!=len(rows):
    raise ValueError("Published workspace source parity mismatch")
if not isinstance(health.get("clinicalRows"),int) or not isinstance(health.get("regulatoryRows"),int):
    raise ValueError("Missing audited NCT and regulatory record counts")
if health["clinicalRows"]+health["regulatoryRows"]!=len(rows):
    raise ValueError("Clinical and regulatory source counts mismatch")
ids=[r.get("id") for r in rows]
if any(not isinstance(x,str) for x in ids) or len(ids)!=len(set(ids)):
    raise ValueError("Source row identifiers invalid or duplicated")
ncts={x.split("|",1)[1] for x in ids if re.fullmatch(r"TRIAL\|NCT\d{8}",x)}
with (ROOT/"data/all_phase_trials.csv").open(encoding="utf-8-sig",newline="") as stream:
    original={r["nct_id"].strip() for r in csv.DictReader(stream)
              if re.fullmatch(r"NCT\d{8}",r.get("nct_id","").strip())}
if ncts!=original:
    raise ValueError(f"Current-source NCT identity drift: {len(ncts)} POOL vs {len(original)} source")
fields=("id","ticker","company","drug","indication","stage")
filtered=[]
for row in rows:
    saved={}
    for field in fields:
        val=row.get(field)
        if val is not None and not isinstance(val,str):
            raise ValueError("Unexpected nontext trial field: "+field)
        saved[field]=val or ""
    filtered.append(saved)
stamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
snapshot={
    "schemaVersion":1,
    "snapshotGeneratedAt":stamp,
    "asOf":raw.get("asOf") or stamp,
    "sourceHealth":{
        "state":health["state"],
        "clinicalRows":health["clinicalRows"],
        "regulatoryRows":health["regulatoryRows"],
        "pipelineSourceParity":{"exactPrograms":len(filtered)}
    },
    "pipeline":filtered
}
TARGET.parent.mkdir(parents=True,exist_ok=True)
payload=json.dumps(snapshot,ensure_ascii=False,separators=(",",":"))+"\n"
# Avoid static asset caches; this is imported only on the server by an
# authenticated API. Reducing row fields avoids exposing unrelated metadata.
TARGET.write_text(payload,encoding="utf-8")
print("PASS: POOL snapshot source parity",len(filtered),"rows,",len(ncts),"NCTs")
print("PASS: exact current-source NCT identity coverage",len(ncts))
print("SOURCE_STATE",health["state"],"SOURCE_AS_OF",snapshot["asOf"])
print("CAPTURED_AT",stamp,"BYTES",len(payload.encode()))
print("NCT_SORTED_SHA256",hashlib.sha256(",".join(sorted(ncts)).encode()).hexdigest())
print("SNAPSHOT_OUTPUT",str(TARGET.relative_to(ROOT)))
