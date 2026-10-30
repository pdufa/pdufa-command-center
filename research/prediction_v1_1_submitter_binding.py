"""Server-owned submitter identity binding for research evidence events.

The binding must be written by trusted service middleware after authentication.
No submission payload reviewer_id or submitter_id is trusted for this purpose.
"""
from research.prediction_v1_1_authorization import ResearchPrincipal

BINDING_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_submitter_bindings (
 evidence_event_id INTEGER PRIMARY KEY REFERENCES evidence_events(event_id),
 submitter_principal TEXT NOT NULL,
 program_id TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS evidence_submitter_bindings_no_update
BEFORE UPDATE ON evidence_submitter_bindings BEGIN SELECT RAISE(ABORT,'append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_submitter_bindings_no_delete
BEFORE DELETE ON evidence_submitter_bindings BEGIN SELECT RAISE(ABORT,'append-only'); END;
"""

def initialize_submitter_bindings(conn):
    conn.executescript(BINDING_SCHEMA)

def bind_verified_submitter(conn, evidence_event_id, principal):
    """Internal-only contract. Never call with user-supplied identity objects."""
    if not isinstance(principal, ResearchPrincipal) or not principal.is_authenticated or not principal.principal.strip():
        raise PermissionError("Trusted authenticated submitter required")
    if "evidence_submitter" not in principal.roles:
        raise PermissionError("Submitter role required")
    row=conn.execute("SELECT program_id,event_kind FROM evidence_events WHERE event_id=?",(evidence_event_id,)).fetchone()
    if not row or row[1]!="RECEIVED_UNVERIFIED" or row[0] not in principal.program_ids:
        raise PermissionError("Accepted evidence and program grant required")
    with conn:
        conn.execute("INSERT INTO evidence_submitter_bindings(evidence_event_id,submitter_principal,program_id) VALUES(?,?,?)",
                     (evidence_event_id,principal.principal,row[0]))

def authorize_independent_review(conn, evidence_event_id, reviewer):
    """Block all reviews without an immutable server-owned submitter binding."""
    if not isinstance(reviewer, ResearchPrincipal) or not reviewer.is_authenticated or not reviewer.principal.strip():
        raise PermissionError("Trusted reviewer required")
    if "evidence_reviewer" not in reviewer.roles:
        raise PermissionError("Reviewer role required")
    row=conn.execute("SELECT submitter_principal,program_id FROM evidence_submitter_bindings WHERE evidence_event_id=?",
                     (evidence_event_id,)).fetchone()
    if not row:
        raise PermissionError("Verified submitter binding missing")
    if row[1] not in reviewer.program_ids or row[0]==reviewer.principal:
        raise PermissionError("Cross-program or self-review denied")
    return True
