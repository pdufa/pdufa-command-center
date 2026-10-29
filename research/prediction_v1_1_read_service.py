"""Research-only authenticated read service contract.

The caller must supply a ResearchPrincipal created by future trusted server
middleware. This does not expose an HTTP endpoint or authenticate credentials.
"""
from research.prediction_v1_1_authorization import authorize_research_read
from research.prediction_v1_1_evidence_projection import program_evidence_summary
from research.prediction_v1_1_audit_ledger import audit_chain
from research.prediction_v1_1_review_workflow import audit_review_chain
from research.prediction_v1_1_integrity_gate import audit_all_research_chains

def read_program_evidence(conn, catalog, principal, program_id):
    """Authorize before any program data access; reject compromised audit chains."""
    authorize_research_read(principal, program_id)
    if not audit_all_research_chains(conn)["valid"]:
        raise RuntimeError("Research audit integrity failed")
    result = program_evidence_summary(conn, catalog, program_id)
    if result["integrity"] != "CHECKED_LOCAL_CHAIN_ONLY":
        raise RuntimeError("Research evidence integrity not established")
    return result
