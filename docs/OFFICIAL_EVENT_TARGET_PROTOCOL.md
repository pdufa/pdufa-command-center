# First-formal-event FDA target protocol

Status: **NOT READY / ABSTAIN**. This is a SHA-pinned engineering proposal,
not an independently reviewed scientific protocol or a validated model.

`research/evidence/official_event_protocol_v1.json` adds explicit event/horizon
semantics without changing the earlier frozen validation protocol. Its digest
is pinned in `research.official_event_protocol.load_event_protocol`.
Changing scientific assumptions requires a new reviewed version; modifying
the existing JSON fails the integrity check.

## Target and chronology

The proposed target is the **first formal FDA action in an exact application
review cycle, after an explicit prediction cutoff and on or before an explicit
evaluation horizon**. PASS means approval; CRL means an official Complete
Response Letter for that review; EXTENSION means a formal FDA target revision
to a later target. An extension is an event, not a permanent terminal outcome.
Extension followed by approval or CRL remains two dated events in the history.
The target for that window remains the first event, not whichever later event
is easier to source.

This target does not answer eventual-approval probability or predict the final
decision after a known extension. Such a different prediction question requires
a separately prespecified target protocol. Under this proposal, cutoffs after
the first formal action are blocked rather than silently selecting a later
action. An observed late/missed target, administrative delay, withdrawal,
refuse-to-file or unresolved event is not converted into CRL or EXTENSION.
No formal action inside the horizon means unresolved, never inferred failure.

Every call supplies an aware prediction cutoff, horizon and evaluation-as-of
timestamp with `cutoff < horizon <= evaluation_as_of`. There is no default
horizon duration. Actual action and publication timestamps must come from
document provenance. Date-only source claims remain date-only; missing aware
label clocks block target acceptance, including ambiguous horizon boundaries.
Publication must be strictly before evaluation-as-of. The selected action must
be strictly after cutoff and on or before horizon.

## Interface

`prepare_event_target(events, *, program_id, application_id, review_cycle_id,
original_target_date, prediction_cutoff, horizon_at, evaluation_as_of)` returns
the full sorted chronology, the selected first-formal event identifier, any
structurally usable research target candidate, blocking reasons, protocol hash
and local input snapshot hash.

Each event envelope has exactly `event_id`, `application_id`, `review_cycle_id`
and `event`. The inner event reuses the existing scientific historical
comparison event schema: `kind`, `action_date`, `public_available_on`,
`source_url`, `target_date`, `revised_target_date` and `decision_label`.
The label reuses the historical-label provenance gate and must bind the exact
application/cycle/program, outcome and official source URL. Original document
SHA-256 is required but is not proof of origin or independent adjudication.

Unknown original PDUFA target stays null and blocks a target candidate. Claimed
event targets do not fill it. Each extension must reference the current target
and move it later. Broken target chains, same-day competing formal actions,
duplicate event identities and later formal actions after a terminal decision
within the same claimed cycle cannot silently collapse into a valid target.
Inputs from different cycles/applications are rejected rather than mixed.

Every result remains ineligible for training/evaluation with zero independently
verified decisions and unavailable probabilities/performance. Caller verification
flags cannot authorize use. The input digest is local reproducibility metadata,
not a document authenticity, public timestamp or reviewer signature.

## Verification and remaining work

The dedicated suite uses synthetic events and document hashes only. It tests
extension-to-approval and extension-to-CRL histories, strict cutoff/horizon/
publication boundaries, missing dates and original targets, exact identity,
same-day ambiguity, broken target chains and prevention of later-event
substitution. These checks do not establish any actual FDA outcome.

External original documents, publication evidence, exact independently reviewed
cycles and authenticated outcome/scientific adjudication remain necessary.
The cohort boundaries, approved horizon duration, model/calibration and minimum
independent sample remain unresolved scientific parameters. Production scanners,
authentication, FS/FA associations, trading, merges and deployments are unchanged.
