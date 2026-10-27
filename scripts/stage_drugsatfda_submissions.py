"""Stage FDA Drugs@FDA submissions from the official downloadable ZIP.

This produces candidate rows only. Submission status is not a PASS/FAIL label.
"""
import argparse
import csv
import io
import json
import zipfile
from collections import Counter
from pathlib import Path


def read_table(zf, basename):
    paths = [n for n in zf.namelist() if Path(n).name.lower() == basename.lower()]
    if len(paths) != 1:
        raise ValueError("missing or ambiguous FDA table: " + basename)
    info = zf.getinfo(paths[0])
    if info.file_size > 100_000_000:
        raise ValueError("FDA table exceeds safe size limit: " + basename)
    with zf.open(paths[0]) as handle:
        return list(csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig"), delimiter="\t"))


def stage(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        if len(zf.infolist()) > 100:
            raise ValueError("unexpectedly large FDA archive file count")
        submissions = read_table(zf, "Submissions.txt")
        documents = read_table(zf, "ApplicationDocs.txt")
        actions = read_table(zf, "Join_Submission_ActionType_Lookup.txt")
        action_names = read_table(zf, "ActionTypes_Lookup.txt")
    action_lookup = {r.get("ActionTypes_LookupID"): r.get("ActionTypes_LookupDescription")
                     for r in action_names}
    action_by_submission = {}
    for row in actions:
        key = tuple((row.get(field) or "").strip() for field in ("ApplNo", "SubmissionType", "SubmissionNo"))
        action_by_submission.setdefault(key, []).append(action_lookup.get(row.get("ActionTypes_LookupID")))
    docs = {}
    for row in documents:
        key = tuple((row.get(field) or "").strip() for field in ("ApplNo", "SubmissionType", "SubmissionNo"))
        docs.setdefault(key, []).append({
            "title": row.get("ApplicationDocsTitle"),
            "url": row.get("ApplicationDocsURL"),
            "date": row.get("ApplicationDocsDate"),
        })
    candidates = []
    for row in submissions:
        key = tuple((row.get(field) or "").strip() for field in ("ApplNo", "SubmissionType", "SubmissionNo"))
        candidates.append({
            "application_id": key[0],
            "submission_type": key[1],
            "submission_number": key[2],
            "submission_status_code": row.get("SubmissionStatus"),
            "submission_status_date": row.get("SubmissionStatusDate"),
            "source_documents": docs.get(key, []),
            "action_descriptions": action_by_submission.get(key, []),
            "independently_verified": False,
            "model_eligible": False,
        })
    return {
        "source": "Drugs@FDA official data-file ZIP",
        "candidate_count": len(candidates),
        "with_source_documents": sum(bool(r["source_documents"]) for r in candidates),
        "without_source_documents": sum(not r["source_documents"] for r in candidates),
        "with_action_descriptions": sum(bool(r["action_descriptions"]) for r in candidates),
        "status_code_counts": dict(sorted(Counter(x["submission_status_code"] for x in candidates).items())),
        "candidates": candidates,
        "warning": "Submission status codes and document links are not independently verified FDA PASS/FAIL outcomes.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--summary-only", action="store_true", help="Emit counts without full candidate list")
    args = p.parse_args()
    report = stage(args.zip)
    if args.summary_only:
        report.pop("candidates")
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
