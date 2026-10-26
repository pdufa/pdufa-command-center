# Full 800-point A/B local consistency audit

This is a read-only **browser-local** comparison of two returned reviewer
worksheets generated for the same checksum-verified archived NCT trial.
It is **not** independent clinical or regulatory adjudication.

The trial page now allows choosing two exported full 800-row reviewer CSV files
and comparing candidate claims. The local parser rejects malformed CSV,
partial/duplicated/moved task identities, mismatched NCT IDs, altered
source-requirement mappings, forged VERIFIED/SUBMITTED/COMPLETE markers,
non-catalog decisions, cross-slot worksheets and oversized files.

The report distinguishes:

- One-sided candidate decisions (A or B only), conflicting candidate
  decisions (A disagrees with B), and conflicting claimed document URLs/SHAs.
- Candidate decisions missing a claimed reviewer name, source HTTPS URL,
  64-character SHA-256 digest, dated publication, document section, or notes.
- Claimed reviewer names that are identical across the two worksheets.
- A capped list of the first 25 task keys for conflicting candidate decisions.

Neither a populated name, HTTPS URL, file hash string nor textual signature
establishes reviewer identity, qualification, original source-byte provenance
or signature validity. Both documents are **untrusted claims**. The tool never
downloads external documents or independently checks their bytes. The
reported number of scientifically adjudicated tasks remains **zero** and no
FDA approval probability or scientific grade is generated. All files remain
inside the user browser and are not submitted to the backend.

This 800-task crosscheck is independent of the existing 320-task A/B review,
its local worksheet audit, trial ratings and all GEM/WT FS/FA preset settings.

Next controlled stage (not provided by this utility): independently authenticated
reviewer identity, original-source acquisition and byte verification,
human adjudication of conflicts with signed decisions, calibration of any
approval model and separate production release approval.
