# Owner-only live-access handoff

The active owner-only policy applies. **No outside reviewer, attestor, challenger, medical credential or A01–A14 signoff is needed for owner research.** Those former requirements are inactive. An owner may review the new ORCA-2 dossier now without external verification; its status remains OWNER_NOT_REVIEWED until the owner records a decision.

Repository audit: the existing Next.js login uses `DASHBOARD_PASSWORD` and an HMAC-signed seven-day cookie (`lib/auth.ts`, `app/api/auth/route.ts`). It does not bind a session to an individual owner subject or prove MFA. Reuse its access-protection pattern where compatible, but do not claim it already satisfies the owner/MFA contract or activate the retired multi-person harness. The root sign-in is a client-side landing-page gate; `proxy.ts` handles retired routes and does not enforce authentication globally. A private dossier route therefore needs explicit server-side protection. No secret values were inspected.

What separates local research readiness from live access:

| Operational item | Concrete information/action needed | Free option | Paid option |
|---|---|---|---|
| Owner login | Identify the existing individual owner account/provider and MFA/recovery method to reuse; supply public issuer/audience/configuration references, not secrets in Git | Local authenticated development; provider developer tier if suitable | Existing approved identity service plan; confirm current terms |
| Destination | Name an existing approved private preview/research destination and administrator, or explicitly approve a new one | Localhost/private development preview | Approved existing hosting or separately approved isolated service |
| Persistence/access | Confirm which existing restricted storage, credentials/secret references, immutable revisions and backup policy this destination uses | Private local research files for read-only inspection | Approved isolated database/storage; no production migration implied |
| Browser acceptance | Implement/qualify the actual owner sign-in and access checks against the chosen provider/origin; prevent unauthenticated access and preserve unreviewed labels | Local disposable acceptance tests | Protected private preview acceptance |
| Release | Explicitly authorize deployment of a specific commit/configuration after access and rollback checks | Stay local | Approved destination; costs require separate authorization |

No resources were provisioned, no identity was minted, no source signed and no deployment performed. The existing synthetic multi-person staging harness is retained as inactive history, not reused as the owner's live workflow. A provider name or filled configuration alone does not establish working owner authentication. Existing production credentials, scan schedules and Levels 7–20 implementation are outside this change.

The next engineering action is to connect the current owner research screen to the **chosen existing owner authentication and private destination**, then test sign-in, denied access, source/cutoff display, owner status and versioned revision storage. Destination/provider details must be real; external medical review is not a prerequisite. Owner research and evidence collection can continue while those operational choices are resolved.

ORCA-2 source questions remain factual uncertainties, not outside-human gates: earlier protocol/SAP versions, SAP v3/v4 reference mismatch, embedded March 29 signing claim, actual database lock/unblinding and paper multiplicity citation. The owner can accept limitations or request more evidence; the software does not invent those decisions.
