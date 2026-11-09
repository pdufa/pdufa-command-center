#!/usr/bin/env python3
"""R50 PDF source probe for FDA FY2024 *approved applications* review-cycle appendix.

Use this ONLY as postdecision regulator source evidence. Appendix A omits
applications never approved in FY2024; cannot estimate accuracy from it.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from urllib.request import Request,urlopen
import fitz
URL="https://www.fda.gov/media/188188/download?attachment="
MAX_BYTES=45_000_000
def run(directory:Path):
    if not directory.is_dir() or directory.is_symlink():raise ValueError("SAFE_OUTPUT_DIRECTORY_REQUIRED")
    with urlopen(Request(URL,headers={"User-Agent":"PDUFA-Original-FDA-Postdecision-Research/1.0",
                                     "Accept":"application/pdf"}),timeout=60) as r:
        data=r.read(MAX_BYTES+1)
        ctype=r.headers.get("Content-Type","").lower()
        final=r.geturl()
    if not 50000<len(data)<=MAX_BYTES or not data.startswith(b"%PDF") or not final.startswith("https://www.fda.gov/"):
        raise ValueError("UNVERIFIED_ORIGINAL_FDA_REPORT_PDF")
    p=directory/"original_fda_fy2024_pdufa_report.pdf"
    with p.open("xb") as f:f.write(data)
    doc=fitz.open(stream=data,filetype="pdf")
    out={"sourceUrl":URL,"resolvedUrl":final,"bytes":len(data),
         "sha256":hashlib.sha256(data).hexdigest(),"pageCount":len(doc),
         "scope":"APPROVED_FY2024_ONLY_NOT_CONSECUTIVE_ORIGINAL_FILING_COHORT",
         "originalFilingDenominatorIndependentlyVerified":False,
         "independentHistoricalPredictions":0,"calibrationAccuracy":None,
         "modelTrainingAuthorized":False,"samples":[]}
    if len(doc)<92:raise ValueError("FDA_REPORT_APPENDIX_TOO_SHORT")
    for page_i in (82,83,84,87,89):
        page=doc[page_i]
        body=page.get_text("text",sort=True)
        t=page.find_tables()
        tables=[]
        for table in t.tables[:3]:
            rows=table.extract()
            tables.append({"rows":len(rows),"cols":max((len(r) for r in rows),default=0),
                           "firstRows":[r[:9] for r in rows[:4]]})
        out["samples"].append({"pageIndex":page_i,"pageLabel":page_i+1,
            "hasAppendixA":"Appendix A" in body,
            "hasReviewCycle":"Review Cycle" in body,
            "hasCycleResult":"Cycle Result" in body,
            "hasTableA1":"Table A-1" in body,
            "tables":tables,
            "textStart":body[:1800]})
    q=directory/"appendix_pdf_table_shape_probe.json"
    with q.open("xb") as f:f.write((json.dumps(out,indent=2)+"\n").encode())
    print(json.dumps({k:out[k] for k in ("sourceUrl","sha256","bytes","pageCount","samples")},indent=2),flush=True)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    run(args.out)
