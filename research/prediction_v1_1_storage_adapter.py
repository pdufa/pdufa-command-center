"""Research-only SQLite storage contract; no production database binding.

The current deployment uses PostgreSQL. This adapter deliberately refuses
non-SQLite DSNs and must not be mounted into the production service.
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from research.prediction_v1_1_audit_ledger import connect_ledger, audit_chain
from research.prediction_v1_1_review_workflow import initialize_review_ledger, audit_review_chain
from research.prediction_v1_1_submitter_binding import initialize_submitter_bindings
from research.prediction_v1_1_integrity_gate import audit_all_research_chains


def open_research_evidence_store(path: str | Path | None = None):
    """Require explicit local path, avoid silently creating an ephemeral store."""
    if path is None:
        path = os.getenv("PDUFA_V11_RESEARCH_SQLITE_PATH")
    if not isinstance(path, (str, Path)) or not str(path).strip() or str(path) == ":memory:":
        raise RuntimeError("Persistent research SQLite path not configured")
    resolved = Path(path).expanduser().resolve()
    if resolved.suffix not in (".sqlite3", ".db"):
        raise ValueError("Research evidence store must be an explicit SQLite file")
    if not resolved.parent.is_dir():
        raise FileNotFoundError("Research evidence storage directory missing")
    conn = connect_ledger(resolved)
    initialize_review_ledger(conn)
    initialize_submitter_bindings(conn)
    integrity = audit_all_research_chains(conn)
    if not integrity["valid"]:
        conn.close()
        raise RuntimeError("Research evidence audit integrity failed")
    return conn


def store_health(conn: sqlite3.Connection):
    """Read-only health status; local chains are not externally anchored."""
    integrity = audit_all_research_chains(conn)
    return {"healthy": integrity["valid"],
            "evidence_events": integrity["evidence"]["checked"], "review_events": integrity["reviews"]["checked"],
            "submitter_bindings": integrity["bindings"]["checked"],
            "externally_anchored": False, "production_connected": False}
