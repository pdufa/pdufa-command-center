"""Research-only binding consistency audit; not external integrity anchoring."""
from research.prediction_v1_1_audit_ledger import audit_chain
from research.prediction_v1_1_review_workflow import audit_review_chain

def audit_submitter_bindings(conn):
    rows=conn.execute("""SELECT b.evidence_event_id,b.submitter_principal,b.program_id,
          e.program_id,e.event_kind
          FROM evidence_submitter_bindings b
          LEFT JOIN evidence_events e ON e.event_id=b.evidence_event_id""").fetchall()
    for event_id,principal,bound_program,event_program,kind in rows:
        if not principal or not principal.strip() or event_program is None or bound_program!=event_program or kind!="RECEIVED_UNVERIFIED":
            return {"valid":False,"checked":len(rows),"reason":"invalid submitter binding"}
    unbound=conn.execute("""SELECT COUNT(*) FROM review_events r
       LEFT JOIN evidence_submitter_bindings b ON b.evidence_event_id=r.evidence_event_id
       WHERE b.evidence_event_id IS NULL OR b.submitter_principal=r.reviewer_principal""").fetchone()[0]
    if unbound:
        return {"valid":False,"checked":len(rows),"reason":"unbound or self-reviewed evidence"}
    return {"valid":True,"checked":len(rows),"externally_anchored":False}

def audit_all_research_chains(conn):
    evidence=audit_chain(conn)
    reviews=audit_review_chain(conn)
    bindings=audit_submitter_bindings(conn)
    return {"valid":all(x["valid"] for x in (evidence,reviews,bindings)),
            "evidence":evidence,"reviews":reviews,"bindings":bindings,
            "externally_anchored":False}
